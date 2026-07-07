"""Callbacks da reconstrução da Cadeia de Eventos."""

from __future__ import annotations

from dash import Input, Output, State, ctx, html, no_update

from components.chain_panel import (
    _blank_figure,
    build_chain_event_list,
    build_chain_figure,
)
from services.event_chain_service import build_event_chain
from services.timeline_service import get_event_by_id


def _seed_summary(chain_start):
    if not chain_start or chain_start.get("type") != "event":
        return "Nenhum evento selecionado."
    event = get_event_by_id(chain_start.get("id"))
    if not event:
        return "O evento selecionado não foi encontrado."
    return (
        f"Ponto de partida: evento {event['id']} — {event['short_name']} · "
        f"{event['event_time_utc']}"
    )


def _status_text(chain):
    if chain["strategy"] == "artifact":
        artifacts = ", ".join(chain.get("artifact_families", []))
        return (
            f"Estratégia por artefato ({artifacts}) · "
            f"{chain['core_event_count']} eventos essenciais · "
            f"{chain['related_event_count']} eventos relacionados · "
            f"{chain['handoff_count']} transferências · "
            f"{chain['related_entity_count']} entidades."
        )
    return (
        "Nenhum artefato explícito foi encontrado; foi usada proximidade temporal "
        f"e participantes compartilhados. {chain['related_event_count']} candidatos relacionados."
    )


def register(app):
    @app.callback(
        Output("chain-graph", "figure"),
        Output("chain-event-list", "children"),
        Output("chain-status", "children"),
        Output("event-chain-store", "data"),
        Output("chain-seed-summary", "children"),
        Output("chain-build-button", "disabled"),
        Input("chain-start-store", "data"),
        Input("chain-build-button", "n_clicks"),
        Input("chain-view-mode", "value"),
        Input("chain-clear-button", "n_clicks"),
        State("event-chain-store", "data"),
        prevent_initial_call=True,
    )
    def update_chain(chain_start, _build_clicks, view_mode, _clear_clicks, current_chain):
        triggered = ctx.triggered_id

        if triggered == "chain-clear-button":
            return (
                _blank_figure(),
                "Nenhuma cadeia reconstruída.",
                "Cadeia limpa. Selecione um evento na Timeline.",
                None,
                _seed_summary(chain_start),
                not bool(chain_start and chain_start.get("type") == "event"),
            )

        if triggered == "chain-start-store":
            enabled = bool(chain_start and chain_start.get("type") == "event")
            # Não altera o store da cadeia aqui. Limpar esse store em um
            # segundo callback faria o grafo apagar imediatamente o destaque
            # dos participantes que acabou de ser aplicado pela Timeline.
            return (
                _blank_figure("Evento selecionado. Clique em “Reconstruir cadeia”."),
                "Nenhuma cadeia reconstruída.",
                "Evento selecionado; a reconstrução ainda não foi executada.",
                no_update,
                _seed_summary(chain_start),
                not enabled,
            )

        if not chain_start or chain_start.get("type") != "event":
            return (
                no_update,
                no_update,
                "Selecione primeiro um evento individual na Timeline.",
                no_update,
                _seed_summary(chain_start),
                True,
            )

        if triggered == "chain-view-mode" and (
            not current_chain
            or int(current_chain.get("seed_event_id", -1)) != int(chain_start.get("id", -2))
        ):
            return no_update, no_update, no_update, no_update, no_update, False

        chain = build_event_chain(int(chain_start["id"]), view_mode or "core")
        if not chain:
            return (
                _blank_figure("Não foi possível reconstruir a cadeia."),
                "Nenhuma evidência relacionada encontrada.",
                "Falha ao reconstruir a cadeia para o evento selecionado.",
                None,
                _seed_summary(chain_start),
                False,
            )

        return (
            build_chain_figure(chain),
            build_chain_event_list(chain),
            _status_text(chain),
            chain,
            _seed_summary(chain_start),
            False,
        )
