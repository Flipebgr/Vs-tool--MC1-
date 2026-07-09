"""Painel de respostas investigativas das Questões 1, 2 e 3."""

from __future__ import annotations

import pandas as pd
from dash import dcc, html

LEVEL_LABELS = {
    "direct": "Evidência direta",
    "inference": "Inferência suportada",
    "limitation": "Limitação",
    "recommendation": "Recomendação",
}


def _placeholder():
    return html.Div(
        [
            html.Strong("Análise ainda não executada."),
            html.P("Use o evento 373902 ou selecione outro evento na Timeline e clique em Analisar."),
        ],
        className="analysis-placeholder",
    )


def _metric_cards(metrics: dict):
    labels = [
        ("Eventos essenciais", metrics.get("essential_events")),
        ("Eventos relacionados", metrics.get("related_events")),
        ("Transferências", metrics.get("transfers")),
        ("Entidades", metrics.get("entities")),
        ("Duração", metrics.get("duration")),
        ("Handoff final", f"{int(metrics.get('final_handoff_seconds') or 0)}s antes"),
    ]
    return html.Div(
        [
            html.Div(
                [html.Span(str(value), className="analysis-metric-value"), html.Span(label, className="analysis-metric-label")],
                className="analysis-metric-card",
            )
            for label, value in labels
        ],
        className="analysis-metrics",
    )


def _evidence_cards(items: list[dict]):
    cards = []
    for item in items:
        event_ids = item.get("event_ids", [])
        event_text = ", ".join(str(event_id) for event_id in event_ids)
        cards.append(
            html.Div(
                [
                    html.Div(
                        [
                            html.Span(LEVEL_LABELS.get(item.get("level"), item.get("level", "Evidência")), className="analysis-evidence-badge"),
                            html.Span(f"Eventos: {event_text}" if event_text else "Sem evento direto", className="analysis-evidence-events"),
                        ],
                        className="analysis-evidence-header",
                    ),
                    html.Div(item.get("claim", ""), className="analysis-evidence-claim"),
                    html.Div(item.get("detail", ""), className="analysis-evidence-detail") if item.get("detail") else None,
                ],
                className=f"analysis-evidence-card evidence-{item.get('level', 'direct')}",
            )
        )
    return html.Div(cards, className="analysis-evidence-list")


def _route_view(route: list[dict]):
    if not route:
        return html.Div("Rota essencial não identificada.")
    children = []
    for index, entity in enumerate(route):
        subtitle = entity.get("owner_label") or entity.get("department_label") or entity.get("type")
        children.append(
            html.Div(
                [
                    html.Div(str(index + 1), className="analysis-route-index"),
                    html.Div(
                        [
                            html.Strong(entity.get("label", entity.get("id"))),
                            html.Span(subtitle or "", className="analysis-route-subtitle"),
                            html.Span(f"Evento {entity.get('event_id')}", className="analysis-route-event"),
                        ]
                    ),
                ],
                className="analysis-route-node",
            )
        )
        if index < len(route) - 1:
            children.append(html.Div("→", className="analysis-route-arrow"))
    return html.Div(children, className="analysis-route")


def _q1_content(q1: dict):
    return html.Div(
        [
            html.Div(q1.get("answer", ""), className="analysis-answer"),
            _metric_cards(q1.get("metrics", {})),
            html.H4("Rota essencial observada"),
            _route_view(q1.get("essential_route", [])),
            html.Div(
                [
                    html.Div(
                        [html.H4("Artefatos"), html.Ul([html.Li(value) for value in q1.get("artifacts", [])])],
                        className="analysis-summary-box",
                    ),
                    html.Div(
                        [
                            html.H4("Sistemas"),
                            html.Ul([html.Li(system.get("label", system.get("id"))) for system in q1.get("systems", [])]),
                        ],
                        className="analysis-summary-box",
                    ),
                ],
                className="analysis-summary-grid",
            ),
            html.H4("Rastreabilidade"),
            _evidence_cards(q1.get("evidence", [])),
        ]
    )


def _q2_content(q2: dict):
    known = q2.get("known", {})
    return html.Div(
        [
            html.Div(q2.get("answer", ""), className="analysis-answer"),
            html.Div(
                [
                    html.Div([html.Span("Conteúdo publicado"), html.Strong(known.get("content_source") or "Não identificado")], className="analysis-fact-row"),
                    html.Div([html.Span("Arquivo de instrução"), html.Strong(known.get("instruction_file") or "Não identificado")], className="analysis-fact-row"),
                    html.Div([html.Span("Origem observada"), html.Strong(known.get("origin_agent") or "Não observada")], className="analysis-fact-row"),
                    html.Div([html.Span("Agente publicador"), html.Strong(known.get("publisher_agent") or "Não identificado")], className="analysis-fact-row"),
                    html.Div([html.Span("Pessoa como party direta"), html.Strong("Sim" if known.get("human_direct_party") else "Não")], className="analysis-fact-row"),
                ],
                className="analysis-facts",
            ),
            html.Div(
                [html.Strong("Interpretação operacional"), html.P(q2.get("operational_interpretation", ""))],
                className="analysis-interpretation",
            ),
            html.H4("Evidências e limites"),
            _evidence_cards(q2.get("evidence", [])),
        ]
    )


