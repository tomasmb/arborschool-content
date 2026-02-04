"""Question feedback pipeline module.

This module handles the generation and validation of feedback for PAES questions.
Feedback is embedded directly in QTI XML following the QTI 3.0 standard.

Main components:
- FeedbackEnhancer: Generates complete QTI XML with feedback embedded
- FeedbackReviewer: Lightweight review of generated feedback (used during enrichment)
- FinalValidator: Comprehensive validation of complete QTI (separate validation step)
- QuestionPipeline: Orchestrates the enrichment pipeline
"""

from __future__ import annotations

from app.question_feedback.enhancer import FeedbackEnhancer
from app.question_feedback.models import (
    CheckResult,
    CheckStatus,
    CorrectAnswerCheck,
    EnhancementResult,
    FeedbackReviewResult,
    PipelineResult,
    ValidationResult,
)
from app.question_feedback.pipeline import QuestionPipeline
from app.question_feedback.reviewer import FeedbackReviewer
from app.question_feedback.validator import FinalValidator

__all__ = [
    # Models
    "CheckStatus",
    "CheckResult",
    "CorrectAnswerCheck",
    "ValidationResult",
    "FeedbackReviewResult",
    "EnhancementResult",
    "PipelineResult",
    # Classes
    "FeedbackEnhancer",
    "FeedbackReviewer",
    "FinalValidator",
    "QuestionPipeline",
]
