"""Feedback enhancement using OpenAI GPT models."""

from __future__ import annotations

import importlib.util
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from app.question_feedback.models import EnhancementResult
from app.question_feedback.prompts import (
    FEEDBACK_CORRECTION_PROMPT,
    FEEDBACK_ENHANCEMENT_PROMPT,
)
from app.question_feedback.utils.image_utils import load_images_from_urls


def _import_xml_validator() -> Any:
    """Import validate_qti_xml from the hyphenated pdf-to-qti folder.

    Python doesn't allow hyphens in module names, so we use importlib.util
    to load the module directly from its file path.
    """
    # Build path to the xml_validator module
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

    spec = importlib.util.spec_from_file_location("xml_validator", module_path)
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
    # Fallback: define a stub if import fails
    def validate_qti_xml(
        qti_xml: str, validation_endpoint: str | None = None
    ) -> dict[str, Any]:
        """Stub validator when real one is not available."""
        return {"success": True, "valid": True, "message": "Validation skipped"}

logger = logging.getLogger(__name__)


class FeedbackEnhancer:
    """Enhance QTI XML with feedback using OpenAI GPT models.

    This class takes a base QTI XML (without feedback) and generates a complete
    QTI XML with embedded feedback using an LLM. XSD validation is performed
    immediately after generation with retry logic.
    """

    DEFAULT_MODEL = "gpt-5.1"

    def __init__(
        self,
        model: str | None = None,
        max_retries: int = 2,
        api_key: str | None = None,
    ):
        """Initialize the enhancer.

        Args:
            model: OpenAI model to use. Defaults to gpt-5.1.
            max_retries: Maximum XSD validation retries.
            api_key: OpenAI API key. Defaults to OPENAI_API_KEY env var.
        """
        load_dotenv()
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self._api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.model = model or self.DEFAULT_MODEL
        self.max_retries = max_retries
        self._last_xsd_errors: str | None = None

        # Import OpenAIClient from llm_clients
        from app.llm_clients import OpenAIClient

        self._client = OpenAIClient(api_key=self._api_key, model=self.model)

    def enhance(
        self,
        qti_xml: str,
        image_urls: list[str] | None = None,
    ) -> EnhancementResult:
        """Generate complete QTI XML with feedback embedded.

        Args:
            qti_xml: Original QTI XML without feedback.
            image_urls: Optional list of image URLs for multimodal input.

        Returns:
            EnhancementResult with success status and enhanced XML or errors.
        """
        # Load images once (outside retry loop)
        images: list[Any] = []
        if image_urls:
            images = load_images_from_urls(image_urls)

        for attempt in range(self.max_retries + 1):
            logger.info(
                f"Enhancement attempt {attempt + 1}/{self.max_retries + 1} "
                f"({len(images)} images)"
            )

            # Build prompt with images section
            images_section = ""
            if images:
                images_section = (
                    f"IMÁGENES: {len(images)} imagen(es) adjuntas. "
                    "Considera las imágenes al generar el feedback educativo."
                )
            elif image_urls:
                images_section = (
                    f"IMÁGENES: Se detectaron {len(image_urls)} imagen(es) pero "
                    "no se pudieron cargar. Genera feedback basándote solo en el texto."
                )

            prompt = FEEDBACK_ENHANCEMENT_PROMPT.format(
                original_qti_xml=qti_xml,
                images_section=images_section,
            )

            # Add XSD errors if this is a retry
            if attempt > 0 and self._last_xsd_errors:
                prompt += f"\n\nERRORES XSD DEL INTENTO ANTERIOR:\n{self._last_xsd_errors}\n"
                prompt += "Por favor corrige estos errores en tu respuesta."

            try:
                # Build multimodal prompt if we have images
                if images:
                    multimodal_prompt: list[Any] = [prompt]
                    multimodal_prompt.extend(images)
                    response_text = self._client.generate_text(
                        multimodal_prompt,
                        temperature=0.0,
                        max_tokens=8000,
                    )
                else:
                    response_text = self._client.generate_text(
                        prompt,
                        temperature=0.0,
                        max_tokens=8000,
                    )

                enhanced_xml = self._extract_xml(response_text)

                # XSD Validation immediately
                xsd_result = validate_qti_xml(enhanced_xml)

                if xsd_result.get("valid"):
                    logger.info("XSD validation passed")
                    return EnhancementResult(
                        success=True,
                        qti_xml=enhanced_xml,
                        attempts=attempt + 1,
                    )

                # Store errors for retry
                self._last_xsd_errors = str(
                    xsd_result.get("validation_errors", "Unknown error")
                )
                logger.warning(f"XSD validation failed: {self._last_xsd_errors}")

            except Exception as e:
                logger.error(f"Enhancement attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries:
                    return EnhancementResult(
                        success=False,
                        error=f"Enhancement failed: {str(e)}",
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
            review_issues: Description of the issues found by the reviewer.
            image_urls: Optional list of image URLs for multimodal input.

        Returns:
            EnhancementResult with success status and corrected XML or errors.
        """
        logger.info("Attempting feedback correction based on review issues")

        images: list[Any] = []
        if image_urls:
            images = load_images_from_urls(image_urls)

        images_section = ""
        if images:
            images_section = (
                f"IMÁGENES: {len(images)} imagen(es) adjuntas. "
                "Considera las imágenes al corregir el feedback."
            )

        prompt = FEEDBACK_CORRECTION_PROMPT.format(
            qti_xml_with_errors=qti_xml_with_errors,
            images_section=images_section,
            review_issues=review_issues,
        )

        try:
            if images:
                multimodal_prompt: list[Any] = [prompt]
                multimodal_prompt.extend(images)
                response_text = self._client.generate_text(
                    multimodal_prompt,
                    temperature=0.0,
                    max_tokens=8000,
                )
            else:
                response_text = self._client.generate_text(
                    prompt,
                    temperature=0.0,
                    max_tokens=8000,
                )

            corrected_xml = self._extract_xml(response_text)

            # XSD Validation
            xsd_result = validate_qti_xml(corrected_xml)

            if xsd_result.get("valid"):
                logger.info("Correction XSD validation passed")
                return EnhancementResult(
                    success=True,
                    qti_xml=corrected_xml,
                    attempts=1,
                )

            xsd_errors = str(xsd_result.get("validation_errors", "Unknown error"))
            logger.warning(f"Correction XSD validation failed: {xsd_errors}")
            return EnhancementResult(
                success=False,
                error="Correction failed XSD validation",
                xsd_errors=xsd_errors,
                attempts=1,
            )

        except Exception as e:
            logger.error(f"Feedback correction failed: {e}")
            return EnhancementResult(
                success=False,
                error=f"Correction failed: {str(e)}",
                attempts=1,
            )

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
            lines = lines[1:]  # Remove first line (```xml or ```)
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]  # Remove last line (```)
            text = "\n".join(lines)

        # Ensure it starts with the QTI element
        if "<qti-assessment-item" in text:
            start = text.index("<qti-assessment-item")
            end = text.rindex("</qti-assessment-item>") + len("</qti-assessment-item>")
            text = text[start:end]

        return text.strip()
