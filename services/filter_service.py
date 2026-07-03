"""
Calcula quais nós/arestas do grafo unificado devem ficar visíveis dado um
conjunto de filtros combináveis (tipo de nó, tipo de relação, departamento),
e monta os elementos do Cytoscape já com classes de destaque (highlight)
para a busca do Módulo 3.

Semântica dos filtros (todos combináveis com AND entre dimensões):

    tipo de nó     -> só nós cujo `type` esteja na lista selecionada
    departamento   -> só nós dentro da subárvore do(s) departamento(s)
                      selecionado(s): o departamento, seus times, as
                      pessoas desses times, as pessoas lideradas
                      diretamente (aresta `led_by`) e os agentes dessas
                      pessoas (aresta `has_agent`)
    tipo de relação -> não filtra nós, só esconde arestas cuja `relation`
                      não esteja selecionada (nós continuam visíveis
                      mesmo "soltos")

Filtro vazio ([] ou None) em qualquer dimensão significa "não restringe".
"""

from typing import Iterable, Optional, Set

import networkx as nx


def _department_subtree(G: nx.DiGraph, department_id: str) -> Set[str]:
    """BFS a partir de um departamento seguindo `contains`, `led_by` e
    `has_agent`, para capturar toda a equipe (e agentes) daquele
    departamento — incluindo lideranças, que só se conectam via `led_by`,
    não `contains`."""
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


def get_filter_options(G: nx.DiGraph) -> dict:
    """Opções disponíveis para os 3 dropdowns, calculadas a partir do grafo
    (nada hardcoded, então se o dataset mudar as opções acompanham)."""
    types = sorted({attrs.get("type") for _, attrs in G.nodes(data=True) if attrs.get("type")})
    relations = sorted({data.get("relation") for _, _, data in G.edges(data=True) if data.get("relation")})
    departments = sorted(
        (
            {"value": n, "label": attrs.get("label", n)}
            for n, attrs in G.nodes(data=True)
            if attrs.get("type") == "department"
        ),
        key=lambda d: d["label"],
    )
    return {"types": types, "relations": relations, "departments": departments}


def get_visible_node_ids(
    G: nx.DiGraph,
    type_filter: Optional[Iterable[str]] = None,
    department_filter: Optional[Iterable[str]] = None,
) -> Set[str]:
    visible = set(G.nodes)

    if department_filter:
        allowed: Set[str] = set()
        for dept_id in department_filter:
            allowed |= _department_subtree(G, dept_id)
        visible &= allowed

    if type_filter:
        type_set = set(type_filter)
        visible = {n for n in visible if G.nodes[n].get("type") in type_set}

    return visible


def build_filtered_elements(
    G: nx.DiGraph,
    type_filter: Optional[Iterable[str]] = None,
    relation_filter: Optional[Iterable[str]] = None,
    department_filter: Optional[Iterable[str]] = None,
    highlight_node_id: Optional[str] = None,
) -> list:
    """Monta a lista de elementos do Cytoscape já filtrada, com classes de
    destaque aplicadas quando `highlight_node_id` é informado."""
    visible_nodes = get_visible_node_ids(G, type_filter, department_filter)
    relation_set = set(relation_filter) if relation_filter else None

    neighbor_ids: Set[str] = set()
    if highlight_node_id and highlight_node_id in visible_nodes:
        for _, target in G.out_edges(highlight_node_id):
            if target in visible_nodes:
                neighbor_ids.add(target)
        for source, _ in G.in_edges(highlight_node_id):
            if source in visible_nodes:
                neighbor_ids.add(source)

    elements = []

    for node_id in visible_nodes:
        attrs = G.nodes[node_id]
        classes = ""
        if highlight_node_id:
            if node_id == highlight_node_id:
                classes = "highlighted"
            elif node_id in neighbor_ids:
                classes = "neighbor"
            else:
                classes = "faded"

        elements.append(
            {
                "data": {
                    "id": node_id,
                    "label": attrs.get("label", node_id),
                    "type": attrs.get("type", ""),
                },
                "classes": classes,
            }
        )

    for source, target, attrs in G.edges(data=True):
        if source not in visible_nodes or target not in visible_nodes:
            continue
        relation = attrs.get("relation", "")
        if relation_set is not None and relation not in relation_set:
            continue

        classes = ""
        if highlight_node_id:
            touches_highlight = highlight_node_id in (source, target)
            both_in_neighborhood = (source in neighbor_ids or source == highlight_node_id) and (
                target in neighbor_ids or target == highlight_node_id
            )
            classes = "highlighted-edge" if (touches_highlight and both_in_neighborhood) else "faded"

        elements.append(
            {
                "data": {"source": source, "target": target, "relation": relation},
                "classes": classes,
            }
        )

    return elements
