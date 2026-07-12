"""Callbacks das visões coordenadas de Visual Analytics."""

from __future__ import annotations

from dash import Input, Output, State, ctx, html, no_update
import plotly.graph_objects as go

from components.visual_analytics_panel import _blank_figure
from services.visual_analytics_service import (
    EVENT_CATEGORY_COLORS,
    build_visual_analytics_model,
)


def _safe_model(model):
    return model if isinstance(model, dict) and model.get("status") == "ok" else None


def _case_identity(overview: dict):
    return html.Div(
        [
            html.Div(
                [
                    html.Span("Caso ativo", className="visual-eyebrow"),
                    html.Strong(f"Evento {overview['event_id']} — {overview['short_name']}"),
                    html.Span(overview["event_time_label"]),
                ]
            ),
            html.Div(
                [
                    html.Span("Conteúdo", className="visual-eyebrow"),
                    html.Strong(overview["artifact"]),
                    html.Span(f"Instrução: {overview['instruction_file']}"),
                ]
            ),
            html.Div(
                [
                    html.Span("Execução", className="visual-eyebrow"),
                    html.Strong(f"{overview['publisher']} → {overview['system']}"),
                    html.Span(f"Origem observada: {overview['origin']}"),
                ]
            ),
        ],
        className="visual-case-identity-grid",
    )


def _summary_cards(overview: dict):
    cards = []
    for card in overview.get("cards", []):
        cards.append(
            html.Div(
                [
                    html.Span(card["label"]),
                    html.Strong(str(card["value"])),
                ],
                className=f"visual-summary-card visual-summary-{card.get('kind', 'value')}",
            )
        )
    return cards


def _category_figure(overview: dict) -> go.Figure:
    rows = overview.get("category_counts", [])
    figure = go.Figure(
        go.Bar(
            x=[row["category"] for row in rows],
            y=[row["count"] for row in rows],
            marker_color=[row["color"] for row in rows],
            text=[row["count"] for row in rows],
            textposition="outside",
            hovertemplate="%{x}: %{y} evento(s)<extra></extra>",
        )
    )
    figure.update_layout(
        template="plotly_white",
        height=330,
        margin={"l": 45, "r": 20, "t": 20, "b": 55},
        yaxis={"title": "Eventos", "rangemode": "tozero", "dtick": 1},
        xaxis={"title": "Categoria"},
        showlegend=False,
    )
    return figure


def _analysis_summary(model: dict):
    summary = model.get("analysis_summary", {})
    return html.Div(
        [
            html.Div([html.Strong("Produção"), html.P(summary.get("q1", ""))]),
            html.Div([html.Strong("Origem e significado"), html.P(summary.get("q2", ""))]),
            html.Div([html.Strong("Recorrência e prevenção"), html.P(summary.get("q3", ""))]),
        ],
        className="visual-analysis-summary-list",
    )


def _flow_figure(flow: dict) -> go.Figure:
    nodes = flow.get("nodes", [])
    links = flow.get("links", [])
    if not nodes:
        return _blank_figure("Nenhum fluxo de evidência disponível.")

    node_custom = [
        [node.get("token", ""), f"Tipo: {node.get('entity_type') or node.get('artifact_role') or node.get('kind')}"]
        for node in nodes
    ]
    link_custom = [
        [link.get("token", ""), link.get("hover", link.get("label", ""))]
        for link in links
    ]
    figure = go.Figure(
        go.Sankey(
            arrangement="snap",
            node={
                "label": [node["label"] for node in nodes],
                "color": [node.get("color", "#64748b") for node in nodes],
                "customdata": node_custom,
                "pad": 22,
                "thickness": 20,
                "line": {"color": "rgba(15,23,42,0.38)", "width": 0.8},
                "hovertemplate": "%{label}<br>%{customdata[1]}<extra></extra>",
            },
            link={
                "source": [link["source"] for link in links],
                "target": [link["target"] for link in links],
                "value": [link["value"] for link in links],
                "color": [link.get("color", "rgba(100,116,139,0.45)") for link in links],
                "customdata": link_custom,
                "hovertemplate": "%{customdata[1]}<extra></extra>",
            },
        )
    )
    figure.update_layout(
        template="plotly_white",
        height=520,
        margin={"l": 20, "r": 20, "t": 35, "b": 20},
        title={"text": "Fluxo rastreável de instruções, conteúdo, agentes e sistemas", "x": 0.02},
        font={"size": 12},
    )
    return figure


