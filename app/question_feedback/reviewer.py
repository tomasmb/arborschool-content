"""Feedback reviewer for enrichment pipeline.

This module validates generated feedback by solving the problem and
verifying mathematical accuracy. Used as a gate after feedback generation
to catch factual errors and incomplete explanations before final validation.
"""

from __future__ import annotations

import json
import logging
import os

from dotenv import load_dotenv

from app.question_feedback.models import CheckResult, CheckStatus, FeedbackReviewResult
from app.question_feedback.prompts import FEEDBACK_REVIEW_PROMPT
from app.question_feedback.schemas import FEEDBACK_REVIEW_SCHEMA

logger = logging.getLogger(__name__)


class FeedbackReviewer:
    """Reviewer for generated feedback.

    Validates feedback by solving the problem and verifying mathematical accuracy.
    Used during enrichment to catch errors before final validation.
    """

    DEFAULT_MODEL = "gpt-5.1"

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
    ):
        """Initialize the reviewer.

        Args:
            model: OpenAI model to use. Defaults to gpt-5.1.
            api_key: OpenAI API key. Defaults to OPENAI_API_KEY env var.
        """
        load_dotenv()
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self._api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.model = model or self.DEFAULT_MODEL

        from app.llm_clients import OpenAIClient

        self._client = OpenAIClient(api_key=self._api_key, model=self.model)

    def review(self, qti_xml_with_feedback: str) -> FeedbackReviewResult:
        """Review the generated feedback in QTI XML.

        Args:
            qti_xml_with_feedback: QTI XML with embedded feedback to review.

        Returns:
            FeedbackReviewResult with review status and details.
        """
        prompt = FEEDBACK_REVIEW_PROMPT.format(
            qti_xml_with_feedback=qti_xml_with_feedback,
        )

        # Add JSON schema instruction
        prompt += "\n\nResponde en formato JSON siguiendo este schema:\n"
        prompt += json.dumps(FEEDBACK_REVIEW_SCHEMA, indent=2, ensure_ascii=False)

        logger.info(f"Running feedback review with {self.model}")

        try:
            response_text = self._client.generate_text(
                prompt,
                response_mime_type="application/json",
                temperature=0.0,
            )

            result = json.loads(response_text)
            logger.info(f"Feedback review result: {result.get('review_result')}")

            return self._parse_result(result)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse review response as JSON: {e}")
            return self._create_error_result(f"Invalid JSON response: {e}")
        except Exception as e:
            logger.error(f"Feedback review failed: {e}")
            return self._create_error_result(str(e))

    def _parse_result(self, result: dict) -> FeedbackReviewResult:
        """Parse the raw JSON result into a FeedbackReviewResult."""
        accuracy = result.get("feedback_accuracy", {})
        feedback_accuracy = CheckResult(
            status=CheckStatus(accuracy.get("status", "fail")),
            issues=accuracy.get("issues", []),
            reasoning=accuracy.get("reasoning", ""),
        )

        clarity = result.get("feedback_clarity", {})
        feedback_clarity = CheckResult(
            status=CheckStatus(clarity.get("status", "fail")),
            issues=clarity.get("issues", []),
            reasoning=clarity.get("reasoning", ""),
        )

        formatting = result.get("formatting_check", {})
        formatting_check = CheckResult(
            status=CheckStatus(formatting.get("status", "fail")),
            issues=formatting.get("issues", []),
            reasoning=formatting.get("reasoning", ""),
        )

        return FeedbackReviewResult(
            review_result=result.get("review_result", "fail"),
            feedback_accuracy=feedback_accuracy,
            feedback_clarity=feedback_clarity,
            formatting_check=formatting_check,
            overall_reasoning=result.get("overall_reasoning", ""),
        )

    def _create_error_result(self, error_message: str) -> FeedbackReviewResult:
        """Create an error FeedbackReviewResult."""
        error_check = CheckResult(
            status=CheckStatus.FAIL,
            issues=[error_message],
            reasoning="Review failed due to error",
        )
        return FeedbackReviewResult(
            review_result="fail",
            feedback_accuracy=error_check,
            feedback_clarity=error_check,
            formatting_check=error_check,
            overall_reasoning=f"Review failed: {error_message}",
        )
