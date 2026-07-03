"""
Ponto único de registro de callbacks. app.py só precisa chamar
`register_callbacks(app)` uma vez — cada módulo de callback (node, graph,
search, filter, timeline...) se registra aqui conforme for sendo
implementado nos próximos módulos.
"""

from callbacks import node_callbacks


def register_callbacks(app):
    node_callbacks.register(app)
