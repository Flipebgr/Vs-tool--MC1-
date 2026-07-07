"""
Calcula quais nós/arestas do grafo unificado devem ficar visíveis dado um
conjunto de filtros combináveis (tipo, relação, departamento e tempo), e
monta os elementos do Cytoscape com classes de destaque.

Semântica dos filtros (AND entre dimensões):

    departamento -> restringe à subárvore organizacional selecionada;
    tempo        -> mantém entidades ativas e o contexto organizacional mínimo;
    relação      -> mantém participantes das relações selecionadas;
    tipo         -> mantém apenas os tipos escolhidos.

Nós estruturais incluídos apenas para contextualizar uma atividade temporal
recebem a classe `temporal-context`; eles não são tratados como participantes
do evento.
"""

from typing import Iterable, Optional, Set

import networkx as nx


def _department_subtree(G: nx.DiGraph, department_id: str) -> Set[str]:
    """Retorna o departamento e sua subárvore organizacional."""
    if department_id not in G:
        return set()

    visited = {department_id}
    queue = [department_id]

    while queue:
        node = queue.pop()
        for _, target, data in G.out_edges(node, data=True):
            relation = data.get("relation")
            if target in visited:
                continue
            if relation in ("contains", "led_by", "has_agent"):
                visited.add(target)
                if relation in ("contains", "led_by"):
                    queue.append(target)

    return visited


def _relation_endpoint_ids(
    G: nx.DiGraph,
    relation_filter: Iterable[str],
    candidate_nodes: Set[str],
) -> Set[str]:
    relation_set = set(relation_filter)
    endpoints: Set[str] = set()

    for source, target, attrs in G.edges(data=True):
        if attrs.get("relation") not in relation_set:
            continue
        if source not in candidate_nodes or target not in candidate_nodes:
            continue
        endpoints.add(source)
        endpoints.add(target)

    return endpoints


def get_temporal_scope_node_ids(
    G: nx.DiGraph,
    active_node_ids: Iterable[str],
) -> tuple[Set[str], Set[str]]:
    """Expande entidades ativas com o contexto organizacional mínimo.

    A expansão sobe apenas por relações estruturais existentes:
    `has_agent` liga um agente ao proprietário; `contains` e `led_by` ligam
    pessoas/equipes/departamentos aos seus ancestrais. Sistemas e calendário
    permanecem sem vínculo inventado.

    Retorna `(escopo_total, nós_de_contexto)`.
    """
    active = {node_id for node_id in active_node_ids if node_id in G}
    scope = set(active)
    queue = list(active)

    while queue:
        node_id = queue.pop()
        for source, _, attrs in G.in_edges(node_id, data=True):
            relation = attrs.get("relation")
            if relation not in ("contains", "led_by", "has_agent"):
                continue
            if source not in scope:
                scope.add(source)
                queue.append(source)

    return scope, scope - active


def get_filter_options(G: nx.DiGraph) -> dict:
    types = sorted(
        {
            attrs.get("type")
            for _, attrs in G.nodes(data=True)
            if attrs.get("type")
        }
    )
    relations = sorted(
        {
            data.get("relation")
            for _, _, data in G.edges(data=True)
            if data.get("relation")
        }
    )
    departments = sorted(
        (
            {"value": node_id, "label": attrs.get("label", node_id)}
            for node_id, attrs in G.nodes(data=True)
            if attrs.get("type") == "department"
        ),
        key=lambda item: item["label"],
    )
    return {
        "types": types,
        "relations": relations,
        "departments": departments,
    }


def get_visible_node_ids(
    G: nx.DiGraph,
    type_filter: Optional[Iterable[str]] = None,
    department_filter: Optional[Iterable[str]] = None,
    relation_filter: Optional[Iterable[str]] = None,
    active_node_ids: Optional[Iterable[str]] = None,
) -> Set[str]:
    """Calcula os nós visíveis respeitando todas as dimensões do filtro."""
    visible = set(G.nodes)

    if department_filter:
        allowed_by_department: Set[str] = set()
        for department_id in department_filter:
            allowed_by_department |= _department_subtree(G, department_id)
        visible &= allowed_by_department

    if active_node_ids is not None:
        temporal_scope, _ = get_temporal_scope_node_ids(G, active_node_ids)
        visible &= temporal_scope

    if relation_filter:
        visible &= _relation_endpoint_ids(G, relation_filter, visible)

    if type_filter:
        allowed_types = set(type_filter)
        visible = {
            node_id
            for node_id in visible
            if G.nodes[node_id].get("type") in allowed_types
        }

    return visible


