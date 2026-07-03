import dash_cytoscape as cyto

from utils.entity_style import TYPE_COLORS, TYPE_SHAPES, RELATION_COLORS, DEFAULT_COLOR, DEFAULT_SHAPE


def _node_selectors():
    """Uma regra de stylesheet por tipo de nó (person, agent, system, ...)."""
    selectors = []
    for node_type, color in TYPE_COLORS.items():
        selectors.append(
            {
                "selector": f'node[type = "{node_type}"]',
                "style": {
                    "background-color": color,
                    "shape": TYPE_SHAPES.get(node_type, DEFAULT_SHAPE),
                },
            }
        )
    return selectors


def _edge_selectors():
    """Uma regra de stylesheet por tipo de relação (contains, led_by, has_agent)."""
    selectors = []
    for relation, color in RELATION_COLORS.items():
        selectors.append(
            {
                "selector": f'edge[relation = "{relation}"]',
                "style": {
                    "line-color": color,
                    "target-arrow-color": color,
                },
            }
        )
    return selectors


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

                    "background-color": DEFAULT_COLOR,

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

            },

            *_node_selectors(),
            *_edge_selectors(),

        ]

    )
