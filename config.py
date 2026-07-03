"""
Configurações globais do projeto Tenant Thread Visual Analytics.

Centraliza caminhos de dados para que services/, callbacks/ e app.py
nunca precisem hardcodar strings de path.
"""

from pathlib import Path

# --- Diretórios base -------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
EXPORTS_DIR = BASE_DIR / "exports"

# --- Dados brutos (entrada do desafio, nunca modificados) ------------------

ORG_CHART_RAW = RAW_DIR / "org_chart.json"
MC2_DATA_RAW = RAW_DIR / "MC2_data.json"

# --- Dados processados (gerados pelo ETL, consumidos pelo app) -------------

EVENTS_PARQUET = PROCESSED_DIR / "events.parquet"
ENTITIES_JSON = PROCESSED_DIR / "entities.json"
GRAPH_JSON = PROCESSED_DIR / "graph.json"
UNRESOLVED_LOG = PROCESSED_DIR / "unresolved_parties.json"


def ensure_processed_dir() -> None:
    """Garante que data/processed/ existe antes do ETL escrever nela."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