def build_filtered_elements(
    G: nx.DiGraph,
    type_filter: Optional[Iterable[str]] = None,
    relation_filter: Optional[Iterable[str]] = None,
    department_filter: Optional[Iterable[str]] = None,
    highlight_node_id: Optional[str] = None,
    highlight_node_ids: Optional[Iterable[str]] = None,
    chain_node_ids: Optional[Iterable[str]] = None,
    active_node_ids: Optional[Iterable[str]] = None,
) -> list:
    """Monta elementos Cytoscape filtrados e aplica classes visuais.

    `highlight_node_id` preserva o comportamento de clique/busca em um único
    nó, incluindo seus vizinhos diretos. `highlight_node_ids` representa uma
    seleção analítica de múltiplos nós — usada para destacar os participantes
    de um evento da Timeline sem inventar novas arestas estruturais.
    """
    active_set = set(active_node_ids) if active_node_ids is not None else None
    temporal_context: Set[str] = set()
    if active_set is not None:
        _, temporal_context = get_temporal_scope_node_ids(G, active_set)

    visible_nodes = get_visible_node_ids(
        G,
        type_filter=type_filter,
        department_filter=department_filter,
        relation_filter=relation_filter,
        active_node_ids=active_set,
    )
    relation_set = set(relation_filter) if relation_filter else None

    event_participant_ids = {
        node_id
        for node_id in (highlight_node_ids or [])
        if node_id in visible_nodes
    }
    chain_participant_ids = {
        node_id
        for node_id in (chain_node_ids or [])
        if node_id in visible_nodes
    }

    neighbor_ids: Set[str] = set()
    if not chain_participant_ids and not event_participant_ids and highlight_node_id and highlight_node_id in visible_nodes:
        for _, target, attrs in G.out_edges(highlight_node_id, data=True):
            relation = attrs.get("relation", "")
            if target in visible_nodes and (relation_set is None or relation in relation_set):
                neighbor_ids.add(target)
        for source, _, attrs in G.in_edges(highlight_node_id, data=True):
            relation = attrs.get("relation", "")
            if source in visible_nodes and (relation_set is None or relation in relation_set):
                neighbor_ids.add(source)

    elements = []

    for node_id in sorted(visible_nodes):
        attrs = G.nodes[node_id]
        classes = []

        if active_set is not None and node_id in temporal_context:
            classes.append("temporal-context")

        if chain_participant_ids:
            if node_id in chain_participant_ids:
                classes.append("chain-participant")
            else:
                classes.append("faded")
        elif event_participant_ids:
            if node_id in event_participant_ids:
                classes.append("event-participant")
            else:
                classes.append("faded")
        elif highlight_node_id:
            if node_id == highlight_node_id:
                classes.append("highlighted")
            elif node_id in neighbor_ids:
                classes.append("neighbor")
            else:
                classes.append("faded")

        elements.append(
            {
                "data": {
                    "id": node_id,
                    "label": attrs.get("label", node_id),
                    "type": attrs.get("type", ""),
                },
                "classes": " ".join(classes),
            }
        )

    for source, target, attrs in G.edges(data=True):
        if source not in visible_nodes or target not in visible_nodes:
            continue

        relation = attrs.get("relation", "")
        if relation_set is not None and relation not in relation_set:
            continue

        classes = []
        if chain_participant_ids:
            if source in chain_participant_ids and target in chain_participant_ids:
                classes.append("chain-participant-edge")
            else:
                classes.append("faded")
        elif event_participant_ids:
            if source in event_participant_ids and target in event_participant_ids:
                classes.append("event-participant-edge")
            else:
                classes.append("faded")
        elif highlight_node_id:
            touches_highlight = highlight_node_id in (source, target)
            both_in_neighborhood = (
                source in neighbor_ids or source == highlight_node_id
            ) and (
                target in neighbor_ids or target == highlight_node_id
            )
            classes.append(
                "highlighted-edge"
                if touches_highlight and both_in_neighborhood
                else "faded"
            )

        elements.append(
            {
                "data": {
                    "source": source,
                    "target": target,
                    "relation": relation,
                },
                "classes": " ".join(classes),
            }
        )

    return elements
