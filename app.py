from dash import Dash

from utils.loader import load_json
from utils.parser import build_graph
from utils.graph_builder import nx_to_cytoscape
from utils.statistics import graph_statistics

from components.layout import create_layout


org = load_json("data/org_chart.json")

G = build_graph(org)

elements = nx_to_cytoscape(G)

stats = graph_statistics(G)

app = Dash(__name__)

app.layout = create_layout(elements, stats)

if __name__ == "__main__":
    app.run(debug=True)