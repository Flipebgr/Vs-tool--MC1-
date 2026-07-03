"""
Formata as estatísticas do grafo unificado (utils/statistics.py) em uma
estrutura pronta para exibição no sidebar, na ordem e com os rótulos em
português definidos em utils/entity_style.py.
"""

from utils.statistics import graph_statistics
from utils.entity_style import TYPE_ORDER, TYPE_LABELS, TYPE_COLORS, RELATION_LABELS
from services.graph_service import load_graph


def get_stats_summary() -> dict:
    """
    Retorna:
        {
            "nodes": int,
            "edges": int,
            "by_type": [{"type": "person", "label": "Pessoa", "count": 49, "color": "#..."}, ...],
            "by_relation": [{"relation": "contains", "label": "contém", "count": 69}, ...],
        }
    """
    raw = graph_statistics(load_graph())

    by_type = []
    for t in TYPE_ORDER:
        count = raw["node_types"].get(t, 0)
        if count:
            by_type.append(
                {
                    "type": t,
                    "label": TYPE_LABELS.get(t, t),
                    "count": count,
                    "color": TYPE_COLORS.get(t, "#bab0ac"),
                }
            )

    # Tipos não previstos em TYPE_ORDER (segurança caso o dataset mude)
    for t, count in raw["node_types"].items():
        if t not in TYPE_ORDER:
            by_type.append({"type": t, "label": t, "count": count, "color": "#bab0ac"})

    by_relation = [
        {"relation": r, "label": RELATION_LABELS.get(r, r), "count": c}
        for r, c in sorted(raw["edge_types"].items(), key=lambda x: -x[1])
    ]

    return {
        "nodes": raw["nodes"],
        "edges": raw["edges"],
        "by_type": by_type,
        "by_relation": by_relation,
    }
