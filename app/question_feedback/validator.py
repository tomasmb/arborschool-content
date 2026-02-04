"""Final LLM validation for PAES questions."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from dotenv import load_dotenv

from app.question_feedback.models import (
    CheckResult,
    CheckStatus,
    ContentQualityCheck,
    CorrectAnswerCheck,
    ValidationResult,
)
from app.question_feedback.prompts import FINAL_VALIDATION_PROMPT
from app.question_feedback.schemas import FINAL_VALIDATION_SCHEMA

logger = logging.getLogger(__name__)


class FinalValidator:
    """Final LLM validation for PAES questions.

    This class performs comprehensive validation of QTI XML with embedded feedback,
    checking mathematical correctness, feedback quality, and content quality.
    """

    DEFAULT_MODEL = "gpt-5.1"

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
    ):
        """Initialize the validator.

        Args:
            model: OpenAI model to use. Defaults to gpt-5.1.
            api_key: OpenAI API key. Defaults to OPENAI_API_KEY env var.
        """
        load_dotenv()
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self._api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.model = model or self.DEFAULT_MODEL

        # Import OpenAIClient from llm_clients
        from app.llm_clients import OpenAIClient

        self._client = OpenAIClient(api_key=self._api_key, model=self.model)

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
        images_section = ""
        if image_urls:
            images_section = (
                f"IMÁGENES: {len(image_urls)} imagen(es) adjuntas para validación."
            )

        prompt = FINAL_VALIDATION_PROMPT.format(
            qti_xml_with_feedback=qti_xml_with_feedback,
            images_section=images_section,
        )

        # Add JSON schema instruction
        prompt += "\n\nRespuesta en formato JSON siguiendo este schema:\n"
        prompt += json.dumps(FINAL_VALIDATION_SCHEMA, indent=2, ensure_ascii=False)

        logger.info(f"Running final validation with {self.model}")

        try:
            response_text = self._client.generate_text(
                prompt,
                response_mime_type="application/json",
                temperature=0.0,
                max_tokens=4000,
            )

            result = json.loads(response_text)
            logger.info(f"Validation result: {result.get('validation_result')}")

            return self._parse_result(result)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse validation response as JSON: {e}")
            return self._create_error_result(f"Invalid JSON response: {e}")
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return self._create_error_result(str(e))

    def _parse_result(self, result: dict[str, Any]) -> ValidationResult:
        """Parse the raw JSON result into a ValidationResult.

        Args:
            result: Raw JSON result from LLM.

        Returns:
            Parsed ValidationResult.
        """
        # Parse correct_answer_check
        ca_check = result.get("correct_answer_check", {})
        correct_answer_check = CorrectAnswerCheck(
            status=CheckStatus(ca_check.get("status", "fail")),
            expected_answer=ca_check.get("expected_answer", ""),
            marked_answer=ca_check.get("marked_answer", ""),
            verification_steps=ca_check.get("verification_steps", ""),
            issues=ca_check.get("issues", []),
        )

        # Parse feedback_check
        fb_check = result.get("feedback_check", {})
        feedback_check = CheckResult(
            status=CheckStatus(fb_check.get("status", "fail")),
            issues=fb_check.get("issues", []),
            reasoning=fb_check.get("reasoning", ""),
        )

        # Parse content_quality_check
        cq_check = result.get("content_quality_check", {})
        content_quality_check = ContentQualityCheck(
            status=CheckStatus(cq_check.get("status", "fail")),
            typos_found=cq_check.get("typos_found", []),
            character_issues=cq_check.get("character_issues", []),
            clarity_issues=cq_check.get("clarity_issues", []),
        )

        # Parse image_check
        img_check = result.get("image_check", {})
        image_check = CheckResult(
            status=CheckStatus(img_check.get("status", "not_applicable")),
            issues=img_check.get("issues", []),
            reasoning=img_check.get("reasoning", ""),
        )

        # Parse math_validity_check
        math_check = result.get("math_validity_check", {})
        math_validity_check = CheckResult(
            status=CheckStatus(math_check.get("status", "fail")),
            issues=math_check.get("issues", []),
            reasoning=math_check.get("reasoning", ""),
        )

        return ValidationResult(
            validation_result=result.get("validation_result", "fail"),
            correct_answer_check=correct_answer_check,
            feedback_check=feedback_check,
            content_quality_check=content_quality_check,
            image_check=image_check,
            math_validity_check=math_validity_check,
            overall_reasoning=result.get("overall_reasoning", ""),
        )

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
