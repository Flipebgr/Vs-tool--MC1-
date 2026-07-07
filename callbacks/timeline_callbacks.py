"""Callbacks da Timeline investigativa da Sprint 3."""

from __future__ import annotations

import pandas as pd
from dash import Input, Output, State, ctx, html, no_update

from components.timeline import build_timeline_figure, format_timeline_status
from services.graph_service import load_entities
from utils.entity_style import TYPE_LABELS
from services.timeline_service import (
    get_event_by_id,
    get_full_range_store,
    get_time_bounds,
    normalize_window,
    parse_event_details,
)

ANOMALOUS_EVENT_ID = 373902
EVENT_FOCUS_RADIUS = pd.Timedelta(hours=2)

DETAIL_KEYS = (
    "content_source",
    "file",
    "target",
    "task",
    "subject",
    "topic",
    "forum",
    "action",
    "from",
    "to",
    "person",
    "target_agent",
)


def _parse_relayout_range(relayout_data, current_range):
    if not relayout_data:
        return None

    if relayout_data.get("xaxis.autorange"):
        start, end = get_time_bounds()
        return start, end, True

    if "xaxis.range" in relayout_data:
        values = relayout_data["xaxis.range"]
        if isinstance(values, (list, tuple)) and len(values) == 2:
            start, end = normalize_window(values[0], values[1])
            return start, end, False

    start_value = relayout_data.get("xaxis.range[0]")
    end_value = relayout_data.get("xaxis.range[1]")
    if start_value is not None and end_value is not None:
        start, end = normalize_window(start_value, end_value)
        return start, end, False

    if current_range:
        start, end = normalize_window(current_range.get("start"), current_range.get("end"))
        return start, end, bool(current_range.get("is_full_range"))

    return None


def _click_customdata(click_data):
    if not click_data or not click_data.get("points"):
        return None
    return click_data["points"][0].get("customdata")


def _selected_event_id(click_data):
    custom = _click_customdata(click_data)
    if isinstance(custom, (list, tuple)) and len(custom) >= 2 and custom[0] == "event":
        return custom[1]
    return None


def _selected_density_window(click_data):
    custom = _click_customdata(click_data)
    if isinstance(custom, (list, tuple)) and len(custom) >= 3 and custom[0] == "density":
        return normalize_window(custom[1], custom[2])
    return None


def _event_details_component(event):
    entities = load_entities()
    labels = []
    party_ids = event.get("parties_canonical", [])
    party_types = event.get("parties_types", [])
    for index, entity_id in enumerate(party_ids):
        entity = entities.get(entity_id, {})
        label = entity.get("label", entity_id)
        entity_type = entity.get("type")
        if entity_type == "agent" and label.endswith(" (Agente)"):
            label = label[:-9]
        if not entity_type and index < len(party_types):
            entity_type = party_types[index]
        type_label = TYPE_LABELS.get(entity_type, entity_type or "Entidade")
        labels.append(f"{label} ({type_label})")
    details = parse_event_details(event)

    relevant = []
    for key in DETAIL_KEYS:
        value = details.get(key)
        if value not in (None, "", [], {}):
            relevant.append(html.Li(f"{key}: {value}"))

    children = [
        html.Strong(f"Evento {event['id']} — {event['short_name']}"),
        html.Div(f"Horário: {event['event_time_utc']}"),
        html.Div(f"Fonte temporal: {event['time_source']}"),
        html.Div(f"Participantes: {', '.join(labels) if labels else 'nenhum'}"),
    ]
    if relevant:
        children.extend([html.Div("Detalhes relevantes:"), html.Ul(relevant)])
    return html.Div(children)


def _focus_event(event_id):
    event = get_event_by_id(event_id)
    if not event:
        return None

    event_time = pd.to_datetime(event["event_time_utc"], utc=True)
    start, end = normalize_window(
        event_time - EVENT_FOCUS_RADIUS,
        event_time + EVENT_FOCUS_RADIUS,
    )
    figure, metadata = build_timeline_figure(start, end)
    range_store = {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "is_full_range": False,
    }
    return (
        figure,
        range_store,
        format_timeline_status(start, end, metadata),
        _event_details_component(event),
        {"type": "event", "id": event["id"]},
    )


def register(app):

    @app.callback(
        Output("timeline-graph", "figure"),
        Output("time-range-store", "data"),
        Output("timeline-status", "children"),
        Output("timeline-event-details", "children"),
        Output("chain-start-store", "data"),
        Input("timeline-graph", "relayoutData"),
        Input("timeline-graph", "clickData"),
        Input("timeline-reset-button", "n_clicks"),
        Input("timeline-locate-event-button", "n_clicks"),
        Input("timeline-anomaly-button", "n_clicks"),
        State("time-range-store", "data"),
        State("timeline-event-id-input", "value"),
        prevent_initial_call=True,
    )
    def update_timeline(
        relayout_data,
        click_data,
        _reset_clicks,
        _locate_clicks,
        _anomaly_clicks,
        current_range,
        requested_event_id,
    ):
        triggered_id = ctx.triggered_id
        triggered_prop = ctx.triggered[0]["prop_id"] if ctx.triggered else ""

        if triggered_id == "timeline-anomaly-button":
            return _focus_event(ANOMALOUS_EVENT_ID)

        if triggered_id == "timeline-locate-event-button":
            focused = _focus_event(requested_event_id)
            if focused:
                return focused
            return (
                no_update,
                no_update,
                no_update,
                html.Div(f"Evento {requested_event_id!s} não encontrado."),
                no_update,
            )

        if triggered_prop == "timeline-graph.clickData" and click_data:
            event_id = _selected_event_id(click_data)
            if event_id is not None:
                event = get_event_by_id(event_id)
                if event:
                    return (
                        no_update,
                        no_update,
                        no_update,
                        _event_details_component(event),
                        {"type": "event", "id": event["id"]},
                    )

            density_window = _selected_density_window(click_data)
            if density_window is not None:
                start, end = density_window
                figure, metadata = build_timeline_figure(start, end)
                range_store = {
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "is_full_range": False,
                }
                return (
                    figure,
                    range_store,
                    format_timeline_status(start, end, metadata),
                    "Intervalo aprofundado. Clique novamente em uma barra ou selecione um evento individual.",
                    None,
                )

        if triggered_id == "timeline-reset-button":
            range_store = get_full_range_store()
            start, end = normalize_window(range_store["start"], range_store["end"])
        else:
            parsed = _parse_relayout_range(relayout_data, current_range)
            if parsed is None:
                return no_update, no_update, no_update, no_update, no_update
            start, end, is_full_range = parsed
            range_store = {
                "start": start.isoformat(),
                "end": end.isoformat(),
                "is_full_range": is_full_range,
            }

        figure, metadata = build_timeline_figure(start, end)
        return (
            figure,
            range_store,
            format_timeline_status(start, end, metadata),
            "Nenhum evento individual selecionado.",
            None,
        )
