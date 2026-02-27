"""Image generation for mini-lesson sections.

Thin wrapper around the shared ImageGenerationEngine that handles
HTML-specific concerns: placeholder replacement in section HTML,
S3 path under ``images/mini-lessons/``, and content-aware S3 keys
to prevent stale images on re-runs.

Sections that need images arrive from Phase 2 with:
- ``IMAGE_PLACEHOLDER`` in the HTML (where the image should go)
- ``image_description`` on the LessonSection (detailed prompt)

This module generates the image, validates it, uploads to S3,
and replaces the placeholder with the real URL.
"""

from __future__ import annotations

import hashlib
import logging
import re

from app.image_generation.core import ImageGenerationEngine
from app.llm_clients import GeminiImageClient, OpenAIClient
from app.mini_lessons.models import LessonSection

logger = logging.getLogger(__name__)

_S3_PATH_PREFIX = "images/mini-lessons/"
_MAX_IMAGE_RETRIES = 1
_PLACEHOLDER_SRC = "IMAGE_PLACEHOLDER"


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
        atom_id: str,
    ) -> list[LessonSection]:
        """Generate images for sections that need them.

        A section needs an image when it has both a non-empty
        ``image_description`` and an ``IMAGE_PLACEHOLDER`` in
        its HTML (placed there by the section generator).

        Uses a content-aware S3 key (hash of description) so that:
        - Re-runs with the **same** description reuse existing images.
        - Re-runs with a **changed** description upload new images
          without overwriting the old ones.

        Returns the same list of sections (mutated in-place).
        """
        image_sections = [
            s for s in sections
            if s.image_description and _has_placeholder(s.html)
        ]
        if not image_sections:
            return sections

        self._engine.ensure_gemini()

        for section in image_sections:
            self._process_one(section, atom_id)

        return sections

    def _process_one(
        self,
        section: LessonSection,
        atom_id: str,
    ) -> None:
        """Generate, validate, upload, and replace for one section."""
        desc = section.image_description
        file_id = _build_file_id(section, desc)

        existing_url = self._engine.check_s3_exists(
            file_id, _S3_PATH_PREFIX, atom_id,
        )
        if existing_url:
            section.html = _replace_placeholder(
                section.html, existing_url,
            )
            logger.info(
                "Reused existing S3 image for %s/%s",
                atom_id, section.block_name,
            )
            return

        context = _extract_section_text(section.html)
        image_bytes = self._engine.generate_validated_image(
            desc, context, max_retries=_MAX_IMAGE_RETRIES,
        )
        if image_bytes is None:
            section.image_failed = True
            logger.warning(
                "Image generation failed for %s/%s",
                atom_id, section.block_name,
            )
            return

        s3_url = self._engine.upload_to_s3(
            image_bytes, file_id,
            _S3_PATH_PREFIX, atom_id,
        )
        if s3_url is None:
            section.image_failed = True
            logger.warning(
                "S3 upload failed for %s/%s",
                atom_id, section.block_name,
            )
            return

        section.html = _replace_placeholder(section.html, s3_url)
        logger.info(
            "Image OK for %s/%s: %s",
            atom_id, section.block_name, s3_url,
        )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _has_placeholder(html: str) -> bool:
    """Check if HTML contains the image placeholder."""
    return _PLACEHOLDER_SRC in html


def _replace_placeholder(html: str, s3_url: str) -> str:
    """Replace IMAGE_PLACEHOLDER src with the actual S3 URL."""
    return html.replace(
        f'src="{_PLACEHOLDER_SRC}"',
        f'src="{s3_url}"',
        1,
    )


def _build_file_id(
    section: LessonSection,
    description: str,
) -> str:
    """Build a content-aware S3 file identifier.

    Format: ``{block_name}-{index}-{hash8}``

    The 8-char hash of the description ensures that:
    - Same description -> same key -> S3 deduplication works.
    - Different description -> different key -> no stale reuse.
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


# ------------------------------------------------------------------
# Post-Phase-2b cleanup
# ------------------------------------------------------------------

_PLACEHOLDER_IMG_RE = re.compile(
    r'<p>\s*<img\s[^>]*src="IMAGE_PLACEHOLDER"[^>]*/>\s*</p>',
    re.IGNORECASE,
)


def strip_failed_image_placeholders(
    sections: list[LessonSection],
) -> list[str]:
    """Strip IMAGE_PLACEHOLDER from sections where image_failed.

    Prevents the destructive retry loop: if image gen failed,
    remove the placeholder so Phase 3 validation doesn't trigger
    a retry that silently drops the image reference.

    Returns a list of block_names that had placeholders stripped.
    """
    stripped: list[str] = []
    for section in sections:
        if not section.image_failed:
            continue
        if _PLACEHOLDER_SRC not in section.html:
            continue
        section.html = _PLACEHOLDER_IMG_RE.sub("", section.html)
        section.html = section.html.replace(
            f'src="{_PLACEHOLDER_SRC}"', "",
        )
        stripped.append(section.block_name)
        logger.warning(
            "Stripped IMAGE_PLACEHOLDER from %s (image_failed)",
            section.block_name,
        )
    return stripped
