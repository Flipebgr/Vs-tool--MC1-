import dash_cytoscape as cyto

from utils.entity_style import TYPE_COLORS, TYPE_SHAPES, RELATION_COLORS, DEFAULT_COLOR, DEFAULT_SHAPE

# Precisa ser chamado uma única vez, antes do Dash(__name__) ser
# instanciado em app.py, para que os layouts extras (dagre, cola, etc,
# que não vêm no core do Cytoscape.js) fiquem disponíveis no seletor de
# layout do sidebar.
cyto.load_extra_layouts()

# Layouts oferecidos no seletor do sidebar. "dagre" é o melhor pro nosso
# caso (grafo majoritariamente hierárquico: empresa -> departamento ->
# time -> pessoa -> agente), por isso é o padrão.
AVAILABLE_LAYOUTS = {
    "dagre": "Hierárquico (Dagre)",
    "breadthfirst": "Hierárquico (Breadthfirst)",
    "cose": "Força dirigida (COSE)",
    "circle": "Circular",
    "grid": "Grade",
}

DEFAULT_LAYOUT = "dagre"


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


def get_layout_config(layout_name: str = DEFAULT_LAYOUT) -> dict:
    """
    Configuração do layout do Cytoscape. Alguns algoritmos precisam de
    parâmetros extras para não sobrepor nós (nodeSep/rankSep no dagre,
    padding no breadthfirst).
    """
    if layout_name == "dagre":
        return {"name": "dagre", "rankDir": "LR", "nodeSep": 25, "rankSep": 90, "animate": True}
    if layout_name == "breadthfirst":
        return {"name": "breadthfirst", "spacingFactor": 1.4, "animate": True}
    if layout_name == "cose":
        return {"name": "cose", "idealEdgeLength": 90, "nodeRepulsion": 8000, "animate": True}
    return {"name": layout_name, "animate": True}


def graph_component(elements):

    return cyto.Cytoscape(

        id="graph",

        elements=elements,

        layout=get_layout_config(DEFAULT_LAYOUT),

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

                    "color": "#1a1a1a",

                    "font-size": "11px",

                    # --- Legibilidade: nó cresce pra caber o texto, texto
                    # quebra em vez de cortar, e ganha contorno claro pra
                    # não sumir por baixo de arestas que passam por cima. ---
                    "width": "label",
                    "height": "label",
                    "padding": "10px",
                    "text-wrap": "wrap",
                    "text-max-width": "90px",
                    "text-outline-width": 2,
                    "text-outline-color": "#ffffff",
                    "text-outline-opacity": 0.6,

                }
            },

            {
                "selector": "edge",

                "style": {

                    "curve-style": "bezier",

                    "target-arrow-shape": "triangle",

                    "line-color": "#999",

                    "target-arrow-color": "#999",

                    "width": 1.5,

                    "arrow-scale": 0.8,

                }

            },

            *_node_selectors(),
            *_edge_selectors(),

            # --- Destaque de busca (Módulo 3) -----------------------------
            {
                "selector": "node.highlighted",
                "style": {
                    "border-width": 4,
                    "border-color": "#2c3e50",
                    "z-index": 999,
                },
            },
            {
                "selector": "node.neighbor",
                "style": {
                    "border-width": 2,
                    "border-color": "#2c3e50",
                    "opacity": 1,
                },
            },
            {
                "selector": "node.faded",
                "style": {
                    "opacity": 0.15,
                },
            },
            {
                "selector": "edge.highlighted-edge",
                "style": {
                    "width": 3,
                    "line-color": "#2c3e50",
                    "target-arrow-color": "#2c3e50",
                    "opacity": 1,
                    "z-index": 999,
                },
            },
            {
                "selector": "edge.faded",
                "style": {
                    "opacity": 0.08,
                },
            },

        ]

    )
