"""Componente visual da Timeline investigativa da Sprint 3."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html

from services.graph_service import load_entities
from utils.entity_style import TYPE_LABELS

from services.timeline_service import (
    get_density_buckets,
    get_events_in_window,
    get_full_range_store,
    get_time_bounds,
    get_window_event_count,
    normalize_window,
    should_show_individual_events,
)


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if hasattr(value, "tolist"):
        converted = value.tolist()
        return converted if isinstance(converted, list) else [converted]
    return [value]


def _participant_hover_text(parties, party_types) -> str:
    """Rótulos legíveis dos participantes para o tooltip do Plotly."""
    entities = load_entities()
    ids = _as_list(parties)
    types = _as_list(party_types)
    labels = []

    for index, entity_id in enumerate(ids):
        entity = entities.get(entity_id, {})
        label = entity.get("label", entity_id)
        entity_type = entity.get("type")
        if entity_type == "agent" and label.endswith(" (Agente)"):
            label = label[:-9]
        if not entity_type and index < len(types):
            entity_type = types[index]
        type_label = TYPE_LABELS.get(entity_type, entity_type or "Entidade")
        labels.append(f"{label} ({type_label})")

    return "<br>".join(labels) if labels else "Nenhum"


def _base_layout(figure: go.Figure, start: pd.Timestamp, end: pd.Timestamp) -> go.Figure:
    figure.update_layout(
        margin={"l": 55, "r": 20, "t": 18, "b": 45},
        height=280,
        paper_bgcolor="white",
        plot_bgcolor="white",
        dragmode="zoom",
        clickmode="event+select",
        hovermode="closest",
        showlegend=False,
        uirevision=f"{start.isoformat()}::{end.isoformat()}",
    )
    figure.update_xaxes(
        title="Tempo (UTC)",
        range=[start, end],
        showgrid=True,
        gridcolor="#e5e7eb",
    )
    return figure


def build_timeline_figure(start=None, end=None) -> tuple[go.Figure, dict]:
    """Monta densidade agregada ou eventos individuais conforme o zoom."""
    start_ts, end_ts = normalize_window(start, end)
    count = get_window_event_count(start_ts, end_ts)

    if should_show_individual_events(start_ts, end_ts):
        events = get_events_in_window(start_ts, end_ts)
        figure = go.Figure()
        figure.add_trace(
            go.Scattergl(
                x=events["event_time_utc"],
                y=events["short_name"],
                mode="markers",
                marker={"size": 8, "opacity": 0.75},
                customdata=[
                    [
                        "event",
                        int(row.id),
                        row.time_source,
                        len(_as_list(row.parties_canonical)),
                        _participant_hover_text(row.parties_canonical, row.parties_types),
                    ]
                    for row in events.itertuples(index=False)
                ],
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "%{x|%d/%m/%Y %H:%M:%S UTC}<br>"
                    "Evento: %{customdata[1]}<br>"
                    "Participantes (%{customdata[3]}):<br>%{customdata[4]}<br>"
                    "Fonte temporal: %{customdata[2]}<extra></extra>"
                ),
            )
        )
        figure.update_yaxes(title="Tipo de evento", automargin=True)
        metadata = {
            "mode": "individual",
            "count": count,
            "bucket_label": None,
        }
    else:
        density, bucket_label = get_density_buckets(start_ts, end_ts)
        figure = go.Figure()
        figure.add_trace(
            go.Bar(
                x=density["bucket_start"],
                y=density["count"],
                customdata=[
                    [
                        "density",
                        row.bucket_start.isoformat(),
                        row.bucket_end.isoformat(),
                        int(row.embedded_count),
                    ]
                    for row in density.itertuples(index=False)
                ],
                hovertemplate=(
                    "<b>%{x|%d/%m/%Y %H:%M UTC}</b><br>"
                    "Eventos: %{y}<br>"
                    "Timestamp interno: %{customdata[3]}<extra></extra>"
                ),
            )
        )
        figure.update_yaxes(title="Quantidade de eventos", rangemode="tozero")
        metadata = {
            "mode": "density",
            "count": count,
            "bucket_label": bucket_label,
        }

    return _base_layout(figure, start_ts, end_ts), metadata


def format_timeline_status(start=None, end=None, metadata=None) -> str:
    start_ts, end_ts = normalize_window(start, end)
    metadata = metadata or {}
    mode = metadata.get("mode")
    count = metadata.get("count", get_window_event_count(start_ts, end_ts))

    if mode == "individual":
        view = "eventos individuais"
    else:
        view = f"densidade por {metadata.get('bucket_label', 'intervalo')}"

    return (
        f"{start_ts.strftime('%d/%m/%Y %H:%M')} — "
        f"{end_ts.strftime('%d/%m/%Y %H:%M')} UTC · "
        f"{count:,} eventos · visão de {view}"
    ).replace(",", ".")


def create_timeline():
    start, end = get_time_bounds()
    figure, metadata = build_timeline_figure(start, end)

    return html.Section(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.H3("Timeline de eventos", className="timeline-title"),
                            html.P(
                                "Clique em uma barra para aprofundar o período, use o zoom horizontal "
                                "ou localize um evento pelo ID. Em janelas pequenas, os eventos tornam-se clicáveis.",
                                className="timeline-help",
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            dcc.Input(
                                id="timeline-event-id-input",
                                type="number",
                                placeholder="ID do evento (ex.: 373902)",
                                debounce=True,
                                className="timeline-event-id-input",
                            ),
                            html.Button(
                                "Localizar evento",
                                id="timeline-locate-event-button",
                                n_clicks=0,
                                className="timeline-action-button",
                            ),
                            html.Button(
                                "Abrir caso 373902",
                                id="timeline-anomaly-button",
                                n_clicks=0,
                                className="timeline-action-button timeline-anomaly-button",
                            ),
                            html.Button(
                                "Restaurar período completo",
                                id="timeline-reset-button",
                                n_clicks=0,
                                className="timeline-reset-button",
                            ),
                        ],
                        className="timeline-controls",
                    ),
                ],
                className="timeline-header",
            ),
            html.Div(
                format_timeline_status(start, end, metadata),
                id="timeline-status",
                className="timeline-status",
            ),
            dcc.Graph(
                id="timeline-graph",
                figure=figure,
                config={
                    "displaylogo": False,
                    "scrollZoom": True,
                    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                },
            ),
            html.Div(
                "Nenhum evento individual selecionado.",
                id="timeline-event-details",
                className="timeline-event-details",
            ),
            dcc.Store(id="time-range-store", data=get_full_range_store()),
            dcc.Store(id="chain-start-store"),
        ],
        className="timeline-panel",
    )
