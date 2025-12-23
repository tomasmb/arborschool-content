"""Pydantic models for PDF to QTI pipeline.

Contains all data models for:
- Parsed PDF input (from Extend.ai)
- Segmentation results
- QTI generation output
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# =============================================================================
# Type Aliases
# =============================================================================

SourceFormat = Literal["markdown", "html"]
ModelProvider = Literal["gemini", "gpt", "opus"]


# =============================================================================
# Parsed PDF Models (from Extend.ai)
# =============================================================================

class BlockDetails(BaseModel):
    """Details for a block (varies by block type)."""
    
    type: str | None = None
    imageUrl: str | None = None
    figureType: str | None = None
    rowCount: int | None = None
    columnCount: int | None = None
    
    class Config:
        extra = "allow"


class BlockBoundingBox(BaseModel):
    """Bounding box coordinates for a block."""
    
    left: float
    top: float
    right: float
    bottom: float


class BlockMetadata(BaseModel):
    """Metadata for a block."""
    
    page: dict[str, object] | None = None


class Block(BaseModel):
    """Represents a single block within a chunk."""
    
    object: str | None = "block"
    id: str | None = None
    type: str
    content: str
    details: BlockDetails | None = None
    metadata: BlockMetadata | None = None
    boundingBox: BlockBoundingBox | None = None
    
    class Config:
        extra = "allow"


class ChunkMetadata(BaseModel):
    """Metadata for a chunk."""
    
    pageRange: dict[str, int] | None = None
    
    class Config:
        extra = "allow"


class Chunk(BaseModel):
    """Represents a chunk (page) from parsedPdf."""

    id: str
    object: str = "chunk"
    type: str = "page"
    content: str
    metadata: ChunkMetadata | None = None
    blocks: list[Block] | None = None
    
    class Config:
        extra = "allow"


class ParsedPdf(BaseModel):
    """Represents the parsedPdf structure from extend.ai."""

    id: str
    object: str = "parser_run"
    chunks: list[Chunk]
    fileId: str | None = None
    status: str | None = None
    
    class Config:
        extra = "allow"


# =============================================================================
# Segmentation Models
# =============================================================================

class SharedContext(BaseModel):
    """Shared context that applies to multiple questions."""

    id: str
    content: str


class QuestionBoundary(BaseModel):
    """Boundary information for extracting a question from blocks."""

    start_block_id: str
    end_block_id: str
    chunk_id: str | None = None
    start_marker: str | None = None
    end_marker: str | None = None


class QuestionChunk(BaseModel):
    """A segmented question with optional shared context reference."""

    id: str
    content: str
    shared_context_id: str | None = None
    boundary: QuestionBoundary | None = None
    question_type: str | None = None
    images: list[str] = Field(default_factory=list)


class SegmentationResult(BaseModel):
    """Result from segmentation step."""

    shared_contexts: list[SharedContext] = Field(default_factory=list)
    questions: list[QuestionChunk]


class SplitValidationError(BaseModel):
    """Validation error for a specific question."""

    question_id: str
    is_self_contained: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SplitValidationResult(BaseModel):
    """Result from split validation step."""

    is_valid: bool
    validation_results: list[SplitValidationError]


class SegmenterOutput(BaseModel):
    """Final output from segmentation."""

    success: bool
    shared_contexts: list[SharedContext] = Field(default_factory=list)
    validated_questions: list[QuestionChunk] = Field(default_factory=list)
    unvalidated_questions: list[QuestionChunk] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


# =============================================================================
# QTI Generation Models
# =============================================================================

class QTIItem(BaseModel):
    """Generated QTI item."""

    question_id: str
    qti_xml: str
    question_type: str | None = None


class SemanticValidationResult(BaseModel):
    """Result from semantic validation."""

    is_valid: bool
    fidelity_score: int
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class GeneratorOutput(BaseModel):
    """Final output from QTI generation."""

    success: bool
    qti_items: list[QTIItem] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


# =============================================================================
# Pipeline Report Model
# =============================================================================

class PipelineReport(BaseModel):
    """Report from full pipeline execution."""
    
    input_file: str
    total_questions: int
    successful_questions: int
    failed_questions: int
    parse_status: str = "pending"
    segment_status: str = "pending"
    generate_status: str = "pending"
    validate_status: str = "pending"
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# =============================================================================
# QTI Validation Models (for extraction quality validation)
# =============================================================================

class ImageInput(BaseModel):
    """Image reference for validation."""
    url: str = Field(..., description="URL of the image to validate")
    alt_text: str | None = Field(None, description="Alt text or description")


class ValidationResult(BaseModel):
    """Result of a single validation check."""
    passed: bool = Field(..., description="Whether this validation check passed")
    score: int = Field(..., ge=0, le=100, description="Score from 0-100")
    issues: list[str] = Field(default_factory=list, description="Issues found")
    details: str | None = Field(None, description="Additional details")


class MediaValidationDetail(BaseModel):
    """Detailed validation result for a single media item."""
    url: str = Field(..., description="URL of the media item")
    exists: bool = Field(..., description="Whether the media resource is accessible")
    contextually_correct: bool | None = Field(
        None, description="Whether the image matches the question context"
    )
    issues: list[str] = Field(default_factory=list, description="Issues with this media")
    ai_analysis: str | None = Field(None, description="AI analysis of the image")


class QTIValidationOutput(BaseModel):
    """
    Output schema for QTI extraction validation.
    
    Validates extraction quality:
    - xsd_validity: Does XML conform to QTI 3.0 XSD schema? (mandatory)
    - content_completeness: Was all content extracted? (stem, choices, etc.)
    - structure_validity: Is structure correct for question type?
    - parse_quality: Is content clean? (no artifacts, no contamination)
    - media_integrity: Are images correct for this question?
    
    Does NOT validate:
    - responseDeclaration / correctResponse (answer keys)
    - Feedback elements
    - Distractor quality
    - Pedagogical completeness
    """
    question_id: str = Field(..., description="Question identifier")
    is_valid: bool = Field(..., description="Overall extraction validation result")
    overall_score: int = Field(..., ge=0, le=100, description="Overall quality score 0-100")
    
    # Individual validation results
    content_completeness: ValidationResult = Field(
        ..., description="Was all content extracted?"
    )
    media_integrity: ValidationResult = Field(
        ..., description="Are referenced images correct for this question?"
    )
    structure_validity: ValidationResult = Field(
        ..., description="Is structure correct for the question type?"
    )
    parse_quality: ValidationResult = Field(
        ..., description="Is content clean? (no artifacts, encoding issues)"
    )
    xsd_validity: ValidationResult = Field(
        ..., description="Does XML conform to QTI 3.0 XSD schema?"
    )
    
    # Optional detailed results
    media_details: list[MediaValidationDetail] = Field(
        default_factory=list, description="Detailed validation for each media item"
    )
    
    detected_question_type: str | None = Field(
        None, description="Detected QTI interaction type"
    )
    
    errors: list[str] = Field(default_factory=list, description="Errors during validation")
    ai_reasoning: str | None = Field(None, description="AI explanation of the result")
    ai_validation_failed: bool = Field(
        default=False, description="True if AI validation failed - results incomplete"
    )


class AIValidationResponse(BaseModel):
    """Schema for AI validation response (internal use)."""
    is_complete: bool = Field(..., description="Whether all content was extracted")
    content_score: int = Field(..., ge=0, le=100)
    content_issues: list[str] = Field(default_factory=list)
    
    structure_valid: bool = Field(..., description="Whether structure is valid")
    structure_score: int = Field(..., ge=0, le=100)
    structure_issues: list[str] = Field(default_factory=list)
    
    parse_clean: bool = Field(..., description="Whether parsing is clean")
    parse_score: int = Field(..., ge=0, le=100)
    parse_issues: list[str] = Field(default_factory=list)
    
    images_contextual: bool | None = Field(None)
    images_score: int = Field(default=100)
    images_issues: list[str] = Field(default_factory=list)
    
    detected_type: str = Field(..., description="Detected question/interaction type")
    reasoning: str = Field(..., description="AI reasoning for the validation")


class ValidatorOutput(BaseModel):
    """Output from validation step."""
    success: bool
    validation_results: list[QTIValidationOutput] = Field(default_factory=list)
    valid_count: int = 0
    invalid_count: int = 0
    errors: list[str] = Field(default_factory=list)


# =============================================================================
# Factory Functions for Validation (DRY principle)
# =============================================================================

def create_error_validation_result(error_message: str) -> ValidationResult:
    """Create a ValidationResult for error cases."""
    return ValidationResult(passed=False, score=0, issues=[error_message])


def create_empty_validation_result() -> ValidationResult:
    """Create an empty (failed) ValidationResult."""
    return ValidationResult(passed=False, score=0, issues=[])


def create_error_validation_output(
    question_id: str, error_message: str
) -> QTIValidationOutput:
    """Create a QTIValidationOutput for error cases."""
    return QTIValidationOutput(
        question_id=question_id,
        is_valid=False,
        overall_score=0,
        content_completeness=create_error_validation_result(error_message),
        media_integrity=create_empty_validation_result(),
        structure_validity=create_empty_validation_result(),
        parse_quality=create_empty_validation_result(),
        xsd_validity=create_empty_validation_result(),
        errors=[error_message],
    )

