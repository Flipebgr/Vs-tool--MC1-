"""
Callbacks do Módulo 3 (Sprint 2): filtros combináveis + busca com destaque
e centralização de câmera.
"""

from dash import ClientsideFunction, Input, Output, State, ctx

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
        Input("graph", "tapNodeData"),
        Input("clear-graph-highlight", "n_clicks"),
        State("search-node", "value"),
    )
    def update_graph(
        type_filter,
        relation_filter,
        department_filter,
        _n_clicks,
        tapped_node,
        _clear_clicks,
        query,
    ):
        G = load_graph()

        visible_ids = get_visible_node_ids(
            G,
            type_filter=type_filter,
            department_filter=department_filter,
            relation_filter=relation_filter,
        )

        highlight_id = None
        centered_node_id = None
        feedback = ""

        # Clicar no fundo vazio do Cytoscape limpa somente o destaque visual.
        # Os filtros permanecem ativos e o campo de busca não precisa ser
        # apagado. O evento chega por um botão oculto acionado pelo JS em
        # assets/graph_interactions.js.
        if ctx.triggered_id == "clear-graph-highlight":
            highlight_id = None
            feedback = ""

        # O clique em nó tem prioridade sobre uma consulta antiga ainda
        # presente no campo de busca. Assim, o analista pode explorar
        # livremente o grafo depois de uma pesquisa sem apagar o texto.
        elif ctx.triggered_id == "graph" and tapped_node:
            tapped_id = tapped_node.get("id")
            if tapped_id in visible_ids:
                highlight_id = tapped_id
                label = G.nodes[tapped_id].get("label", tapped_id)
                feedback = f"Selecionado no grafo: {label}"

        # A busca continua sendo recalculada quando o botão ou algum filtro
        # dispara o callback. Apenas a busca centraliza a câmera; no clique o
        # nó já está sob o cursor e um novo zoom seria desnecessário.
        elif query and query.strip():
            highlight_id, total_matches = find_best_match(query, visible_ids, G)

            if highlight_id:
                label = G.nodes[highlight_id].get("label", highlight_id)
                feedback = (
                    f"{total_matches} resultado(s) — destacando: {label}"
                    if total_matches > 1
                    else f"Encontrado: {label}"
                )
                centered_node_id = highlight_id
            else:
                feedback = "Nenhum resultado nos nós visíveis (confira os filtros ativos)."

        # Sem busca ativa, preserva o último nó clicado enquanto ele continuar
        # pertencendo ao conjunto filtrado. Isso evita perder o contexto ao
        # ajustar um filtro compatível com a seleção atual.
        elif tapped_node:
            tapped_id = tapped_node.get("id")
            if tapped_id in visible_ids:
                highlight_id = tapped_id
                label = G.nodes[tapped_id].get("label", tapped_id)
                feedback = f"Selecionado no grafo: {label}"

        elements = build_filtered_elements(
            G,
            type_filter=type_filter,
            relation_filter=relation_filter,
            department_filter=department_filter,
            highlight_node_id=highlight_id,
        )

        return elements, feedback, centered_node_id

    app.clientside_callback(
        ClientsideFunction(namespace="graph_interactions", function_name="center_on_node"),
        Output("centering-dummy-output", "children"),
        Input("centered-node-store", "data"),
    )
