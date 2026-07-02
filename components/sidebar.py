from dash import html, dcc

def create_sidebar(stats):

    return html.Div(

        [

            html.H3("Organização"),

            html.Hr(),

            html.P(
                """
                Organograma da Tenant Thread.
                Representa departamentos, funcionários,
                agentes e sistemas.
                """
            ),

            html.H4("Resumo"),

            html.P(f"Nós: {stats['nodes']}"),

            html.P(f"Arestas: {stats['edges']}"),

            html.Hr(),

            html.H4("Buscar"),

            dcc.Input(
            id="search-node",
            type="text",
            placeholder="John Windward...",
            style={"width": "100%"}
            ),

            html.Br(),

            html.Br(),

            html.Button(
                "Pesquisar",
                id="search-button"
            )

        ],

        className="sidebar"

    )