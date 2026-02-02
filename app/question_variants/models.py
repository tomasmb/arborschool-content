"""Data models for the assessment variant generation pipeline."""

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
        test_id: Test identifier (e.g., "Prueba-invierno-2025")
        qti_xml: The raw QTI 3.0 XML content
        metadata: The metadata_tags.json content including atoms, difficulty, feedback
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
        metadata: Generated metadata (inherits atoms, updated feedback)
        validation_result: Result of validation phase
    """
    variant_id: str
    source_question_id: str
    source_test_id: str
    qti_xml: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    validation_result: Optional["ValidationResult"] = None


@dataclass
class ValidationResult:
    """Result of variant validation.

    Attributes:
        verdict: APROBADA or RECHAZADA
        concept_aligned: Does it test the same concept?
        difficulty_equal: Is difficulty the same?
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
    rejection_reason: str = ""

    @property
    def is_approved(self) -> bool:
        return self.verdict == ValidationVerdict.APPROVED


@dataclass
class PipelineConfig:
    """Configuration for the variant generation pipeline.

    Attributes:
        variants_per_question: Number of variants to generate per source question
        temperature: LLM temperature for generation (0.0 = deterministic)
        validate_variants: Whether to run validation phase
        save_rejected: Whether to save rejected variants for debugging
        output_dir: Directory for saving generated variants (by test)
        diagnostic_output_dir: Optional consolidated directory for diagnostic variants
    """
    variants_per_question: int = 3
    temperature: float = 0.3  # Slight variation for diversity
    validate_variants: bool = True
    save_rejected: bool = True
    output_dir: str = "app/data/pruebas/alternativas"
    diagnostic_output_dir: Optional[str] = None  # e.g., "app/data/diagnostico/variantes"


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
    """
    source_question_id: str
    source_test_id: str
    total_generated: int = 0
    total_approved: int = 0
    total_rejected: int = 0
    variants: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
