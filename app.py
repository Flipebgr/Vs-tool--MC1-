from dash import Dash

from services.graph_service import get_cytoscape_elements
from services.statistics_service import get_stats_summary
from callbacks import register_callbacks

from components.layout import create_layout


elements = get_cytoscape_elements()
stats = get_stats_summary()

app = Dash(__name__)

app.layout = create_layout(elements, stats)

register_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True)
