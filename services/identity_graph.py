"""
Constrói o grafo unificado da Tenant Thread: organograma oficial
(org_chart.json) enriquecido com os nós de agente de IA, sistema e "world"
que só aparecem implicitamente dentro dos eventos de MC2_data.json.

O org_chart.json sozinho só descreve company/department/team/person. Este
módulo adiciona:

    person:X  --[has_agent]-->  agent:X

para todo agente observado nos eventos, e nós avulsos (sem aresta
hierárquica inventada) para cada system:X e world:X observado - não temos
no dataset nenhuma relação explícita de "sistema pertence a tal
departamento", então não fabricamos essa aresta.
"""

from typing import Dict, Iterable, List, Set, Tuple

import networkx as nx

from services.identity_resolver import (
    build_name_lookup,
    person_id_for_agent,
    resolve_party,
)


def build_unified_graph(
    org_graph: nx.DiGraph, events: Iterable[dict]
) -> Tuple[nx.DiGraph, List[dict]]:
    """
    Retorna (grafo_unificado, lista_de_parties_nao_resolvidas).

    grafo_unificado é uma cópia de org_graph com nós/arestas adicionais.
    Cada `party` não resolvida gera um registro
    {"event_id": ..., "raw_party": ...} na lista retornada, para auditoria.
    """
    G = org_graph.copy()
    name_lookup: Dict[str, str] = build_name_lookup(org_graph)

    seen_agents: Set[str] = set()
    seen_systems: Set[str] = set()
    seen_worlds: Set[str] = set()
    unresolved: List[dict] = []

    for event in events:
        for raw_party in event.get("parties", []) or []:
            resolved = resolve_party(raw_party, name_lookup)

            if not resolved.resolved:
                unresolved.append({"event_id": event.get("id"), "raw_party": raw_party})
                continue

            if resolved.type == "agent" and resolved.canonical_id not in seen_agents:
                seen_agents.add(resolved.canonical_id)
                slug = resolved.canonical_id.split(":", 1)[1]
                label = slug.replace("_", " ").title()
                G.add_node(resolved.canonical_id, label=f"{label} (Agente)", type="agent")

                person_id = person_id_for_agent(resolved.canonical_id)
                if G.has_node(person_id):
                    G.add_edge(person_id, resolved.canonical_id, relation="has_agent")
                else:
                    # Pessoa referenciada no evento mas ausente do org_chart.
                    # Registramos como não-resolvido em vez de inventar o nó.
                    unresolved.append(
                        {"event_id": event.get("id"), "raw_party": f"missing_person_for:{raw_party}"}
                    )

            elif resolved.type == "system" and resolved.canonical_id not in seen_systems:
                seen_systems.add(resolved.canonical_id)
                slug = resolved.canonical_id.split(":", 1)[1]
                label = slug.replace("_", " ").title()
                G.add_node(resolved.canonical_id, label=label, type="system")

            elif resolved.type == "world" and resolved.canonical_id not in seen_worlds:
                seen_worlds.add(resolved.canonical_id)
                slug = resolved.canonical_id.split(":", 1)[1]
                label = slug.replace("_", " ").title()
                G.add_node(resolved.canonical_id, label=label, type="world")

            # type == "person" -> já existe no org_graph, nada a fazer.

    return G, unresolved


def build_entity_registry(G: nx.DiGraph) -> Dict[str, dict]:
    """
    Serializa todos os nós do grafo unificado em um registro plano
    {canonical_id: {label, type, ...demais atributos}}, salvo depois em
    data/processed/entities.json para consultas rápidas (busca, painel de
    informações) sem precisar carregar o grafo inteiro.
    """
    registry: Dict[str, dict] = {}
    for node_id, attrs in G.nodes(data=True):
        registry[node_id] = dict(attrs)
    return registry
