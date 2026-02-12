"""Data models for the per-atom question generation pipeline.

Covers all pipeline data structures: configuration, phase results,
plan slots, enrichment, pipeline metadata, and exemplars.
Matches the spec in docs/research/arbor_paes_question_generation_pipeline_v3_1_llm_optimized.md
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DifficultyLevel(str, Enum):
    """Within-atom difficulty levels (spec section 4.2)."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class EnrichmentStatus(str, Enum):
    """Outcome of the atom enrichment phase (spec section 5)."""

    PRESENT = "present"
    MISSING = "missing"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Phase groups that can be run individually.
# Each maps to one or more pipeline phases (0-10).
PHASE_GROUPS: dict[str, tuple[int, int]] = {
    "all": (0, 10),
    "enrich": (0, 1),        # Phases 0-1: inputs + enrichment
    "plan": (2, 3),           # Phases 2-3: plan generation + validation
    "generate": (4, 4),       # Phase 4: base QTI generation
    "validate": (5, 6),       # Phases 5-6: dedupe + base validation
    "feedback": (7, 8),       # Phases 7-8: feedback enrichment
    "finalize": (9, 10),      # Phases 9-10: final validation + sync
}

PHASE_GROUP_CHOICES = list(PHASE_GROUPS.keys())


# ---------------------------------------------------------------------------
# Difficulty distribution (mastery-driven pool sizing)
# ---------------------------------------------------------------------------


@dataclass
class DifficultyDistribution:
    """Per-difficulty item counts for the question pool.

    Derived from the mastery spec: max 20 questions per attempt,
    2 full attempts of unique questions, plus a per-level buffer.
    See docs/specifications/learning-method-specification.md.
    """

    easy: int
    medium: int
    hard: int

    @property
    def total(self) -> int:
        """Total items across all difficulty levels."""
        return self.easy + self.medium + self.hard


def compute_planned_distribution(
    target: DifficultyDistribution,
    buffer_ratio: float,
) -> DifficultyDistribution:
    """Apply buffer ratio to a target distribution.

    Ceiling is used so every level gets at least the buffer.

    Args:
        target: Mastery-driven target counts per difficulty.
        buffer_ratio: Multiplier for over-generation (e.g. 1.3).

    Returns:
        New distribution with buffered counts.
    """
    return DifficultyDistribution(
        easy=math.ceil(target.easy * buffer_ratio),
        medium=math.ceil(target.medium * buffer_ratio),
        hard=math.ceil(target.hard * buffer_ratio),
    )


# Mastery spec: 14 easy + 18 medium + 14 hard = 46 target items.
# See docs/specifications/learning-method-specification.md §Question Pool.
DEFAULT_TARGET_DISTRIBUTION = DifficultyDistribution(
    easy=14, medium=18, hard=14,
)

# 30% over-generation to absorb pipeline attrition
# (dedupe, validation, feedback gates).
DEFAULT_BUFFER_RATIO: float = 1.3


@dataclass
class PipelineConfig:
    """Configuration for a single atom question generation run.

    Attributes:
        atom_id: Target atom identifier (e.g. "A-M1-ALG-01-02").
        target_distribution: Mastery-driven target counts per
            difficulty (default 14E/18M/14H = 46).
        buffer_ratio: Over-generation multiplier (default 1.3).
        max_retries: Max LLM retries per phase.
        output_dir: Override for output directory.
        skip_enrichment: Skip Phase 1 enrichment.
        skip_sync: Skip Phase 10 DB sync.
        dry_run: Run through Phase 9 but skip DB sync.
        resume: Resume from last checkpoint if available.
        phase: Phase group to run (default "all"). See PHASE_GROUPS.
    """

    atom_id: str
    target_distribution: DifficultyDistribution = field(
        default_factory=lambda: DEFAULT_TARGET_DISTRIBUTION,
    )
    buffer_ratio: float = DEFAULT_BUFFER_RATIO
    max_retries: int = 2
    output_dir: str | None = None
    skip_enrichment: bool = False
    skip_sync: bool = False
    dry_run: bool = False
    resume: bool = False
    phase: str = "all"

    @property
    def planned_distribution(self) -> DifficultyDistribution:
        """Distribution sent to the planner (target + buffer)."""
        return compute_planned_distribution(
            self.target_distribution, self.buffer_ratio,
        )


# ---------------------------------------------------------------------------
# Exemplars (sourced from finalized tests)
# ---------------------------------------------------------------------------


@dataclass
class Exemplar:
    """A real PAES item used as a reference for generation.

    Exemplars are NEVER served to students or paraphrased.
    They anchor plan slots to real-PAES difficulty and style.
    """

    question_id: str
    test_id: str
    qti_xml: str
    atom_ids: list[str] = field(default_factory=list)
    difficulty_level: str = "medium"
    question_text: str = ""


# ---------------------------------------------------------------------------
# Phase 1 — Atom Enrichment (spec section 10.1)
# ---------------------------------------------------------------------------


class ScopeGuardrails(BaseModel):
    """Defines what is in/out of scope for the atom."""

    in_scope: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    common_traps: list[str] = Field(default_factory=list)


