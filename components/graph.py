import dash_cytoscape as cyto


def graph_component(elements):

    return cyto.Cytoscape(

        id="graph",

        elements=elements,

        layout={"name": "breadthfirst"},

        style={
            "width": "100%",
            "height": "100%"
        },

        stylesheet=[

            {
                "selector": "node",
                "style": {

                    "label": "data(label)",

                    "text-valign": "center",

                    "text-halign": "center",

                    "background-color": "#4e79a7",

                    "color": "white",

                    "font-size": "10px"

                }
            },

            {
                "selector": "edge",

                "style": {

                    "curve-style": "bezier",

                    "target-arrow-shape": "triangle",

                    "line-color": "#999",

                    "target-arrow-color": "#999"

                }

            }

        ]

    )