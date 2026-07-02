from dash import html


def create_header():

    return html.Div(

        [

            html.H2(
                "Tenant Thread Visual Analytics",
                className="title"
            ),

            html.Div(
                "VAST Challenge 2026 • Mini Challenge 2",
                className="subtitle"
            )

        ],

        className="header"

    )