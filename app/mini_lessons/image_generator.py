"""Image generation for mini-lesson visual-intuition sections.

Thin wrapper around the shared ImageGenerationEngine that handles
HTML-specific concerns: ``<img>`` tag injection into section HTML,
S3 path under ``images/mini-lessons/``.
"""

from __future__ import annotations

import logging
import re

from app.image_generation.core import ImageGenerationEngine
from app.llm_clients import GeminiImageClient, OpenAIClient
from app.mini_lessons.models import LessonPlan, LessonSection

logger = logging.getLogger(__name__)

_S3_PATH_PREFIX = "images/mini-lessons/"
_MAX_IMAGE_RETRIES = 1
_IMAGE_PLACEHOLDER = "IMAGE_PLACEHOLDER"


class LessonImageGenerator:
    """Generates images for visual-intuition sections."""

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

        Currently targets ``visual-intuition`` sections whose
        plan entry includes an image description. Updates the
        section HTML in place with the S3 URL.

        Returns the same list of sections (mutated).
        """
        self._engine.ensure_gemini()

        for section in sections:
            if not _needs_image(section, plan):
                continue

            desc = _extract_image_description(section, plan)
            if not desc:
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

            file_id = f"{section.block_name}-{section.index or 0}"
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


def _needs_image(
    section: LessonSection,
    plan: LessonPlan,
) -> bool:
    """Check if the section's plan entry includes image content."""
    if section.block_name == "visual-intuition":
        return True
    if _IMAGE_PLACEHOLDER in section.html:
        return True
    for opt in plan.optional_sections:
        if (opt.block_name == section.block_name
                and "image" in opt.content_spec.lower()):
            return True
    return False


def _extract_image_description(
    section: LessonSection,
    plan: LessonPlan,
) -> str:
    """Get the image description from the plan's optional spec."""
    for opt in plan.optional_sections:
        if opt.block_name == section.block_name:
            return opt.content_spec
    return ""


def _extract_section_text(html: str) -> str:
    """Strip tags to get plain text for validation context."""
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()[:500]


def _inject_image_tag(
    html: str,
    s3_url: str,
    alt_text: str,
) -> str:
    """Inject an ``<img>`` tag into the section HTML.

    If the HTML contains IMAGE_PLACEHOLDER, replaces it.
    Otherwise appends the image before the closing ``</section>``.
    """
    img_tag = f'<img src="{s3_url}" alt="{alt_text}" />'

    if _IMAGE_PLACEHOLDER in html:
        return html.replace(
            f'src="{_IMAGE_PLACEHOLDER}"',
            f'src="{s3_url}"',
            1,
        )

    closing = "</section>"
    if closing in html:
        return html.replace(
            closing,
            f"  {img_tag}\n{closing}",
            1,
        )
    return html + f"\n{img_tag}"
