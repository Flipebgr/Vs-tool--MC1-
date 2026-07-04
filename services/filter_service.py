"""
Calcula quais nós/arestas do grafo unificado devem ficar visíveis dado um
conjunto de filtros combináveis (tipo de nó, tipo de relação, departamento),
e monta os elementos do Cytoscape já com classes de destaque para a busca.

Semântica dos filtros (AND entre dimensões):

    departamento    -> restringe o universo à subárvore organizacional do(s)
                       departamento(s) selecionado(s)
    tipo de relação -> mantém apenas entidades que participam de pelo menos
                       uma aresta com uma das relações selecionadas, dentro do
                       universo departamental atual
    tipo de nó      -> entre essas entidades, mantém apenas os tipos escolhidos

O filtro de relação restringe nós e arestas. Isso evita deixar dezenas de nós
soltos no grafo; por exemplo, selecionar `led_by` com os tipos `person` e
`department` exibe somente os departamentos que possuem essa relação e seus
respectivos líderes.

Filtro vazio ([] ou None) em qualquer dimensão significa "não restringe".
"""

from typing import Iterable, Optional, Set

import networkx as nx


def _department_subtree(G: nx.DiGraph, department_id: str) -> Set[str]:
    """Retorna o departamento e sua subárvore organizacional.

    A busca segue `contains`, `led_by` e `has_agent` para capturar times,
    pessoas, lideranças e agentes associados. Lideranças precisam de tratamento
    explícito porque se ligam ao departamento por `led_by`, não por `contains`.
    """
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
    """Retorna endpoints de relações selecionadas dentro do escopo atual.

    Uma aresta só participa do resultado quando os dois endpoints pertencem ao
    escopo departamental atual. O filtro por tipo é aplicado depois, permitindo
    usos como `person` + `led_by`, que mostra apenas as pessoas líderes mesmo
    que o departamento não esteja entre os tipos selecionados.
    """
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


def get_filter_options(G: nx.DiGraph) -> dict:
    """Calcula dinamicamente as opções dos dropdowns a partir do grafo."""
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
) -> Set[str]:
    """Calcula os nós visíveis respeitando todas as dimensões do filtro.

    A ordem é deliberada:

    1. define o escopo departamental;
    2. restringe aos participantes das relações selecionadas;
    3. aplica o filtro de tipo aos endpoints restantes.
    """
    visible = set(G.nodes)

    if department_filter:
        allowed_by_department: Set[str] = set()
        for department_id in department_filter:
            allowed_by_department |= _department_subtree(G, department_id)
        visible &= allowed_by_department

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
) -> list:
    """Monta os elementos Cytoscape filtrados e aplica classes de busca."""
    visible_nodes = get_visible_node_ids(
        G,
        type_filter=type_filter,
        department_filter=department_filter,
        relation_filter=relation_filter,
    )
    relation_set = set(relation_filter) if relation_filter else None

    neighbor_ids: Set[str] = set()
    if highlight_node_id and highlight_node_id in visible_nodes:
        for _, target, attrs in G.out_edges(highlight_node_id, data=True):
            relation = attrs.get("relation", "")
            if target in visible_nodes and (relation_set is None or relation in relation_set):
                neighbor_ids.add(target)
        for source, _, attrs in G.in_edges(highlight_node_id, data=True):
            relation = attrs.get("relation", "")
            if source in visible_nodes and (relation_set is None or relation in relation_set):
                neighbor_ids.add(source)

    elements = []

    # Ordenação estabiliza o resultado e facilita testes/reprodutibilidade.
    for node_id in sorted(visible_nodes):
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
            both_in_neighborhood = (
                source in neighbor_ids or source == highlight_node_id
            ) and (
                target in neighbor_ids or target == highlight_node_id
            )
            classes = (
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
                "classes": classes,
            }
        )

    return elements
