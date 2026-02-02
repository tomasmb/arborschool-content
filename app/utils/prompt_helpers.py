"""Shared prompt helper functions.

This module provides common formatting functions used in prompt building
across different modules (atoms, standards) to avoid code duplication.
"""

from __future__ import annotations

from typing import Any


def format_habilidades_context(habilidades: dict[str, Any]) -> str:
    """Format habilidades dict as readable context for prompts.

    This function takes a dictionary of habilidades (skills) and formats
    them into a human-readable string suitable for inclusion in LLM prompts.

    Args:
        habilidades: Dictionary mapping habilidad IDs to their data, where
            each habilidad has 'descripcion' and 'criterios_evaluacion' keys.

    Returns:
        A formatted string with markdown-style headers and bullet points.

    Example:
        >>> habs = {
        ...     "resolver_problemas": {
        ...         "descripcion": "Resolver problemas matemáticos",
        ...         "criterios_evaluacion": ["Criterio 1", "Criterio 2"]
        ...     }
        ... }
        >>> print(format_habilidades_context(habs))
        ### resolver_problemas
        Descripción: Resolver problemas matemáticos
        Criterios de evaluación:
          - Criterio 1
          - Criterio 2
    """
    lines: list[str] = []
    for hab_id, hab_data in habilidades.items():
        lines.append(f"### {hab_id}")
        lines.append(f"Descripción: {hab_data['descripcion']}")
        lines.append("Criterios de evaluación:")
        for criterio in hab_data["criterios_evaluacion"]:
            lines.append(f"  - {criterio}")
        lines.append("")
    return "\n".join(lines)
