"""Pydantic models for prerequisite atoms and standards.

These models mirror the M1 atom/standard schemas but allow grade-level
prefixes (EB1–EB8, EM1–EM2) in IDs instead of the M1-only pattern.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

from app.models.constants import (
    EJE_PREFIXES,
    VALID_EJES,
    VALID_HABILIDAD_IDS,
    VALID_TIPO_ATOMICO,
)
from app.prerequisites.constants import (
    PREREQ_ATOM_ID_RE,
    PREREQ_STANDARD_ID_RE,
    VALID_GRADE_PREFIXES,
)

_ATOM_RE = re.compile(PREREQ_ATOM_ID_RE)


# --------------------------------------------------------------------------
# Prerequisite Standard
# --------------------------------------------------------------------------

class PrereqHabilidadRelacionada(BaseModel):
    """Habilidad link (same structure as M1, no DEMRE source)."""

    habilidad_id: str
    criterios_relevantes: list[str] = Field(default_factory=list)

    @field_validator("habilidad_id")
    @classmethod
    def _validate(cls, v: str) -> str:
        if v not in VALID_HABILIDAD_IDS:
            raise ValueError(
                f"habilidad_id must be one of "
                f"{VALID_HABILIDAD_IDS}, got '{v}'"
            )
        return v


class PrereqStandard(BaseModel):
    """A prerequisite standard (e.g. EB5-NUM-01)."""

    id: str = Field(..., pattern=PREREQ_STANDARD_ID_RE)
    grade_level: str
    eje: str
    titulo: str
    descripcion_general: str = Field(..., min_length=50)
    incluye: list[str] = Field(..., min_length=1)
    no_incluye: list[str] = Field(..., min_length=1)
    subcontenidos_clave: list[str] = Field(..., min_length=1)
    ejemplos_conceptuales: list[str] = Field(..., min_length=1)
    habilidades_relacionadas: list[PrereqHabilidadRelacionada] = Field(
        default_factory=list,
    )

    @field_validator("eje")
    @classmethod
    def _val_eje(cls, v: str) -> str:
        if v not in VALID_EJES:
            raise ValueError(f"eje must be one of {VALID_EJES}")
        return v

    @field_validator("grade_level")
    @classmethod
    def _val_grade(cls, v: str) -> str:
        if v not in VALID_GRADE_PREFIXES:
            raise ValueError(
                f"grade_level must be one of "
                f"{VALID_GRADE_PREFIXES}, got '{v}'"
            )
        return v


class PrereqStandardsFile(BaseModel):
    """Top-level wrapper for prerequisite standards JSON."""

    metadata: dict[str, str] = Field(default_factory=dict)
    standards: list[PrereqStandard] = Field(..., min_length=1)


# --------------------------------------------------------------------------
# Prerequisite Atom
# --------------------------------------------------------------------------

class PrereqAtom(BaseModel):
    """A single prerequisite learning atom (e.g. A-EB5-NUM-01-01)."""

    id: str = Field(
        ..., description="e.g. A-EB5-NUM-01-01",
    )
    grade_level: str
    eje: str
    standard_ids: list[str] = Field(..., min_length=1)
    habilidad_principal: str
    habilidades_secundarias: list[str] = Field(default_factory=list)
    tipo_atomico: str
    titulo: str
    descripcion: str = Field(..., min_length=50)
    criterios_atomicos: list[str] = Field(..., min_length=1)
    ejemplos_conceptuales: list[str] = Field(
        ..., min_length=1, max_length=4,
    )
    prerrequisitos: list[str] = Field(default_factory=list)
    notas_alcance: list[str] = Field(default_factory=list)
    en_alcance_m1: bool = Field(default=False)

    @field_validator("id")
    @classmethod
    def _val_id(cls, v: str) -> str:
        if not _ATOM_RE.match(v):
            raise ValueError(
                f"id must match {PREREQ_ATOM_ID_RE}, got '{v}'"
            )
        return v

    @field_validator("grade_level")
    @classmethod
    def _val_grade(cls, v: str) -> str:
        if v not in VALID_GRADE_PREFIXES:
            raise ValueError(
                f"grade_level must be in {VALID_GRADE_PREFIXES}"
            )
        return v

    @field_validator("eje")
    @classmethod
    def _val_eje(cls, v: str) -> str:
        if v not in VALID_EJES:
            raise ValueError(f"eje must be one of {VALID_EJES}")
        return v

    @field_validator("habilidad_principal")
    @classmethod
    def _val_hab(cls, v: str) -> str:
        if v not in VALID_HABILIDAD_IDS:
            raise ValueError(
                f"habilidad_principal must be one of "
                f"{VALID_HABILIDAD_IDS}"
            )
        return v

    @field_validator("habilidades_secundarias")
    @classmethod
    def _val_hab_sec(cls, v: list[str]) -> list[str]:
        for h in v:
            if h not in VALID_HABILIDAD_IDS:
                raise ValueError(f"Invalid habilidad: '{h}'")
        return v

    @field_validator("tipo_atomico")
    @classmethod
    def _val_tipo(cls, v: str) -> str:
        if v not in VALID_TIPO_ATOMICO:
            raise ValueError(
                f"tipo_atomico must be one of {VALID_TIPO_ATOMICO}"
            )
        return v


def validate_prereq_atom_id_matches_eje(atom: PrereqAtom) -> None:
    """Ensure the atom ID eje prefix matches its eje field."""
    expected = EJE_PREFIXES.get(atom.eje)
    if expected is None:
        raise ValueError(f"Unknown eje '{atom.eje}'")
    parts = atom.id.split("-")
    if len(parts) < 3:
        raise ValueError(f"Invalid atom ID format: {atom.id}")
    id_eje = parts[2]
    if id_eje != expected:
        raise ValueError(
            f"ID prefix '{id_eje}' doesn't match "
            f"eje '{atom.eje}' (expected '{expected}')"
        )


class PrereqAtomsFile(BaseModel):
    """Top-level wrapper for prerequisite atoms JSON."""

    metadata: dict[str, str] = Field(default_factory=dict)
    atoms: list[PrereqAtom] = Field(..., min_length=1)
