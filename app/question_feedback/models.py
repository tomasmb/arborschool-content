"""Pydantic models for question feedback pipeline results."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CheckStatus(str, Enum):
    """Status of a validation check."""

    PASS = "pass"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"


class CheckResult(BaseModel):
    """Result of a single validation check."""

    status: CheckStatus
    issues: list[str] = Field(default_factory=list)
    reasoning: str = ""


class CorrectAnswerCheck(BaseModel):
    """Result of correct answer validation."""

    status: CheckStatus
    expected_answer: str
    marked_answer: str
    verification_steps: str
    issues: list[str] = Field(default_factory=list)


class ContentQualityCheck(BaseModel):
    """Result of content quality validation."""

    status: CheckStatus
    typos_found: list[str] = Field(default_factory=list)
    character_issues: list[str] = Field(default_factory=list)
    clarity_issues: list[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    """Complete validation result from FinalValidator."""

    validation_result: str  # "pass" or "fail"
    correct_answer_check: CorrectAnswerCheck
    feedback_check: CheckResult
    content_quality_check: ContentQualityCheck
    image_check: CheckResult
    math_validity_check: CheckResult
    overall_reasoning: str


class EnhancementResult(BaseModel):
    """Result from FeedbackEnhancer."""

    success: bool
    qti_xml: str | None = None
    error: str | None = None
    xsd_errors: str | None = None
    attempts: int = 1


class FeedbackReviewResult(BaseModel):
    """Result from feedback-only review (used during enrichment).

    This is a lightweight validation that checks only the generated feedback,
    not the original question content. Used as a gate after feedback generation.
    """

    review_result: str  # "pass" or "fail"
    feedback_accuracy: CheckResult
    feedback_clarity: CheckResult
    overall_reasoning: str


class PipelineResult(BaseModel):
    """Complete pipeline result."""

    question_id: str
    success: bool
    stage_failed: str | None = None
    error: str | None = None
    xsd_errors: str | None = None
    qti_xml_final: str | None = None
    feedback_review_details: dict[str, Any] | None = None
    can_sync: bool = False