def _matrix_figure(participation: dict) -> go.Figure:
    entities = participation.get("entities", [])
    categories = participation.get("categories", [])
    values = participation.get("values", [])
    event_ids = participation.get("event_ids", [])
    if not entities:
        return _blank_figure("Nenhuma participação disponível.")

    customdata = []
    annotations = []
    for row_index, entity in enumerate(entities):
        custom_row = []
        for col_index, category in enumerate(categories):
            ids = event_ids[row_index][col_index]
            ids_text = ", ".join(str(item) for item in ids) if ids else "nenhum"
            token = f"matrix|{entity['id']}|{category}|{','.join(str(item) for item in ids)}"
            custom_row.append([token, ids_text])
            value = values[row_index][col_index]
            if value:
                annotations.append(
                    {
                        "x": category,
                        "y": entity["label"],
                        "text": str(value),
                        "showarrow": False,
                        "font": {"color": "#0f172a", "size": 12},
                    }
                )
        customdata.append(custom_row)

    figure = go.Figure(
        go.Heatmap(
            z=values,
            x=categories,
            y=[entity["label"] for entity in entities],
            customdata=customdata,
            colorscale=[
                [0.0, "#f8fafc"],
                [0.15, "#dbeafe"],
                [0.50, "#60a5fa"],
                [1.0, "#1d4ed8"],
            ],
            zmin=0,
            zmax=max(1, participation.get("max_value", 1)),
            colorbar={"title": "Eventos", "thickness": 12},
            hovertemplate=(
                "%{y}<br>%{x}: %{z} evento(s)<br>IDs: %{customdata[1]}<extra></extra>"
            ),
            xgap=2,
            ygap=2,
        )
    )
    figure.update_layout(
        template="plotly_white",
        height=max(430, 62 * len(entities)),
        margin={"l": 150, "r": 55, "t": 35, "b": 65},
        title={"text": "Entidade × ação na cadeia essencial", "x": 0.02},
        annotations=annotations,
        xaxis={"side": "top", "title": "Categoria de evento"},
        yaxis={"title": "Entidade", "autorange": "reversed"},
    )
    return figure


def _comparison_figure(comparison: dict, scale_mode: str = "normalized", metric: str = "all") -> go.Figure:
    cases = comparison.get("cases", [])
    if not cases:
        return _blank_figure("Nenhum caso comparável disponível.")

    labels = [f"{case['event_id']}<br>{case['artifact']}" for case in cases]
    metric_defs = {
        "related_events": ("Eventos relacionados", "#4f46e5"),
        "transfers": ("Transferências", "#ef4444"),
        "entities": ("Entidades", "#14b8a6"),
    }
    selected_metrics = list(metric_defs) if metric == "all" else [metric]
    selected_metrics = [key for key in selected_metrics if key in metric_defs]
    if not selected_metrics:
        selected_metrics = list(metric_defs)

    figure = go.Figure()
    for key in selected_metrics:
        label, color = metric_defs[key]
        raw_values = [int(case.get(key, 0)) for case in cases]
        if scale_mode == "normalized":
            maximum = max(raw_values) or 1
            plotted = [(value / maximum) * 100 for value in raw_values]
            figure.add_bar(
                name=label,
                x=labels,
                y=plotted,
                marker_color=color,
                text=[str(value) for value in raw_values],
                textposition="outside",
                customdata=raw_values,
                hovertemplate=(
                    "%{x}<br>" + label + ": %{customdata}<br>"
                    "Escala relativa: %{y:.1f}%<extra></extra>"
                ),
            )
        else:
            figure.add_bar(
                name=label,
                x=labels,
                y=raw_values,
                marker_color=color,
                text=[str(value) for value in raw_values],
                textposition="outside",
                hovertemplate="%{x}<br>" + label + ": %{y}<extra></extra>",
            )

    normalized = scale_mode == "normalized"
    figure.update_layout(
        template="plotly_white",
        height=520,
        barmode="group",
        margin={"l": 65, "r": 30, "t": 75, "b": 95},
        yaxis={
            "title": "Percentual do maior caso por métrica" if normalized else "Contagem",
            "rangemode": "tozero",
            "range": [0, 118] if normalized else None,
            "ticksuffix": "%" if normalized else "",
        },
        xaxis={"title": "Caso", "automargin": True},
        legend={"orientation": "h", "y": 1.12, "x": 0},
        uniformtext={"minsize": 10, "mode": "show"},
    )
    return figure

