"""Callbacks do painel de análise investigativa."""

from dash import Input, Output, State, no_update

from components.analysis_panel import build_analysis_content
from services.analysis_service import analyze_investigative_case


def register(app):
    @app.callback(
        Output("analysis-event-id", "value"),
        Input("chain-start-store", "data"),
        prevent_initial_call=True,
    )
    def sync_selected_event(chain_start):
        if chain_start and chain_start.get("type") == "event":
            return chain_start.get("id")
        return no_update

    @app.callback(
        Output("analysis-store", "data"),
        Output("analysis-status", "children"),
        Input("analysis-run-button", "n_clicks"),
        State("analysis-event-id", "value"),
        prevent_initial_call=True,
    )
    def run_analysis(_clicks, event_id):
        if event_id is None:
            return None, "Informe um ID de evento válido."
        try:
            event_id = int(event_id)
        except (TypeError, ValueError):
            return None, "O ID do evento deve ser numérico."

        analysis = analyze_investigative_case(event_id)
        if analysis.get("status") != "ok":
            return analysis, analysis.get("message", "Falha ao executar a análise.")
        return (
            analysis,
            f"Evento {analysis['seed_event_id']} analisado · artefato: {analysis.get('artifact') or 'não identificado'}.",
        )

    @app.callback(
        Output("analysis-content", "children"),
        Input("analysis-store", "data"),
        Input("analysis-tabs", "value"),
    )
    def render_analysis(analysis, tab):
        return build_analysis_content(analysis, tab or "q1")
