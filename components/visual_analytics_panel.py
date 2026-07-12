"""Componentes das visões coordenadas de Visual Analytics investigativo."""

from __future__ import annotations

from dash import dcc, html
import plotly.graph_objects as go

from services.analysis_service import ANOMALY_EVENT_ID
from services.visual_analytics_service import get_case_selector_options


def _blank_figure(message: str = "Selecione um caso para construir a visualização.") -> go.Figure:
    figure = go.Figure()
    figure.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"size": 14, "color": "#64748b"},
    )
    figure.update_layout(
        template="plotly_white",
        height=420,
        margin={"l": 30, "r": 30, "t": 45, "b": 30},
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return figure


def _graph(graph_id: str, height: int = 480) -> dcc.Graph:
    figure = _blank_figure()
    figure.update_layout(height=height)
    return dcc.Graph(
        id=graph_id,
        figure=figure,
        config={"displaylogo": False, "responsive": True},
        responsive=True,
        style={"height": f"{height}px", "minHeight": f"{height}px", "width": "100%"},
        className="visual-analytics-graph",
    )


def create_visual_analytics_controls():
    """Controles compartilhados pelas quatro views de Visual Analytics."""
    return html.Section(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Div("Caso investigado", className="visual-eyebrow"),
                            html.Div(
                                [
                                    dcc.Input(
                                        id="visual-event-id",
                                        type="number",
                                        min=1,
                                        step=1,
                                        value=ANOMALY_EVENT_ID,
                                        debounce=True,
                                    ),
                                    html.Button("Analisar", id="visual-run-button", n_clicks=0),
                                ],
                                className="visual-control-row",
                            ),
                        ],
                        className="visual-event-control-block",
                    ),
                    html.Div(
                        [
                            html.Label("Caso conhecido", htmlFor="visual-case-selector"),
                            dcc.Dropdown(
                                id="visual-case-selector",
                                options=get_case_selector_options(),
                                value=ANOMALY_EVENT_ID,
                                clearable=False,
                                searchable=False,
                            ),
                        ],
                        className="visual-case-selector-wrap",
                    ),
                    html.Div(
                        [
                            html.Button(
                                "Localizar na Timeline",
                                id="visual-locate-timeline-button",
                                n_clicks=0,
                                className="secondary-action-button",
                            ),
                            html.Button(
                                "Limpar destaque",
                                id="visual-clear-selection",
                                n_clicks=0,
                                className="secondary-action-button",
                            ),
                        ],
                        className="visual-control-actions",
                    ),
                ],
                className="visual-analytics-toolbar workspace-visual-toolbar",
            ),
            html.Div(
                [
                    html.Div(id="visual-analytics-status", className="visual-analytics-status"),
                    html.Div(id="visual-analytics-feedback", className="visual-analytics-feedback"),
                ],
                className="visual-toolbar-messages",
            ),
        ],
        id="visual-analytics-shared-controls",
        className="visual-analytics-shared-controls",
    )


def create_visual_overview_view():
    return html.Section(
        [
            html.Div(id="visual-case-identity", className="visual-case-identity"),
            html.Div(id="visual-summary-cards", className="visual-summary-cards"),
            html.Div(
                [
                    html.Div(
                        [
                            html.H3("Composição da cadeia essencial"),
                            _graph("visual-category-chart", 390),
                        ],
                        className="visual-analytics-card visual-overview-chart",
                    ),
                    html.Div(
                        [
                            html.H3("Síntese investigativa"),
                            html.Div(id="visual-analysis-summary"),
                        ],
                        className="visual-analytics-card visual-overview-summary",
                    ),
                ],
                className="visual-overview-grid",
            ),
        ],
        className="workspace-panel visual-workspace-panel",
    )


def create_evidence_flow_view():
    return html.Section(
        [
            html.Div(
                [
                    html.H3("Fluxo rastreável"),
                    html.P(
                        "Clique em um agente ou sistema para destacá-lo no grafo organizacional.",
                        className="visual-help-text",
                    ),
                ],
                className="workspace-section-heading",
            ),
            html.Div(
                _graph("evidence-flow-graph", 650),
                className="visual-analytics-card visual-full-chart-card",
            ),
            html.Div(id="evidence-flow-detail", className="visual-context-detail"),
        ],
        className="workspace-panel visual-workspace-panel",
    )