class ErrorFamily(BaseModel):
    """A common misconception or error pattern."""

    name: str
    description: str
    how_to_address: str = ""


class AtomEnrichment(BaseModel):
    """Enrichment data for an atom (spec section 10.1).

    Provides scope guardrails, difficulty rubric, and pedagogical
    guidance for the planner and validators.
    """

    scope_guardrails: ScopeGuardrails = Field(
        default_factory=ScopeGuardrails,
    )
    difficulty_rubric: dict[str, list[str]] = Field(
        default_factory=lambda: {"easy": [], "medium": [], "hard": []},
    )
    ambiguity_avoid: list[str] = Field(default_factory=list)
    error_families: list[ErrorFamily] = Field(default_factory=list)
    future_targets: list[str] = Field(default_factory=list)
    representation_variants: list[str] = Field(default_factory=list)
    numbers_profiles: list[str] = Field(
        default_factory=lambda: [
            "small_integers", "fractions", "mixed", "decimals",
        ],
    )
    # Image type analysis (Phase 1 enrichment extension)
    required_image_types: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase 2 — Plan Slot (spec section 10.2)
# ---------------------------------------------------------------------------


class PlanSlot(BaseModel):
    """A single planned item specification.

    Each slot is materialized into a base QTI XML item in Phase 4.
    """

    slot_index: int = 0
    component_tag: str
    difficulty_level: DifficultyLevel
    operation_skeleton_ast: str
    surface_context: str = "pure_math"
    numbers_profile: str = "small_integers"
    # Exemplar anchoring (required when exemplars exist)
    target_exemplar_id: str | None = None
    distance_level: str | None = None
    # Image generation fields (set by planner when atom needs images)
    image_required: bool = False
    image_type: str | None = None
    image_description: str | None = None


# ---------------------------------------------------------------------------
# Pipeline metadata (spec section 10.3)
# ---------------------------------------------------------------------------


class ValidatorReports(BaseModel):
    """Validation status for each check (spec section 10.3)."""

    xsd: str = "pending"
    solve_check: str = "pending"
    scope: str = "pending"
    exemplar_copy_check: str = "pending"
    feedback: str = "pending"
    dedupe: str = "pending"


class PipelineMeta(BaseModel):
    """Non-QTI metadata stored alongside each item (spec section 10.3)."""

    atom_id: str
    component_tag: str
    difficulty_level: DifficultyLevel
    operation_skeleton_ast: str
    surface_context: str = "pure_math"
    numbers_profile: str = "small_integers"
    fingerprint: str = ""
    # Exemplar anchoring (carried from PlanSlot for validation)
    target_exemplar_id: str | None = None
    distance_level: str | None = None
    validators: ValidatorReports = Field(
        default_factory=ValidatorReports,
    )


# ---------------------------------------------------------------------------
# Phase results (generic container)
# ---------------------------------------------------------------------------


@dataclass
class PhaseResult:
    """Result of a single pipeline phase.

    Attributes:
        phase_name: Human-readable phase identifier.
        success: Whether the phase passed its gate (if blocking).
        data: Phase-specific output payload.
        errors: Blocking errors that caused failure.
        warnings: Non-blocking warnings.
    """

    phase_name: str
    success: bool
    data: Any = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Atom context (Phase 0 output)
# ---------------------------------------------------------------------------


@dataclass
class AtomContext:
    """Aggregated context for a single atom's generation run.

    Built in Phase 0 from the atom definition, exemplars,
    component definitions, and existing inventory summary.
    """

    atom_id: str
    atom_title: str
    atom_description: str
    eje: str
    standard_ids: list[str]
    tipo_atomico: str
    criterios_atomicos: list[str]
    ejemplos_conceptuales: list[str]
    notas_alcance: list[str]
    exemplars: list[Exemplar] = field(default_factory=list)
    existing_item_count: int = 0


# ---------------------------------------------------------------------------
# Pipeline-level result
# ---------------------------------------------------------------------------


@dataclass
class GeneratedItem:
    """A single generated question with its QTI XML and metadata."""

    item_id: str
    qti_xml: str
    pipeline_meta: PipelineMeta | None = None
    slot_index: int = 0


@dataclass
class PipelineResult:
    """Full result of running the atom question generation pipeline.

    Attributes:
        atom_id: The atom that was processed.
        success: Overall pipeline success.
        phase_results: Ordered list of phase results for traceability.
        final_items: Items that passed all validation gates.
        total_planned: Number of plan slots generated.
        total_generated: Base items generated (Phase 4).
        total_passed_dedupe: Items surviving dedupe gate (Phase 5).
        total_passed_base_validation: Items passing base checks (Phase 6).
        total_passed_feedback: Items passing feedback enrichment (Phase 7-8).
        total_final: Items passing final validation (Phase 9).
        total_synced: Items synced to DB (Phase 10).
    """

    atom_id: str
    success: bool = False
    phase_results: list[PhaseResult] = field(default_factory=list)
    final_items: list[GeneratedItem] = field(default_factory=list)
    total_planned: int = 0
    total_generated: int = 0
    total_passed_dedupe: int = 0
    total_passed_base_validation: int = 0
    total_passed_feedback: int = 0
    total_final: int = 0
    total_synced: int = 0
