"""
Busca textual parcial (case-insensitive) sobre o conjunto de nós
atualmente visíveis (já filtrado pelos dropdowns) — ver services/filter_service.

Não busca em qualquer nó do grafo de propósito: se o usuário filtrou o
grafo e busca algo que está escondido pelo filtro, o resultado é
"nenhum encontrado" com uma mensagem explicando, em vez de silenciosamente
ignorar o filtro.
"""

from typing import Iterable, Optional, Tuple

import networkx as nx


def find_best_match(
    query: str, visible_node_ids: Iterable[str], G: nx.DiGraph
) -> Tuple[Optional[str], int]:
    """
    Retorna (id_do_melhor_match, total_de_matches).
    Critério de ranking: match exato > label começa com a busca > label
    contém a busca em qualquer posição. Empates resolvidos por ordem
    alfabética do label.
    """
    normalized_query = " ".join(query.strip().lower().split())
    if not normalized_query:
        return None, 0

    exact, prefix, contains = [], [], []

    for node_id in visible_node_ids:
        label = G.nodes[node_id].get("label", node_id)
        normalized_label = label.lower()

        if normalized_label == normalized_query:
            exact.append((label, node_id))
        elif normalized_label.startswith(normalized_query):
            prefix.append((label, node_id))
        elif normalized_query in normalized_label:
            contains.append((label, node_id))

    total_matches = len(exact) + len(prefix) + len(contains)

    for bucket in (exact, prefix, contains):
        if bucket:
            bucket.sort(key=lambda pair: pair[0])
            return bucket[0][1], total_matches

    return None, 0
