"""
Callback do seletor de layout (Módulo 4). Troca o algoritmo de
posicionamento do Cytoscape (dagre, breadthfirst, cose, circle, grid) sem
precisar recarregar a página nem recalcular os elementos do grafo.
"""

from dash import Input, Output

from components.graph import get_layout_config


def register(app):

    @app.callback(
        Output("graph", "layout"),
        Input("layout-select", "value"),
    )
    def update_layout(layout_name):
        return get_layout_config(layout_name)
