from dash import html

from components.header import create_header
from components.sidebar import create_sidebar
from components.graph import graph_component
from components.info_panel import create_info_panel


def create_layout(elements, stats):

    return html.Div(

        [

            create_header(),

            html.Div(

                [

                    create_sidebar(stats),

                    html.Div(

                        graph_component(elements),

                        className="graph-container"

                    )

                ],

                className="main-container"

            ),

            create_info_panel()

        ]

    )