def _similar_cases_table(cases: list[dict]):
    if not cases:
        return html.Div("Nenhum caso anterior semelhante foi encontrado.")
    header = html.Thead(
        html.Tr([
            html.Th("Evento"), html.Th("Artefato"), html.Th("Data UTC"), html.Th("Origem"),
            html.Th("Transferências"), html.Th("Entidades"), html.Th("Duração"), html.Th("Similaridade"),
        ])
    )
    rows = []
    for case in cases:
        timestamp = pd.to_datetime(case.get("event_time_utc"), utc=True).strftime("%d/%m/%Y %H:%M:%S")
        rows.append(
            html.Tr([
                html.Td(str(case.get("event_id"))),
                html.Td(case.get("artifact")),
                html.Td(timestamp),
                html.Td(case.get("origin")),
                html.Td(str(case.get("transfers"))),
                html.Td(str(case.get("entities"))),
                html.Td(case.get("duration")),
                html.Td(f"{case.get('similarity_score')}%"),
            ])
        )
    return html.Div(
        html.Table([header, html.Tbody(rows)], className="analysis-comparison-table"),
        className="analysis-table-wrap",
    )


def _q3_content(q3: dict):
    recommendation = q3.get("recommendation", {})
    return html.Div(
        [
            html.Div(q3.get("answer", ""), className="analysis-answer"),
            html.H4("Casos anteriores comparáveis"),
            _similar_cases_table(q3.get("similar_cases", [])),
            html.Div(
                [
                    html.H4("Padrão recorrente"),
                    html.Ul([html.Li(value) for value in q3.get("common_pattern", [])]),
                ],
                className="analysis-pattern-box",
            ),
            html.Div(
                [
                    html.Div("Ponto de intervenção recomendado", className="analysis-recommendation-label"),
                    html.H4(recommendation.get("control_point", "")),
                    html.P(recommendation.get("primary_action", "")),
                    html.P(recommendation.get("why", ""), className="analysis-recommendation-why"),
                    html.Div(f"Cobertura estimada nos casos conhecidos: {recommendation.get('coverage', 'n/d')}", className="analysis-coverage"),
                    html.Details(
                        [
                            html.Summary("Controles complementares"),
                            html.Ul([html.Li(value) for value in recommendation.get("secondary_controls", [])]),
                        ]
                    ),
                ],
                className="analysis-recommendation",
            ),
            html.H4("Fundamentação"),
            _evidence_cards(q3.get("evidence", [])),
        ]
    )


def build_analysis_content(analysis: dict | None, tab: str):
    if not analysis:
        return _placeholder()
    if analysis.get("status") != "ok":
        return html.Div(analysis.get("message", "Falha na análise."), className="analysis-error")
    if tab == "q2":
        return _q2_content(analysis.get("q2", {}))
    if tab == "q3":
        return _q3_content(analysis.get("q3", {}))
    return _q1_content(analysis.get("q1", {}))


def create_analysis_panel():
    return html.Section(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.H3("Análise Investigativa", className="analysis-title"),
                            html.P(
                                "Consolida evidências diretas, inferências e recomendações para as três questões do desafio.",
                                className="analysis-help",
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            dcc.Input(
                                id="analysis-event-id",
                                type="number",
                                value=373902,
                                min=0,
                                debounce=True,
                                className="analysis-event-input",
                            ),
                            html.Button("Analisar evento", id="analysis-run-button", n_clicks=0, className="analysis-run-button"),
                        ],
                        className="analysis-controls",
                    ),
                ],
                className="analysis-header",
            ),
            html.Div(
                "Evento padrão: 373902. Selecionar um evento na Timeline atualiza o campo automaticamente.",
                id="analysis-status",
                className="analysis-status",
            ),
            dcc.Tabs(
                id="analysis-tabs",
                value="q1",
                children=[
                    dcc.Tab(label="Questão 1 — Produção", value="q1"),
                    dcc.Tab(label="Questão 2 — Origem e significado", value="q2"),
                    dcc.Tab(label="Questão 3 — Recorrência e prevenção", value="q3"),
                ],
                className="analysis-tabs",
            ),
            html.Div(id="analysis-content", children=_placeholder(), className="analysis-content"),
        ],
        className="analysis-panel",
    )
