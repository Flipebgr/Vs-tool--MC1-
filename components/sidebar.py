from dash import html, dcc


def _type_breakdown_rows(stats):
    rows = []
    for item in stats.get("by_type", []):
        rows.append(
            html.Div(
                [
                    html.Span(
                        style={
                            "display": "inline-block",
                            "width": "10px",
                            "height": "10px",
                            "borderRadius": "50%",
                            "backgroundColor": item["color"],
                            "marginRight": "6px",
                        }
                    ),
                    html.Span(f"{item['label']}: {item['count']}"),
                ],
                style={"marginBottom": "4px"},
            )
        )
    return rows


def create_sidebar(stats):

    return html.Div(

        [

            html.H3("Organização"),

            html.Hr(),

            html.P(
                """
                Grafo unificado da Tenant Thread.
                Representa departamentos, funcionários,
                agentes e sistemas.
                """
            ),

            html.H4("Resumo"),

            html.P(f"Nós: {stats['nodes']}"),

            html.P(f"Arestas: {stats['edges']}"),

            html.Div(_type_breakdown_rows(stats)),

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