def _sequence_figure(comparison: dict) -> go.Figure:
    rows = comparison.get("sequence", [])
    cases = comparison.get("cases", [])
    if not rows:
        return _blank_figure("Nenhuma sequência comparável disponível.")
    stage_order = ["Origem", "Instrução", "Transferência final", "Publicação", "Exclusão"]
    y_order = [f"{case['event_id']} — {case['artifact']}" for case in cases]
    figure = go.Figure()
    for case in cases:
        case_rows = [row for row in rows if row["event_id"] == case["event_id"]]
        figure.add_trace(
            go.Scatter(
                x=[row["stage_index"] for row in case_rows],
                y=[f"{case['event_id']} — {case['artifact']}" for _ in case_rows],
                mode="lines+markers+text",
                line={"width": 3 if case["active"] else 1.7},
                marker={"size": 13 if case["active"] else 10, "symbol": "diamond" if case["active"] else "circle"},
                text=[str(row["source_event_id"]) for row in case_rows],
                textposition="top center",
                customdata=[[row["event_time_label"], row["source_event_id"]] for row in case_rows],
                hovertemplate=(
                    f"{case['artifact']}<br>Evento %{{customdata[1]}}<br>%{{customdata[0]}}<extra></extra>"
                ),
                name=str(case["event_id"]),
                showlegend=False,
            )
        )
    figure.update_layout(
        template="plotly_white",
        height=540,
        margin={"l": 210, "r": 35, "t": 45, "b": 95},
        xaxis={
            "tickmode": "array",
            "tickvals": list(range(len(stage_order))),
            "ticktext": stage_order,
            "title": "Etapa operacional",
        },
        yaxis={"categoryorder": "array", "categoryarray": list(reversed(y_order))},
    )
    return figure


def _comparison_table(comparison: dict):
    cases = comparison.get("cases", [])
    header = html.Thead(
        html.Tr(
            [
                html.Th("Caso"),
                html.Th("Origem"),
                html.Th("Eventos"),
                html.Th("Transferências"),
                html.Th("Entidades"),
                html.Th("Duração"),
                html.Th("Última transferência"),
                html.Th("Exclusões"),
            ]
        )
    )
    body_rows = []
    for case in cases:
        cleanup_values = [case.get("cleanup_instruction_seconds"), case.get("cleanup_content_seconds")]
        cleanup_label = " / ".join(
            f"+{int(value)}s" for value in cleanup_values if value is not None
        ) or "—"
        body_rows.append(
            html.Tr(
                [
                    html.Td(
                        [
                            html.Strong(f"{case['event_id']} — {case['artifact']}"),
                            html.Br(),
                            html.Small("Caso ativo" if case["active"] else case["event_time_label"]),
                        ],
                        className="active-case-cell" if case["active"] else "",
                    ),
                    html.Td(case["origin"]),
                    html.Td(case["related_events"]),
                    html.Td(case["transfers"]),
                    html.Td(case["entities"]),
                    html.Td(case["duration_label"]),
                    html.Td(f"-{int(case['final_handoff_seconds'])}s"),
                    html.Td(cleanup_label),
                ]
            )
        )
    return html.Div(
        html.Table([header, html.Tbody(body_rows)], className="visual-comparison-table"),
        className="visual-comparison-table-wrap",
    )


