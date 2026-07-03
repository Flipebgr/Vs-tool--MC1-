"""
Callbacks do Módulo 3 (Sprint 2): filtros combináveis + busca com destaque
e centralização de câmera.
"""

from dash import ClientsideFunction, Input, Output, State

from services.graph_service import load_graph
from services.filter_service import build_filtered_elements
from services.search_service import find_best_match
from services.filter_service import get_visible_node_ids


def register(app):

    @app.callback(
        Output("graph", "elements"),
        Output("search-feedback", "children"),
        Output("centered-node-store", "data"),
        Input("type-filter", "value"),
        Input("relation-filter", "value"),
        Input("department-filter", "value"),
        Input("search-button", "n_clicks"),
        State("search-node", "value"),
    )
    def update_graph(type_filter, relation_filter, department_filter, _n_clicks, query):
        G = load_graph()

        visible_ids = get_visible_node_ids(G, type_filter, department_filter)

        highlight_id = None
        feedback = ""

        if query and query.strip():
            highlight_id, total_matches = find_best_match(query, visible_ids, G)

            if highlight_id:
                label = G.nodes[highlight_id].get("label", highlight_id)
                feedback = (
                    f"{total_matches} resultado(s) — destacando: {label}"
                    if total_matches > 1
                    else f"Encontrado: {label}"
                )
            else:
                feedback = "Nenhum resultado nos nós visíveis (confira os filtros ativos)."

        elements = build_filtered_elements(
            G,
            type_filter=type_filter,
            relation_filter=relation_filter,
            department_filter=department_filter,
            highlight_node_id=highlight_id,
        )

        return elements, feedback, highlight_id

    app.clientside_callback(
        ClientsideFunction(namespace="graph_interactions", function_name="center_on_node"),
        Output("centering-dummy-output", "children"),
        Input("centered-node-store", "data"),
    )
