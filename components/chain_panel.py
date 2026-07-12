"""Painel visual da Cadeia de Eventos."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html

from services.graph_service import load_entities
from utils.entity_style import TYPE_LABELS

ROLE_LABELS = {
    "origin": "Origem",
    "instruction": "Instrução",
    "handoff": "Transferência",
    "seed": "Evento investigado",
    "aftermath": "Ação posterior",
    "related": "Evento relacionado",
}


def _blank_figure(message: str = "Selecione um evento na Timeline e reconstrua a cadeia.") -> go.Figure:
    figure = go.Figure()
    figure.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"size": 14, "color": "#64748b"},
    )
    figure.update_layout(
        height=270,
        margin={"l": 30, "r": 20, "t": 20, "b": 35},
        xaxis={"visible": False},
        yaxis={"visible": False},
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    return figure


def _participant_labels(event: dict) -> list[str]:
    entities = load_entities()
    labels = []
    for entity_id in event.get("party_ids", []):
        entity = entities.get(entity_id, {})
        label = entity.get("label", entity_id)
        entity_type = entity.get("type")
        if entity_type == "agent" and label.endswith(" (Agente)"):
            label = label[:-9]
        labels.append(f"{label} ({TYPE_LABELS.get(entity_type, entity_type or 'Entidade')})")
    return labels


ROLE_Y = {
    "origin": 0.0,
    "instruction": 1.0,
    "handoff": 2.0,
    "seed": 3.0,
    "aftermath": 4.0,
    "related": 5.0,
}


def _separated_y_positions(events: list[dict], timestamps: list[pd.Timestamp]) -> list[float]:
    """Separa visualmente eventos quase simultâneos na mesma faixa.

    Os timestamps reais permanecem intactos no eixo X e no hover. Somente a
    posição vertical recebe um pequeno deslocamento quando dois ou mais
    eventos da mesma função ocorreram próximos demais para serem distinguidos
    na escala temporal atual.
    """
    positions = [ROLE_Y.get(event.get("role"), ROLE_Y["related"]) for event in events]
    if len(events) < 2:
        return positions

    total_span = max(timestamps) - min(timestamps)
    # Aproxima a menor distância temporal distinguível em um gráfico de tela
    # inteira, mantendo um piso de 2 segundos e teto de 30 minutos.
    threshold_seconds = min(1800.0, max(2.0, total_span.total_seconds() / 500.0))

    indices_by_role: dict[str, list[int]] = {}
    for index, event in enumerate(events):
        indices_by_role.setdefault(event.get("role", "related"), []).append(index)

    for role_indices in indices_by_role.values():
        ordered = sorted(role_indices, key=lambda index: timestamps[index])
        clusters: list[list[int]] = []
        cluster: list[int] = []

        for index in ordered:
            if not cluster:
                cluster = [index]
                continue
            gap = (timestamps[index] - timestamps[cluster[-1]]).total_seconds()
            if gap <= threshold_seconds:
                cluster.append(index)
            else:
                clusters.append(cluster)
                cluster = [index]
        if cluster:
            clusters.append(cluster)

        for cluster_indices in clusters:
            if len(cluster_indices) <= 1:
                continue
            max_offset = min(0.28, 0.10 * (len(cluster_indices) - 1))
            if len(cluster_indices) == 2:
                offsets = [-max_offset, max_offset]
            else:
                step = (2 * max_offset) / (len(cluster_indices) - 1)
                offsets = [-max_offset + step * i for i in range(len(cluster_indices))]
            for index, offset in zip(cluster_indices, offsets):
                positions[index] += offset

    return positions


def build_chain_figure(chain: dict | None) -> go.Figure:
    if not chain or not chain.get("events"):
        return _blank_figure()

    events = chain["events"]
    x = [pd.to_datetime(event["event_time_utc"], utc=True) for event in events]
    y = _separated_y_positions(events, x)
    custom = []
    for sequence, event in enumerate(events, start=1):
        custom.append([
            event["id"],
            event["short_name"],
            event.get("reason", ""),
            "<br>".join(_participant_labels(event)) or "Nenhum",
            event.get("time_source") or "desconhecida",
            sequence,
            ROLE_LABELS.get(event.get("role"), event.get("role", "Evento")),
        ])

    show_sequence = len(events) <= 30
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="lines+markers+text" if show_sequence else "lines+markers",
            line={"width": 1.5},
            marker={"size": 11},
            text=[str(index) for index in range(1, len(events) + 1)] if show_sequence else None,
            textposition="top center",
            textfont={"size": 10},
            customdata=custom,
            hovertemplate=(
                "<b>%{customdata[5]}. %{customdata[1]}</b> · evento %{customdata[0]}<br>"
                "%{x|%d/%m/%Y %H:%M:%S UTC}<br>"
                "Categoria: %{customdata[6]}<br>"
                "%{customdata[2]}<br>"
                "Participantes:<br>%{customdata[3]}<br>"
                "Fonte temporal: %{customdata[4]}<extra></extra>"
            ),
        )
    )
    figure.update_layout(
        height=320,
        margin={"l": 110, "r": 20, "t": 18, "b": 45},
        paper_bgcolor="white",
        plot_bgcolor="white",
        hovermode="closest",
        showlegend=False,
    )
    figure.update_xaxes(title="Tempo (UTC)", showgrid=True, gridcolor="#e5e7eb")
    tick_roles = ["origin", "instruction", "handoff", "seed", "aftermath", "related"]
    figure.update_yaxes(
        title="",
        automargin=True,
        tickmode="array",
        tickvals=[ROLE_Y[role] for role in tick_roles],
        ticktext=[ROLE_LABELS[role] for role in tick_roles],
        range=[-0.45, max(y) + 0.45],
    )
    return figure


def build_chain_event_list(chain: dict | None):
    if not chain or not chain.get("events"):
        return html.Div("Nenhuma cadeia reconstruída.")

    cards = []
    for index, event in enumerate(chain["events"], start=1):
        timestamp = pd.to_datetime(event["event_time_utc"], utc=True)
        participants = ", ".join(_participant_labels(event)) or "Nenhum"
        artifacts = ", ".join(event.get("artifact_references", []))
        children = [
            html.Div(
                [
                    html.Strong(f"{index}. {event['short_name']}"),
                    html.Span(f"Evento {event['id']}", className="chain-event-id"),
                ],
                className="chain-event-header",
            ),
            html.Div(timestamp.strftime("%d/%m/%Y %H:%M:%S UTC"), className="chain-event-time"),
            html.Div(event.get("reason", ""), className="chain-event-reason"),
            html.Div(f"Participantes: {participants}", className="chain-event-participants"),
        ]
        if artifacts:
            children.append(html.Div(f"Artefatos: {artifacts}", className="chain-event-artifacts"))
        cards.append(html.Div(children, className=f"chain-event-card chain-role-{event.get('role', 'related')}"))
    return cards


def create_chain_panel():
    return html.Section(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.H3("Cadeia de Eventos", className="chain-title"),
                            html.P(
                                "Reconstrói uma sequência rastreável a partir do evento selecionado na Timeline.",
                                className="chain-help",
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            dcc.Dropdown(
                                id="chain-view-mode",
                                options=[
                                    {"label": "Cadeia essencial", "value": "core"},
                                    {"label": "Todos os eventos relacionados", "value": "all"},
                                ],
                                value="core",
                                clearable=False,
                                className="chain-mode-dropdown",
                            ),
                            html.Button(
                                "Reconstruir cadeia",
                                id="chain-build-button",
                                n_clicks=0,
                                disabled=True,
                                className="chain-build-button",
                            ),
                            html.Button(
                                "Limpar",
                                id="chain-clear-button",
                                n_clicks=0,
                                className="chain-clear-button",
                            ),
                        ],
                        className="chain-controls",
                    ),
                ],
                className="chain-header",
            ),
            html.Div(
                "Nenhum evento selecionado.",
                id="chain-seed-summary",
                className="chain-seed-summary",
            ),
            html.Div(
                "Selecione um evento individual na Timeline.",
                id="chain-status",
                className="chain-status",
            ),
            dcc.Graph(
                id="chain-graph",
                figure=_blank_figure(),
                config={"displaylogo": False, "responsive": True, "scrollZoom": True},
            ),
            html.Div(id="chain-event-list", className="chain-event-list"),
        ],
        className="chain-panel",
    )
