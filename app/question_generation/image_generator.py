"""Phase 4b — Image Generation & Validation.

Per-item flow: generate image (Gemini) -> validate (GPT-5.1 vision)
-> upload to S3 -> replace IMAGE_PLACEHOLDER in QTI XML -> XSD check.
Items that fail get image_failed=True but keep their XML intact.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import re
import threading
import time
from collections import deque
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from PIL import Image

from app.llm_clients import (
    GeminiImageClient,
    OpenAIClient,
    RateLimitError,
    load_default_gemini_image_client,
)
from app.question_generation.models import (
    GeneratedItem,
    PhaseResult,
    PlanSlot,
)
from app.question_generation.prompts.image_generation import (
    GEMINI_IMAGE_GENERATION_PROMPT,
    GEMINI_IMAGE_RETRY_PROMPT,
    IMAGE_VALIDATION_PROMPT,
)
from app.question_generation.validation_checks import validate_qti_xml

logger = logging.getLogger(__name__)

_VALIDATION_REASONING = "low"
_PLACEHOLDER_SRC = "IMAGE_PLACEHOLDER"
_MAX_PARALLEL_IMAGES = 3
_MAX_IMAGE_RETRIES = 1


class _RateLimiter:
    """Thread-safe sliding-window rate limiter."""

    def __init__(self, max_rpm: int) -> None:
        self._max = max_rpm
        self._times: deque[float] = deque()
        self._lock = threading.Lock()

    def wait(self) -> None:
        """Block the calling thread until a slot is available."""
        while True:
            with self._lock:
                now = time.monotonic()
                while (self._times
                       and now - self._times[0] >= 60.0):
                    self._times.popleft()
                if len(self._times) < self._max:
                    self._times.append(now)
                    return
                delay = 60.0 - (now - self._times[0])
            time.sleep(delay + 0.1)


_DEFAULT_GEMINI_RPM = 10


class ImageGenerator:
    """Generates and validates images for QTI items (Phase 4b)."""

    def __init__(
        self,
        openai_client: OpenAIClient,
        gemini_image_client: GeminiImageClient | None = None,
        gemini_max_rpm: int = _DEFAULT_GEMINI_RPM,
    ) -> None:
        self._openai = openai_client
        self._gemini: GeminiImageClient | None = gemini_image_client
        self._rate_limiter = _RateLimiter(gemini_max_rpm)

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
        """Generate images for items where slot has image_required."""
        self._ensure_gemini()
        image_items = _select_image_items(items, slot_map)
        if not image_items:
            return _build_result(items, errors=[])
        return self._run_parallel_generation(
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
        self._ensure_gemini()
        image_items = [
            it for it in items
            if _has_placeholder(it.qti_xml) and it.image_description
        ]
        if not image_items:
            return _build_result(items, errors=[])
        return self._run_parallel_generation(
            image_items, items, atom_id, on_image_complete,
        )

    def _run_parallel_generation(
        self,
        image_items: list[GeneratedItem],
        all_items: list[GeneratedItem],
        atom_id: str,
        on_image_complete: (
            Callable[[GeneratedItem], None] | None
        ),
    ) -> PhaseResult:
        """Run image gen + validation in parallel for selected items."""
        total = len(image_items)
        logger.info(
            "Phase 4b: %d images to generate (%d workers)",
            total, _MAX_PARALLEL_IMAGES,
        )
        errors: list[str] = []
        lock = threading.Lock()
        done = [0]

        def _worker(item: GeneratedItem) -> None:
            error = self._process_image_for_item(item, atom_id)
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
                except RateLimitError:
                    logger.error(
                        "Daily quota exhausted — cancelling "
                        "remaining images",
                    )
                    for f in futures:
                        f.cancel()
                    with lock:
                        errors.append("daily quota exhausted")
                    break
                except Exception as exc:
                    item = futures[future]
                    item.image_failed = True
                    with lock:
                        errors.append(
                            f"{item.item_id}: unexpected — {exc}",
                        )

        return _build_result(all_items, errors)

    def _process_image_for_item(
        self,
        item: GeneratedItem,
        atom_id: str,
    ) -> str | None:
        """Run full pipeline for one item. Returns error or None."""
        item.image_failed = False
        desc = item.image_description
        if not desc:
            item.image_failed = True
            return f"{item.item_id}: no image_description"

        stem = _extract_stem_text(item.qti_xml)
        max_attempts = _MAX_IMAGE_RETRIES + 1
        image_bytes = self._generate_and_validate_with_retries(
            item.item_id, desc, stem, max_attempts,
        )
        if image_bytes is None:
            item.image_failed = True
            return (
                f"{item.item_id}: image gen/validation failed"
                f" after {max_attempts} attempts"
            )

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

    def _generate_and_validate_with_retries(
        self,
        item_id: str,
        description: str,
        stem: str,
        max_attempts: int,
    ) -> bytes | None:
        """Try generate+validate up to *max_attempts* times.

        Per-minute 429 -> sleep 60 s (no attempt consumed).
        Per-day 429 -> re-raise to stop the pipeline.
        """
        rejection: str | None = None
        attempt = 0
        while attempt < max_attempts:
            try:
                image_bytes = self._generate_image(
                    description, previous_rejection=rejection,
                )
            except RateLimitError as rle:
                if rle.is_daily:
                    raise
                logger.warning(
                    "%s: per-minute rate limit — sleeping 60 s",
                    item_id,
                )
                time.sleep(60)
                continue

            if image_bytes is None:
                logger.warning(
                    "%s: generation failed (attempt %d/%d)",
                    item_id, attempt + 1, max_attempts,
                )
                attempt += 1
                continue

            passed, reason = self._validate_image(
                image_bytes, description, stem,
            )
            if not passed:
                logger.warning(
                    "%s: validation failed (attempt %d/%d)",
                    item_id, attempt + 1, max_attempts,
                )
                rejection = reason
                attempt += 1
                continue

            return image_bytes
        return None

    def _generate_image(
        self,
        image_description: str,
        previous_rejection: str | None = None,
    ) -> bytes | None:
        """Generate image via Gemini. Lets RateLimitError propagate."""
        self._rate_limiter.wait()
        gemini = self._ensure_gemini()
        if previous_rejection:
            prompt = GEMINI_IMAGE_RETRY_PROMPT.format(
                generation_prompt=image_description,
                rejection_reason=previous_rejection,
            )
        else:
            prompt = GEMINI_IMAGE_GENERATION_PROMPT.format(
                generation_prompt=image_description,
            )
        try:
            return gemini.generate_image(prompt)
        except RateLimitError:
            raise
        except (TimeoutError, OSError) as exc:
            logger.error(
                "Gemini image generation timed out: %s", exc,
            )
            return None
        except Exception as exc:
            logger.error("Gemini image generation failed: %s", exc)
            return None

    def _validate_image(
        self,
        image_bytes: bytes,
        image_description: str,
        stem_context: str,
    ) -> tuple[bool, str]:
        """Validate via GPT-5.1 vision. Returns (passed, reason)."""
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
                return True, reason

            logger.warning("Image validation failed: %s", reason)
            return False, reason

        except Exception as exc:
            logger.error("Image validation error: %s", exc)
            return False, f"validation error: {exc}"

    def _upload_to_s3(
        self,
        image_bytes: bytes,
        item_id: str,
        atom_id: str,
    ) -> str | None:
        """Upload PNG to S3. Returns public URL or None."""
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


_s3_upload_fn: Any = None


def _load_s3_upload_fn() -> Any:
    """Lazily load upload_image_to_s3 from the pdf-to-qti module."""
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
    """Filter items whose slot has image_required and a placeholder."""
    return [
        it for it in items
        if (s := slot_map.get(it.slot_index)) is not None
        and s.image_required
        and _has_placeholder(it.qti_xml)
    ]


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
        qti_xml,
        re.DOTALL,
    )
    if not match:
        return ""

    body = match.group(1)
    text = re.sub(r"<[^>]+>", " ", body)
    return re.sub(r"\s+", " ", text).strip()
