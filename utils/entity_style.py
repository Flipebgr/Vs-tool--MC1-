"""
Constantes visuais compartilhadas entre components/graph.py (stylesheet do
Cytoscape) e services/statistics_service.py (legenda/ordem no sidebar).

Centralizado aqui para que as cores usadas no grafo e na legenda do painel
lateral nunca fiquem dessincronizadas.
"""

# Ordem de exibição no sidebar (dos mais "estruturais" aos mais "operacionais")
TYPE_ORDER = ["company", "department", "team", "person", "agent", "system", "world"]

TYPE_LABELS = {
    "company": "Empresa",
    "department": "Departamento",
    "team": "Time",
    "person": "Pessoa",
    "agent": "Agente de IA",
    "system": "Sistema",
    "world": "Entidade externa",
}

# Paleta com contraste suficiente entre categorias próximas (person/agent
# ficam visualmente relacionadas mas distinguíveis).
TYPE_COLORS = {
    "company": "#2c3e50",
    "department": "#4e79a7",
    "team": "#76b7b2",
    "person": "#f28e2b",
    "agent": "#f2b134",
    "system": "#e15759",
    "world": "#af7aa1",
}

TYPE_SHAPES = {
    "company": "star",
    "department": "round-rectangle",
    "team": "round-rectangle",
    "person": "ellipse",
    "agent": "diamond",
    "system": "hexagon",
    "world": "octagon",
}

RELATION_LABELS = {
    "contains": "contém",
    "led_by": "liderado por",
    "has_agent": "possui agente",
}

RELATION_COLORS = {
    "contains": "#999999",
    "led_by": "#e15759",
    "has_agent": "#f2b134",
}

DEFAULT_COLOR = "#bab0ac"
DEFAULT_SHAPE = "ellipse"
