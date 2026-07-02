import networkx as nx

def build_graph(org_data):

    G = nx.node_link_graph(org_data)

    return G