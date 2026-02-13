"""Feedback enhancement using OpenAI GPT models."""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from typing import Any

from app.llm_clients import OpenAIClient, load_default_openai_client
from app.question_feedback.models import EnhancementResult
from app.question_feedback.prompts import (
    FEEDBACK_CORRECTION_PROMPT,
    FEEDBACK_ENHANCEMENT_PROMPT,
)
from app.question_feedback.utils.image_utils import (
    build_images_section,
    load_images_from_urls,
)
from app.question_generation.prompts.reference_examples import (
    FEEDBACK_QTI_REFERENCE,
)


def _import_xml_validator() -> Any:
    """Import validate_qti_xml from the hyphenated pdf-to-qti folder.

    Python doesn't allow hyphens in module names, so we use importlib.util
    to load the module directly from its file path.
    """
    module_path = (
        Path(__file__).parent.parent
        / "pruebas"
        / "pdf-to-qti"
        / "modules"
        / "validation"
        / "xml_validator.py"
    )

    if not module_path.exists():
        return None

    spec = importlib.util.spec_from_file_location(
        "xml_validator", module_path,
    )
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Import the XSD validator
_xml_validator_module = _import_xml_validator()
if _xml_validator_module:
    validate_qti_xml = _xml_validator_module.validate_qti_xml
else:
    import logging as _stub_logging
    _stub_logging.getLogger(__name__).warning(
        "XSD validator unavailable (import failed) — "
        "all XSD checks will REJECT items as a safety measure",
    )

    def validate_qti_xml(
        qti_xml: str, validation_endpoint: str | None = None,
    ) -> dict[str, Any]:
        """Fail-safe stub: rejects items when validator is missing."""
        return {
            "valid": False,
            "message": "XSD validator unavailable",
        }

logger = logging.getLogger(__name__)

# Reasoning effort for generation / correction (structured output, not deep
# reasoning) — "low" is sufficient and much cheaper than "high".
_ENHANCE_REASONING = "low"


