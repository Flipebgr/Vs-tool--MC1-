"""Shell principal da aplicação com navegação lateral persistente."""

from dash import html

from components.navigation_sidebar import create_navigation_sidebar
from components.sidebar import create_sidebar
from components.graph import graph_component
from components.info_panel import create_info_panel
from components.timeline import create_timeline
from components.chain_panel import create_chain_panel
from components.analysis_panel import create_analysis_panel
from components.visual_analytics_panel import (
    create_visual_analytics_controls,
    create_visual_overview_view,
    create_evidence_flow_view,
    create_participation_view,
    create_similar_cases_view,
)


def _view(view_name: str, content, active: bool = False):
    return html.Div(
        content,
        id=f"workspace-view-{view_name}",
        className="workspace-view is-active" if active else "workspace-view",
    )


def _graph_view(elements, stats, filter_options):
    return html.Div(
        [
            html.Div(
                [
                    create_sidebar(stats, filter_options),
                    html.Div(graph_component(elements), className="workspace-graph-canvas"),
                ],
                className="workspace-graph-layout",
            ),
            create_info_panel(),
        ],
        className="workspace-panel workspace-graph-panel",
    )


def create_workspace(elements, stats, filter_options):
    return html.Div(
        [
            create_navigation_sidebar(),
            html.Main(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div("Workspace investigativo", className="workspace-view-kicker"),
                                    html.H2("Grafo organizacional", id="workspace-view-title"),
                                    html.P(
                                        "Explore pessoas, agentes, departamentos, equipes, sistemas e suas relações estruturais.",
                                        id="workspace-view-description",
                                    ),
                                ]
                            ),
                            html.Div(
                                [
                                    html.Span("Estado preservado", className="workspace-state-badge"),
                                    html.Span(
                                        "Evento · período · cadeia · destaque",
                                        className="workspace-state-description",
                                    ),
                                ],
                                className="workspace-state-summary",
                            ),
                        ],
                        className="workspace-view-header",
                    ),
                    create_visual_analytics_controls(),
                    html.Div(
                        [
                            _view("graph", _graph_view(elements, stats, filter_options), active=True),
                            _view("timeline", create_timeline()),
                            _view("chain", create_chain_panel()),
                            _view("overview", create_visual_overview_view()),
                            _view("evidence-flow", create_evidence_flow_view()),
                            _view("participation", create_participation_view()),
                            _view("similar-cases", create_similar_cases_view()),
                            _view("investigation", create_analysis_panel()),
                        ],
                        className="workspace-view-stack",
                    ),
                ],
                className="workspace-main",
            ),
        ],
        className="application-workspace",
    )
