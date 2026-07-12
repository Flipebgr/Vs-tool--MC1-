"""Ponto único de registro de callbacks da aplicação."""

from callbacks import (
    node_callbacks,
    graph_callbacks,
    layout_callbacks,
    timeline_callbacks,
    chain_callbacks,
    analysis_callbacks,
    visual_analytics_callbacks,
    navigation_callbacks,
)


def register_callbacks(app):
    node_callbacks.register(app)
    graph_callbacks.register(app)
    layout_callbacks.register(app)
    timeline_callbacks.register(app)
    chain_callbacks.register(app)
    analysis_callbacks.register(app)
    visual_analytics_callbacks.register(app)
    navigation_callbacks.register(app)
