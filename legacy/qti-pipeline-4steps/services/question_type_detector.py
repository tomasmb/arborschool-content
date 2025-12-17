"""Question Type Detector Service.

Detects the QTI 3.0 question type from question content using AI.
"""

from __future__ import annotations

from typing import Any

# Import from parent package
try:
    from models import QuestionChunk, SourceFormat
    from prompts.question_type_detection import create_detection_prompt
except ImportError:
    from ..models import QuestionChunk, SourceFormat
    from ..prompts.question_type_detection import create_detection_prompt

from .ai_client_factory import AIClient


# Supported QTI 3.0 question types
SUPPORTED_QTI_TYPES = [
    "choice",
    "match",
    "text-entry",
    "extended-text",
    "composite",
    "hotspot",
    "gap-match",
    "order",
    "inline-choice",
    "select-point",
    "hot-text",
    "graphic-gap-match",
    "media-interaction",
]


class QuestionTypeDetector:
    """Detects QTI 3.0 question type from question content."""

    def __init__(self, ai_client: AIClient):
        """Initialize with AI client."""
        self.client = ai_client

    def detect(
        self, question: QuestionChunk, source_format: SourceFormat = "markdown"
    ) -> dict[str, Any]:
        """
        Detect question type from question content.

        Returns:
            Dictionary with detection results:
            {
                "success": bool,
                "question_type": str,
                "can_represent": bool,
                "confidence": float,
                "reason": str
            }
        """
        prompt = create_detection_prompt(question.content, source_format)

        try:
            response_data = self.client.generate_json(prompt, thinking_level="high")
            return self._parse_response(response_data)
        except ValueError as e:
            raise ValueError(f"Question type detection failed - invalid response format: {e}")
        except Exception as e:
            raise Exception(f"Question type detection failed - API error: {e}")

    def _parse_response(self, data: dict[str, Any]) -> dict[str, Any]:
        """Parse and validate response."""
        can_represent = data.get("can_represent", False)
        question_type = data.get("question_type")

        if can_represent and question_type not in SUPPORTED_QTI_TYPES:
            return {
                "success": False,
                "error": (
                    f"Invalid question type: {question_type}. "
                    f"Must be one of: {SUPPORTED_QTI_TYPES}"
                ),
            }

        return {
            "success": True,
            "question_type": question_type or "choice",
            "can_represent": can_represent,
            "confidence": data.get("confidence", 0.0),
            "reason": data.get("reason", ""),
            "key_elements": data.get("key_elements", []),
            "potential_issues": data.get("potential_issues", []),
        }

