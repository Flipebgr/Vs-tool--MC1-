"""
Pipeline de pré-processamento (ETL) do Tenant Thread Visual Analytics.

Lê os dados brutos do desafio (data/raw/org_chart.json e
data/raw/MC2_data.json), resolve identidades, constrói o grafo unificado e
grava artefatos otimizados em data/processed/ para consumo rápido pelo app
Dash.

Uso:
    python -m services.etl

Este script roda uma única vez (ou sempre que os dados brutos mudarem) -
não é chamado a cada request/callback do Dash.
"""

import json
import sys
import time
from pathlib import Path

import networkx as nx
import pandas as pd

# Permite rodar tanto como `python -m services.etl` quanto `python services/etl.py`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from utils.loader import load_json
from utils.parser import build_graph
from utils.timestamp_resolver import resolve_event_timestamp
from services.identity_graph import build_entity_registry, build_unified_graph
from services.identity_resolver import build_name_lookup, resolve_party


def _flatten_events(events: list, name_lookup: dict) -> pd.DataFrame:
    """Converte a lista bruta de eventos em um DataFrame normalizado."""
    rows = []
    for event in events:
        raw_parties = event.get("parties", []) or []
        resolved = [resolve_party(p, name_lookup) for p in raw_parties]
        short_name = event.get("short_name")

        details_raw = event.get("details")
        embedded_ts, ts_source = resolve_event_timestamp(short_name, details_raw)

        rows.append(
            {
                "id": event.get("id"),
                "short_name": short_name,
                "when": event.get("when"),
                "datetime_utc": pd.to_datetime(event.get("when"), unit="s", utc=True),
                "parties_raw": raw_parties,
                "parties_canonical": [r.canonical_id for r in resolved if r.resolved],
                "parties_types": [r.type for r in resolved if r.resolved],
                # `details` varia de formato conforme short_name; guardamos como
                # JSON string para não forçar um schema único no Parquet.
                "details": json.dumps(details_raw, ensure_ascii=False),
                # Timestamp mais confiável disponível: se `details` trouxer um
                # ISO embutido (ver utils/timestamp_resolver.py), usa ele;
                # senão cai em datetime_utc (derivado de `when`, que é hora
                # de log, não hora real da ação).
                "event_time_utc": (
                    pd.to_datetime(embedded_ts, utc=True)
                    if embedded_ts
                    else pd.to_datetime(event.get("when"), unit="s", utc=True)
                ),
                "time_source": ts_source or "fallback_when",
            }
        )

    df = pd.DataFrame(rows)
    # Ordenar por event_time_utc (não por `when`) — é a ordem cronológica
    # real que interessa pra Timeline e Cadeia de Eventos.
    df.sort_values("event_time_utc", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def run() -> None:
    t0 = time.time()
    config.ensure_processed_dir()

    print(f"[1/5] Lendo dados brutos de {config.RAW_DIR} ...")
    org_data = load_json(config.ORG_CHART_RAW)
    mc2_data = load_json(config.MC2_DATA_RAW)
    events = mc2_data["events"]
    print(f"      org_chart: {len(org_data.get('nodes', []))} nós, "
          f"{len(org_data.get('edges', []))} arestas")
    print(f"      MC2_data : {len(events)} eventos")

    print("[2/5] Construindo grafo organizacional base ...")
    org_graph = build_graph(org_data)

    print("[3/5] Resolvendo identidades e unificando o grafo "
          "(pessoas + agentes + sistemas) ...")
    unified_graph, unresolved = build_unified_graph(org_graph, events)
    print(f"      grafo unificado: {unified_graph.number_of_nodes()} nós, "
          f"{unified_graph.number_of_edges()} arestas")
    if unresolved:
        print(f"      ATENÇÃO: {len(unresolved)} parties não resolvidas "
              f"(ver {config.UNRESOLVED_LOG.name})")
    else:
        print("      todas as parties foram resolvidas com sucesso.")

    print("[4/5] Achatando eventos em DataFrame ...")
    name_lookup = build_name_lookup(org_graph)
    events_df = _flatten_events(events, name_lookup)
    embedded_count = (events_df["time_source"] == "embedded").sum()
    print(f"      timestamp embutido confiável: {embedded_count}/{len(events_df)} "
          f"({100 * embedded_count / len(events_df):.1f}%) — restante usa fallback (when)")

    print("[5/5] Gravando artefatos em", config.PROCESSED_DIR, "...")
    events_df.to_parquet(config.EVENTS_PARQUET, index=False)

    entities = build_entity_registry(unified_graph)
    with open(config.ENTITIES_JSON, "w", encoding="utf8") as f:
        json.dump(entities, f, ensure_ascii=False, indent=2)

    with open(config.GRAPH_JSON, "w", encoding="utf8") as f:
        json.dump(nx.node_link_data(unified_graph), f, ensure_ascii=False, indent=2)

    with open(config.UNRESOLVED_LOG, "w", encoding="utf8") as f:
        json.dump(unresolved, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - t0
    print(f"\nConcluído em {elapsed:.1f}s.")
    print(f"  {config.EVENTS_PARQUET.name}: {len(events_df)} eventos")
    print(f"  {config.ENTITIES_JSON.name}: {len(entities)} entidades")
    print(f"  {config.GRAPH_JSON.name}: {unified_graph.number_of_nodes()} nós / "
          f"{unified_graph.number_of_edges()} arestas")


if __name__ == "__main__":
    run()
