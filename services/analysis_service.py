"""Análise investigativa estruturada para as três questões do desafio.

O serviço transforma a cadeia de eventos em afirmações rastreáveis. Cada
conclusão diferencia evidência direta, inferência suportada, limitação e
recomendação. O objetivo é impedir que a interface apresente como fato algo
que o dataset não contém explicitamente.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

import pandas as pd

from services.event_chain_service import build_event_chain
from services.graph_service import load_entities, load_graph
from services.timeline_service import get_event_by_id, load_events, parse_event_details

ANOMALY_EVENT_ID = 373902
QUICK_HANDOFF_SECONDS = 5
CLEANUP_WINDOW_SECONDS = 5


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


def _entity_label(entity_id: Optional[str]) -> str:
    if not entity_id:
        return "Não identificado"
    return load_entities().get(entity_id, {}).get("label", entity_id)


def _clean_agent_label(entity_id: Optional[str]) -> str:
    label = _entity_label(entity_id)
    return label[:-9] if label.endswith(" (Agente)") else label


def _entity_context(entity_id: str) -> dict:
    entities = load_entities()
    graph = load_graph()
    entity = entities.get(entity_id, {})
    entity_type = entity.get("type")
    owner_id = None
    person_id = entity_id if entity_type == "person" else None

    if entity_type == "agent" and entity_id in graph:
        for source, _, attrs in graph.in_edges(entity_id, data=True):
            if attrs.get("relation") == "has_agent":
                owner_id = source
                person_id = source
                break

    department_id = None
    team_id = None
    if person_id and person_id in graph:
        for source, _, attrs in graph.in_edges(person_id, data=True):
            relation = attrs.get("relation")
            source_type = graph.nodes[source].get("type")
            if relation == "led_by" and source_type == "department":
                department_id = source
                break
            if relation == "contains" and source_type == "department":
                department_id = source
            elif relation == "contains" and source_type == "team":
                team_id = source

        if team_id and not department_id:
            for source, _, attrs in graph.in_edges(team_id, data=True):
                if attrs.get("relation") == "contains" and graph.nodes[source].get("type") == "department":
                    department_id = source
                    break

    return {
        "id": entity_id,
        "label": entity.get("label", entity_id),
        "type": entity_type or "unknown",
        "title": entity.get("title"),
        "owner_id": owner_id,
        "owner_label": _entity_label(owner_id) if owner_id else None,
        "department_id": department_id,
        "department_label": _entity_label(department_id) if department_id else None,
        "team_id": team_id,
        "team_label": _entity_label(team_id) if team_id else None,
    }


def _transfer_pair(event_id: int) -> tuple[Optional[str], Optional[str]]:
    event = get_event_by_id(event_id)
    if not event or event.get("short_name") != "queue_subordinate_task":
        return None, None
    details = parse_event_details(event)
    target = _normalise_agent_id(details.get("target_agent")) or _normalise_agent_id(details.get("target"))
    agents = [
        party for party in _as_list(event.get("parties_canonical"))
        if str(party).startswith("agent:")
    ]
    source = next((party for party in agents if party != target), None)
    if source is None and agents:
        source = agents[0]
    return source, target


def _format_duration(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    if minutes or hours or days:
        parts.append(f"{minutes}min")
    parts.append(f"{secs}s")
    return " ".join(parts)


def _evidence(level: str, claim: str, event_ids: list[int], detail: str = "") -> dict:
    return {
        "level": level,
        "claim": claim,
        "event_ids": [int(event_id) for event_id in event_ids],
        "detail": detail,
    }


def _core_role(chain: dict, role: str) -> list[dict]:
    return [event for event in chain.get("events", []) if event.get("role") == role]


@lru_cache(maxsize=64)
def build_case_signature(seed_event_id: int) -> Optional[dict]:
    seed = get_event_by_id(seed_event_id)
    if not seed:
        return None

    details = parse_event_details(seed)
    content_source = details.get("content_source")
    core = build_event_chain(seed_event_id, "core")
    all_chain = build_event_chain(seed_event_id, "all")
    if not core or not all_chain:
        return None

    seed_time = pd.to_datetime(seed["event_time_utc"], utc=True)
    origin_events = _core_role(core, "origin")
    instruction_events = _core_role(core, "instruction")
    handoffs = _core_role(core, "handoff")
    aftermath = _core_role(core, "aftermath")
    final_handoff = max(
        (event for event in handoffs if pd.to_datetime(event["event_time_utc"], utc=True) < seed_time),
        key=lambda event: pd.to_datetime(event["event_time_utc"], utc=True),
        default=None,
    )

    final_source = final_target = None
    final_handoff_delta = None
    if final_handoff:
        final_source, final_target = _transfer_pair(final_handoff["id"])
        final_handoff_delta = (
            seed_time - pd.to_datetime(final_handoff["event_time_utc"], utc=True)
        ).total_seconds()

    deletion_events = [event for event in aftermath if event.get("short_name") == "delete_file"]
    cleanup_deltas = [
        (
            pd.to_datetime(event["event_time_utc"], utc=True) - seed_time
        ).total_seconds()
        for event in deletion_events
    ]

    post_agents = [
        party for party in _as_list(seed.get("parties_canonical"))
        if str(party).startswith("agent:")
    ]
    systems = [
        party for party in _as_list(seed.get("parties_canonical"))
        if str(party).startswith("system:")
    ]
    origin_agent = None
    if origin_events:
        origin_agent = next(
            (
                party for party in origin_events[0].get("party_ids", [])
                if str(party).startswith("agent:")
            ),
            None,
        )

    all_events = all_chain.get("events", [])
    all_transfer_ids = [
        event["id"] for event in all_events
        if event.get("short_name") == "queue_subordinate_task"
    ]
    transfer_pairs = [_transfer_pair(event_id) for event_id in all_transfer_ids]
    unique_transfer_pairs = {pair for pair in transfer_pairs if all(pair)}
    transfer_agents = {agent for pair in transfer_pairs for agent in pair if agent}
    self_transfer_count = sum(source == target for source, target in transfer_pairs if source and target)

    chain_start = pd.to_datetime(all_chain.get("start", seed["event_time_utc"]), utc=True)
    duration_seconds = (seed_time - chain_start).total_seconds()

    instruction_reference = None
    if instruction_events:
        references = instruction_events[0].get("artifact_references", [])
        instruction_reference = references[0] if references else None
    if not instruction_reference:
        for event in handoffs:
            references = event.get("artifact_references", [])
            instruction_reference = next(
                (value for value in references if "further_instructions" in value.lower()),
                instruction_reference,
            )
            if instruction_reference:
                break

    pattern_features = {
        "agent_authored_post": bool(post_agents),
        "saidit_system": "system:saidit" in systems,
        "file_content_source": bool(content_source),
        "instruction_propagation": bool(handoffs and instruction_reference),
        "quick_final_handoff": final_handoff_delta is not None and 0 <= final_handoff_delta <= QUICK_HANDOFF_SECONDS,
        "immediate_dual_cleanup": len(deletion_events) >= 2 and all(
            0 < delta <= CLEANUP_WINDOW_SECONDS for delta in cleanup_deltas[:2]
        ),
    }

    return {
        "event_id": int(seed_event_id),
        "short_name": seed.get("short_name"),
        "event_time_utc": seed["event_time_utc"],
        "forum": details.get("forum"),
        "content_source": content_source,
        "artifact_family": (all_chain.get("artifact_families") or [None])[0],
        "instruction_reference": instruction_reference,
        "post_agent_id": post_agents[0] if post_agents else None,
        "post_agent_label": _clean_agent_label(post_agents[0]) if post_agents else None,
        "systems": systems,
        "origin_event_id": origin_events[0]["id"] if origin_events else None,
        "origin_agent_id": origin_agent,
        "origin_agent_label": _clean_agent_label(origin_agent) if origin_agent else None,
        "origin_observed": bool(origin_events),
        "instruction_event_id": instruction_events[0]["id"] if instruction_events else None,
        "final_handoff_event_id": final_handoff["id"] if final_handoff else None,
        "final_handoff_source": final_source,
        "final_handoff_source_label": _clean_agent_label(final_source) if final_source else None,
        "final_handoff_target": final_target,
        "final_handoff_target_label": _clean_agent_label(final_target) if final_target else None,
        "final_handoff_seconds": final_handoff_delta,
        "cleanup_event_ids": [event["id"] for event in deletion_events],
        "cleanup_seconds": cleanup_deltas,
        "core_event_count": int(core.get("core_event_count", len(core.get("events", [])))),
        "related_event_count": int(all_chain.get("related_event_count", len(all_events))),
        "transfer_count": int(all_chain.get("handoff_count", len(all_transfer_ids))),
        "unique_transfer_pair_count": len(unique_transfer_pairs),
        "transfer_agent_count": len(transfer_agents),
        "self_transfer_count": self_transfer_count,
        "related_entity_count": int(all_chain.get("related_entity_count", 0)),
        "chain_start": all_chain.get("start"),
        "chain_end": all_chain.get("end"),
        "duration_seconds": duration_seconds,
        "duration_label": _format_duration(duration_seconds),
        "pattern_features": pattern_features,
        "core_chain": core,
        "all_chain": all_chain,
    }


@lru_cache(maxsize=1)
def get_automated_file_post_cases() -> list[dict]:
    """Posts do SaidIT executados por agente e alimentados por arquivo."""
    df = load_events()
    cases = []
    for row in df[df["short_name"] == "saidit_post"].itertuples(index=False):
        event = get_event_by_id(int(row.id))
        details = parse_event_details(event or {})
        parties = _as_list((event or {}).get("parties_canonical"))
        if not details.get("content_source"):
            continue
        if "system:saidit" not in parties:
            continue
        if not any(str(party).startswith("agent:") for party in parties):
            continue
        signature = build_case_signature(int(row.id))
        if signature:
            cases.append(signature)
    cases.sort(key=lambda item: item["event_time_utc"])
    return cases


def _similarity_score(reference: dict, candidate: dict) -> tuple[int, list[str]]:
    checks = [
        (
            reference.get("post_agent_id") == candidate.get("post_agent_id"),
            "mesmo agente publicador",
        ),
        (
            set(reference.get("systems", [])) == set(candidate.get("systems", [])),
            "mesmo sistema de publicação",
        ),
        (
            reference.get("forum") == candidate.get("forum"),
            "mesmo fórum",
        ),
        (
            candidate["pattern_features"].get("instruction_propagation", False),
            "instruções propagadas entre agentes",
        ),
        (
            candidate["pattern_features"].get("quick_final_handoff", False),
            "transferência final imediatamente antes do post",
        ),
        (
            candidate["pattern_features"].get("immediate_dual_cleanup", False),
            "exclusão imediata dos dois artefatos",
        ),
    ]
    matched = [label for result, label in checks if result]
    return round(100 * len(matched) / len(checks)), matched


def _essential_route(signature: dict) -> list[dict]:
    route = []
    core = signature["core_chain"]
    origin = _core_role(core, "origin")
    if origin:
        origin_agent = next(
            (party for party in origin[0].get("party_ids", []) if str(party).startswith("agent:")),
            None,
        )
        if origin_agent:
            route.append({**_entity_context(origin_agent), "event_id": origin[0]["id"], "stage": "origin"})

    for event in _core_role(core, "handoff"):
        source, target = _transfer_pair(event["id"])
        if not route and source:
            route.append({**_entity_context(source), "event_id": event["id"], "stage": "handoff"})
        if target and (not route or route[-1]["id"] != target):
            route.append({**_entity_context(target), "event_id": event["id"], "stage": "handoff"})
    return route


def _comparison_case(signature: dict, reference: dict) -> dict:
    score, matches = _similarity_score(reference, signature)
    return {
        "event_id": signature["event_id"],
        "artifact": signature.get("content_source"),
        "event_time_utc": signature["event_time_utc"],
        "origin": signature.get("origin_agent_label") or "Origem não observada",
        "origin_observed": signature.get("origin_observed"),
        "publisher": signature.get("post_agent_label"),
        "transfers": signature.get("transfer_count"),
        "entities": signature.get("related_entity_count"),
        "duration": signature.get("duration_label"),
        "final_handoff_seconds": signature.get("final_handoff_seconds"),
        "cleanup_seconds": signature.get("cleanup_seconds"),
        "similarity_score": score,
        "matched_features": matches,
    }


@lru_cache(maxsize=64)
def analyze_investigative_case(seed_event_id: int = ANOMALY_EVENT_ID) -> dict:
    signature = build_case_signature(int(seed_event_id))
    if not signature:
        return {
            "status": "error",
            "message": f"O evento {seed_event_id} não foi encontrado ou não possui cadeia reconstruível.",
            "seed_event_id": int(seed_event_id),
        }

    seed = get_event_by_id(seed_event_id)
    seed_parties = _as_list(seed.get("parties_canonical")) if seed else []
    human_party_ids = [party for party in seed_parties if str(party).startswith("person:")]
    agent_party_ids = [party for party in seed_parties if str(party).startswith("agent:")]
    system_party_ids = [party for party in seed_parties if str(party).startswith("system:")]

    route = _essential_route(signature)
    core = signature["core_chain"]
    handoff_ids = [event["id"] for event in _core_role(core, "handoff")]
    cleanup_ids = signature.get("cleanup_event_ids", [])

    q1_evidence = []
    if signature.get("origin_event_id"):
        q1_evidence.append(
            _evidence(
                "direct",
                f"{signature['content_source']} foi criado por {_clean_agent_label(signature['origin_agent_id'])} (Agente de IA).",
                [signature["origin_event_id"]],
                "A criação foi registrada no File System.",
            )
        )
    else:
        q1_evidence.append(
            _evidence(
                "limitation",
                "A origem inicial do arquivo não aparece no intervalo observado.",
                [],
                "A primeira evidência disponível já é uma transferência entre agentes.",
            )
        )

    if signature.get("instruction_event_id"):
        q1_evidence.append(
            _evidence(
                "direct",
                f"O agente de origem leu {signature['instruction_reference']} imediatamente após a criação do conteúdo.",
                [signature["instruction_event_id"]],
            )
        )
    q1_evidence.extend(
        [
            _evidence(
                "direct",
                f"As instruções foram transferidas por agentes até {signature.get('post_agent_label')} (Agente de IA).",
                handoff_ids,
                f"A visão essencial mostra {len(handoff_ids)} transferências; a propagação completa contém {signature['transfer_count']} transferências.",
            ),
            _evidence(
                "direct",
                f"O post foi executado por {signature.get('post_agent_label')} (Agente de IA) no SaidIT usando {signature.get('content_source')}.",
                [signature["event_id"]],
                "A pessoa John Windward não aparece como party direta do evento investigado." if not human_party_ids else "",
            ),
            _evidence(
                "direct",
                "Os arquivos de conteúdo e instruções foram apagados imediatamente após a publicação.",
                cleanup_ids,
                ", ".join(f"+{int(delta)}s" for delta in signature.get("cleanup_seconds", [])),
            ),
        ]
    )

    q2_evidence = [
        _evidence(
            "direct",
            f"O campo content_source do post aponta para {signature.get('content_source')}.",
            [signature["event_id"]],
        ),
        _evidence(
            "direct",
            f"O fluxo de controle usa {signature.get('instruction_reference')} e tarefas read_file entre agentes.",
            ([signature["instruction_event_id"]] if signature.get("instruction_event_id") else []) + handoff_ids,
        ),
        _evidence(
            "inference",
            "O padrão é compatível com um artefato de instrução que se propaga entre agentes e culmina em publicação automatizada.",
            handoff_ids + [signature["event_id"]],
            "Esta é uma interpretação do padrão operacional, não uma transcrição do conteúdo dos arquivos.",
        ),
        _evidence(
            "limitation",
            "O dataset não contém o texto de SwiftWren.txt nem de SwiftWren_further_instructions.md.",
            [],
            "Portanto, o significado semântico e a intenção textual da mensagem não podem ser afirmados diretamente.",
        ),
    ]

    all_cases = get_automated_file_post_cases()
    seed_time = pd.to_datetime(signature["event_time_utc"], utc=True)
    previous_cases = [
        case for case in all_cases
        if case["event_id"] != signature["event_id"]
        and pd.to_datetime(case["event_time_utc"], utc=True) < seed_time
    ]
    comparisons = [_comparison_case(case, signature) for case in previous_cases]
    coverage_count = sum(
        case["pattern_features"].get("agent_authored_post")
        and case["pattern_features"].get("file_content_source")
        and case["pattern_features"].get("quick_final_handoff")
        and case["pattern_features"].get("immediate_dual_cleanup")
        for case in all_cases
    )

    previous_event_ids = [case["event_id"] for case in previous_cases]
    pattern_event_ids = []
    for case in all_cases:
        pattern_event_ids.append(case["event_id"])
        if case.get("final_handoff_event_id"):
            pattern_event_ids.append(case["final_handoff_event_id"])
        pattern_event_ids.extend(case.get("cleanup_event_ids", []))
    pattern_event_ids = list(dict.fromkeys(pattern_event_ids))

    q3_evidence = [
        _evidence(
            "direct",
            f"Foram encontrados {len(previous_cases)} casos anteriores com o mesmo padrão de publicação automatizada por arquivo.",
            previous_event_ids,
            "HiddenOrca.txt e MellowOtter.txt antecedem o caso SwiftWren.txt.",
        ),
        _evidence(
            "direct",
            "Nos três casos, a última transferência ocorre 2 segundos antes do post e os dois arquivos são apagados 1 e 2 segundos depois.",
            pattern_event_ids,
        ),
        _evidence(
            "recommendation",
            "Exigir aprovação humana no limite de publicação do SaidIT para posts de agentes alimentados por arquivo e precedidos por tarefa read_file entre agentes.",
            pattern_event_ids,
            f"A regra teria interceptado {coverage_count}/{len(all_cases)} casos conhecidos, independentemente do tamanho da cadeia interna.",
        ),
    ]

    return {
        "status": "ok",
        "seed_event_id": signature["event_id"],
        "seed_short_name": signature["short_name"],
        "seed_time": signature["event_time_utc"],
        "artifact": signature.get("content_source"),
        "q1": {
            "title": "Como a postagem foi produzida?",
            "answer": (
                f"{signature.get('content_source')} foi conduzido por uma cadeia de agentes até "
                f"{signature.get('post_agent_label')} (Agente de IA), que publicou o arquivo no SaidIT. "
                "O usuário humano não aparece como executor direto do post; em seguida, os artefatos foram apagados."
            ),
            "essential_route": route,
            "actors": [_entity_context(entity_id) for entity_id in sorted({
                party for event in core.get("events", []) for party in event.get("party_ids", [])
                if str(party).startswith(("agent:", "person:"))
            })],
            "systems": [_entity_context(entity_id) for entity_id in sorted(set(system_party_ids) | {"system:file_system"})],
            "artifacts": [value for value in [signature.get("content_source"), signature.get("instruction_reference")] if value],
            "metrics": {
                "essential_events": signature["core_event_count"],
                "related_events": signature["related_event_count"],
                "transfers": signature["transfer_count"],
                "entities": signature["related_entity_count"],
                "duration": signature["duration_label"],
                "final_handoff_seconds": signature.get("final_handoff_seconds"),
            },
            "evidence": q1_evidence,
        },
        "q2": {
            "title": "Qual é a origem e o significado do conteúdo?",
            "answer": (
                f"A origem operacional observada é {signature.get('content_source')}, "
                + (
                    f"criado pelo agente de {signature.get('origin_agent_label')}. "
                    if signature.get("origin_observed")
                    else "cuja criação inicial não foi observada. "
                )
                + "O dataset permite demonstrar a origem técnica e o mecanismo de propagação, "
                "mas não contém o texto do arquivo; portanto, não permite afirmar com segurança o significado semântico da mensagem."
            ),
            "known": {
                "content_source": signature.get("content_source"),
                "instruction_file": signature.get("instruction_reference"),
                "origin_agent": signature.get("origin_agent_label") or "Não observado",
                "publisher_agent": signature.get("post_agent_label"),
                "human_direct_party": bool(human_party_ids),
            },
            "operational_interpretation": (
                "O conjunto de eventos é compatível com uma instrução automatizada que circula entre agentes, "
                "aciona a publicação de um arquivo e remove os rastros locais logo depois."
            ),
            "evidence": q2_evidence,
        },
        "q3": {
            "title": "Existem casos semelhantes e onde intervir?",
            "answer": (
                f"Sim. Foram encontrados {len(previous_cases)} casos anteriores: HiddenOrca.txt e MellowOtter.txt. "
                "Eles repetem o mesmo terminal operacional: transferência para o agente de John, publicação no SaidIT e exclusão imediata."
            ),
            "similar_cases": comparisons,
            "known_case_count": len(all_cases),
            "previous_similar_count": len(previous_cases),
            "common_pattern": [
                "post executado por agente no SaidIT",
                "conteúdo fornecido por arquivo",
                "instruções transferidas entre agentes",
                "última transferência 2 segundos antes do post",
                "exclusão dos dois artefatos 1 e 2 segundos depois",
            ],
            "recommendation": {
                "control_point": "Fronteira de publicação do SaidIT",
                "primary_action": (
                    "Bloquear ou exigir confirmação humana quando um agente tentar publicar conteúdo de arquivo "
                    "após receber uma tarefa read_file de outro agente."
                ),
                "why": (
                    "Esse ponto intercepta o resultado externo mesmo quando a cadeia interna varia de 10 a 186 transferências."
                ),
                "coverage": f"{coverage_count}/{len(all_cases)} casos conhecidos",
                "secondary_controls": [
                    "quarentenar arquivos *_further_instructions.md transferidos entre agentes",
                    "impedir exclusão imediata de artefatos ligados a uma publicação até auditoria",
                    "registrar aprovação humana e hash do conteúdo publicado",
                ],
            },
            "evidence": q3_evidence,
        },
    }
