"""Callbacks de navegação entre as views do workspace."""

from dash import Input, Output, ctx


VIEWS = [
    "graph",
    "timeline",
    "chain",
    "overview",
    "evidence-flow",
    "participation",
    "similar-cases",
    "investigation",
]

VIEW_METADATA = {
    "graph": (
        "Grafo organizacional",
        "Explore pessoas, agentes, departamentos, equipes, sistemas e suas relações estruturais.",
    ),
    "timeline": (
        "Linha do tempo",
        "Localize eventos, aproxime períodos e selecione o ponto inicial da investigação.",
    ),
    "chain": (
        "Cadeia de eventos",
        "Reconstrua a sequência essencial ou inspecione todos os eventos relacionados.",
    ),
    "overview": (
        "Visão geral do caso",
        "Leia os indicadores centrais e a composição da cadeia investigada.",
    ),
    "evidence-flow": (
        "Fluxo da evidência",
        "Acompanhe instruções, artefatos, agentes e sistemas até a publicação.",
    ),
    "participation": (
        "Matriz de participação",
        "Compare os papéis desempenhados por cada entidade na cadeia essencial.",
    ),
    "similar-cases": (
        "Casos semelhantes",
        "Compare recorrência, sequência operacional, valores exatos e ponto de intervenção.",
    ),
    "investigation": (
        "Análise investigativa",
        "Consulte evidências diretas, inferências suportadas, limitações e recomendações.",
    ),
}


def register(app):
    nav_inputs = [Input(f"workspace-nav-{view}", "n_clicks") for view in VIEWS]

    @app.callback(
        Output("active-view-store", "data"),
        *nav_inputs,
        prevent_initial_call=True,
    )
    def choose_view(*_clicks):
        triggered = ctx.triggered_id
        prefix = "workspace-nav-"
        if isinstance(triggered, str) and triggered.startswith(prefix):
            view = triggered[len(prefix):]
            if view in VIEWS:
                return view
        return "graph"

    @app.callback(
        *[Output(f"workspace-nav-{view}", "className") for view in VIEWS],
        *[Output(f"workspace-view-{view}", "className") for view in VIEWS],
        Output("workspace-view-title", "children"),
        Output("workspace-view-description", "children"),
        Output("visual-analytics-shared-controls", "className"),
        Input("active-view-store", "data"),
    )
    def render_active_view(active_view):
        active_view = active_view if active_view in VIEWS else "graph"
        nav_classes = [
            "workspace-nav-button is-active" if view == active_view else "workspace-nav-button"
            for view in VIEWS
        ]
        view_classes = [
            "workspace-view is-active" if view == active_view else "workspace-view"
            for view in VIEWS
        ]
        title, description = VIEW_METADATA[active_view]
        visual_class = (
            "visual-analytics-shared-controls is-visible"
            if active_view in {"overview", "evidence-flow", "participation", "similar-cases"}
            else "visual-analytics-shared-controls"
        )
        return (*nav_classes, *view_classes, title, description, visual_class)

    app.clientside_callback(
        """
        function(activeView, comparisonTab) {
            function resizeActiveView() {
                if (window.Plotly && (activeView === 'timeline' || activeView === 'chain')) {
                    const plotId = activeView === 'timeline' ? 'timeline-graph' : 'chain-graph';
                    const container = document.getElementById(plotId);
                    const plot = container && (
                        container.matches('.js-plotly-plot')
                            ? container
                            : container.querySelector('.js-plotly-plot')
                    );
                    const isVisible = plot && plot.getClientRects().length > 0;
                    if (isVisible && plot._fullLayout && Array.isArray(plot.data)) {
                        window.Plotly.Plots.resize(plot);
                    }
                }
                if (activeView === 'graph') {
                    const graph = document.getElementById('graph');
                    const cy = graph && graph._cyreg && graph._cyreg.cy;
                    if (cy && typeof cy.resize === 'function') {
                        cy.resize();
                    }
                }
                window.dispatchEvent(new Event('resize'));
            }
            window.setTimeout(function() {
                resizeActiveView();
            }, 100);
            return String(activeView || '') + ':' + String(comparisonTab || '');
        }
        """,
        Output("workspace-resize-dummy", "children"),
        Input("active-view-store", "data"),
        Input("similar-cases-tabs", "value"),
    )
