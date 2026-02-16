"""Phase 4b — Image Generation.

Generates images for QTI items that need them, uploads to S3,
and embeds the image URL in the QTI XML. Uses GPT-5.1 for
description generation and Gemini for image generation.

No fallback: items that fail image generation are excluded.
"""

from __future__ import annotations

import base64
import json
import logging
import re
from typing import Any

from app.llm_clients import (
    GeminiImageClient,
    OpenAIClient,
    load_default_gemini_image_client,
)
from app.question_generation.models import (
    GeneratedItem,
    PhaseResult,
    PlanSlot,
)
from app.question_generation.prompts.image_generation import (
    GEMINI_IMAGE_GENERATION_PROMPT,
    IMAGE_DESCRIPTION_PROMPT,
)

logger = logging.getLogger(__name__)

_DESCRIPTION_REASONING = "low"


class ImageGenerator:
    """Generates images for QTI items that need them (Phase 4b).

    Flow per item:
    1. Generate detailed image description (GPT-5.1)
    2. Generate image with Gemini
    3. Upload to S3
    4. Embed <img> URL in QTI XML
    """

    def __init__(
        self,
        openai_client: OpenAIClient,
        gemini_image_client: GeminiImageClient | None = None,
    ) -> None:
        """Initialize the image generator.

        Args:
            openai_client: GPT-5.1 client for description generation.
            gemini_image_client: Gemini client for image generation.
                Loaded from env if None.
        """
        self._openai = openai_client
        self._gemini: GeminiImageClient | None = gemini_image_client

    def _ensure_gemini(self) -> GeminiImageClient:
        """Lazily load the Gemini image client.

        Returns:
            Initialized GeminiImageClient.
        """
        if self._gemini is None:
            self._gemini = load_default_gemini_image_client()
        return self._gemini

    def generate_images(
        self,
        items: list[GeneratedItem],
        slot_map: dict[int, PlanSlot],
        atom_id: str,
    ) -> PhaseResult:
        """Generate images for items whose slots need them.

        Items without image_required=True pass through unchanged.
        Items that fail image generation are excluded (no fallback).

        Args:
            items: Generated QTI items from Phase 4.
            slot_map: Map of slot_index to PlanSlot.
            atom_id: Atom ID for S3 path organization.

        Returns:
            PhaseResult with list of items (images embedded in XML).
        """
        result_items: list[GeneratedItem] = []
        errors: list[str] = []

        for item in items:
            slot = slot_map.get(item.slot_index)
            if not slot or not slot.image_required:
                result_items.append(item)
                continue

            logger.info(
                "Generating image for %s (type: %s)",
                item.item_id, slot.image_type,
            )

            enriched = self._generate_for_item(
                item, slot, atom_id, errors,
            )
            if enriched is not None:
                result_items.append(enriched)

        success = len(result_items) > 0
        return PhaseResult(
            phase_name="image_generation",
            success=success,
            data={"items": result_items},
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Per-item generation flow
    # ------------------------------------------------------------------

    def _generate_for_item(
        self,
        item: GeneratedItem,
        slot: PlanSlot,
        atom_id: str,
        errors: list[str],
    ) -> GeneratedItem | None:
        """Run the full image pipeline for a single item.

        Args:
            item: The QTI item to enrich with an image.
            slot: PlanSlot with image_type and image_description.
            atom_id: Atom ID for S3 path.
            errors: List to append error messages to.

        Returns:
            Item with image embedded in QTI XML, or None on failure.
        """
        # Step 1: Generate detailed image description (GPT-5.1)
        desc = self._generate_description(item, slot)
        if desc is None:
            errors.append(
                f"{item.item_id}: image description generation failed",
            )
            return None

        # Step 2: Generate image with Gemini
        image_bytes = self._generate_image(desc["generation_prompt"])
        if image_bytes is None:
            errors.append(
                f"{item.item_id}: Gemini image generation failed",
            )
            return None

        # Step 3: Upload to S3
        s3_url = self._upload_to_s3(
            image_bytes, item.item_id, atom_id,
        )
        if s3_url is None:
            errors.append(
                f"{item.item_id}: S3 upload failed",
            )
            return None

        # Step 4: Embed image URL in QTI XML
        item.qti_xml = self._embed_image_in_qti(
            item.qti_xml, s3_url, desc["alt_text"],
        )

        logger.info(
            "Image generated and embedded for %s: %s",
            item.item_id, s3_url,
        )
        return item

    # ------------------------------------------------------------------
    # Step 1: Description generation
    # ------------------------------------------------------------------

    def _generate_description(
        self,
        item: GeneratedItem,
        slot: PlanSlot,
    ) -> dict[str, str] | None:
        """Generate a detailed image description using GPT-5.1.

        Args:
            item: The QTI item (for stem context).
            slot: PlanSlot with image metadata.

        Returns:
            Dict with 'generation_prompt' and 'alt_text', or None.
        """
        stem = _extract_stem_text(item.qti_xml)
        prompt = IMAGE_DESCRIPTION_PROMPT.format(
            image_type=slot.image_type or "general",
            plan_description=slot.image_description or "",
            stem_context=stem[:500],
        )

        try:
            llm_resp = self._openai.generate_text(
                prompt,
                response_mime_type="application/json",
                reasoning_effort=_DESCRIPTION_REASONING,
            )
            data: dict[str, Any] = json.loads(llm_resp.text)

            gen_prompt = data.get("generation_prompt", "")
            alt_text = data.get("alt_text", "Imagen educativa")

            if not gen_prompt:
                logger.warning("Empty generation_prompt from LLM")
                return None

            return {
                "generation_prompt": gen_prompt,
                "alt_text": alt_text,
            }

        except Exception as exc:
            logger.error("Image description generation failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Step 2: Gemini image generation
    # ------------------------------------------------------------------

    def _generate_image(self, generation_prompt: str) -> bytes | None:
        """Generate an image using Gemini.

        Args:
            generation_prompt: Detailed description from Step 1.

        Returns:
            Raw PNG bytes, or None on failure.
        """
        gemini = self._ensure_gemini()
        prompt = GEMINI_IMAGE_GENERATION_PROMPT.format(
            generation_prompt=generation_prompt,
        )

        try:
            return gemini.generate_image(prompt)
        except Exception as exc:
            logger.error("Gemini image generation failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Step 3: S3 upload
    # ------------------------------------------------------------------

    def _upload_to_s3(
        self,
        image_bytes: bytes,
        item_id: str,
        atom_id: str,
    ) -> str | None:
        """Upload image bytes to S3.

        Uses importlib to load the S3 uploader from the pdf-to-qti
        module (which has dashes in its directory name).

        Args:
            image_bytes: Raw PNG data.
            item_id: Item ID for file naming.
            atom_id: Atom ID for path organization.

        Returns:
            Public S3 URL, or None on failure.
        """
        upload_fn = _load_s3_upload_fn()
        if upload_fn is None:
            logger.error("S3 uploader not available")
            return None

        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        return upload_fn(
            image_base64=image_b64,
            question_id=item_id,
            path_prefix="images/question-generation/",
            test_name=atom_id,
        )

    # ------------------------------------------------------------------
    # Step 4: QTI XML embedding
    # ------------------------------------------------------------------

    def _embed_image_in_qti(
        self,
        qti_xml: str,
        s3_url: str,
        alt_text: str,
    ) -> str:
        """Embed an image URL in the QTI XML stem.

        Inserts an <img> tag right after the opening <qti-item-body>
        tag, before any existing content.

        Args:
            qti_xml: Original QTI XML string.
            s3_url: Public S3 URL for the image.
            alt_text: Accessibility alt text.

        Returns:
            Updated QTI XML with embedded image.
        """
        img_tag = (
            f'<img src="{s3_url}" alt="{alt_text}" '
            f'style="max-width:100%;height:auto;" />'
        )

        # Insert after <qti-item-body> opening tag
        pattern = r"(<qti-item-body[^>]*>)"
        replacement = rf"\1\n        {img_tag}"
        return re.sub(pattern, replacement, qti_xml, count=1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Cached reference to the S3 upload function
_s3_upload_fn: Any = None


def _load_s3_upload_fn() -> Any:
    """Lazily load upload_image_to_s3 from the pdf-to-qti module.

    The pdf-to-qti directory uses dashes, so we need importlib
    to import it. Caches the function after first load.

    Returns:
        The upload_image_to_s3 function, or None if unavailable.
    """
    global _s3_upload_fn  # noqa: PLW0603
    if _s3_upload_fn is not None:
        return _s3_upload_fn

    import importlib
    from pathlib import Path

    spec_path = (
        Path(__file__).resolve().parents[1]
        / "pruebas" / "pdf-to-qti" / "modules" / "utils"
        / "s3_uploader.py"
    )
    if not spec_path.exists():
        logger.error("S3 uploader module not found: %s", spec_path)
        return None

    try:
        spec = importlib.util.spec_from_file_location(
            "s3_uploader", spec_path,
        )
        mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        _s3_upload_fn = mod.upload_image_to_s3
        return _s3_upload_fn
    except Exception as exc:
        logger.error("Failed to load S3 uploader: %s", exc)
        return None


def _extract_stem_text(qti_xml: str) -> str:
    """Extract plain text from the QTI XML stem for context.

    Strips XML tags to get readable text content from the
    item body (before the choice interaction).

    Args:
        qti_xml: Full QTI XML string.

    Returns:
        Plain text content of the stem (truncated).
    """
    # Extract content between <qti-item-body> and first
    # <qti-choice-interaction>
    match = re.search(
        r"<qti-item-body[^>]*>(.*?)<qti-choice-interaction",
        qti_xml,
        re.DOTALL,
    )
    if not match:
        return ""

    body = match.group(1)
    # Strip XML/HTML tags
    text = re.sub(r"<[^>]+>", " ", body)
    # Collapse whitespace
    return re.sub(r"\s+", " ", text).strip()
