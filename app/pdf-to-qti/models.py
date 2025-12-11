"""Pydantic models for PDF to QTI pipeline.

Contains all data models for:
- Parsed PDF input (from Extend.ai)
- Segmentation results
- QTI generation output
"""

from typing import Optional, List, Dict, Any, Literal
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
    
    type: Optional[str] = None
    imageUrl: Optional[str] = None
    figureType: Optional[str] = None
    rowCount: Optional[int] = None
    columnCount: Optional[int] = None
    
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
    
    page: Optional[Dict[str, Any]] = None


class Block(BaseModel):
    """Represents a single block within a chunk."""
    
    object: Optional[str] = "block"
    id: Optional[str] = None
    type: str
    content: str
    details: Optional[BlockDetails] = None
    metadata: Optional[BlockMetadata] = None
    boundingBox: Optional[BlockBoundingBox] = None
    
    class Config:
        extra = "allow"


class ChunkMetadata(BaseModel):
    """Metadata for a chunk."""
    
    pageRange: Optional[Dict[str, int]] = None
    
    class Config:
        extra = "allow"


class Chunk(BaseModel):
    """Represents a chunk (page) from parsedPdf."""

    id: str
    object: str = "chunk"
    type: str = "page"
    content: str
    metadata: Optional[ChunkMetadata] = None
    blocks: Optional[List[Block]] = None
    
    class Config:
        extra = "allow"


class ParsedPdf(BaseModel):
    """Represents the parsedPdf structure from extend.ai."""

    id: str
    object: str = "parser_run"
    chunks: List[Chunk]
    fileId: Optional[str] = None
    status: Optional[str] = None
    
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
    chunk_id: Optional[str] = None
    start_marker: Optional[str] = None
    end_marker: Optional[str] = None


class QuestionChunk(BaseModel):
    """A segmented question with optional shared context reference."""

    id: str
    content: str
    shared_context_id: Optional[str] = None
    boundary: Optional[QuestionBoundary] = None
    question_type: Optional[str] = None
    images: List[str] = Field(default_factory=list)


class SegmentationResult(BaseModel):
    """Result from segmentation step."""

    shared_contexts: List[SharedContext] = Field(default_factory=list)
    questions: List[QuestionChunk]


class SplitValidationError(BaseModel):
    """Validation error for a specific question."""

    question_id: str
    is_self_contained: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class SplitValidationResult(BaseModel):
    """Result from split validation step."""

    is_valid: bool
    validation_results: List[SplitValidationError]


class SegmenterOutput(BaseModel):
    """Final output from segmentation."""

    success: bool
    shared_contexts: List[SharedContext] = Field(default_factory=list)
    validated_questions: List[QuestionChunk] = Field(default_factory=list)
    unvalidated_questions: List[QuestionChunk] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


# =============================================================================
# QTI Generation Models
# =============================================================================

class QTIItem(BaseModel):
    """Generated QTI item."""

    question_id: str
    qti_xml: str
    question_type: Optional[str] = None


class SemanticValidationResult(BaseModel):
    """Result from semantic validation."""

    is_valid: bool
    fidelity_score: int
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class GeneratorOutput(BaseModel):
    """Final output from QTI generation."""

    success: bool
    qti_items: List[QTIItem] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


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
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# =============================================================================
# QTI Validation Models (for extraction quality validation)
# =============================================================================

class ImageInput(BaseModel):
    """Image reference for validation."""
    url: str = Field(..., description="URL of the image to validate")
    alt_text: Optional[str] = Field(None, description="Alt text or description")


class ValidationResult(BaseModel):
    """Result of a single validation check."""
    passed: bool = Field(..., description="Whether this validation check passed")
    score: int = Field(..., ge=0, le=100, description="Score from 0-100")
    issues: List[str] = Field(default_factory=list, description="Issues found")
    details: Optional[str] = Field(None, description="Additional details")


class MediaValidationDetail(BaseModel):
    """Detailed validation result for a single media item."""
    url: str = Field(..., description="URL of the media item")
    exists: bool = Field(..., description="Whether the media resource is accessible")
    contextually_correct: Optional[bool] = Field(
        None, description="Whether the image matches the question context"
    )
    issues: List[str] = Field(default_factory=list, description="Issues with this media")
    ai_analysis: Optional[str] = Field(None, description="AI analysis of the image")


class QTIValidationOutput(BaseModel):
    """
    Output schema for QTI extraction validation.
    
    Validates extraction quality:
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
    
    # Optional detailed results
    media_details: List[MediaValidationDetail] = Field(
        default_factory=list, description="Detailed validation for each media item"
    )
    
    detected_question_type: Optional[str] = Field(
        None, description="Detected QTI interaction type"
    )
    
    errors: List[str] = Field(default_factory=list, description="Errors during validation")
    ai_reasoning: Optional[str] = Field(None, description="AI explanation of the result")
    ai_validation_failed: bool = Field(
        default=False, description="True if AI validation failed - results incomplete"
    )


class AIValidationResponse(BaseModel):
    """Schema for AI validation response (internal use)."""
    is_complete: bool = Field(..., description="Whether all content was extracted")
    content_score: int = Field(..., ge=0, le=100)
    content_issues: List[str] = Field(default_factory=list)
    
    structure_valid: bool = Field(..., description="Whether structure is valid")
    structure_score: int = Field(..., ge=0, le=100)
    structure_issues: List[str] = Field(default_factory=list)
    
    parse_clean: bool = Field(..., description="Whether parsing is clean")
    parse_score: int = Field(..., ge=0, le=100)
    parse_issues: List[str] = Field(default_factory=list)
    
    images_contextual: Optional[bool] = Field(None)
    images_score: int = Field(default=100)
    images_issues: List[str] = Field(default_factory=list)
    
    detected_type: str = Field(..., description="Detected question/interaction type")
    reasoning: str = Field(..., description="AI reasoning for the validation")


class ValidatorOutput(BaseModel):
    """Output from validation step."""
    success: bool
    validation_results: List[QTIValidationOutput] = Field(default_factory=list)
    valid_count: int = 0
    invalid_count: int = 0
    errors: List[str] = Field(default_factory=list)


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
        errors=[error_message],
    )

