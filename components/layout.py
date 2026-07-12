from dash import html, dcc

from components.header import create_header
from components.workspace import create_workspace


def create_layout(elements, stats, filter_options):
    return html.Div(
        [
            create_header(),
            create_workspace(elements, stats, filter_options),

            # Estado de navegação entre as visualizações.
            dcc.Store(id="active-view-store", data="graph"),

            # Guarda o id do nó atualmente destacado pela busca ou seleção.
            dcc.Store(id="centered-node-store"),

            # Cadeia reconstruída a partir do evento selecionado na Timeline.
            dcc.Store(id="event-chain-store"),

            # Resultado estruturado das Questões 1, 2 e 3.
            dcc.Store(id="analysis-store"),

            # Modelo e seleção compartilhados pelas visões coordenadas.
            dcc.Store(id="visual-analytics-store"),
            dcc.Store(id="visual-analytics-selection-store"),
            dcc.Store(id="visual-timeline-request-store"),

            # Outputs invisíveis de callbacks clientside.
            html.Div(id="centering-dummy-output", style={"display": "none"}),
            html.Div(id="workspace-resize-dummy", style={"display": "none"}),

            # Ponte invisível para limpar destaque ao clicar no fundo do grafo.
            html.Button(
                id="clear-graph-highlight",
                n_clicks=0,
                style={"display": "none"},
                **{"aria-hidden": "true"},
            ),
        ]
    )