def _intervention_figure(intervention: dict) -> go.Figure:
    steps = intervention.get("steps", [])
    x_values = [step["index"] for step in steps]
    labels = [step["label"] for step in steps]
    colors = ["#dc2626" if step["kind"] == "control" else "#64748b" for step in steps]
    sizes = [30 if step["kind"] == "control" else 20 for step in steps]
    figure = go.Figure(
        go.Scatter(
            x=x_values,
            y=[1] * len(steps),
            mode="lines+markers+text",
            line={"color": "#94a3b8", "width": 4},
            marker={"color": colors, "size": sizes, "line": {"color": "#ffffff", "width": 2}},
            text=labels,
            textposition="bottom center",
            hovertemplate="%{text}<extra></extra>",
        )
    )
    figure.add_vrect(
        x0=2.65,
        x1=3.35,
        fillcolor="rgba(220,38,38,0.10)",
        line_color="#dc2626",
        line_width=2,
        annotation_text="PONTO DE CONTROLE",
        annotation_position="top",
    )
    figure.update_layout(
        template="plotly_white",
        height=330,
        margin={"l": 30, "r": 30, "t": 55, "b": 95},
        xaxis={"visible": False, "range": [-0.35, 4.35]},
        yaxis={"visible": False, "range": [0.62, 1.28]},
        showlegend=False,
    )
    return figure


def _intervention_summary(intervention: dict):
    return html.Div(
        [
            html.Div(
                [
                    html.Span("Controle recomendado", className="visual-eyebrow"),
                    html.Strong(intervention.get("control_point", "")),
                    html.P(intervention.get("primary_action", "")),
                ],
                className="visual-intervention-primary",
            ),
            html.Div(
                [
                    html.Span("Cobertura observada", className="visual-eyebrow"),
                    html.Strong(intervention.get("coverage", "")),
                    html.P(intervention.get("why", "")),
                ],
                className="visual-intervention-coverage",
            ),
            html.Div(
                [
                    html.Span("Controles complementares", className="visual-eyebrow"),
                    html.Ul([html.Li(item) for item in intervention.get("secondary_controls", [])]),
                ],
                className="visual-intervention-secondary",
            ),
        ],
        className="visual-intervention-summary",
    )


def _token_from_click(click_data):
    if not click_data or not click_data.get("points"):
        return None
    custom = click_data["points"][0].get("customdata")
    if isinstance(custom, (list, tuple)):
        return custom[0] if custom else None
    return custom


