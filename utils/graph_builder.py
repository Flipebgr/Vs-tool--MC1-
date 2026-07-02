import networkx as nx


def nx_to_cytoscape(G):

    elements = []

    # Nós
    for node, attrs in G.nodes(data=True):

        elements.append(
            {
                "data": {
                    "id": node,
                    "label": attrs.get("label", node),
                    "type": attrs.get("type", "")
                }
            }
        )

    # Arestas
    for source, target, attrs in G.edges(data=True):

        elements.append(
            {
                "data": {
                    "source": source,
                    "target": target,
                    "relation": attrs.get("relation", "")
                }
            }
        )

    return elements