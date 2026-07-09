"""
Ponto único de registro de callbacks. app.py só precisa chamar
`register_callbacks(app)` uma vez — cada módulo de callback (node, graph,
search, filter, timeline...) se registra aqui conforme for sendo
implementado nos próximos módulos.
"""

from callbacks import (
    node_callbacks,
    graph_callbacks,
    layout_callbacks,
    timeline_callbacks,
    chain_callbacks,
    analysis_callbacks,
)


def register_callbacks(app):
    node_callbacks.register(app)
    graph_callbacks.register(app)
    layout_callbacks.register(app)
    timeline_callbacks.register(app)
    chain_callbacks.register(app)
    analysis_callbacks.register(app)
