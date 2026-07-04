from dash import html, dcc

from components.header import create_header
from components.sidebar import create_sidebar
from components.graph import graph_component
from components.info_panel import create_info_panel


def create_layout(elements, stats, filter_options):

    return html.Div(

        [

            create_header(),

            html.Div(

                [

                    create_sidebar(stats, filter_options),

                    html.Div(

                        graph_component(elements),

                        className="graph-container"

                    )

                ],

                className="main-container"

            ),

            create_info_panel(),

            # Guarda o id do nó atualmente destacado pela busca; ao mudar,
            # dispara o callback clientside que centraliza a câmera nele
            # (callbacks/graph_callbacks.py + assets/graph_interactions.js).
            dcc.Store(id="centered-node-store"),

            # Output "morto" exigido pelo Dash para o clientside_callback de
            # centralização de câmera — ele não renderiza nada visível.
            html.Div(id="centering-dummy-output", style={"display": "none"}),

            # Ponte invisível entre o evento nativo de clique no fundo do
            # Cytoscape e o callback Python. O JavaScript dispara este botão
            # quando o usuário toca em uma área sem nós ou arestas.
            html.Button(
                id="clear-graph-highlight",
                n_clicks=0,
                style={"display": "none"},
                **{"aria-hidden": "true"},
            ),

        ]

    )
