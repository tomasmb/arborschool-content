"""Data models for the assessment variant generation pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ValidationVerdict(str, Enum):
    """Possible validation outcomes."""

    APPROVED = "APROBADA"
    REJECTED = "RECHAZADA"


@dataclass
class SourceQuestion:
    """A source question loaded from the finalized tests.

    Attributes:
        question_id: Unique identifier (e.g., "Q1")
        test_id: Test identifier (e.g., "prueba-invierno-2025")
        qti_xml: The raw QTI 3.0 XML content
        metadata: The metadata_tags.json content including atoms and difficulty
        question_text: Extracted text from QTI for prompt context
        choices: List of choice texts
        correct_answer: The correct answer text
        image_urls: List of image URLs in the question
    """

    question_id: str
    test_id: str
    qti_xml: str
    metadata: dict[str, Any]
    question_text: str = ""
    choices: list[str] = field(default_factory=list)
    correct_answer: str = ""
    image_urls: list[str] = field(default_factory=list)

    @property
    def atoms(self) -> list[dict[str, Any]]:
        """Get the selected atoms from metadata."""
        return self.metadata.get("selected_atoms", [])

    @property
    def primary_atoms(self) -> list[dict[str, Any]]:
        """Get only primary atoms."""
        return [a for a in self.atoms if a.get("relevance") == "primary"]

    @property
    def difficulty(self) -> dict[str, Any]:
        """Get difficulty info from metadata."""
        return self.metadata.get("difficulty", {})


@dataclass
class VariantQuestion:
    """A generated variant question.

    Attributes:
        variant_id: Unique identifier (e.g., "Q1_v1")
        source_question_id: Original question ID
        source_test_id: Original test ID
        qti_xml: Generated QTI 3.0 XML
        metadata: Generated metadata for the variant
        validation_result: Result of validation phase
    """

    variant_id: str
    source_question_id: str
    source_test_id: str
    qti_xml: str
    metadata: dict[str, Any] = field(default_factory=dict)
    validation_result: ValidationResult | None = None


@dataclass
class VariantBlueprint:
    """A planning blueprint for a single hard variant.

    Attributes:
        variant_id: Stable planned id (e.g., "Q1_v1")
        scenario_description: New scenario/context description
        non_mechanizable_axes: Structural changes that prevent rote solving
        required_reasoning: Why understanding is required (not recipe)
        difficulty_target: Relative target ("equal_or_harder", etc.)
        requires_image: Whether this variant needs an image to be solvable
        image_description: Detailed image specification when required
        selected_shape_id: The specific Family-Constrained shape assigned.
    """

    variant_id: str
    scenario_description: str
    non_mechanizable_axes: list[str] = field(default_factory=list)
    required_reasoning: str = ""
    difficulty_target: str = "equal_or_harder"
    requires_image: bool = False
    image_description: str = ""
    selected_shape_id: str = "standard_variant"


@dataclass
class ValidationResult:
    """Result of variant validation.

    Attributes:
        verdict: APROBADA or RECHAZADA
        concept_aligned: Does it test the same concept?
        difficulty_equal: Compatibility field; in the hard-variants pipeline this
            means the difficulty is acceptable relative to the target contract
            (same or slightly harder when the blueprint allows it).
        answer_correct: Is the marked answer mathematically correct?
        calculation_steps: Step-by-step calculation for verification
        distractors_plausible: Are distractors reasonable errors?
        rejection_reason: If rejected, why?
    """

    verdict: ValidationVerdict
    concept_aligned: bool
    difficulty_equal: bool
    answer_correct: bool
    calculation_steps: str = ""
    distractors_plausible: bool = True
    non_mechanizable: bool = True
    rejection_reason: str = ""

    @property
    def difficulty_acceptable(self) -> bool:
        """Preferred alias for the hard-variants difficulty gate semantics."""
        return self.difficulty_equal

    @property
    def is_approved(self) -> bool:
        return self.verdict == ValidationVerdict.APPROVED


@dataclass
class PipelineConfig:
    """Configuration for the variant generation pipeline.

    Attributes:
        variants_per_question: Number of variants to generate per source question.
        temperature: LLM temperature for generation.
        llm_request_timeout_seconds: Per-call timeout for sync LLM stages.
        llm_max_attempts: Max retry attempts for sync LLM stages.
        model: OpenAI model used for generation/validation (phases 1-5, 7).
        use_batch_api: When True, uses OpenAI Batch API (50% cost discount).
            When False, runs sync calls (for debugging / pilot).
        batch_poll_interval: Seconds between polls when waiting for a batch.
        job_id: Resume a previous batch run from this job ID.
        validate_variants: Whether to run Phase 4 (3-gate validation).
        save_rejected: Whether to save rejected variants for debugging.
        output_dir: Directory for saving generated variants (by test).
        skip_enrichment: When True, skip phases 5-7 (solvability, enrichment,
            final validation).  Useful for backward-compat or debugging.
        enrichment_model: Model for feedback enrichment & review (Phase 6).
        enrichment_max_workers: Max parallel threads for Phase 6.
        enrichment_max_correction_retries: Correction retries in Phase 6.
        prior_approved: Existing approved variants per question_id, used
            for cross-run deduplication in Phase 4.  Default empty.
        variant_id_offset: Per question_id starting index for new variant
            IDs so they don't collide with existing approved folders on
            disk.  E.g. {\"Q17\": 3} means new IDs start at Q17_v4.
        dedup_threshold: Surface-similarity ceiling for deduplication.
            Variants above this are rejected as too similar.  Default
            0.85; lower (e.g. 0.80) for narrow-construct top-up runs.
        generation_reasoning_effort: Reasoning effort for the generation
            phase (Phase 2).  "medium" (default) or "high" for stubborn
            questions where the LLM struggles with answer correctness.
        lenient: When True, relax validation for stubborn questions:
            Phase 4 approves any variant whose answer is correct
            (ignores concept_aligned / es_diferente gates), and
            phases 5 + 7 are skipped (enrichment still runs).
    """

    variants_per_question: int = 10
    temperature: float = 0.3
    llm_request_timeout_seconds: int = 180
    llm_max_attempts: int = 2
    model: str = "gpt-5.1"
    use_batch_api: bool = True
    batch_poll_interval: int = 30
    job_id: str | None = None
    validate_variants: bool = True
    save_rejected: bool = True
    output_dir: str = "app/data/pruebas/hard_variants"
    skip_enrichment: bool = False
    enrichment_model: str = "gpt-5.4"
    enrichment_max_workers: int = 10
    enrichment_max_correction_retries: int = 2
    prior_approved: dict[str, list[VariantQuestion]] = field(
        default_factory=dict,
    )
    variant_id_offset: dict[str, int] = field(
        default_factory=dict,
    )
    dedup_threshold: float = 0.85
    lenient: bool = False
    generation_reasoning_effort: str = "medium"


@dataclass
class VariantResult:
    """Result of variant generation through the optional feedback pipeline.

    Attributes:
        success: Whether variant passed all pipeline stages.
        variant_id: Unique identifier for the variant.
        qti_xml: Final QTI XML after optional post-processing.
        error: Error message if any stage failed.
        stage_failed: Name of the stage that failed (e.g., "feedback_enhancement").
        validation_details: Full validation details from pipeline.
    """

    success: bool
    variant_id: str
    qti_xml: str | None = None
    error: str | None = None
    stage_failed: str | None = None
    validation_details: dict[str, Any] | None = None


@dataclass
class GenerationReport:
    """Report of a generation run.

    Attributes:
        source_question_id: Original question ID
        source_test_id: Original test ID
        total_generated: Number of variants generated
        total_approved: Number that passed all phases
        total_rejected: Number that failed any phase
        total_solvability_failed: Rejected by Phase 5 (solvability gate)
        total_enrichment_failed: Rejected by Phase 6 (feedback enrichment)
        total_final_validation_failed: Rejected by Phase 7 (final validation)
        variants: List of final approved variant IDs
        errors: Any errors encountered
        stage_failures: Counts of failures by pipeline stage
        rejection_reasons: Semantic rejection reasons collected during the run
    """

    source_question_id: str
    source_test_id: str
    total_generated: int = 0
    total_approved: int = 0
    total_rejected: int = 0
    total_solvability_failed: int = 0
    total_enrichment_failed: int = 0
    total_final_validation_failed: int = 0
    variants: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    stage_failures: dict[str, int] = field(default_factory=dict)
    rejection_reasons: list[str] = field(default_factory=list)
