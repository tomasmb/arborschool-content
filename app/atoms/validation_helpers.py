"""Shared atom granularity validation heuristics.

Used by both M1 and prerequisite atom generation pipelines to check
basic granularity indicators (description length, criteria count,
secondary habilidades count).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class HasGranularityFields(Protocol):
    """Any atom-like object with the fields needed for granularity checks."""

    id: str
    descripcion: str
    criterios_atomicos: list[str]
    habilidades_secundarias: list[str]


_MAX_DESCRIPCION_LEN = 300
_MAX_CRITERIOS = 5
_MAX_HABILIDADES_SEC = 2


def validate_atom_granularity(
    atoms: list[HasGranularityFields],
) -> list[str]:
    """Basic granularity heuristics applicable to any atom type.

    Returns list of warning messages (empty if all pass).
    """
    warnings: list[str] = []
    for atom in atoms:
        if len(atom.descripcion) > _MAX_DESCRIPCION_LEN:
            warnings.append(
                f"{atom.id}: descripcion may be too long "
                f"({len(atom.descripcion)} chars), "
                f"might contain multiple intentions"
            )
        if len(atom.criterios_atomicos) > _MAX_CRITERIOS:
            warnings.append(
                f"{atom.id}: too many criterios_atomicos "
                f"({len(atom.criterios_atomicos)}), "
                f"might overload working memory"
            )
        if len(atom.habilidades_secundarias) > _MAX_HABILIDADES_SEC:
            warnings.append(
                f"{atom.id}: many habilidades_secundarias "
                f"({len(atom.habilidades_secundarias)}), "
                f"might need splitting"
            )
    return warnings
