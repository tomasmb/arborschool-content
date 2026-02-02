"""Shared constants for the arborschool-content application.

This module centralizes constants used across multiple modules to ensure
consistency and follow DRY principles.

Constants defined here:
- Eje (axis) identifiers and their prefixes
- Habilidad (skill) identifiers
- Atom type identifiers
"""

from __future__ import annotations

# -----------------------------------------------------------------------------
# Eje (Axis) Constants
# -----------------------------------------------------------------------------

VALID_EJES = frozenset(
    {
        "numeros",
        "algebra_y_funciones",
        "geometria",
        "probabilidad_y_estadistica",
    }
)

EJE_PREFIXES = {
    "numeros": "NUM",
    "algebra_y_funciones": "ALG",
    "geometria": "GEO",
    "probabilidad_y_estadistica": "PROB",
}

# Alias for compatibility with prompts modules that use EJE_PREFIX_MAP
EJE_PREFIX_MAP = EJE_PREFIXES


# -----------------------------------------------------------------------------
# Habilidad (Skill) Constants
# -----------------------------------------------------------------------------

VALID_HABILIDAD_IDS = frozenset(
    {
        "resolver_problemas",
        "modelar",
        "representar",
        "argumentar",
    }
)


# -----------------------------------------------------------------------------
# Atom Type Constants
# -----------------------------------------------------------------------------

VALID_TIPO_ATOMICO = frozenset(
    {
        "concepto",
        "procedimiento",
        "representacion",
        "argumentacion",
        "modelizacion",
        "concepto_procedimental",
    }
)
