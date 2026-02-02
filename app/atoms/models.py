"""Pydantic models for canonical atoms JSON.

These models enforce the schema defined in `docs/standards-from-temarios.md`
section 7, ensuring strict validation of all generated atoms.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.models.constants import (
    EJE_PREFIXES,
    VALID_EJES,
    VALID_HABILIDAD_IDS,
    VALID_TIPO_ATOMICO,
)

# -----------------------------------------------------------------------------
# Atom model
# -----------------------------------------------------------------------------


class Atom(BaseModel):
    """A single learning atom as defined in docs/standards-from-temarios.md."""

    id: str = Field(
        ...,
        description="Stable identifier, e.g. A-M1-NUM-01-01",
        pattern=r"^A-M1-(NUM|ALG|GEO|PROB)-\d{2}-\d{2}$",
    )
    eje: str = Field(
        ...,
        description="Eje temático label",
    )
    standard_ids: list[str] = Field(
        ...,
        min_length=1,
        description="One or more standards this atom supports",
    )
    habilidad_principal: str = Field(
        ...,
        description="Primary habilidad: resolver_problemas, modelar, representar, argumentar",
    )
    habilidades_secundarias: list[str] = Field(
        default_factory=list,
        description="Optional secondary habilidades",
    )
    tipo_atomico: str = Field(
        ...,
        description="Classification: concepto, procedimiento, representacion, etc.",
    )
    titulo: str = Field(
        ...,
        description="Short, student-facing title",
    )
    descripcion: str = Field(
        ...,
        min_length=50,
        description="Rich description of the cognitive intention (learning objective)",
    )
    criterios_atomicos: list[str] = Field(
        ...,
        min_length=1,
        description="Success criteria for mastering this atom",
    )
    ejemplos_conceptuales: list[str] = Field(
        ...,
        min_length=1,
        max_length=3,
        description="1-3 non-exercise examples illustrating the atom",
    )
    prerrequisitos: list[str] = Field(
        default_factory=list,
        description="List of other atom IDs required before this atom",
    )
    notas_alcance: list[str] = Field(
        default_factory=list,
        description="Optional list clarifying what is excluded from this atom",
    )
    en_alcance_m1: bool = Field(
        default=True,
        description="Whether this atom is within the evaluable scope of current M1",
    )

    @field_validator("eje")
    @classmethod
    def validate_eje(cls, v: str) -> str:
        if v not in VALID_EJES:
            msg = f"eje must be one of {VALID_EJES}, got '{v}'"
            raise ValueError(msg)
        return v

    @field_validator("habilidad_principal")
    @classmethod
    def validate_habilidad_principal(cls, v: str) -> str:
        if v not in VALID_HABILIDAD_IDS:
            msg = f"habilidad_principal must be one of {VALID_HABILIDAD_IDS}, got '{v}'"
            raise ValueError(msg)
        return v

    @field_validator("habilidades_secundarias")
    @classmethod
    def validate_habilidades_secundarias(cls, v: list[str]) -> list[str]:
        for hab in v:
            if hab not in VALID_HABILIDAD_IDS:
                msg = f"habilidades_secundarias must contain only {VALID_HABILIDAD_IDS}, got '{hab}'"
                raise ValueError(msg)
        return v

    @field_validator("tipo_atomico")
    @classmethod
    def validate_tipo_atomico(cls, v: str) -> str:
        if v not in VALID_TIPO_ATOMICO:
            msg = f"tipo_atomico must be one of {VALID_TIPO_ATOMICO}, got '{v}'"
            raise ValueError(msg)
        return v

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        parts = v.split("-")
        if len(parts) != 5 or parts[0] != "A" or parts[1] != "M1":
            msg = f"id must follow pattern A-M1-<EJE>-NN-MM, got '{v}'"
            raise ValueError(msg)
        return v

    @field_validator("standard_ids")
    @classmethod
    def validate_standard_ids_format(cls, v: list[str]) -> list[str]:
        for std_id in v:
            if not std_id.startswith("M1-"):
                msg = f"standard_ids must start with 'M1-', got '{std_id}'"
                raise ValueError(msg)
        return v


# -----------------------------------------------------------------------------
# Top-level structures
# -----------------------------------------------------------------------------


class AtomsMetadata(BaseModel):
    """Document-level information for a canonical atoms file."""

    id: str = Field(
        ...,
        description="Unique identifier, e.g. paes_m1_regular_2026_atoms",
    )
    proceso_admision: int = Field(
        ...,
        ge=2020,
        le=2100,
        description="Year of the admission process",
    )
    tipo_aplicacion: str = Field(
        ...,
        description="Type of application: regular, invierno, etc.",
    )
    nombre_prueba: str = Field(
        ...,
        description="Full name of the test",
    )
    source_standards_json: str = Field(
        ...,
        description="Path to the source standards JSON file",
    )
    generated_with: str = Field(
        default="gemini-3-pro-preview",
        description="Model used for generation",
    )
    version: str = Field(
        ...,
        description="Date string for versioning, e.g. 2025-11-26",
    )


class CanonicalAtomsFile(BaseModel):
    """Top-level structure for a canonical atoms JSON file."""

    metadata: AtomsMetadata
    atoms: list[Atom] = Field(
        ...,
        min_length=1,
        description="List of atoms covering all standards",
    )

    def get_atom_by_id(self, atom_id: str) -> Atom | None:
        """Find an atom by its ID."""
        for a in self.atoms:
            if a.id == atom_id:
                return a
        return None

    def get_atoms_by_standard(self, standard_id: str) -> list[Atom]:
        """Get all atoms that support a given standard."""
        return [a for a in self.atoms if standard_id in a.standard_ids]

    def get_atoms_by_eje(self, eje: str) -> list[Atom]:
        """Get all atoms for a given eje."""
        return [a for a in self.atoms if a.eje == eje]


# -----------------------------------------------------------------------------
# Validation helpers
# -----------------------------------------------------------------------------


def validate_atom_id_matches_eje(atom: Atom) -> None:
    """Ensure the atom ID prefix matches its eje."""
    expected_prefix = EJE_PREFIXES.get(atom.eje)
    if expected_prefix is None:
        msg = f"Unknown eje '{atom.eje}'"
        raise ValueError(msg)

    id_parts = atom.id.split("-")
    if len(id_parts) < 3:
        msg = f"Invalid atom ID format: {atom.id}"
        raise ValueError(msg)

    id_prefix = id_parts[2]
    if id_prefix != expected_prefix:
        msg = f"Atom ID prefix '{id_prefix}' doesn't match eje '{atom.eje}' (expected '{expected_prefix}')"
        raise ValueError(msg)