def register(app):
    @app.callback(
        Output("visual-analytics-store", "data"),
        Output("visual-analytics-status", "children"),
        Output("visual-event-id", "value"),
        Input("chain-start-store", "data"),
        Input("visual-run-button", "n_clicks"),
        Input("visual-case-selector", "value"),
        State("visual-event-id", "value"),
    )
    def update_model(chain_start, _run_clicks, selected_case, typed_event_id):
        triggered = ctx.triggered_id
        requested = typed_event_id
        if triggered == "chain-start-store" and chain_start and chain_start.get("type") == "event":
            requested = chain_start.get("id")
        elif triggered == "visual-case-selector":
            requested = selected_case
        elif triggered is None:
            requested = selected_case or typed_event_id

        model = build_visual_analytics_model(requested)
        if model.get("status") != "ok":
            return model, model.get("message", "Não foi possível analisar o evento."), requested
        overview = model["overview"]
        status = (
            f"Evento {overview['event_id']} analisado · {overview['artifact']} · "
            f"{len(model['comparison']['cases'])} casos conhecidos."
        )
        return model, status, overview["event_id"]

    @app.callback(
        Output("visual-case-identity", "children"),
        Output("visual-summary-cards", "children"),
        Output("visual-category-chart", "figure"),
        Output("visual-analysis-summary", "children"),
        Output("evidence-flow-graph", "figure"),
        Output("evidence-flow-detail", "children"),
        Output("participation-matrix", "figure"),
        Output("participation-detail", "children"),
        Output("case-comparison-chart", "figure"),
        Output("case-sequence-chart", "figure"),
        Output("case-comparison-table", "children"),
        Output("intervention-diagram", "figure"),
        Output("intervention-summary", "children"),
        Input("visual-analytics-store", "data"),
        Input("comparison-scale-mode", "value"),
        Input("comparison-metric", "value"),
    )
    def render_model(model, comparison_scale_mode, comparison_metric):
        valid = _safe_model(model)
        if not valid:
            blank = _blank_figure(model.get("message", "Sem dados.") if isinstance(model, dict) else "Sem dados.")
            return (
                "Nenhum caso carregado.",
                [],
                blank,
                "",
                blank,
                "",
                blank,
                "",
                blank,
                blank,
                "",
                blank,
                "",
            )
        overview = valid["overview"]
        return (
            _case_identity(overview),
            _summary_cards(overview),
            _category_figure(overview),
            _analysis_summary(valid),
            _flow_figure(valid["flow"]),
            "Selecione um nó ou ligação do fluxo para consultar seu contexto.",
            _matrix_figure(valid["participation"]),
            "Selecione uma célula para ver os eventos e destacar a entidade no grafo.",
            _comparison_figure(
                valid["comparison"],
                comparison_scale_mode or "normalized",
                comparison_metric or "all",
            ),
            _sequence_figure(valid["comparison"]),
            _comparison_table(valid["comparison"]),
            _intervention_figure(valid["intervention"]),
            _intervention_summary(valid["intervention"]),
        )

    @app.callback(
        Output("visual-analytics-selection-store", "data"),
        Output("visual-analytics-feedback", "children"),
        Input("evidence-flow-graph", "clickData"),
        Input("participation-matrix", "clickData"),
        Input("visual-clear-selection", "n_clicks"),
        prevent_initial_call=True,
    )
    def select_visual_context(flow_click, matrix_click, _clear_clicks):
        triggered = ctx.triggered_id
        if triggered == "visual-clear-selection":
            return None, "Destaque visual removido."

        token = _token_from_click(flow_click if triggered == "evidence-flow-graph" else matrix_click)
        if not token:
            return no_update, no_update

        parts = str(token).split("|")
        kind = parts[0]
        if kind == "entity" and len(parts) >= 2:
            entity_id = parts[1]
            return (
                {"type": "entity", "entity_ids": [entity_id], "source": "flow"},
                f"Entidade selecionada no fluxo: {entity_id}",
            )
        if kind == "artifact" and len(parts) >= 2:
            artifact = "|".join(parts[1:])
            return (
                {"type": "artifact", "artifact": artifact, "entity_ids": [], "source": "flow"},
                f"Artefato selecionado: {artifact}. Ele não é um nó estrutural do grafo.",
            )
        if kind == "events" and len(parts) >= 2:
            event_ids = [int(value) for value in parts[1].split(",") if value.isdigit()]
            return (
                {"type": "events", "event_ids": event_ids, "entity_ids": [], "source": "flow"},
                f"Ligação sustentada pelos eventos: {', '.join(map(str, event_ids))}",
            )
        if kind == "matrix" and len(parts) >= 4:
            entity_id, category, ids_text = parts[1], parts[2], parts[3]
            event_ids = [int(value) for value in ids_text.split(",") if value.isdigit()]
            return (
                {
                    "type": "matrix",
                    "entity_ids": [entity_id],
                    "event_type": category,
                    "event_ids": event_ids,
                    "source": "matrix",
                },
                f"{entity_id} × {category}: {len(event_ids)} evento(s) — {', '.join(map(str, event_ids)) or 'nenhum'}",
            )
        return no_update, no_update

    @app.callback(
        Output("visual-timeline-request-store", "data"),
        Input("visual-locate-timeline-button", "n_clicks"),
        State("visual-analytics-store", "data"),
        prevent_initial_call=True,
    )
    def request_timeline_location(_clicks, model):
        valid = _safe_model(model)
        if not valid:
            return no_update
        return {"event_id": valid["seed_event_id"], "request_id": int(_clicks or 0)}
