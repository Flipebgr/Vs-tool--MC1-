from dash import Dash

from services.graph_service import get_cytoscape_elements, load_graph
from services.statistics_service import get_stats_summary
from services.filter_service import get_filter_options
from callbacks import register_callbacks

from components.layout import create_layout


elements = get_cytoscape_elements()
stats = get_stats_summary()
filter_options = get_filter_options(load_graph())

app = Dash(__name__)

app.layout = create_layout(elements, stats, filter_options)

register_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True)
