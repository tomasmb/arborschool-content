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
from app.question_feedback.utils.image_utils import load_images_from_urls

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
        # Load images if provided
        images: list[Any] = []
        if image_urls:
            images = load_images_from_urls(image_urls)

        # Build images section text (for context in prompt)
        images_section = ""
        if images:
            images_section = (
                f"IMÁGENES: {len(images)} imagen(es) adjuntas para validación visual. "
                "Examina las imágenes cuidadosamente para verificar que son correctas, "
                "legibles y relevantes para la pregunta."
            )
        elif image_urls:
            # Had URLs but failed to load
            images_section = (
                f"IMÁGENES: Se detectaron {len(image_urls)} imagen(es) en el XML pero "
                "no se pudieron cargar. Valida basándote solo en el texto."
            )

        prompt = FINAL_VALIDATION_PROMPT.format(
            qti_xml_with_feedback=qti_xml_with_feedback,
            images_section=images_section,
        )

        # Add JSON schema instruction
        prompt += "\n\nRespuesta en formato JSON siguiendo este schema:\n"
        prompt += json.dumps(FINAL_VALIDATION_SCHEMA, indent=2, ensure_ascii=False)

        logger.info(
            f"Running final validation with {self.model} "
            f"({len(images)} images attached)"
        )

        try:
            # Build multimodal prompt if we have images
            if images:
                # OpenAIClient expects list with text first, then PIL images
                multimodal_prompt: list[Any] = [prompt]
                multimodal_prompt.extend(images)
                response_text = self._client.generate_text(
                    multimodal_prompt,
                    response_mime_type="application/json",
                    temperature=0.0,
                    max_tokens=4000,
                )
            else:
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

        # Enforce reasoning-verdict consistency
        all_checks = [
            correct_answer_check,
            feedback_check,
            content_quality_check,
            image_check,
            math_validity_check,
        ]
        raw_verdict = result.get("validation_result", "fail")
        computed_verdict = self._compute_consistent_verdict(
            all_checks, raw_verdict
        )

        return ValidationResult(
            validation_result=computed_verdict,
            correct_answer_check=correct_answer_check,
            feedback_check=feedback_check,
            content_quality_check=content_quality_check,
            image_check=image_check,
            math_validity_check=math_validity_check,
            overall_reasoning=result.get("overall_reasoning", ""),
        )

    def _compute_consistent_verdict(
        self,
        checks: list[CorrectAnswerCheck | CheckResult | ContentQualityCheck],
        raw_verdict: str,
    ) -> str:
        """Enforce consistency between individual checks and overall verdict.

        Rules:
        - If ALL checks pass/not_applicable → verdict must be "pass"
        - If ANY check has "fail" with non-empty issues → verdict must be "fail"
        - If a check says "fail" but has NO issues → auto-correct to "pass"

        Args:
            checks: List of parsed check results.
            raw_verdict: The LLM's raw validation_result.

        Returns:
            Consistent verdict string ("pass" or "fail").
        """
        any_real_failure = False

        for check in checks:
            if check.status == CheckStatus.FAIL:
                has_issues = self._check_has_issues(check)
                if has_issues:
                    any_real_failure = True
                else:
                    # Fail with no issues = contradiction → auto-correct
                    check.status = CheckStatus.PASS
                    logger.warning(
                        "Auto-corrected check with fail status but "
                        "no issues to pass"
                    )

        computed = "fail" if any_real_failure else "pass"

        if computed != raw_verdict:
            logger.warning(
                f"Verdict inconsistency: LLM said '{raw_verdict}' "
                f"but checks compute to '{computed}'. "
                f"Using computed verdict."
            )

        return computed

    def _check_has_issues(
        self,
        check: CorrectAnswerCheck | CheckResult | ContentQualityCheck,
    ) -> bool:
        """Return True if a check has any concrete issues reported.

        Args:
            check: A parsed check result of any type.

        Returns:
            True if the check has at least one non-empty issue.
        """
        if isinstance(check, ContentQualityCheck):
            return bool(
                check.typos_found
                or check.character_issues
                or check.clarity_issues
            )
        # CorrectAnswerCheck and CheckResult both have .issues
        return bool(check.issues)

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