class FeedbackEnhancer:
    """Enhance QTI XML with feedback using OpenAI GPT models.

    Takes a base QTI XML (without feedback) and generates a complete QTI XML
    with embedded feedback using an LLM.  XSD validation is performed
    immediately after generation with retry logic.
    """

    DEFAULT_MODEL = "gpt-5.1"

    def __init__(
        self,
        model: str | None = None,
        max_retries: int = 2,
        client: OpenAIClient | None = None,
    ):
        """Initialise the enhancer.

        Args:
            model: OpenAI model to use.  Defaults to gpt-5.1.
            max_retries: Maximum XSD validation retries.
            client: Pre-built client (DIP).  When ``None`` the factory
                ``load_default_openai_client()`` is used.
        """
        self.model = model or self.DEFAULT_MODEL
        self.max_retries = max_retries
        self._last_xsd_errors: str | None = None
        self._client = client or load_default_openai_client(
            model=self.model,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enhance(
        self,
        qti_xml: str,
        image_urls: list[str] | None = None,
    ) -> EnhancementResult:
        """Generate complete QTI XML with feedback embedded.

        Args:
            qti_xml: Original QTI XML without feedback.
            image_urls: Optional image URLs for multimodal input.

        Returns:
            EnhancementResult with success status and enhanced XML or errors.
        """
        images: list[Any] = []
        if image_urls:
            images = load_images_from_urls(image_urls)

        for attempt in range(self.max_retries + 1):
            logger.info(
                "Enhancement attempt %d/%d (%d images)",
                attempt + 1, self.max_retries + 1, len(images),
            )

            images_section = build_images_section(
                images, image_urls,
                action_verb="generar el feedback educativo",
            )

            prompt = FEEDBACK_ENHANCEMENT_PROMPT.format(
                original_qti_xml=qti_xml,
                images_section=images_section,
                feedback_reference_example=FEEDBACK_QTI_REFERENCE,
            )

            if attempt > 0 and self._last_xsd_errors:
                prompt += (
                    f"\n\nERRORES XSD DEL INTENTO ANTERIOR:\n"
                    f"{self._last_xsd_errors}\n"
                    "Por favor corrige estos errores en tu respuesta."
                )

            try:
                response_text = self._client.call_with_images(
                    prompt,
                    images,
                    reasoning_effort=_ENHANCE_REASONING,
                )
                enhanced_xml = self._extract_xml(response_text)

                xsd_result = validate_qti_xml(enhanced_xml)
                if xsd_result.get("valid"):
                    logger.info("XSD validation passed")
                    return EnhancementResult(
                        success=True,
                        qti_xml=enhanced_xml,
                        attempts=attempt + 1,
                    )

                self._last_xsd_errors = str(
                    xsd_result.get("validation_errors", "Unknown error"),
                )
                logger.warning(
                    "XSD validation failed: %s", self._last_xsd_errors,
                )

            except Exception as e:
                logger.error("Enhancement attempt %d failed: %s", attempt + 1, e)
                if attempt == self.max_retries:
                    return EnhancementResult(
                        success=False,
                        error=f"Enhancement failed: {e}",
                        attempts=attempt + 1,
                    )
                continue

            if attempt == self.max_retries:
                return EnhancementResult(
                    success=False,
                    error=f"XSD validation failed after {attempt + 1} attempts",
                    xsd_errors=self._last_xsd_errors,
                    attempts=attempt + 1,
                )

        return EnhancementResult(success=False, error="Max retries exceeded")

    def correct(
        self,
        qti_xml_with_errors: str,
        review_issues: str,
        image_urls: list[str] | None = None,
    ) -> EnhancementResult:
        """Correct feedback errors identified by the reviewer.

        Args:
            qti_xml_with_errors: QTI XML with feedback that has errors.
            review_issues: Issues found by the reviewer.
            image_urls: Optional image URLs for multimodal input.

        Returns:
            EnhancementResult with success status and corrected XML or errors.
        """
        logger.info("Attempting feedback correction based on review issues")

        images: list[Any] = []
        if image_urls:
            images = load_images_from_urls(image_urls)

        images_section = build_images_section(
            images, image_urls,
            action_verb="corregir el feedback",
        )

        prompt = FEEDBACK_CORRECTION_PROMPT.format(
            qti_xml_with_errors=qti_xml_with_errors,
            images_section=images_section,
            review_issues=review_issues,
        )

        try:
            response_text = self._client.call_with_images(
                prompt,
                images,
                reasoning_effort=_ENHANCE_REASONING,
            )
            corrected_xml = self._extract_xml(response_text)

            xsd_result = validate_qti_xml(corrected_xml)
            if xsd_result.get("valid"):
                logger.info("Correction XSD validation passed")
                return EnhancementResult(
                    success=True, qti_xml=corrected_xml, attempts=1,
                )

            xsd_errors = str(
                xsd_result.get("validation_errors", "Unknown error"),
            )
            logger.warning("Correction XSD validation failed: %s", xsd_errors)
            return EnhancementResult(
                success=False,
                error="Correction failed XSD validation",
                xsd_errors=xsd_errors,
                attempts=1,
            )

        except Exception as e:
            logger.error("Feedback correction failed: %s", e)
            return EnhancementResult(
                success=False, error=f"Correction failed: {e}", attempts=1,
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_xml(self, response_text: str) -> str:
        """Extract QTI XML from response, handling any wrapping.

        Args:
            response_text: Raw response text from LLM.

        Returns:
            Clean QTI XML string.
        """
        text = response_text.strip()

        # Remove markdown code blocks if present
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]  # Remove opening fence line
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        # Extract QTI element
        if "<qti-assessment-item" in text:
            start = text.index("<qti-assessment-item")
            end_tag = "</qti-assessment-item>"
            end = text.rindex(end_tag) + len(end_tag)
            text = text[start:end]

        return text.strip()
