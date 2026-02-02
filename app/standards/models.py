"""Pydantic models for canonical standards JSON.

These models enforce the schema defined in `docs/standards-from-temarios.md`
section 2, ensuring strict validation of all generated standards.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

# -----------------------------------------------------------------------------
# Constants for validation
# -----------------------------------------------------------------------------

VALID_EJES = frozenset({
    "numeros",
    "algebra_y_funciones",
    "geometria",
    "probabilidad_y_estadistica",
})

EJE_PREFIXES = {
    "numeros": "NUM",
    "algebra_y_funciones": "ALG",
    "geometria": "GEO",
    "probabilidad_y_estadistica": "PROB",
}

VALID_HABILIDAD_IDS = frozenset({
    "resolver_problemas",
    "modelar",
    "representar",
    "argumentar",
})


# -----------------------------------------------------------------------------
# Standard components
# -----------------------------------------------------------------------------

class HabilidadRelacionada(BaseModel):
    """Link between a standard and a DEMRE habilidad."""

    habilidad_id: str = Field(
        ...,
        description="One of: resolver_problemas, modelar, representar, argumentar",
    )
    criterios_relevantes: list[str] = Field(
        default_factory=list,
        description="Subset of criterios de evaluación aligned with this standard",
    )

    @field_validator("habilidad_id")
    @classmethod
    def validate_habilidad_id(cls, v: str) -> str:
        if v not in VALID_HABILIDAD_IDS:
            msg = f"habilidad_id must be one of {VALID_HABILIDAD_IDS}, got '{v}'"
            raise ValueError(msg)
        return v


class FuentesTemario(BaseModel):
    """Traceability back to the original temario JSON."""

    conocimientos_path: str = Field(
        ...,
        description="JSON path string into the temario, e.g. 'conocimientos.numeros.unidades[0]'",
    )
    descripciones_originales: list[str] = Field(
        ...,
        min_length=1,
        description="Original description strings from the temario",
    )


class Standard(BaseModel):
    """A single canonical standard as defined in docs/standards-from-temarios.md."""

    id: str = Field(
        ...,
        description="Stable code, e.g. M1-NUM-01",
        pattern=r"^M1-(NUM|ALG|GEO|PROB)-\d{2}$",
    )
    eje: str = Field(
        ...,
        description="Eje temático label",
    )
    unidad_temario: str = Field(
        ...,
        description="Exact unidad name from the temario JSON",
    )
    titulo: str = Field(
        ...,
        description="Short human-readable title for the standard",
    )
    descripcion_general: str = Field(
        ...,
        min_length=100,
        description="Rich narrative description of the standard",
    )
    incluye: list[str] = Field(
        ...,
        min_length=1,
        description="Bullet-style strings describing what is inside the scope",
    )
    no_incluye: list[str] = Field(
        ...,
        min_length=1,
        description="Bullet-style strings describing explicit exclusions",
    )
    subcontenidos_clave: list[str] = Field(
        ...,
        min_length=1,
        description="Fine-grained sub-concepts, written with atom granularity in mind",
    )
    ejemplos_conceptuales: list[str] = Field(
        ...,
        min_length=1,
        description="Conceptual example descriptions (no full exercises)",
    )
    habilidades_relacionadas: list[HabilidadRelacionada] = Field(
        default_factory=list,
        description="Mapping to DEMRE habilidades",
    )
    fuentes_temario: FuentesTemario = Field(
        ...,
        description="Traceability back to the original temario JSON",
    )

    @field_validator("eje")
    @classmethod
    def validate_eje(cls, v: str) -> str:
        if v not in VALID_EJES:
            msg = f"eje must be one of {VALID_EJES}, got '{v}'"
            raise ValueError(msg)
        return v

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        # Additional validation: ensure the prefix matches expected pattern
        parts = v.split("-")
        if len(parts) != 3 or parts[0] != "M1":
            msg = f"id must follow pattern M1-<EJE>-NN, got '{v}'"
            raise ValueError(msg)
        return v


# -----------------------------------------------------------------------------
# Top-level structures
# -----------------------------------------------------------------------------

class StandardsMetadata(BaseModel):
    """Document-level information for a canonical standards file."""

    id: str = Field(
        ...,
        description="Unique identifier, e.g. paes_m1_regular_2026",
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
    source_temario_json: str = Field(
        ...,
        description="Path to the source temario JSON file",
    )
    generated_with: str = Field(
        default="gemini-3-pro-preview",
        description="Model used for generation",
    )
    version: str = Field(
        ...,
        description="Date string for versioning, e.g. 2025-11-26",
    )


class CanonicalStandardsFile(BaseModel):
    """Top-level structure for a canonical standards JSON file."""

    metadata: StandardsMetadata
    standards: list[Standard] = Field(
        ...,
        min_length=1,
        description="List of standards covering all temario unidades",
    )

    def get_standard_by_id(self, standard_id: str) -> Standard | None:
        """Find a standard by its ID."""
        for s in self.standards:
            if s.id == standard_id:
                return s
        return None

    def get_standards_by_eje(self, eje: str) -> list[Standard]:
        """Get all standards for a given eje."""
        return [s for s in self.standards if s.eje == eje]


# -----------------------------------------------------------------------------
# Validation helpers
# -----------------------------------------------------------------------------

def validate_standard_id_matches_eje(standard: Standard) -> None:
    """Ensure the standard ID prefix matches its eje."""
    expected_prefix = EJE_PREFIXES.get(standard.eje)
    if expected_prefix is None:
        msg = f"Unknown eje '{standard.eje}'"
        raise ValueError(msg)

    id_prefix = standard.id.split("-")[1]
    if id_prefix != expected_prefix:
        msg = f"Standard ID prefix '{id_prefix}' doesn't match eje '{standard.eje}' (expected '{expected_prefix}')"
        raise ValueError(msg)


def validate_standards_coverage(
    standards: list[Standard],
    temario_unidades: dict[str, list[str]],
) -> list[str]:
    """
    Check that every unidad in the temario is covered by at least one standard.

    Args:
        standards: List of generated standards.
        temario_unidades: Dict mapping eje -> list of unidad names.

    Returns:
        List of error messages (empty if all valid).
    """
    errors: list[str] = []

    covered_unidades: dict[str, set[str]] = {eje: set() for eje in temario_unidades}

    for s in standards:
        if s.eje in covered_unidades:
            covered_unidades[s.eje].add(s.unidad_temario)

    for eje, expected_unidades in temario_unidades.items():
        covered = covered_unidades.get(eje, set())
        for unidad in expected_unidades:
            if unidad not in covered:
                errors.append(f"Unidad '{unidad}' in eje '{eje}' not covered by any standard")

    return errors

