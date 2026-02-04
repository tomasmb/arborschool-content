"""Question feedback pipeline module.

This module handles the generation and validation of feedback for PAES questions.
Feedback is embedded directly in QTI XML following the QTI 3.0 standard.

Main components:
- FeedbackEnhancer: Generates complete QTI XML with feedback embedded
- FinalValidator: Validates content quality with LLM
- QuestionPipeline: Orchestrates the full processing pipeline
"""

from __future__ import annotations

from app.question_feedback.models import (
    CheckResult,
    CheckStatus,
    CorrectAnswerCheck,
    EnhancementResult,
    PipelineResult,
    ValidationResult,
)
from app.question_feedback.enhancer import FeedbackEnhancer
from app.question_feedback.validator import FinalValidator
from app.question_feedback.pipeline import QuestionPipeline

__all__ = [
    # Models
    "CheckStatus",
    "CheckResult",
    "CorrectAnswerCheck",
    "ValidationResult",
    "EnhancementResult",
    "PipelineResult",
    # Classes
    "FeedbackEnhancer",
    "FinalValidator",
    "QuestionPipeline",
]
