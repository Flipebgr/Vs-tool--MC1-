from dash import html, dcc

from utils.entity_style import TYPE_LABELS, RELATION_LABELS
from components.graph import AVAILABLE_LAYOUTS, DEFAULT_LAYOUT


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


def _type_options(filter_options):
    return [
        {"label": TYPE_LABELS.get(t, t), "value": t}
        for t in filter_options.get("types", [])
    ]


def _relation_options(filter_options):
    return [
        {"label": RELATION_LABELS.get(r, r), "value": r}
        for r in filter_options.get("relations", [])
    ]


def _department_options(filter_options):
    return [
        {"label": d["label"], "value": d["value"]}
        for d in filter_options.get("departments", [])
    ]


def create_sidebar(stats, filter_options):

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

            html.H4("Layout"),
            dcc.Dropdown(
                id="layout-select",
                options=[{"label": v, "value": k} for k, v in AVAILABLE_LAYOUTS.items()],
                value=DEFAULT_LAYOUT,
                clearable=False,
            ),

            html.Hr(),

            html.H4("Filtros"),

            html.Label("Tipo de nó", className="filter-label"),
            dcc.Dropdown(
                id="type-filter",
                options=_type_options(filter_options),
                multi=True,
                placeholder="Todos os tipos",
            ),

            html.Br(),

            html.Label("Tipo de relação", className="filter-label"),
            dcc.Dropdown(
                id="relation-filter",
                options=_relation_options(filter_options),
                multi=True,
                placeholder="Todas as relações",
            ),

            html.Br(),

            html.Label("Departamento", className="filter-label"),
            dcc.Dropdown(
                id="department-filter",
                options=_department_options(filter_options),
                multi=True,
                placeholder="Todos os departamentos",
            ),

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
            ),

            html.Div(
                id="search-feedback",
                style={"marginTop": "8px", "fontSize": "12px", "color": "#555"},
            ),

        ],

        className="sidebar"

    )
