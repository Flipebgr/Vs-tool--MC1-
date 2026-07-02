from collections import Counter

def graph_statistics(G):

    node_types = Counter()

    edge_types = Counter()

    for _, attrs in G.nodes(data=True):

        node_types[attrs["type"]] += 1

    for _, _, attrs in G.edges(data=True):

        edge_types[attrs["relation"]] += 1

    return {

        "nodes": G.number_of_nodes(),

        "edges": G.number_of_edges(),

        "node_types": node_types,

        "edge_types": edge_types

    }