"""
Serviço responsável por disponibilizar o grafo unificado (organograma +
agentes + sistemas, gerado pelo services/etl.py) para o restante da
aplicação Dash.

Não recalcula nada pesado em tempo de request: apenas lê os artefatos já
processados em data/processed/.
"""

import json
from functools import lru_cache
from typing import Optional

import networkx as nx

import config
from utils.loader import load_json
from utils.graph_builder import nx_to_cytoscape


@lru_cache(maxsize=1)
def load_graph() -> nx.DiGraph:
    """
    Carrega o grafo unificado a partir de data/processed/graph.json.
    Cacheado em memória: o processo do Dash só lê o arquivo uma vez.
    """
    if not config.GRAPH_JSON.exists():
        raise FileNotFoundError(
            f"{config.GRAPH_JSON} não encontrado. Rode `python -m services.etl` "
            "antes de iniciar o app."
        )
    data = load_json(config.GRAPH_JSON)
    return nx.node_link_graph(data)


@lru_cache(maxsize=1)
def load_entities() -> dict:
    """Carrega o registro plano de entidades (data/processed/entities.json)."""
    with open(config.ENTITIES_JSON, encoding="utf8") as f:
        return json.load(f)


def get_cytoscape_elements() -> list:
    """Grafo unificado convertido para o formato esperado pelo dash-cytoscape."""
    return nx_to_cytoscape(load_graph())


def get_node_details(node_id: str) -> Optional[dict]:
    """
    Retorna os atributos de um nó (label, type, title, ...) mais seus
    vizinhos diretos, para exibição no painel de informações.
    """
    G = load_graph()
    if node_id not in G:
        return None

    attrs = dict(G.nodes[node_id])

    neighbors_out = [
        {"id": target, "label": G.nodes[target].get("label", target), "relation": data.get("relation", "")}
        for target, data in G[node_id].items()
    ]
    neighbors_in = [
        {"id": source, "label": G.nodes[source].get("label", source), "relation": data.get("relation", "")}
        for source, _, data in G.in_edges(node_id, data=True)
    ]

    return {
        "id": node_id,
        "attrs": attrs,
        "neighbors_out": neighbors_out,
        "neighbors_in": neighbors_in,
    }
