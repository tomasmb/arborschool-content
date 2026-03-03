"""Final LLM validation for PAES questions."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.llm_clients import OpenAIClient, load_default_openai_client
from app.question_feedback.final_validation_parser import (
    parse_final_validation_payload,
)
from app.question_feedback.models import (
    CheckResult,
    CheckStatus,
    ContentQualityCheck,
    CorrectAnswerCheck,
    ValidationResult,
)
from app.question_feedback.prompts import FINAL_VALIDATION_PROMPT
from app.question_feedback.schemas import FINAL_VALIDATION_SCHEMA
from app.question_feedback.utils.image_utils import (
    build_images_section,
    load_images_from_urls,
)

logger = logging.getLogger(__name__)

# Reasoning effort for math-correctness / feedback-quality checks.
_VALIDATION_REASONING = "medium"


class FinalValidator:
    """Final LLM validation for PAES questions.

    Performs comprehensive validation of QTI XML with embedded feedback,
    checking mathematical correctness, feedback quality, and content quality.
    """

    DEFAULT_MODEL = "gpt-5.1"

    def __init__(
        self,
        model: str | None = None,
        client: OpenAIClient | None = None,
    ):
        """Initialise the validator.

        Args:
            model: OpenAI model to use. Defaults to gpt-5.1.
            client: Pre-built client (DIP). When ``None`` the factory
                ``load_default_openai_client()`` is used.
        """
        self.model = model or self.DEFAULT_MODEL
        self._client = client or load_default_openai_client(
            model=self.model,
        )

    def validate(
        self,
        qti_xml_with_feedback: str,
        image_urls: list[str] | None = None,
    ) -> ValidationResult:
        """Perform comprehensive validation of QTI XML with feedback.

        Args:
            qti_xml_with_feedback: QTI XML with embedded feedback.
            image_urls: Optional list of image URLs for multimodal validation.

        Returns:
            ValidationResult with detailed check results.
        """
        images: list[Any] = []
        if image_urls:
            images = load_images_from_urls(image_urls)

        images_section = build_images_section(
            images, image_urls, action_verb="validación visual",
        )

        prompt = FINAL_VALIDATION_PROMPT.format(
            qti_xml_with_feedback=qti_xml_with_feedback,
            images_section=images_section,
        )
        prompt += "\n\nRespuesta en formato JSON siguiendo este schema:\n"
        prompt += json.dumps(
            FINAL_VALIDATION_SCHEMA, indent=2, ensure_ascii=False,
        )

        logger.info(
            "Running final validation with %s (%d images attached)",
            self.model, len(images),
        )

        try:
            llm_resp = self._client.call_with_images(
                prompt,
                images,
                reasoning_effort=_VALIDATION_REASONING,
                response_mime_type="application/json",
            )

            result = json.loads(llm_resp.text)
            logger.info("Validation result: %s", result.get("validation_result"))
            return self._parse_result(result)

        except json.JSONDecodeError as e:
            logger.error("Failed to parse validation response as JSON: %s", e)
            return self._create_error_result(f"Invalid JSON response: {e}")
        except Exception as e:
            logger.error("Validation failed: %s", e)
            return self._create_error_result(str(e))

    def _parse_result(self, result: dict[str, Any]) -> ValidationResult:
        """Parse the raw JSON result into a ValidationResult.

        Args:
            result: Raw JSON result from LLM.

        Returns:
            Parsed ValidationResult.
        """
        return parse_final_validation_payload(result)

    def _create_error_result(self, error_message: str) -> ValidationResult:
        """Create an error ValidationResult.

        Args:
            error_message: Error description.

        Returns:
            ValidationResult with fail status and error in reasoning.
        """
        return ValidationResult(
            validation_result="fail",
            correct_answer_check=CorrectAnswerCheck(
                status=CheckStatus.FAIL,
                expected_answer="",
                marked_answer="",
                verification_steps="",
                issues=[error_message],
            ),
            feedback_check=CheckResult(
                status=CheckStatus.FAIL,
                issues=[error_message],
                reasoning="Validation failed due to error",
            ),
            content_quality_check=ContentQualityCheck(
                status=CheckStatus.FAIL,
                typos_found=[],
                character_issues=[],
                clarity_issues=[],
            ),
            image_check=CheckResult(
                status=CheckStatus.NOT_APPLICABLE,
                issues=[],
                reasoning="Validation failed before image check",
            ),
            math_validity_check=CheckResult(
                status=CheckStatus.FAIL,
                issues=[error_message],
                reasoning="Validation failed due to error",
            ),
            overall_reasoning=f"Validation failed: {error_message}",
        )
