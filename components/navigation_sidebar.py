"""Navegação vertical do workspace investigativo."""

from dash import html


NAVIGATION_GROUPS = [
    (
        "Estrutura",
        [
            ("graph", "Grafo organizacional", "Estrutura, filtros e relações"),
        ],
    ),
    (
        "Cronologia",
        [
            ("timeline", "Linha do tempo", "Densidade, zoom e eventos"),
            ("chain", "Cadeia de eventos", "Sequência essencial e completa"),
        ],
    ),
    (
        "Visual Analytics",
        [
            ("overview", "Visão geral", "Resumo visual do caso"),
            ("evidence-flow", "Fluxo da evidência", "Agentes, arquivos e sistemas"),
            ("participation", "Participação", "Entidade × tipo de ação"),
            ("similar-cases", "Casos semelhantes", "Recorrência e intervenção"),
        ],
    ),
    (
        "Conclusões",
        [
            ("investigation", "Análise investigativa", "Evidências, limites e resposta"),
        ],
    ),
]


def create_navigation_sidebar():
    groups = []
    for group_label, items in NAVIGATION_GROUPS:
        groups.append(html.Div(group_label, className="workspace-nav-group-label"))
        for view, label, description in items:
            groups.append(
                html.Button(
                    [
                        html.Span(label, className="workspace-nav-label"),
                        html.Span(description, className="workspace-nav-description"),
                    ],
                    id=f"workspace-nav-{view}",
                    n_clicks=0,
                    className=(
                        "workspace-nav-button is-active"
                        if view == "graph"
                        else "workspace-nav-button"
                    ),
                    title=description,
                )
            )

    return html.Aside(
        [
            html.Div(
                [
                    html.Div("Navegação", className="workspace-nav-kicker"),
                    html.H3("Visualizações", className="workspace-nav-title"),
                    html.P(
                        "Alterne a perspectiva sem perder o evento, o período ou os destaques atuais.",
                        className="workspace-nav-help",
                    ),
                ],
                className="workspace-nav-heading",
            ),
            html.Nav(groups, className="workspace-nav-list", **{"aria-label": "Visualizações"}),
        ],
        className="workspace-navigation",
    )
