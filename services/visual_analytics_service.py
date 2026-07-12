"""Modelos de dados para as visões coordenadas de Visual Analytics.

Este serviço reutiliza a análise investigativa e a cadeia já validadas. Ele não
cria fatos novos: apenas converte evidências existentes em estruturas próprias
para cards, Sankey, heatmap, comparação histórica e diagrama de intervenção.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Optional

import pandas as pd

from services.analysis_service import (
    ANOMALY_EVENT_ID,
    analyze_investigative_case,
    build_case_signature,
    get_automated_file_post_cases,
)
from services.graph_service import load_entities

EVENT_CATEGORY_ORDER = ["Criação", "Leitura", "Transferência", "Publicação", "Exclusão"]
EVENT_CATEGORY_BY_SHORT_NAME = {
    "create_file": "Criação",
    "read_file": "Leitura",
    "queue_subordinate_task": "Transferência",
    "saidit_post": "Publicação",
    "delete_file": "Exclusão",
}
EVENT_CATEGORY_COLORS = {
    "Criação": "#2563eb",
    "Leitura": "#0891b2",
    "Transferência": "#7c3aed",
    "Publicação": "#dc2626",
    "Exclusão": "#ea580c",
}
ENTITY_TYPE_COLORS = {
    "agent": "#f2b134",
    "person": "#f28e2b",
    "system": "#e15759",
    "artifact": "#0f766e",
    "event": "#7c3aed",
}


def _as_plain(value: Any) -> Any:
    """Converte valores pandas/numpy em tipos serializáveis pelo dcc.Store."""
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return value.item()
        except (ValueError, TypeError):
            pass
    if isinstance(value, dict):
        return {str(key): _as_plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_as_plain(item) for item in value]
    return value


def _entity_label(entity_id: str) -> str:
    return load_entities().get(entity_id, {}).get("label", entity_id)


def _clean_label(label: str) -> str:
    return label[:-9] if label.endswith(" (Agente)") else label


def _entity_type(entity_id: str) -> str:
    if entity_id.startswith("agent:"):
        return "agent"
    if entity_id.startswith("person:"):
        return "person"
    if entity_id.startswith("system:"):
        return "system"
    return load_entities().get(entity_id, {}).get("type", "unknown")


def _format_datetime(value: Any) -> str:
    if value is None:
        return "Não disponível"
    timestamp = pd.to_datetime(value, utc=True)
    return timestamp.strftime("%d/%m/%Y %H:%M:%S UTC")


def _event_category(short_name: str) -> str:
    return EVENT_CATEGORY_BY_SHORT_NAME.get(short_name, "Outros")


def _signature_case_record(signature: dict, active_event_id: int) -> dict:
    cleanup = signature.get("cleanup_seconds") or []
    return {
        "event_id": int(signature["event_id"]),
        "artifact": signature.get("content_source") or "Não identificado",
        "event_time_utc": signature.get("event_time_utc"),
        "event_time_label": _format_datetime(signature.get("event_time_utc")),
        "publisher": signature.get("post_agent_label") or "Não identificado",
        "origin": signature.get("origin_agent_label") or "Origem não observada",
        "origin_observed": bool(signature.get("origin_observed")),
        "essential_events": int(signature.get("core_event_count", 0)),
        "related_events": int(signature.get("related_event_count", 0)),
        "transfers": int(signature.get("transfer_count", 0)),
        "entities": int(signature.get("related_entity_count", 0)),
        "duration_seconds": float(signature.get("duration_seconds") or 0),
        "duration_hours": round(float(signature.get("duration_seconds") or 0) / 3600, 2),
        "duration_label": signature.get("duration_label") or "0s",
        "final_handoff_seconds": float(signature.get("final_handoff_seconds") or 0),
        "cleanup_instruction_seconds": float(cleanup[0]) if len(cleanup) > 0 else None,
        "cleanup_content_seconds": float(cleanup[1]) if len(cleanup) > 1 else None,
        "instruction_reference": signature.get("instruction_reference"),
        "post_agent_id": signature.get("post_agent_id"),
        "active": int(signature["event_id"]) == int(active_event_id),
    }


def _build_overview(analysis: dict, signature: dict) -> dict:
    q1 = analysis["q1"]
    metrics = q1["metrics"]
    cleanup = signature.get("cleanup_seconds") or []
    categories = {category: 0 for category in EVENT_CATEGORY_ORDER}
    for event in signature["core_chain"].get("events", []):
        category = _event_category(event.get("short_name", ""))
        if category in categories:
            categories[category] += 1

    publisher = signature.get("post_agent_label") or "Não identificado"
    systems = [
        _clean_label(_entity_label(system_id))
        for system_id in signature.get("systems", [])
    ]
    system_label = ", ".join(systems) if systems else "Não identificado"

    cards = [
        {"key": "essential_events", "label": "Eventos essenciais", "value": int(metrics["essential_events"]), "kind": "count"},
        {"key": "related_events", "label": "Eventos relacionados", "value": int(metrics["related_events"]), "kind": "count"},
        {"key": "transfers", "label": "Transferências", "value": int(metrics["transfers"]), "kind": "count"},
        {"key": "entities", "label": "Entidades", "value": int(metrics["entities"]), "kind": "count"},
        {"key": "duration", "label": "Duração da cadeia", "value": metrics["duration"], "kind": "duration"},
        {
            "key": "handoff_gap",
            "label": "Transferência → publicação",
            "value": f"{int(metrics.get('final_handoff_seconds') or 0)}s",
            "kind": "duration",
        },
        {
            "key": "cleanup",
            "label": "Exclusões após o post",
            "value": " / ".join(f"+{int(item)}s" for item in cleanup) if cleanup else "Não observadas",
            "kind": "duration",
        },
        {
            "key": "similar_cases",
            "label": "Casos anteriores semelhantes",
            "value": int(analysis["q3"]["previous_similar_count"]),
            "kind": "count",
        },
    ]

    return {
        "event_id": int(analysis["seed_event_id"]),
        "short_name": analysis["seed_short_name"],
        "event_time_utc": analysis["seed_time"],
        "event_time_label": _format_datetime(analysis["seed_time"]),
        "artifact": analysis.get("artifact") or "Não identificado",
        "instruction_file": signature.get("instruction_reference") or "Não identificado",
        "publisher": publisher,
        "publisher_id": signature.get("post_agent_id"),
        "system": system_label,
        "origin": signature.get("origin_agent_label") or "Origem não observada",
        "cards": cards,
        "category_counts": [
            {"category": category, "count": categories[category], "color": EVENT_CATEGORY_COLORS[category]}
            for category in EVENT_CATEGORY_ORDER
        ],
    }


def _append_flow_node(nodes: list[dict], index: dict[str, int], node: dict) -> int:
    key = node["key"]
    if key in index:
        return index[key]
    index[key] = len(nodes)
    nodes.append(node)
    return index[key]


def _build_flow(signature: dict) -> dict:
    nodes: list[dict] = []
    node_index: dict[str, int] = {}
    links: list[dict] = []
    core_events = signature["core_chain"].get("events", [])
    content = signature.get("content_source") or "Conteúdo não identificado"
    instruction = signature.get("instruction_reference") or "Instrução não identificada"

    def entity_node(entity_id: str) -> int:
        entity_type = _entity_type(entity_id)
        label = _clean_label(_entity_label(entity_id))
        return _append_flow_node(
            nodes,
            node_index,
            {
                "key": f"entity:{entity_id}",
                "label": label,
                "kind": "entity",
                "entity_id": entity_id,
                "entity_type": entity_type,
                "color": ENTITY_TYPE_COLORS.get(entity_type, "#64748b"),
                "token": f"entity|{entity_id}",
            },
        )

    def artifact_node(name: str, role: str) -> int:
        return _append_flow_node(
            nodes,
            node_index,
            {
                "key": f"artifact:{name}",
                "label": name,
                "kind": "artifact",
                "artifact": name,
                "artifact_role": role,
                "color": ENTITY_TYPE_COLORS["artifact"],
                "token": f"artifact|{name}",
            },
        )

    instruction_idx = artifact_node(instruction, "instruction")
    content_idx = artifact_node(content, "content")

    origin_event = next((event for event in core_events if event.get("role") == "origin"), None)
    instruction_event = next((event for event in core_events if event.get("role") == "instruction"), None)
    seed_event = next((event for event in core_events if event.get("role") == "seed"), None)
    aftermath_events = [event for event in core_events if event.get("role") == "aftermath"]

    origin_agent = signature.get("origin_agent_id")
    if origin_agent:
        origin_idx = entity_node(origin_agent)
        links.append({
            "source": origin_idx,
            "target": content_idx,
            "value": 1,
            "label": "criou o conteúdo",
            "event_ids": [int(origin_event["id"])] if origin_event else [],
            "color": "rgba(37,99,235,0.58)",
        })
        links.append({
            "source": instruction_idx,
            "target": origin_idx,
            "value": 1,
            "label": "leu as instruções",
            "event_ids": [int(instruction_event["id"])] if instruction_event else [],
            "color": "rgba(8,145,178,0.58)",
        })

    route = []
    for event in core_events:
        if event.get("role") != "handoff":
            continue
        agent_ids = [item for item in event.get("party_ids", []) if str(item).startswith("agent:")]
        if len(agent_ids) < 2:
            continue
        source, target = agent_ids[0], agent_ids[1]
        source_idx = entity_node(source)
        target_idx = entity_node(target)
        route.extend([source, target])
        links.append({
            "source": source_idx,
            "target": target_idx,
            "value": 1,
            "label": "transferiu instruções",
            "event_ids": [int(event["id"])],
            "color": "rgba(124,58,237,0.58)",
        })

    publisher_id = signature.get("post_agent_id")
    if publisher_id:
        publisher_idx = entity_node(publisher_id)
        links.append({
            "source": content_idx,
            "target": publisher_idx,
            "value": 1,
            "label": "forneceu o conteúdo",
            "event_ids": [int(seed_event["id"])] if seed_event else [int(signature["event_id"])],
            "color": "rgba(15,118,110,0.58)",
        })
        saidit_idx = entity_node("system:saidit")
        links.append({
            "source": publisher_idx,
            "target": saidit_idx,
            "value": 1,
            "label": "publicou no SaidIT",
            "event_ids": [int(seed_event["id"])] if seed_event else [int(signature["event_id"])],
            "color": "rgba(220,38,38,0.68)",
        })
        file_system_idx = entity_node("system:file_system")
        cleanup_ids = [int(event["id"]) for event in aftermath_events]
        links.append({
            "source": publisher_idx,
            "target": file_system_idx,
            "value": max(1, len(cleanup_ids)),
            "label": "apagou os artefatos",
            "event_ids": cleanup_ids,
            "color": "rgba(234,88,12,0.62)",
        })

    for link in links:
        event_text = ", ".join(str(event_id) for event_id in link["event_ids"]) or "sem ID"
        link["token"] = f"events|{event_text.replace(', ', ',')}"
        link["hover"] = f"{link['label']}<br>Evento(s): {event_text}"

    return {
        "nodes": nodes,
        "links": links,
        "route_entity_ids": list(dict.fromkeys(route)),
        "event_count": len(core_events),
    }


def _build_participation(signature: dict) -> dict:
    core_events = signature["core_chain"].get("events", [])
    entity_ids = sorted({
        entity_id
        for event in core_events
        for entity_id in event.get("party_ids", [])
        if str(entity_id).startswith(("agent:", "person:", "system:"))
    }, key=lambda entity_id: (_entity_type(entity_id), _clean_label(_entity_label(entity_id))))

    values: list[list[int]] = []
    event_ids: list[list[list[int]]] = []
    for entity_id in entity_ids:
        row_values = []
        row_event_ids = []
        for category in EVENT_CATEGORY_ORDER:
            matching = [
                int(event["id"])
                for event in core_events
                if entity_id in event.get("party_ids", [])
                and _event_category(event.get("short_name", "")) == category
            ]
            row_values.append(len(matching))
            row_event_ids.append(matching)
        values.append(row_values)
        event_ids.append(row_event_ids)

    return {
        "entities": [
            {
                "id": entity_id,
                "label": _clean_label(_entity_label(entity_id)),
                "type": _entity_type(entity_id),
            }
            for entity_id in entity_ids
        ],
        "categories": EVENT_CATEGORY_ORDER,
        "values": values,
        "event_ids": event_ids,
        "max_value": max((value for row in values for value in row), default=0),
    }


def _build_comparison(active_event_id: int) -> dict:
    signatures = get_automated_file_post_cases()
    cases = [_signature_case_record(signature, active_event_id) for signature in signatures]
    cases.sort(key=lambda item: item["event_time_utc"])

    sequence_rows = []
    for signature, case in zip(signatures, cases):
        core_events = signature["core_chain"].get("events", [])
        role_to_events: dict[str, list[dict]] = {}
        for event in core_events:
            role_to_events.setdefault(event.get("role", "related"), []).append(event)
        stages = [
            ("Origem", role_to_events.get("origin", [])),
            ("Instrução", role_to_events.get("instruction", [])),
            ("Transferência final", role_to_events.get("handoff", [])[-1:] if role_to_events.get("handoff") else []),
            ("Publicação", role_to_events.get("seed", [])),
            ("Exclusão", role_to_events.get("aftermath", [])),
        ]
        for stage_index, (stage, events) in enumerate(stages):
            for offset, event in enumerate(events):
                sequence_rows.append({
                    "event_id": int(case["event_id"]),
                    "artifact": case["artifact"],
                    "stage": stage,
                    "stage_index": stage_index + (offset * 0.10),
                    "source_event_id": int(event["id"]),
                    "event_time_utc": event["event_time_utc"],
                    "event_time_label": _format_datetime(event["event_time_utc"]),
                    "active": case["active"],
                })

    return {
        "cases": cases,
        "sequence": sequence_rows,
        "active_event_id": int(active_event_id),
    }


def _build_intervention(analysis: dict) -> dict:
    recommendation = analysis["q3"]["recommendation"]
    steps = [
        {"index": 0, "label": "Recebimento\nde tarefa", "kind": "observed"},
        {"index": 1, "label": "Leitura\nde arquivo", "kind": "observed"},
        {"index": 2, "label": "Propagação\nentre agentes", "kind": "observed"},
        {"index": 3, "label": "Tentativa de\npublicação", "kind": "control"},
        {"index": 4, "label": "Publicação\nou bloqueio", "kind": "outcome"},
    ]
    return {
        "steps": steps,
        "control_point": recommendation["control_point"],
        "primary_action": recommendation["primary_action"],
        "why": recommendation["why"],
        "coverage": recommendation["coverage"],
        "secondary_controls": recommendation["secondary_controls"],
    }


@lru_cache(maxsize=64)
def build_visual_analytics_model(seed_event_id: int = ANOMALY_EVENT_ID) -> dict:
    try:
        event_id = int(seed_event_id)
    except (TypeError, ValueError):
        return {"status": "error", "message": "Informe um ID de evento numérico."}

    analysis = analyze_investigative_case(event_id)
    if analysis.get("status") != "ok":
        return _as_plain(analysis)

    signature = build_case_signature(event_id)
    if not signature:
        return {
            "status": "error",
            "message": f"O evento {event_id} não possui cadeia visualizável.",
            "seed_event_id": event_id,
        }

    model = {
        "status": "ok",
        "seed_event_id": event_id,
        "overview": _build_overview(analysis, signature),
        "flow": _build_flow(signature),
        "participation": _build_participation(signature),
        "comparison": _build_comparison(event_id),
        "intervention": _build_intervention(analysis),
        "analysis_summary": {
            "q1": analysis["q1"]["answer"],
            "q2": analysis["q2"]["answer"],
            "q3": analysis["q3"]["answer"],
        },
    }
    return _as_plain(model)


def get_case_selector_options() -> list[dict]:
    options = []
    for signature in get_automated_file_post_cases():
        options.append({
            "label": f"{signature['event_id']} — {signature.get('content_source') or 'arquivo não identificado'}",
            "value": int(signature["event_id"]),
        })
    return options
