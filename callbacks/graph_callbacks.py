"""
Callbacks do grafo: filtros combináveis, busca, seleção e filtro temporal.
"""

from dash import ClientsideFunction, Input, Output, State, ctx

from services.graph_service import load_graph
from services.filter_service import build_filtered_elements, get_visible_node_ids
from services.search_service import find_best_match
from services.timeline_service import get_active_entity_ids_in_range, get_event_by_id


def _active_ids_from_time_range(time_range):
    """Período completo equivale a ausência de restrição temporal."""
    if not time_range or time_range.get("is_full_range"):
        return None
    start = time_range.get("start")
    end = time_range.get("end")
    if not start or not end:
        return None
    return get_active_entity_ids_in_range(start, end)


def _selected_event_participants(chain_start, G, visible_ids):
    """Retorna participantes do evento, separando visíveis e ocultos por filtros."""
    if not chain_start or chain_start.get("type") != "event":
        return None

    event = get_event_by_id(chain_start.get("id"))
    if not event:
        return None

    all_participants = [
        node_id
        for node_id in event.get("parties_canonical", [])
        if node_id in G
    ]
    visible_participants = [
        node_id for node_id in all_participants if node_id in visible_ids
    ]
    hidden_count = len(all_participants) - len(visible_participants)
    return event, all_participants, visible_participants, hidden_count


def register(app):

    @app.callback(
        Output("graph", "elements"),
        Output("search-feedback", "children"),
        Output("centered-node-store", "data"),
        Input("type-filter", "value"),
        Input("relation-filter", "value"),
        Input("department-filter", "value"),
        Input("search-button", "n_clicks"),
        Input("graph", "tapNodeData"),
        Input("clear-graph-highlight", "n_clicks"),
        Input("time-range-store", "data"),
        Input("chain-start-store", "data"),
        Input("event-chain-store", "data"),
        State("search-node", "value"),
    )
    def update_graph(
        type_filter,
        relation_filter,
        department_filter,
        _n_clicks,
        tapped_node,
        _clear_clicks,
        time_range,
        chain_start,
        event_chain,
        query,
    ):
        G = load_graph()
        active_node_ids = _active_ids_from_time_range(time_range)

        triggered_props = set(ctx.triggered_prop_ids)
        chain_selection_triggered = "event-chain-store.data" in triggered_props
        chain_node_ids = set(event_chain.get("entity_ids", [])) if event_chain else set()
        # A cadeia pode atravessar vários dias. Na reconstrução, seus atores
        # são adicionados ao escopo temporal para não desaparecerem por causa
        # da janela curta atualmente selecionada na Timeline.
        if chain_selection_triggered and chain_node_ids and active_node_ids is not None:
            active_node_ids = set(active_node_ids) | chain_node_ids

        visible_ids = get_visible_node_ids(
            G,
            type_filter=type_filter,
            department_filter=department_filter,
            relation_filter=relation_filter,
            active_node_ids=active_node_ids,
        )

        highlight_id = None
        event_participant_ids = None
        chain_participant_ids = None
        centered_node_target = None
        feedback = ""

        event_selection_triggered = "chain-start-store.data" in triggered_props
        graph_click_triggered = "graph.tapNodeData" in triggered_props
        search_triggered = "search-button.n_clicks" in triggered_props

        if chain_selection_triggered and chain_node_ids:
            chain_participant_ids = [node_id for node_id in chain_node_ids if node_id in visible_ids]
            centered_node_target = chain_participant_ids or None
            feedback = (
                f"Cadeia reconstruída — {len(chain_participant_ids)} entidade(s) destacada(s)"
            )

        # A Timeline pode atualizar `time-range-store` e `chain-start-store` no
        # mesmo ciclo. A seleção do evento tem prioridade para que seus
        # participantes sejam destacados imediatamente após o zoom.
        elif event_selection_triggered:
            selected = _selected_event_participants(chain_start, G, visible_ids)
            if selected:
                event, all_participants, visible_participants, hidden_count = selected
                event_participant_ids = visible_participants
                centered_node_target = visible_participants or None

                feedback = (
                    f"Evento {event['id']} — {len(visible_participants)} participante(s) destacado(s)"
                )
                if hidden_count:
                    feedback += f"; {hidden_count} oculto(s) pelos filtros ativos"
                if not visible_participants and all_participants:
                    feedback = (
                        f"Evento {event['id']} — participantes ocultos pelos filtros ativos"
                    )

        # `tapNodeData` mantém o último nó clicado mesmo quando outro componente
        # dispara o callback. Portanto, a seleção só é reaplicada quando o
        # próprio grafo é o gatilho. Mudanças de período/filtro limpam o blur.
        elif graph_click_triggered and tapped_node:
            tapped_id = tapped_node.get("id")
            if tapped_id in visible_ids:
                highlight_id = tapped_id
                label = G.nodes[tapped_id].get("label", tapped_id)
                feedback = f"Selecionado no grafo: {label}"

        elif search_triggered and query and query.strip():
            highlight_id, total_matches = find_best_match(query, visible_ids, G)

            if highlight_id:
                label = G.nodes[highlight_id].get("label", highlight_id)
                feedback = (
                    f"{total_matches} resultado(s) — destacando: {label}"
                    if total_matches > 1
                    else f"Encontrado: {label}"
                )
                centered_node_target = highlight_id
            else:
                feedback = "Nenhum resultado nos nós visíveis (confira os filtros ativos)."

        # clear-graph-highlight, filtros e time-range-store mantêm as seleções
        # vazias, restaurando o grafo sem reutilizar estado antigo.

        elements = build_filtered_elements(
            G,
            type_filter=type_filter,
            relation_filter=relation_filter,
            department_filter=department_filter,
            highlight_node_id=highlight_id,
            highlight_node_ids=event_participant_ids,
            chain_node_ids=chain_participant_ids,
            active_node_ids=active_node_ids,
        )

        return elements, feedback, centered_node_target

    app.clientside_callback(
        ClientsideFunction(namespace="graph_interactions", function_name="center_on_node"),
        Output("centering-dummy-output", "children"),
        Input("centered-node-store", "data"),
    )
