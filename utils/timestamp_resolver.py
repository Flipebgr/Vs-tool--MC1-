"""
Resolve o timestamp "real" de um evento, quando ele existe embutido em
`details` — em vez de depender só de `when`, que é hora de log/servidor
(pode ter até ~9h de defasagem em relação à ação real, ver assign_agent_task
vs access_email nos dados brutos).

O mapeamento abaixo foi levantado empiricamente varrendo amostras de cada
short_name em events.parquet (ver conversa de 03/07/2026). Cobertura é
parcial em vários tipos (ex: access_email só tem `time` embutido em ~16%
dos casos) — por isso a resolução SEMPRE tem fallback para `datetime_utc`
(derivado de `when`), nunca falha nem retorna None.

Cada entrada é uma lista de "paths" (dot-notation) tentados em ordem de
prioridade; o primeiro que existir e for uma string ISO 8601 válida vence.
"""

import re
from typing import Optional

ISO_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

# short_name -> lista de paths (ordem de prioridade) onde procurar o
# timestamp embutido dentro do dict `details` já parseado.
TIMESTAMP_FIELD_MAP = {
    "flex_post": ["timestamp"],
    "saidit_post": ["timestamp"],
    "access_email": ["time"],
    "access_files": ["time"],
    "assign_agent_task": ["details.time"],
    "give_advice": ["time"],
    "post_flex": ["time"],
    "post_saidit": ["time"],
    "propose_meeting": ["meeting.time", "a2a.timestamp", "a2a.payload.time", "details.time", "time"],
    "queue_subordinate_task": ["time"],
    "suggest_contacts": ["time"],
    # Demais short_names (ask_agent, check_access, check_email, check_in,
    # create_file, delete_file, enter_room, list_files, read_file, received,
    # saidit_post_check, send_email, sent) não têm timestamp embutido em
    # nenhuma amostra observada -> caem direto no fallback.
}


def _get_nested(d: dict, path: str) -> Optional[str]:
    """Navega um dict por um path tipo 'details.time' ou 'a2a.payload.time'."""
    node = d
    for key in path.split("."):
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node if isinstance(node, str) else None


def resolve_event_timestamp(short_name: str, details: Optional[dict]):
    """
    Retorna (timestamp_iso_str_or_None, source), onde source é
    "embedded" se achou um timestamp confiável dentro de `details`,
    ou None (o chamador deve usar o fallback datetime_utc).
    """
    if not details:
        return None, None

    for path in TIMESTAMP_FIELD_MAP.get(short_name, []):
        value = _get_nested(details, path)
        if value and ISO_PATTERN.match(value):
            return value, "embedded"

    return None, None
