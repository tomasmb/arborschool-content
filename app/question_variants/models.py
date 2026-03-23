"""Data models for the assessment variant generation pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


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
    metadata: Dict[str, Any]
    question_text: str = ""
    choices: List[str] = field(default_factory=list)
    correct_answer: str = ""
    image_urls: List[str] = field(default_factory=list)

    @property
    def atoms(self) -> List[Dict[str, Any]]:
        """Get the selected atoms from metadata."""
        return self.metadata.get("selected_atoms", [])

    @property
    def primary_atoms(self) -> List[Dict[str, Any]]:
        """Get only primary atoms."""
        return [a for a in self.atoms if a.get("relevance") == "primary"]

    @property
    def difficulty(self) -> Dict[str, Any]:
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
    metadata: Dict[str, Any] = field(default_factory=dict)
    validation_result: Optional["ValidationResult"] = None


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
    """

    variant_id: str
    scenario_description: str
    non_mechanizable_axes: List[str] = field(default_factory=list)
    required_reasoning: str = ""
    difficulty_target: str = "equal_or_harder"
    requires_image: bool = False
    image_description: str = ""


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
        variants_per_question: Number of variants to generate per source question
            (initial default is 10, but fully configurable)
        temperature: LLM temperature for generation (0.0 = deterministic)
        llm_request_timeout_seconds: Per-call timeout for variant LLM stages
        llm_max_attempts: Max retry attempts for variant LLM stages
        planner_provider: Provider used for blueprint planning
        planner_model: Optional explicit model for blueprint planning
        planner_reasoning_level: Reasoning intensity for blueprint planning
        generator_provider: Provider used for QTI variant generation
        generator_model: Optional explicit model for QTI variant generation
        generator_reasoning_level: Reasoning intensity for QTI generation
        validator_provider: Provider used for semantic gate validation
        validator_model: Optional explicit model for semantic gate validation
        validator_reasoning_level: Reasoning intensity for semantic validation
        validate_variants: Whether to run validation phase
        enable_feedback_pipeline: Whether to enrich variants with feedback before
            semantic validation. Disabled by default for the hard-variants pipeline;
            feedback is planned as a later independent process.
        save_rejected: Whether to save rejected variants for debugging
        output_dir: Directory for saving generated variants (by test)
    """

    variants_per_question: int = 10
    temperature: float = 0.3  # Slight variation for diversity
    llm_request_timeout_seconds: int = 180
    llm_max_attempts: int = 2
    planner_provider: str = "gemini"
    planner_model: Optional[str] = None
    planner_reasoning_level: str = "high"
    generator_provider: str = "gemini"
    generator_model: Optional[str] = None
    generator_reasoning_level: str = "medium"
    validator_provider: str = "openai"
    validator_model: Optional[str] = None
    validator_reasoning_level: str = "medium"
    validate_variants: bool = True
    enable_feedback_pipeline: bool = False
    save_rejected: bool = True
    max_retries_per_variant: int = 1  # Re-generate rejected variants with feedback
    output_dir: str = "app/data/pruebas/hard_variants"


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
    validation_details: Dict[str, Any] | None = None


@dataclass
class GenerationReport:
    """Report of a generation run.

    Attributes:
        source_question_id: Original question ID
        source_test_id: Original test ID
        total_generated: Number of variants generated
        total_approved: Number that passed validation
        total_rejected: Number that failed validation
        variants: List of approved variant IDs
        errors: Any errors encountered
        stage_failures: Counts of failures by pipeline stage
        rejection_reasons: Semantic rejection reasons collected during the run
    """

    source_question_id: str
    source_test_id: str
    total_generated: int = 0
    total_approved: int = 0
    total_rejected: int = 0
    total_retried: int = 0
    total_approved_on_retry: int = 0
    variants: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    stage_failures: Dict[str, int] = field(default_factory=dict)
    rejection_reasons: List[str] = field(default_factory=list)
