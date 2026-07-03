"""
Callback: clique em um nó do grafo (Cytoscape) atualiza o painel de
informações (components/info_panel.py) com os detalhes daquele nó e seus
vizinhos diretos.
"""

from dash import Input, Output, html
from dash.exceptions import PreventUpdate

from services.graph_service import get_node_details
from utils.entity_style import TYPE_LABELS


def register(app):

    @app.callback(
        Output("node-information", "children"),
        Input("graph", "tapNodeData"),
    )
    def show_node_details(node_data):
        if not node_data:
            raise PreventUpdate

        node_id = node_data.get("id")
        details = get_node_details(node_id)

        if details is None:
            return html.Div(f"Nó '{node_id}' não encontrado.")

        attrs = details["attrs"]
        node_type = attrs.get("type", "")
        type_label = TYPE_LABELS.get(node_type, node_type)

        children = [
            html.H4(attrs.get("label", node_id)),
            html.P(f"Tipo: {type_label}"),
        ]

        if attrs.get("title"):
            children.append(html.P(f"Cargo: {attrs['title']}"))

        if details["neighbors_out"] or details["neighbors_in"]:
            children.append(html.Hr())
            children.append(html.H5("Conexões"))

            for n in details["neighbors_out"]:
                children.append(html.P(f"→ {n['label']} ({n['relation']})"))

            for n in details["neighbors_in"]:
                children.append(html.P(f"← {n['label']} ({n['relation']})"))

        return html.Div(children)
