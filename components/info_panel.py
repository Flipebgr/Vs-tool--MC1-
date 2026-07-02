from dash import html


def create_info_panel():

    return html.Div(

        [

            html.H3("Informações do Nó"),

            html.Hr(),

            html.Div(

                "Nenhum nó selecionado.",

                id="node-information"

            )

        ],

        className="info-panel"

    )