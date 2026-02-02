"""
Choice Diagrams Processor

Specialized module for handling multiple choice questions with diagram options.
Detects when a question has multiple visual choices (A, B, C, D) and extracts
each choice region separately, avoiding the over-expansion issue that occurs
with single-diagram logic.

This module serves as the main entry point and orchestrator, delegating to:
- choice_detection.py: Detection logic for choice diagram questions
- choice_region_utils.py: Region finding and boundary calculation
"""

from __future__ import annotations

from typing import Any

import fitz  # type: ignore

# Import from split modules
from app.pruebas.pdf_to_qti.modules.image_processing.choice_detection import (
    is_choice_diagram_question,
)
from app.pruebas.pdf_to_qti.modules.image_processing.choice_region_utils import (
    calculate_choice_boundaries,
    create_comprehensive_choice_bbox,
    find_blocks_near_choice_constrained,
    find_choice_regions,
)


class ChoiceDiagramExtractionError(Exception):
    """Custom exception for errors during choice diagram extraction."""
    pass


def detect_and_extract_choice_diagrams(
    page: fitz.Page,
    text_blocks: list[dict[str, Any]],
    ai_categories: dict[int, str] | None = None,
    question_text: str = ""
) -> list[dict[str, Any]] | None:
    """
    Detect if this is a multiple choice question with diagram options and extract
    each choice region separately.

    Args:
        page: PDF page object
        text_blocks: All text blocks from the page
        ai_categories: AI categorization of text blocks
        question_text: The question text for additional context

    Returns:
        List of image dictionaries for each choice, or None if not a choice diagram question

    Raises:
        ChoiceDiagramExtractionError: If detection succeeds but extraction fails
    """
    print("🎯 Checking if this is a choice diagram question...")

    # Step 1: Detect if this is a multiple choice visual question
    if not is_choice_diagram_question(text_blocks, ai_categories, question_text):
        print("🎯 Not a choice diagram question")
        return None

    print("🎯 ✅ Detected choice diagram question")

    # Step 2: Find answer choice regions
    choice_regions = find_choice_regions(page, text_blocks, ai_categories)

    if not choice_regions:
        print("🎯 ⚠️ Could not identify choice regions")
        raise ChoiceDiagramExtractionError(
            "Detected a choice diagram question, but failed to identify the specific "
            "regions for each choice. This is likely because the choice labels "
            "(e.g., A, B, C, D) could not be found."
        )

    print(f"🎯 Found {len(choice_regions)} choice regions")

    # Step 3: Extract each choice region as a separate image
    choice_images = _extract_choice_images(page, choice_regions)

    if not choice_images:
        raise ChoiceDiagramExtractionError(
            "Detected a choice diagram question and found choice regions, "
            "but failed to render the images for the choices."
        )

    return choice_images


def _extract_choice_images(
    page: fitz.Page,
    choice_regions: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Extract images from choice regions.

    Args:
        page: PDF page object
        choice_regions: List of region dictionaries with bbox info

    Returns:
        List of image dictionaries for each successfully extracted choice
    """
    choice_images = []

    for i, region in enumerate(choice_regions):
        choice_letter = region.get('choice_letter', f'Choice{i+1}')
        bbox = region['bbox']

        try:
            render_rect = fitz.Rect(bbox)
            if render_rect.is_empty or render_rect.width < 10 or render_rect.height < 10:
                print(f"🎯 ⚠️ Skipping {choice_letter}: bbox too small")
                continue

            scale = 2.0
            matrix = fitz.Matrix(scale, scale)
            pix = page.get_pixmap(matrix=matrix, clip=render_rect, alpha=False)
            img_bytes = pix.tobytes("png")

            choice_image = {
                "bbox": bbox,
                "width": pix.width,
                "height": pix.height,
                "ext": "png",
                "image": img_bytes,
                "is_table": False,
                "is_grouped": False,
                "is_choice_diagram": True,
                "choice_letter": choice_letter,
                "description": f"Diagram for choice {choice_letter}"
            }

            choice_images.append(choice_image)
            print(f"🎯 ✅ Extracted {choice_letter}: {pix.width}x{pix.height}")

        except Exception as e:
            print(f"🎯 ⚠️ Error extracting {choice_letter}: {e}")
            continue

    return choice_images


# =============================================================================
# Backward-compatible exports
# =============================================================================
# These aliases maintain compatibility with existing imports

# Internal functions that were previously in this module
_is_choice_diagram_question = is_choice_diagram_question
_find_choice_regions = find_choice_regions
_calculate_choice_boundaries = calculate_choice_boundaries
_find_blocks_near_choice_constrained = find_blocks_near_choice_constrained
_create_comprehensive_choice_bbox = create_comprehensive_choice_bbox

__all__ = [
    # Main public API
    "ChoiceDiagramExtractionError",
    "detect_and_extract_choice_diagrams",
    # Re-exported from choice_detection
    "is_choice_diagram_question",
    # Re-exported from choice_region_utils
    "find_choice_regions",
    "calculate_choice_boundaries",
    "find_blocks_near_choice_constrained",
    "create_comprehensive_choice_bbox",
    # Backward-compatible aliases (private functions)
    "_is_choice_diagram_question",
    "_find_choice_regions",
    "_calculate_choice_boundaries",
    "_find_blocks_near_choice_constrained",
    "_create_comprehensive_choice_bbox",
]