def create_participation_view():
    return html.Section(
        [
            html.Div(
                [
                    html.H3("Entidade × ação"),
                    html.P(
                        "A intensidade representa quantos eventos essenciais vinculam a entidade à ação.",
                        className="visual-help-text",
                    ),
                ],
                className="workspace-section-heading",
            ),
            html.Div(
                _graph("participation-matrix", 620),
                className="visual-analytics-card visual-full-chart-card",
            ),
            html.Div(id="participation-detail", className="visual-context-detail"),
        ],
        className="workspace-panel visual-workspace-panel",
    )


def create_similar_cases_view():
    return html.Section(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.H3("Comparação histórica"),
                            html.P(
                                "Alterne entre escala, sequência, valores exatos e intervenção sem comprimir os gráficos.",
                                className="visual-help-text",
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Label("Escala", htmlFor="comparison-scale-mode"),
                                    dcc.RadioItems(
                                        id="comparison-scale-mode",
                                        options=[
                                            {"label": "Normalizada", "value": "normalized"},
                                            {"label": "Absoluta", "value": "absolute"},
                                        ],
                                        value="normalized",
                                        inline=True,
                                        className="comparison-radio",
                                    ),
                                ],
                                className="comparison-control",
                            ),
                            html.Div(
                                [
                                    html.Label("Métrica", htmlFor="comparison-metric"),
                                    dcc.Dropdown(
                                        id="comparison-metric",
                                        options=[
                                            {"label": "Todas", "value": "all"},
                                            {"label": "Eventos relacionados", "value": "related_events"},
                                            {"label": "Transferências", "value": "transfers"},
                                            {"label": "Entidades", "value": "entities"},
                                        ],
                                        value="all",
                                        clearable=False,
                                        searchable=False,
                                    ),
                                ],
                                className="comparison-control comparison-metric-control",
                            ),
                        ],
                        className="comparison-controls",
                    ),
                ],
                className="similar-cases-heading",
            ),
            dcc.Tabs(
                id="similar-cases-tabs",
                value="comparison",
                className="similar-cases-tabs",
                children=[
                    dcc.Tab(
                        label="Comparação",
                        value="comparison",
                        children=html.Div(
                            [
                                html.Div(
                                    [
                                        html.H3("Escala dos casos"),
                                        _graph("case-comparison-chart", 520),
                                    ],
                                    className="visual-analytics-card similar-cases-chart-card",
                                )
                            ],
                            className="similar-tab-content",
                        ),
                    ),
                    dcc.Tab(
                        label="Sequências",
                        value="sequences",
                        children=html.Div(
                            [
                                html.Div(
                                    [
                                        html.H3("Sequência operacional"),
                                        _graph("case-sequence-chart", 540),
                                    ],
                                    className="visual-analytics-card similar-cases-chart-card",
                                )
                            ],
                            className="similar-tab-content",
                        ),
                    ),
                    dcc.Tab(
                        label="Valores exatos",
                        value="values",
                        children=html.Div(
                            [
                                html.Div(
                                    [
                                        html.H3("Valores exatos"),
                                        html.Div(id="case-comparison-table"),
                                    ],
                                    className="visual-analytics-card similar-cases-table-card",
                                )
                            ],
                            className="similar-tab-content",
                        ),
                    ),
                    dcc.Tab(
                        label="Intervenção",
                        value="intervention",
                        children=html.Div(
                            [
                                html.Div(
                                    [
                                        html.H3("Ponto de intervenção"),
                                        _graph("intervention-diagram", 420),
                                        html.Div(id="intervention-summary"),
                                    ],
                                    className="visual-analytics-card visual-intervention-card",
                                )
                            ],
                            className="similar-tab-content",
                        ),
                    ),
                ],
            ),
        ],
        className="workspace-panel visual-workspace-panel similar-cases-panel",
    )


def create_visual_analytics_panel():
    """Compatibilidade com layouts anteriores; o workspace usa as views separadas."""
    return html.Section(
        [
            create_visual_analytics_controls(),
            create_visual_overview_view(),
            create_evidence_flow_view(),
            create_participation_view(),
            create_similar_cases_view(),
        ],
        className="visual-analytics-panel",
    )
