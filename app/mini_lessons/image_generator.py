"""Image generation for mini-lesson sections.

Thin wrapper around the shared ImageGenerationEngine that handles
HTML-specific concerns: ``<img>`` tag injection into section HTML,
S3 path under ``images/mini-lessons/``, and content-aware S3 keys
to prevent stale images on re-runs.
"""

from __future__ import annotations

import hashlib
import logging
import re

from app.image_generation.core import ImageGenerationEngine
from app.llm_clients import GeminiImageClient, OpenAIClient
from app.mini_lessons.models import LessonPlan, LessonSection

logger = logging.getLogger(__name__)

_S3_PATH_PREFIX = "images/mini-lessons/"
_MAX_IMAGE_RETRIES = 1

# Sections that always get an image when present in the plan.
_IMAGE_SECTIONS: frozenset[str] = frozenset({
    "visual-intuition",
})


class LessonImageGenerator:
    """Generates and uploads images for lesson sections."""

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

    def generate_for_sections(
        self,
        sections: list[LessonSection],
        plan: LessonPlan,
        atom_id: str,
    ) -> list[LessonSection]:
        """Generate images for sections that need them.

        Targets sections in ``_IMAGE_SECTIONS`` and any optional
        section whose plan ``content_spec`` contains "imagen".

        Uses a content-aware S3 key (hash of description) so that:
        - Re-runs with the **same** plan reuse existing images.
        - Re-runs with a **changed** plan upload new images
          without overwriting the old ones.

        Returns the same list of sections (mutated).
        """
        self._engine.ensure_gemini()

        for section in sections:
            desc = _resolve_image_description(section, plan)
            if not desc:
                continue

            file_id = _build_file_id(section, desc)

            existing_url = self._engine.check_s3_exists(
                file_id, _S3_PATH_PREFIX, atom_id,
            )
            if existing_url:
                section.html = _inject_image_tag(
                    section.html, existing_url, desc,
                )
                logger.info(
                    "Reused existing S3 image for %s/%s",
                    atom_id, section.block_name,
                )
                continue

            context = _extract_section_text(section.html)
            image_bytes = self._engine.generate_validated_image(
                desc, context, max_retries=_MAX_IMAGE_RETRIES,
            )
            if image_bytes is None:
                logger.warning(
                    "Image generation failed for %s/%s",
                    atom_id, section.block_name,
                )
                continue

            s3_url = self._engine.upload_to_s3(
                image_bytes, file_id,
                _S3_PATH_PREFIX, atom_id,
            )
            if s3_url is None:
                logger.warning(
                    "S3 upload failed for %s/%s",
                    atom_id, section.block_name,
                )
                continue

            section.html = _inject_image_tag(
                section.html, s3_url, desc,
            )
            logger.info(
                "Image injected for %s/%s: %s",
                atom_id, section.block_name, s3_url,
            )

        return sections


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _resolve_image_description(
    section: LessonSection,
    plan: LessonPlan,
) -> str:
    """Return the image generation prompt for *section*, or "" to skip.

    Decision logic (in order):
    1. If the section block is in ``_IMAGE_SECTIONS`` → use its
       matching ``optional_sections`` entry's ``content_spec``.
    2. If an ``optional_sections`` entry matches by ``block_name``
       and its ``content_spec`` mentions "imagen" → use it.
    3. Otherwise → return "" (no image needed).
    """
    for opt in plan.optional_sections:
        if opt.block_name != section.block_name:
            continue
        if section.block_name in _IMAGE_SECTIONS:
            return opt.content_spec
        if "imagen" in opt.content_spec.lower():
            return opt.content_spec
    return ""


def _build_file_id(
    section: LessonSection,
    description: str,
) -> str:
    """Build a content-aware S3 file identifier.

    Format: ``{block_name}-{index}-{hash8}``

    The 8-char hash of the description ensures that:
    - Same description → same key → S3 deduplication works.
    - Different description → different key → no stale reuse.
    """
    idx = section.index or 0
    desc_hash = hashlib.sha256(
        description.encode(),
    ).hexdigest()[:8]
    return f"{section.block_name}-{idx}-{desc_hash}"


def _extract_section_text(html: str) -> str:
    """Strip tags to get plain text for validation context."""
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()[:500]


def _inject_image_tag(
    html: str,
    s3_url: str,
    alt_text: str,
) -> str:
    """Insert an ``<img>`` tag before the closing ``</section>``.

    If the section already contains an ``<img>`` pointing to the
    same URL, the HTML is returned unchanged (idempotent).
    """
    if s3_url in html:
        return html

    safe_alt = alt_text.replace('"', "&quot;")
    img_tag = f'<img src="{s3_url}" alt="{safe_alt}" />'

    closing = "</section>"
    if closing in html:
        return html.replace(
            closing,
            f"  {img_tag}\n{closing}",
            1,
        )
    return html + f"\n{img_tag}"
