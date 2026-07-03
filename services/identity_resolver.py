"""
Resolução de identidade para o dataset do VAST Challenge 2026 - MC2.

O campo `parties` dos eventos em MC2_data.json referencia entidades em
pelo menos 5 formatos textuais diferentes:

    person:isaac_mast          -> pessoa (já no formato canônico do org_chart)
    Agent/person:isaac_mast    -> agente de IA de uma pessoa
    agent:person:isaac_mast    -> mesmo agente acima, formato alternativo de log
    system:saidit               -> sistema interno (email_server, file_system,
                                    flex, saidit)
    world:calendar               -> entidade de "mundo" (não é pessoa/sistema)
    "Owen Hatch"                -> nome completo puro, usado em check_access /
                                    enter_room (controle de acesso físico)

Este módulo resolve qualquer uma dessas variantes para um ID canônico único
e um tipo, de forma que o restante da aplicação nunca precise lidar com essa
ambiguidade.
"""

import re
from dataclasses import dataclass
from typing import Dict, Optional

import networkx as nx

_AGENT_PATTERN = re.compile(r"^(?:Agent/person|agent:person):(?P<slug>.+)$", re.IGNORECASE)
_PERSON_PATTERN = re.compile(r"^person:(?P<slug>.+)$", re.IGNORECASE)
_SYSTEM_PATTERN = re.compile(r"^system:(?P<slug>.+)$", re.IGNORECASE)
_WORLD_PATTERN = re.compile(r"^world:(?P<slug>.+)$", re.IGNORECASE)


@dataclass(frozen=True)
class ResolvedParty:
    raw: str
    canonical_id: Optional[str]
    type: str  # "person" | "agent" | "system" | "world" | "unresolved"
    resolved: bool


def build_name_lookup(org_graph: nx.DiGraph) -> Dict[str, str]:
    """
    Constrói um dicionário {nome_completo_normalizado: node_id} a partir dos
    nós do tipo "person" do organograma. Necessário para resolver eventos
    como check_access/enter_room, que usam nome completo em vez de
    "person:slug".
    """
    lookup: Dict[str, str] = {}
    for node_id, attrs in org_graph.nodes(data=True):
        if attrs.get("type") == "person":
            label = attrs.get("label", "")
            lookup[_normalize_name(label)] = node_id
    return lookup


def _normalize_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def resolve_party(raw_party: str, name_lookup: Dict[str, str]) -> ResolvedParty:
    """
    Resolve uma única string de `parties` para sua identidade canônica.
    """
    if not raw_party:
        return ResolvedParty(raw=raw_party, canonical_id=None, type="unresolved", resolved=False)

    match = _AGENT_PATTERN.match(raw_party)
    if match:
        slug = match.group("slug")
        return ResolvedParty(raw=raw_party, canonical_id=f"agent:{slug}", type="agent", resolved=True)

    match = _PERSON_PATTERN.match(raw_party)
    if match:
        return ResolvedParty(raw=raw_party, canonical_id=raw_party, type="person", resolved=True)

    match = _SYSTEM_PATTERN.match(raw_party)
    if match:
        return ResolvedParty(raw=raw_party, canonical_id=raw_party, type="system", resolved=True)

    match = _WORLD_PATTERN.match(raw_party)
    if match:
        return ResolvedParty(raw=raw_party, canonical_id=raw_party, type="world", resolved=True)

    # Não bateu com nenhum prefixo conhecido -> provavelmente um nome completo
    # (formato usado em check_access / enter_room).
    person_id = name_lookup.get(_normalize_name(raw_party))
    if person_id:
        return ResolvedParty(raw=raw_party, canonical_id=person_id, type="person", resolved=True)

    # Não foi possível resolver. Não inventamos um ID - reportamos como
    # não-resolvido para que o ETL registre e o time possa investigar.
    return ResolvedParty(raw=raw_party, canonical_id=None, type="unresolved", resolved=False)


def person_id_for_agent(agent_canonical_id: str) -> str:
    """
    Dado um ID canônico de agente (ex: "agent:isaac_mast"), retorna o ID
    canônico da pessoa correspondente (ex: "person:isaac_mast").
    """
    slug = agent_canonical_id.split(":", 1)[1]
    return f"person:{slug}"
