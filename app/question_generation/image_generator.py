"""Phase 4b — Image Generation & Validation for QTI items.

Thin wrapper around the shared ImageGenerationEngine that handles
QTI-specific concerns: placeholder replacement, slot selection,
XSD validation, and progress callbacks.
"""

from __future__ import annotations

import logging
import re
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.image_generation.core import ImageGenerationEngine
from app.llm_clients import (
    GeminiImageClient,
    OpenAIClient,
    RateLimitError,
    ServiceUnavailableError,
)
from app.question_generation.models import (
    GeneratedItem,
    PhaseResult,
    PlanSlot,
)

logger = logging.getLogger(__name__)

_PLACEHOLDER_SRC = "IMAGE_PLACEHOLDER"
_MAX_PARALLEL_IMAGES = 3
_MAX_IMAGE_RETRIES = 1
_S3_PATH_PREFIX = "images/question-generation/"


class ImageGenerator:
    """Generates and validates images for QTI items (Phase 4b).

    Delegates core generation/validation/upload to
    ``ImageGenerationEngine``; keeps QTI-specific logic here.
    """

    def __init__(
        self,
        openai_client: OpenAIClient,
        gemini_image_client: GeminiImageClient | None = None,
        gemini_max_rpm: int = 10,
    ) -> None:
        self._engine = ImageGenerationEngine(
            openai_client,
            gemini_image_client,
            gemini_max_rpm,
        )

    def generate_images(
        self,
        items: list[GeneratedItem],
        slot_map: dict[int, PlanSlot],
        atom_id: str,
        on_image_complete: (
            Callable[[GeneratedItem], None] | None
        ) = None,
    ) -> PhaseResult:
        """Generate images for items where slot has image_required."""
        self._engine.ensure_gemini()
        image_items = _select_image_items(items, slot_map)
        if not image_items:
            return _build_result(items, errors=[])
        return self._run_parallel(
            image_items, items, atom_id, on_image_complete,
        )

    def generate_for_placeholders(
        self,
        items: list[GeneratedItem],
        atom_id: str,
        on_image_complete: (
            Callable[[GeneratedItem], None] | None
        ) = None,
    ) -> PhaseResult:
        """Generate images for items with placeholder + description."""
        self._engine.ensure_gemini()
        image_items = [
            it for it in items
            if _has_placeholder(it.qti_xml) and it.image_description
        ]
        if not image_items:
            return _build_result(items, errors=[])
        return self._run_parallel(
            image_items, items, atom_id, on_image_complete,
        )

    def _run_parallel(
        self,
        image_items: list[GeneratedItem],
        all_items: list[GeneratedItem],
        atom_id: str,
        on_image_complete: (
            Callable[[GeneratedItem], None] | None
        ),
    ) -> PhaseResult:
        """Run image gen + validation in parallel."""
        from app.question_generation.validation_checks import (
            validate_qti_xml,
        )

        total = len(image_items)
        logger.info(
            "Phase 4b: %d images to generate (%d workers)",
            total, _MAX_PARALLEL_IMAGES,
        )
        errors: list[str] = []
        lock = threading.Lock()
        done = [0]

        def _worker(item: GeneratedItem) -> None:
            error = self._process_one(
                item, atom_id, validate_qti_xml,
            )
            with lock:
                if error:
                    errors.append(error)
                done[0] += 1
                n = done[0]
            logger.info("Phase 4b progress: %d/%d", n, total)
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
                except (
                    RateLimitError, ServiceUnavailableError,
                ) as exc:
                    kind = (
                        "Daily quota"
                        if isinstance(exc, RateLimitError)
                        else "503 unavailable"
                    )
                    logger.error(
                        "%s — cancelling remaining images", kind,
                    )
                    for f in futures:
                        f.cancel()
                    with lock:
                        errors.append(kind.lower())
                    break
                except Exception as exc:
                    item = futures[future]
                    item.image_failed = True
                    with lock:
                        errors.append(
                            f"{item.item_id}: unexpected — {exc}",
                        )

        return _build_result(all_items, errors)

    def _process_one(
        self,
        item: GeneratedItem,
        atom_id: str,
        validate_qti_fn: Callable[..., dict],
    ) -> str | None:
        """Full pipeline for one QTI item."""
        item.image_failed = False
        desc = item.image_description
        if not desc:
            item.image_failed = True
            return f"{item.item_id}: no image_description"

        existing = self._engine.check_s3_exists(
            item.item_id, _S3_PATH_PREFIX, atom_id,
        )
        if existing:
            logger.info(
                "S3 hit for %s — skipping generation", item.item_id,
            )
            item.qti_xml = _replace_placeholder(
                item.qti_xml, existing,
            )
            return None

        stem = _extract_stem_text(item.qti_xml)
        image_bytes = self._engine.generate_validated_image(
            desc, stem, max_retries=_MAX_IMAGE_RETRIES,
        )
        if image_bytes is None:
            item.image_failed = True
            return f"{item.item_id}: image gen/validation failed"

        s3_url = self._engine.upload_to_s3(
            image_bytes, item.item_id,
            _S3_PATH_PREFIX, atom_id,
        )
        if s3_url is None:
            item.image_failed = True
            return f"{item.item_id}: S3 upload failed"

        item.qti_xml = _replace_placeholder(
            item.qti_xml, s3_url,
        )

        xsd_result = validate_qti_fn(item.qti_xml)
        if not xsd_result.get("valid"):
            item.image_failed = True
            xsd_err = xsd_result.get(
                "validation_errors", "unknown",
            )
            return (
                f"{item.item_id}: XSD invalid after image "
                f"embed — {xsd_err}"
            )

        logger.info(
            "Image OK for %s: %s", item.item_id, s3_url,
        )
        return None


# ------------------------------------------------------------------
# QTI-specific helpers
# ------------------------------------------------------------------


def _select_image_items(
    items: list[GeneratedItem],
    slot_map: dict[int, PlanSlot],
) -> list[GeneratedItem]:
    """Filter items whose slot has image_required."""
    return [
        it for it in items
        if (s := slot_map.get(it.slot_index)) is not None
        and s.image_required
        and _has_placeholder(it.qti_xml)
    ]


def _build_result(
    items: list[GeneratedItem], errors: list[str],
) -> PhaseResult:
    """Build PhaseResult from all items after image generation."""
    return PhaseResult(
        phase_name="image_generation",
        success=any(not it.image_failed for it in items),
        data={"items": items}, errors=errors,
    )


def _has_placeholder(qti_xml: str) -> bool:
    """Check if QTI XML contains the image placeholder."""
    return _PLACEHOLDER_SRC in qti_xml


def _replace_placeholder(qti_xml: str, s3_url: str) -> str:
    """Replace IMAGE_PLACEHOLDER src with the actual S3 URL."""
    return qti_xml.replace(
        f'src="{_PLACEHOLDER_SRC}"',
        f'src="{s3_url}"',
        1,
    )


def _extract_stem_text(qti_xml: str) -> str:
    """Extract plain text from the QTI item body for context."""
    match = re.search(
        r"<qti-item-body[^>]*>(.*?)<qti-choice-interaction",
        qti_xml, re.DOTALL,
    )
    if not match:
        return ""
    text = re.sub(r"<[^>]+>", " ", match.group(1))
    return re.sub(r"\s+", " ", text).strip()
