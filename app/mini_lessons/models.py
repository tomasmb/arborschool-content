"""Data models for the mini-lesson generation pipeline.

Covers configuration, lesson context, planning specs, generated
sections, quality reporting, and phase management.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.question_generation.models import AtomEnrichment

# ---------------------------------------------------------------------------
# Template type mapping (spec section 4)
# ---------------------------------------------------------------------------

TEMPLATE_MAP: dict[str, str] = {
    "procedimiento": "P",
    "concepto": "C",
    "representacion": "C",
    "argumentacion": "C",
    "concepto_procedimental": "M",
    "modelizacion": "M",
}

# ---------------------------------------------------------------------------
# Phase groups for selective execution
# ---------------------------------------------------------------------------

PHASE_GROUPS: dict[str, tuple[int, int]] = {
    "all": (0, 6),
    "plan": (0, 1),
    "generate": (2, 3),
    "assemble": (4, 4),
    "quality": (5, 5),
    "output": (6, 6),
}

PHASE_GROUP_CHOICES = list(PHASE_GROUPS.keys())

PHASE_PREREQUISITES: dict[str, list[tuple[int, str]]] = {
    "all": [],
    "plan": [],
    "generate": [(1, "plan")],
    "assemble": [(3, "validated")],
    "quality": [(4, "assembled")],
    "output": [(5, "quality")],
}

# ---------------------------------------------------------------------------
# Section word budgets (soft limits; 2x = hard reject)
# ---------------------------------------------------------------------------

SECTION_WORD_BUDGETS: dict[str, int] = {
    "objective": 35,
    "concept": 100,
    "worked-example": 180,
    "prerequisite-refresh": 80,
}

HARD_BUDGET_MULTIPLIER: float = 2.0

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class LessonConfig:
    """Configuration for a single atom mini-lesson generation run."""

    atom_id: str
    max_retries: int = 1
    output_dir: str | None = None
    resume: bool = False
    phase: str = "all"


# ---------------------------------------------------------------------------
# Lesson context (Phase 0 output)
# ---------------------------------------------------------------------------


@dataclass
class LessonContext:
    """Aggregated context for a single atom's lesson generation run.

    Built in Phase 0 from the atom definition, enrichment data,
    and sample questions from the question pipeline.
    """

    atom_id: str
    atom_title: str
    atom_description: str
    eje: str
    tipo_atomico: str
    template_type: str
    criterios_atomicos: list[str]
    ejemplos_conceptuales: list[str]
    notas_alcance: list[str]
    prerequisites: list[str]
    enrichment: AtomEnrichment | None = None
    sample_questions: dict[str, list[str]] = field(
        default_factory=dict,
    )


# ---------------------------------------------------------------------------
# Planning specs (Phase 1 output)
# ---------------------------------------------------------------------------


class WorkedExampleSpec(BaseModel):
    """Specification for the single worked example in the plan."""

    topic: str
    mathematical_context: str
    step_count: int
    numbers_to_use: str
    in_scope_items_covered: list[str] = Field(default_factory=list)
    error_families_addressed: list[str] = Field(default_factory=list)


class QuickCheckSpec(BaseModel):
    """Legacy model kept for deserializing old checkpoints."""

    stem_topic: str = ""
    correct_answer_theme: str = ""
    distractor_themes: list[str] = Field(default_factory=list)
    error_families_addressed: list[str] = Field(default_factory=list)
    difficulty: str = "simple"


class OptionalSectionSpec(BaseModel):
    """Specification for an optional section with justification.

    .. deprecated::
        Kept for backward compatibility with old checkpoints.
        Image-related sections now use ``ImagePlanEntry`` via
        ``LessonPlan.image_plan`` instead.
    """

    block_name: str
    justification: str
    content_spec: str


class ImagePlanEntry(BaseModel):
    """Which section needs an image, what type, and a brief hint.

    The hint is a short directive for the section generator; the
    generator produces the full ``image_description`` alongside
    the HTML so text and image are designed together.
    """

    target_section: str
    image_type: str
    image_description_hint: str


class LessonPlan(BaseModel):
    """Full lesson plan generated in Phase 1.

    Maps every in_scope item to at least one section and selects
    up to 5 error families to address in the worked example.
    """

    template_type: str
    objective_spec: str
    concept_spec: str
    concept_in_scope_items: list[str] = Field(default_factory=list)
    canonical_steps: list[str] = Field(
        default_factory=list,
        description=(
            "P-template only: 3-5 named steps that form the "
            "repeatable procedure for the worked example."
        ),
    )
    worked_example: WorkedExampleSpec
    checklist_items: list[str] = Field(
        default_factory=list,
        description="3 one-line PAES checklist items for the WE closing.",
    )
    optional_sections: list[OptionalSectionSpec] = Field(
        default_factory=list,
        description="Deprecated — kept for old checkpoints. Use image_plan.",
    )
    image_plan: list[ImagePlanEntry] = Field(
        default_factory=list,
        description=(
            "Sections that need a generated image. Each entry "
            "specifies the target section, image type from the "
            "taxonomy, and a brief content hint."
        ),
    )
    include_prerequisite_refresh: bool = False
    justifications: dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Generated sections (Phase 2-3 output)
# ---------------------------------------------------------------------------


class LessonSection(BaseModel):
    """A single generated HTML section of the mini-lesson."""

    block_name: str
    index: int | None = None
    html: str
    word_count: int = 0
    validation_status: str = "pending"
    validation_errors: list[str] = Field(default_factory=list)
    image_description: str = ""
    image_failed: bool = False


# ---------------------------------------------------------------------------
# Quality reporting (Phase 5 output)
# ---------------------------------------------------------------------------

RUBRIC_DIMENSIONS: list[str] = [
    "objective_clarity",
    "brevity_cognitive_load",
    "worked_example_correctness",
    "step_rationale_clarity",
]


class QualityReport(BaseModel):
    """Result of Phase 5 quality gate validation."""

    math_correct: bool = False
    math_errors: list[str] = Field(default_factory=list)
    coverage_pass: bool = False
    coverage_gaps: list[str] = Field(default_factory=list)
    dimension_scores: dict[str, int] = Field(default_factory=dict)
    total_score: int = 0
    auto_fail_triggered: bool = False
    auto_fail_reasons: list[str] = Field(default_factory=list)
    publishable: bool = False


# ---------------------------------------------------------------------------
# Phase results
# ---------------------------------------------------------------------------


@dataclass
class PhaseResult:
    """Result of a single pipeline phase."""

    phase_name: str
    success: bool
    data: Any = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pipeline-level result
# ---------------------------------------------------------------------------


@dataclass
class LessonResult:
    """Full result of running the mini-lesson pipeline for one atom."""

    atom_id: str
    success: bool = False
    phase_results: list[PhaseResult] = field(default_factory=list)
    html: str = ""
    meta: dict[str, Any] = field(default_factory=dict)
    quality_report: QualityReport | None = None
    cost_usd: float = 0.0
