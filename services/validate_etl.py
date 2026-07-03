"""
Confere a integridade dos artefatos gerados pelo ETL.

Uso:
    python -m services.validate_etl
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

import config
from utils.loader import load_json


def run() -> None:
    print("Validando artefatos processados ...\n")
    ok = True

    # --- Contagem de eventos originais vs. processados ---------------------
    raw_events = load_json(config.MC2_DATA_RAW)["events"]
    events_df = pd.read_parquet(config.EVENTS_PARQUET)

    print(f"Eventos brutos     : {len(raw_events)}")
    print(f"Eventos processados: {len(events_df)}")
    if len(raw_events) != len(events_df):
        print("  [FALHA] Quantidade de eventos não bate.")
        ok = False
    else:
        print("  [OK]")

    # --- Parties não resolvidas ---------------------------------------------
    with open(config.UNRESOLVED_LOG, encoding="utf8") as f:
        unresolved = json.load(f)

    print(f"\nParties não resolvidas: {len(unresolved)}")
    if unresolved:
        print("  [ATENÇÃO] Exemplos:")
        for item in unresolved[:10]:
            print(f"    - evento {item['event_id']}: {item['raw_party']!r}")
        ok = False
    else:
        print("  [OK]")

    # --- Entidades no grafo vs. referenciadas nos eventos -------------------
    with open(config.ENTITIES_JSON, encoding="utf8") as f:
        entities = json.load(f)

    referenced_ids = set()
    for parties in events_df["parties_canonical"]:
        referenced_ids.update(parties)

    missing = referenced_ids - set(entities.keys())
    print(f"\nEntidades no registro: {len(entities)}")
    print(f"IDs referenciados nos eventos mas ausentes do registro: {len(missing)}")
    if missing:
        print(f"  [FALHA] Exemplos: {list(missing)[:10]}")
        ok = False
    else:
        print("  [OK]")

    # --- Distribuição por tipo de entidade -----------------------------------
    from collections import Counter

    type_counts = Counter(attrs.get("type") for attrs in entities.values())
    print("\nDistribuição de entidades por tipo:")
    for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {t or '(sem tipo)'}: {c}")

    print("\n" + ("TUDO OK ✔" if ok else "ENCONTRADOS PROBLEMAS ✘"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    run()
