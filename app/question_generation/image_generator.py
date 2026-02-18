"""Phase 4b — Image Generation & Validation.

Generates images for QTI items that have IMAGE_PLACEHOLDER in their
XML, validates them with GPT-5.1 vision, uploads to S3, and replaces
the placeholder with the S3 URL.

Flow per item:
1. Extract image_description from GeneratedItem (set by Phase 4).
2. Generate image with Gemini (nano banana pro).
3. Validate image with GPT-5.1 (vision).
4. Upload to S3.
5. Replace IMAGE_PLACEHOLDER with S3 URL in QTI XML.
6. Re-validate XSD on the final XML.

Items that fail any step get image_failed=True but keep their XML
so checkpoints preserve the work done in Phase 4.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import re
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from PIL import Image

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
    IMAGE_VALIDATION_PROMPT,
)
from app.question_generation.validation_checks import validate_qti_xml

logger = logging.getLogger(__name__)

_VALIDATION_REASONING = "low"
_PLACEHOLDER_SRC = "IMAGE_PLACEHOLDER"
_MAX_PARALLEL_IMAGES = 3


class ImageGenerator:
    """Generates and validates images for QTI items (Phase 4b).

    Flow per item:
    1. Generate image with Gemini from item.image_description
    2. Validate image with GPT-5.1 vision
    3. Upload to S3
    4. Replace placeholder with S3 URL
    5. Re-validate XSD
    """

    def __init__(
        self,
        openai_client: OpenAIClient,
        gemini_image_client: GeminiImageClient | None = None,
    ) -> None:
        """Initialize the image generator.

        Args:
            openai_client: GPT-5.1 client for image validation.
            gemini_image_client: Gemini client for image generation.
                Loaded from env if None.
        """
        self._openai = openai_client
        self._gemini: GeminiImageClient | None = gemini_image_client

    def _ensure_gemini(self) -> GeminiImageClient:
        """Lazily load the Gemini image client."""
        if self._gemini is None:
            self._gemini = load_default_gemini_image_client()
        return self._gemini

    def generate_images(
        self,
        items: list[GeneratedItem],
        slot_map: dict[int, PlanSlot],
        atom_id: str,
        on_image_complete: (
            Callable[[GeneratedItem], None] | None
        ) = None,
    ) -> PhaseResult:
        """Generate images concurrently for items that need them.

        Runs up to _MAX_PARALLEL_IMAGES items in parallel.
        Items without image_required pass through unchanged.
        Items that fail get image_failed=True but are still
        included so checkpoints preserve their XML.

        Args:
            items: Generated QTI items from Phase 4.
            slot_map: Map of slot_index to PlanSlot.
            atom_id: Atom ID for S3 path organization.
            on_image_complete: Optional callback after each image
                item finishes (pass or fail), for incremental
                checkpoint saves.

        Returns:
            PhaseResult with all items (failed ones flagged).
        """
        self._ensure_gemini()
        image_items = _select_image_items(items, slot_map)
        total = len(image_items)
        if not total:
            return _build_result(items, errors=[])

        logger.info(
            "Phase 4b: %d images to generate (%d workers)",
            total, _MAX_PARALLEL_IMAGES,
        )
        errors: list[str] = []
        lock = threading.Lock()
        done = [0]

        def _worker(item: GeneratedItem) -> None:
            slot = slot_map.get(item.slot_index)
            logger.info(
                "Generating image for %s (type: %s)",
                item.item_id,
                slot.image_type if slot else "unknown",
            )
            error = self._process_image_for_item(item, atom_id)
            with lock:
                if error:
                    errors.append(error)
                done[0] += 1
                n = done[0]
            logger.info(
                "Phase 4b progress: %d/%d images done",
                n, total,
            )
            if on_image_complete:
                try:
                    on_image_complete(item)
                except Exception as cb_exc:
                    logger.error(
                        "Checkpoint callback error: %s", cb_exc,
                    )

        with ThreadPoolExecutor(
            max_workers=_MAX_PARALLEL_IMAGES,
        ) as pool:
            futures = {
                pool.submit(_worker, it): it
                for it in image_items
            }
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as exc:
                    item = futures[future]
                    item.image_failed = True
                    with lock:
                        errors.append(
                            f"{item.item_id}: unexpected — {exc}",
                        )

        return _build_result(items, errors)

    # ------------------------------------------------------------------
    # Per-item pipeline
    # ------------------------------------------------------------------

    def _process_image_for_item(
        self,
        item: GeneratedItem,
        atom_id: str,
    ) -> str | None:
        """Run the full image pipeline for a single item.

        On failure at any step, sets item.image_failed=True and
        returns an error message. The XML is NOT modified on
        failure so it can be preserved in checkpoints.

        Each item is independent, so this method is safe to call
        from multiple threads concurrently.

        Args:
            item: QTI item with IMAGE_PLACEHOLDER in its XML.
            atom_id: Atom ID for S3 path.

        Returns:
            Error message on failure, None on success.
        """
        desc = item.image_description
        if not desc:
            item.image_failed = True
            return f"{item.item_id}: no image_description"

        image_bytes = self._generate_image(desc)
        if image_bytes is None:
            item.image_failed = True
            return f"{item.item_id}: Gemini image generation failed"

        stem = _extract_stem_text(item.qti_xml)
        valid = self._validate_image(image_bytes, desc, stem)
        if not valid:
            item.image_failed = True
            return f"{item.item_id}: image validation failed"

        s3_url = self._upload_to_s3(
            image_bytes, item.item_id, atom_id,
        )
        if s3_url is None:
            item.image_failed = True
            return f"{item.item_id}: S3 upload failed"

        item.qti_xml = _replace_placeholder(item.qti_xml, s3_url)

        xsd_result = validate_qti_xml(item.qti_xml)
        if not xsd_result.get("valid"):
            item.image_failed = True
            xsd_err = xsd_result.get(
                "validation_errors", "unknown",
            )
            return (
                f"{item.item_id}: XSD invalid after image embed "
                f"— {xsd_err}"
            )

        logger.info(
            "Image OK for %s: %s", item.item_id, s3_url,
        )
        return None

    # ------------------------------------------------------------------
    # Step 1: Gemini image generation
    # ------------------------------------------------------------------

    def _generate_image(
        self, image_description: str,
    ) -> bytes | None:
        """Generate an image using Gemini.

        Args:
            image_description: Detailed content description
                from Phase 4 (item.image_description).

        Returns:
            Raw PNG bytes, or None on failure.
        """
        gemini = self._ensure_gemini()
        prompt = GEMINI_IMAGE_GENERATION_PROMPT.format(
            generation_prompt=image_description,
        )
        try:
            return gemini.generate_image(prompt)
        except Exception as exc:
            logger.error("Gemini image generation failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Step 2: GPT-5.1 image validation (vision)
    # ------------------------------------------------------------------

    def _validate_image(
        self,
        image_bytes: bytes,
        image_description: str,
        stem_context: str,
    ) -> bool:
        """Validate generated image using GPT-5.1 with vision.

        Args:
            image_bytes: Raw PNG data from Gemini.
            image_description: Expected content description.
            stem_context: Question stem text for context.

        Returns:
            True if image passes validation.
        """
        prompt = IMAGE_VALIDATION_PROMPT.format(
            image_description=image_description,
            stem_context=stem_context[:500],
        )
        pil_img = Image.open(io.BytesIO(image_bytes))

        try:
            resp = self._openai.call_with_images(
                prompt,
                [pil_img],
                reasoning_effort=_VALIDATION_REASONING,
                response_mime_type="application/json",
            )
            data: dict[str, Any] = json.loads(resp.text)
            result = data.get("result", "fail")
            reason = data.get("reason", "no reason")

            if result == "pass":
                logger.info("Image validation passed: %s", reason)
                return True

            logger.warning("Image validation failed: %s", reason)
            return False

        except Exception as exc:
            logger.error("Image validation error: %s", exc)
            return False

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _select_image_items(
    items: list[GeneratedItem],
    slot_map: dict[int, PlanSlot],
) -> list[GeneratedItem]:
    """Filter items that need image generation."""
    result: list[GeneratedItem] = []
    for item in items:
        slot = slot_map.get(item.slot_index)
        if (
            slot is not None
            and slot.image_required
            and _has_placeholder(item.qti_xml)
        ):
            result.append(item)
    return result


def _build_result(
    items: list[GeneratedItem],
    errors: list[str],
) -> PhaseResult:
    """Build PhaseResult from all items after image generation."""
    active = [it for it in items if not it.image_failed]
    return PhaseResult(
        phase_name="image_generation",
        success=len(active) > 0,
        data={"items": items},
        errors=errors,
    )


def _has_placeholder(qti_xml: str) -> bool:
    """Check if QTI XML contains the image placeholder."""
    return _PLACEHOLDER_SRC in qti_xml


def _replace_placeholder(qti_xml: str, s3_url: str) -> str:
    """Replace IMAGE_PLACEHOLDER src with the actual S3 URL.

    Args:
        qti_xml: QTI XML with IMAGE_PLACEHOLDER in an <img> tag.
        s3_url: Public S3 URL to substitute.

    Returns:
        Updated QTI XML with the real image URL.
    """
    return qti_xml.replace(
        f'src="{_PLACEHOLDER_SRC}"',
        f'src="{s3_url}"',
        1,
    )


def _extract_stem_text(qti_xml: str) -> str:
    """Extract plain text from the QTI XML stem for context.

    Strips XML tags to get readable text content from the
    item body (before the choice interaction).

    Args:
        qti_xml: Full QTI XML string.

    Returns:
        Plain text content of the stem.
    """
    match = re.search(
        r"<qti-item-body[^>]*>(.*?)<qti-choice-interaction",
        qti_xml,
        re.DOTALL,
    )
    if not match:
        return ""

    body = match.group(1)
    text = re.sub(r"<[^>]+>", " ", body)
    return re.sub(r"\s+", " ", text).strip()
