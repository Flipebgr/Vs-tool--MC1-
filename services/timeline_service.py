"""
Serviço temporal da Sprint 3.

Carrega o Parquet processado uma única vez e oferece operações leves para a
Timeline, o filtro temporal do grafo e, posteriormente, a reconstrução de
cadeias de eventos.
"""

from __future__ import annotations

import json
from functools import lru_cache
from collections.abc import Iterable
from typing import Optional

import pandas as pd

import config

EVENT_COLUMNS = [
    "id",
    "short_name",
    "event_time_utc",
    "parties_canonical",
    "parties_types",
    "details",
    "time_source",
]

INDIVIDUAL_MAX_SPAN = pd.Timedelta(hours=6)
INDIVIDUAL_MAX_EVENTS = 1200


@lru_cache(maxsize=1)
def load_events() -> pd.DataFrame:
    """Carrega e ordena os eventos processados, mantendo-os em memória."""
    if not config.EVENTS_PARQUET.exists():
        raise FileNotFoundError(
            f"{config.EVENTS_PARQUET} não encontrado. Rode `python -m services.etl` "
            "antes de iniciar o app."
        )

    df = pd.read_parquet(config.EVENTS_PARQUET, columns=EVENT_COLUMNS)
    df["event_time_utc"] = pd.to_datetime(df["event_time_utc"], utc=True)
    df.sort_values("event_time_utc", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df



def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if hasattr(value, "tolist"):
        converted = value.tolist()
        return converted if isinstance(converted, list) else [converted]
    return [value]


def _to_utc(value) -> pd.Timestamp:
    """Converte strings/timestamps do Plotly para Timestamp UTC."""
    return pd.to_datetime(value, utc=True)


@lru_cache(maxsize=1)
def get_time_bounds() -> tuple[pd.Timestamp, pd.Timestamp]:
    """Retorna o primeiro e o último timestamp disponíveis."""
    df = load_events()
    return df["event_time_utc"].iloc[0], df["event_time_utc"].iloc[-1]


def get_full_range_store() -> dict:
    """Estado inicial usado por `time-range-store`."""
    start, end = get_time_bounds()
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "is_full_range": True,
    }


def normalize_window(start=None, end=None) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Normaliza e limita uma janela aos limites reais do dataset."""
    min_time, max_time = get_time_bounds()
    start_ts = _to_utc(start) if start is not None else min_time
    end_ts = _to_utc(end) if end is not None else max_time

    if start_ts > end_ts:
        start_ts, end_ts = end_ts, start_ts

    start_ts = max(start_ts, min_time)
    end_ts = min(end_ts, max_time)
    return start_ts, end_ts


def _slice_window(start=None, end=None) -> pd.DataFrame:
    """Recorta a janela por busca binária no DataFrame ordenado."""
    start_ts, end_ts = normalize_window(start, end)
    df = load_events()
    times = df["event_time_utc"]
    left = times.searchsorted(start_ts, side="left")
    right = times.searchsorted(end_ts, side="right")
    return df.iloc[left:right]


def _choose_bucket(span: pd.Timedelta) -> tuple[str, str]:
    """Escolhe granularidade legível conforme o intervalo visível."""
    if span > pd.Timedelta(days=45):
        return "1D", "1 dia"
    if span > pd.Timedelta(days=14):
        return "12h", "12 horas"
    if span > pd.Timedelta(days=3):
        return "3h", "3 horas"
    if span > pd.Timedelta(hours=12):
        return "30min", "30 minutos"
    return "5min", "5 minutos"


def get_density_buckets(start=None, end=None) -> tuple[pd.DataFrame, str]:
    """Agrega eventos em buckets adaptativos para a visão de densidade."""
    start_ts, end_ts = normalize_window(start, end)
    window = _slice_window(start_ts, end_ts)
    frequency, label = _choose_bucket(end_ts - start_ts)

    if window.empty:
        return pd.DataFrame(columns=["bucket_start", "bucket_end", "count", "embedded_count"]), label

    indexed = window.set_index("event_time_utc")
    counts = indexed["id"].resample(frequency).count().rename("count")
    embedded = (
        indexed["time_source"]
        .eq("embedded")
        .astype(int)
        .resample(frequency)
        .sum()
        .rename("embedded_count")
    )
    result = pd.concat([counts, embedded], axis=1).reset_index()
    result.rename(columns={"event_time_utc": "bucket_start"}, inplace=True)
    result["bucket_end"] = result["bucket_start"] + pd.tseries.frequencies.to_offset(frequency)
    result = result[result["count"] > 0]
    return result, label


def get_window_event_count(start=None, end=None) -> int:
    return int(len(_slice_window(start, end)))


def should_show_individual_events(start=None, end=None) -> bool:
    """Troca para eventos individuais somente em uma janela controlável."""
    start_ts, end_ts = normalize_window(start, end)
    if end_ts - start_ts > INDIVIDUAL_MAX_SPAN:
        return False
    return get_window_event_count(start_ts, end_ts) <= INDIVIDUAL_MAX_EVENTS


def get_events_in_window(start=None, end=None, limit: int = INDIVIDUAL_MAX_EVENTS) -> pd.DataFrame:
    """Retorna eventos individuais de uma janela pequena."""
    window = _slice_window(start, end)
    if len(window) > limit:
        return window.iloc[:limit].copy()
    return window.copy()


@lru_cache(maxsize=256)
def _active_entity_ids_cached(start_iso: str, end_iso: str) -> frozenset[str]:
    window = _slice_window(start_iso, end_iso)
    active: set[str] = set()
    for parties in window["parties_canonical"]:
        if isinstance(parties, Iterable) and not isinstance(parties, (str, bytes)):
            active.update(p for p in parties if p)
    return frozenset(active)


def get_active_entity_ids_in_range(start, end) -> set[str]:
    """Entidades que aparecem como `party` em pelo menos um evento da janela."""
    start_ts, end_ts = normalize_window(start, end)
    return set(_active_entity_ids_cached(start_ts.isoformat(), end_ts.isoformat()))


@lru_cache(maxsize=1)
def _event_index() -> dict[int, dict]:
    records = {}
    for row in load_events().itertuples(index=False):
        records[int(row.id)] = {
            "id": int(row.id),
            "short_name": row.short_name,
            "event_time_utc": row.event_time_utc.isoformat(),
            "parties_canonical": _as_list(row.parties_canonical),
            "parties_types": _as_list(row.parties_types),
            "details": row.details,
            "time_source": row.time_source,
        }
    return records


def get_event_by_id(event_id) -> Optional[dict]:
    """Consulta rápida de evento para o painel e futura cadeia."""
    try:
        key = int(event_id)
    except (TypeError, ValueError):
        return None
    event = _event_index().get(key)
    return dict(event) if event else None


def parse_event_details(event: dict) -> dict:
    """Converte a coluna JSON de detalhes em dicionário seguro."""
    raw = event.get("details")
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}
