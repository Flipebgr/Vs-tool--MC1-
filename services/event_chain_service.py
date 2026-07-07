"""Reconstrução rastreável de cadeias de eventos.

A estratégia prioriza evidências explícitas do dataset:
- mesmo artefato referenciado em ``details``;
- transferências ``queue_subordinate_task`` entre agentes;
- proximidade temporal e participantes compartilhados como fallback.

Nenhuma aresta causal é inventada. Cada evento retornado informa o motivo pelo
qual entrou na cadeia, permitindo ao analista verificar a evidência original.
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from typing import Iterable, Optional

import pandas as pd

from services.timeline_service import get_event_by_id, load_events, parse_event_details

ARTIFACT_KEYS = {
    "target",
    "file",
    "path",
    "content_source",
    "file_saved",
}
LOOKBACK = pd.Timedelta(days=14)
AFTERMATH = pd.Timedelta(minutes=5)
PARTY_FALLBACK_WINDOW = pd.Timedelta(hours=2)
MAX_RELATED_EVENTS = 500


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


def _normalise_agent_id(value) -> Optional[str]:
    if not value:
        return None
    text = str(value).strip()
    if text.startswith("Agent/person:"):
        return f"agent:{text.split(':', 1)[1]}"
    if text.startswith("agent:person:"):
        return f"agent:{text.split('agent:person:', 1)[1]}"
    if text.startswith("agent:"):
        return text
    return None


def _iter_artifact_values(value, key: str = ""):
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            if child_key in ARTIFACT_KEYS and isinstance(child_value, str):
                yield child_value
            yield from _iter_artifact_values(child_value, child_key)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_artifact_values(item, key)


def _artifact_family(value: str) -> str:
    """Agrupa arquivo principal e arquivo de instruções no mesmo artefato."""
    basename = os.path.basename(str(value)).strip().lower()
    basename = basename.split("?", 1)[0]
    basename = re.sub(r"_further_instructions(?=\.)", "", basename)
    basename = re.sub(r"\.(txt|md|json|prompt)$", "", basename)
    return basename


def _artifact_evidence(details: dict) -> tuple[set[str], list[str]]:
    references = list(dict.fromkeys(_iter_artifact_values(details)))
    families = {_artifact_family(value) for value in references if value}
    families.discard("")
    return families, references


def _compact_event(row, reason: str = "", role: str = "related") -> dict:
    if isinstance(row, dict):
        event = row
    else:
        event = {
            "id": int(row.id),
            "short_name": row.short_name,
            "event_time_utc": row.event_time_utc.isoformat(),
            "parties_canonical": _as_list(row.parties_canonical),
            "parties_types": _as_list(row.parties_types),
            "details": row.details,
            "time_source": row.time_source,
        }

    details = parse_event_details(event)
    families, references = _artifact_evidence(details)
    return {
        "id": int(event["id"]),
        "short_name": event["short_name"],
        "event_time_utc": pd.to_datetime(event["event_time_utc"], utc=True).isoformat(),
        "party_ids": _as_list(event.get("parties_canonical")),
        "party_types": _as_list(event.get("parties_types")),
        "time_source": event.get("time_source"),
        "artifact_families": sorted(families),
        "artifact_references": references,
        "reason": reason,
        "role": role,
    }


def _queue_transfer(event: dict) -> tuple[Optional[str], Optional[str]]:
    if event.get("short_name") != "queue_subordinate_task":
        return None, None

    details = parse_event_details(event)
    target = _normalise_agent_id(details.get("target_agent"))
    if not target:
        target = _normalise_agent_id(details.get("target"))

    agents = [
        party for party in _as_list(event.get("parties_canonical"))
        if str(party).startswith("agent:")
    ]
    source = next((party for party in agents if party != target), None)
    if source is None and agents:
        source = agents[0]
    return source, target


def _row_to_event(row) -> dict:
    return {
        "id": int(row.id),
        "short_name": row.short_name,
        "event_time_utc": row.event_time_utc.isoformat(),
        "parties_canonical": _as_list(row.parties_canonical),
        "parties_types": _as_list(row.parties_types),
        "details": row.details,
        "time_source": row.time_source,
    }


def _related_artifact_events(seed: dict, families: set[str]) -> list[dict]:
    seed_time = pd.to_datetime(seed["event_time_utc"], utc=True)
    start = seed_time - LOOKBACK
    end = seed_time + AFTERMATH
    df = load_events()
    window = df[(df["event_time_utc"] >= start) & (df["event_time_utc"] <= end)]

    # A busca textual reduz drasticamente o número de JSONs analisados.
    tokens = sorted(families, key=len, reverse=True)
    if tokens:
        text_mask = pd.Series(False, index=window.index)
        details_text = window["details"].fillna("")
        for token in tokens:
            text_mask |= details_text.str.contains(token, case=False, regex=False)
        window = window[text_mask]

    related = []
    for row in window.itertuples(index=False):
        event = _row_to_event(row)
        event_families, _ = _artifact_evidence(parse_event_details(event))
        if event_families & families:
            related.append(event)

    related.sort(key=lambda item: (item["event_time_utc"], item["id"]))
    return related[:MAX_RELATED_EVENTS]


def _earliest_temporal_path(
    transfers: list[dict],
    origin_agent: str,
    target_agent: str,
    start_time: pd.Timestamp,
    end_time: pd.Timestamp,
) -> list[dict]:
    """Menor tempo de chegada em uma sequência de transferências válidas."""
    state: dict[str, tuple[pd.Timestamp, list[dict]]] = {
        origin_agent: (start_time, [])
    }

    for event in sorted(transfers, key=lambda item: item["event_time_utc"]):
        event_time = pd.to_datetime(event["event_time_utc"], utc=True)
        if event_time < start_time or event_time >= end_time:
            continue
        source, target = _queue_transfer(event)
        if not source or not target or source not in state:
            continue
        arrival, path = state[source]
        if arrival > event_time:
            continue

        candidate = (event_time, path + [event])
        current = state.get(target)
        if current is None or (candidate[0], len(candidate[1])) < (current[0], len(current[1])):
            state[target] = candidate

    return state.get(target_agent, (end_time, []))[1]


def _reason_for_related(event: dict, families: set[str]) -> str:
    source, target = _queue_transfer(event)
    if source and target:
        return f"Transferência explícita do artefato: {source} → {target}"
    if event["short_name"] == "create_file":
        return "Criação do artefato"
    if event["short_name"] == "read_file":
        return "Leitura de arquivo relacionado"
    if event["short_name"] == "delete_file":
        return "Remoção de arquivo relacionado"
    return f"Referência ao mesmo artefato: {', '.join(sorted(families))}"


def _build_artifact_chain(seed: dict, families: set[str], view_mode: str) -> dict:
    related = _related_artifact_events(seed, families)
    seed_time = pd.to_datetime(seed["event_time_utc"], utc=True)
    seed_agents = {
        party for party in _as_list(seed.get("parties_canonical"))
        if str(party).startswith("agent:")
    }

    creation_events = [event for event in related if event["short_name"] == "create_file"]
    origin_event = creation_events[0] if creation_events else (related[0] if related else seed)
    origin_agents = [
        party for party in _as_list(origin_event.get("parties_canonical"))
        if str(party).startswith("agent:")
    ]
    origin_agent = origin_agents[0] if origin_agents else None
    origin_time = pd.to_datetime(origin_event["event_time_utc"], utc=True)

    transfers = [event for event in related if event["short_name"] == "queue_subordinate_task"]
    final_handoffs = []
    for event in transfers:
        source, target = _queue_transfer(event)
        event_time = pd.to_datetime(event["event_time_utc"], utc=True)
        if target in seed_agents and event_time < seed_time:
            final_handoffs.append((event_time, event, source, target))
    final_handoffs.sort(key=lambda item: item[0])
    final_handoff = final_handoffs[-1] if final_handoffs else None

    core: list[dict] = []
    if origin_event:
        core.append(_compact_event(origin_event, "Origem observada do artefato", "origin"))

    if origin_agent:
        origin_reads = [
            event for event in related
            if event["short_name"] == "read_file"
            and origin_agent in _as_list(event.get("parties_canonical"))
            and origin_time <= pd.to_datetime(event["event_time_utc"], utc=True) <= origin_time + pd.Timedelta(minutes=10)
        ]
        if origin_reads:
            core.append(_compact_event(origin_reads[0], "Leitura das instruções associadas ao artefato", "instruction"))

    if final_handoff and origin_agent and final_handoff[2]:
        path = _earliest_temporal_path(
            transfers,
            origin_agent,
            final_handoff[2],
            origin_time,
            final_handoff[0],
        )
        for event in path:
            source, target = _queue_transfer(event)
            core.append(
                _compact_event(
                    event,
                    f"Propagação explícita: {source} → {target}",
                    "handoff",
                )
            )

        event = final_handoff[1]
        source, target = final_handoff[2], final_handoff[3]
        core.append(
            _compact_event(
                event,
                f"Última transferência antes do evento investigado: {source} → {target}",
                "handoff",
            )
        )

    core.append(_compact_event(seed, "Evento investigado", "seed"))

    seed_parties = set(_as_list(seed.get("parties_canonical")))
    for event in related:
        event_time = pd.to_datetime(event["event_time_utc"], utc=True)
        if not (seed_time < event_time <= seed_time + AFTERMATH):
            continue
        if not seed_parties.intersection(_as_list(event.get("parties_canonical"))):
            continue
        if event["short_name"] in {"delete_file", "read_file", "saidit_post", "saidit_post_check"}:
            core.append(
                _compact_event(
                    event,
                    "Ação imediatamente posterior envolvendo o mesmo ator/artefato",
                    "aftermath",
                )
            )

    # Deduplicação preservando ordem temporal.
    deduplicated = {}
    for event in core:
        deduplicated[event["id"]] = event
    core = sorted(deduplicated.values(), key=lambda item: (item["event_time_utc"], item["id"]))

    all_events = [
        _compact_event(event, _reason_for_related(event, families), "related")
        for event in related
    ]
    # Mantém os papéis da visão essencial também na visão completa.
    core_by_id = {event["id"]: event for event in core}
    all_events = [core_by_id.get(event["id"], event) for event in all_events]

    displayed = core if view_mode == "core" else all_events
    entity_ids = sorted({party for event in displayed for party in event["party_ids"]})
    unique_related_entities = sorted({
        party for event in all_events for party in event["party_ids"]
    })
    handoff_count = sum(event["short_name"] == "queue_subordinate_task" for event in all_events)

    return {
        "seed_event_id": int(seed["id"]),
        "strategy": "artifact",
        "view_mode": view_mode,
        "artifact_families": sorted(families),
        "events": displayed,
        "core_event_count": len(core),
        "related_event_count": len(all_events),
        "handoff_count": handoff_count,
        "entity_ids": entity_ids,
        "related_entity_count": len(unique_related_entities),
        "start": displayed[0]["event_time_utc"] if displayed else seed["event_time_utc"],
        "end": displayed[-1]["event_time_utc"] if displayed else seed["event_time_utc"],
    }


def _build_party_fallback(seed: dict, view_mode: str) -> dict:
    seed_time = pd.to_datetime(seed["event_time_utc"], utc=True)
    seed_parties = set(_as_list(seed.get("parties_canonical")))
    df = load_events()
    window = df[
        (df["event_time_utc"] >= seed_time - PARTY_FALLBACK_WINDOW)
        & (df["event_time_utc"] <= seed_time + PARTY_FALLBACK_WINDOW)
    ]

    candidates = []
    for row in window.itertuples(index=False):
        parties = set(_as_list(row.parties_canonical))
        shared = seed_parties & parties
        if not shared:
            continue
        event = _row_to_event(row)
        distance = abs(pd.to_datetime(event["event_time_utc"], utc=True) - seed_time)
        candidates.append((distance, event, shared))

    candidates.sort(key=lambda item: (item[0], item[1]["event_time_utc"]))
    selected = candidates[:25 if view_mode == "all" else 10]
    compact = []
    for _, event, shared in selected:
        role = "seed" if event["id"] == seed["id"] else "related"
        reason = "Evento investigado" if role == "seed" else f"Participante compartilhado: {', '.join(sorted(shared))}"
        compact.append(_compact_event(event, reason, role))
    compact.sort(key=lambda item: (item["event_time_utc"], item["id"]))

    entity_ids = sorted({party for event in compact for party in event["party_ids"]})
    return {
        "seed_event_id": int(seed["id"]),
        "strategy": "party_proximity",
        "view_mode": view_mode,
        "artifact_families": [],
        "events": compact,
        "core_event_count": len(compact),
        "related_event_count": len(candidates),
        "handoff_count": 0,
        "entity_ids": entity_ids,
        "related_entity_count": len(entity_ids),
        "start": compact[0]["event_time_utc"] if compact else seed["event_time_utc"],
        "end": compact[-1]["event_time_utc"] if compact else seed["event_time_utc"],
    }


@lru_cache(maxsize=128)
def build_event_chain(seed_event_id: int, view_mode: str = "core") -> Optional[dict]:
    """Reconstrói uma cadeia a partir de um evento selecionado.

    ``view_mode`` aceita ``core`` (rota essencial) ou ``all`` (todas as
    evidências relacionadas encontradas dentro da janela de investigação).
    """
    seed = get_event_by_id(seed_event_id)
    if not seed:
        return None

    view_mode = "all" if view_mode == "all" else "core"
    families, _ = _artifact_evidence(parse_event_details(seed))
    if families:
        return _build_artifact_chain(seed, families, view_mode)
    return _build_party_fallback(seed, view_mode)
