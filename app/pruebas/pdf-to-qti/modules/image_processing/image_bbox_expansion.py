"""Image bounding box intelligent expansion.

Provides functions to expand PyMuPDF detected bboxes to capture full visual content.
"""

from __future__ import annotations

from typing import Any

import fitz  # type: ignore


def expand_pymupdf_bbox_intelligently(
    pymupdf_bbox: list[float],
    page: fitz.Page,
    text_blocks: list[dict[str, Any]],
    ai_categories: dict[int, str] | None = None,
) -> list[float]:
    """
    Intelligently expand a PyMuPDF detected bbox to capture the full visual content.

    This method starts with a small PyMuPDF detection (like just the "Sun" in a diagram)
    and expands it in all directions until it hits question/answer text or page boundaries.

    Args:
        pymupdf_bbox: Original PyMuPDF detected bbox [x0, y0, x1, y1]
        page: PDF page object
        text_blocks: All text blocks from the page
        ai_categories: Optional AI categorization of text blocks

    Returns:
        Expanded bbox that captures the full visual content
    """
    print(f"📸 Smart expansion starting from PyMuPDF bbox: {pymupdf_bbox}")

    original_x0, original_y0, original_x1, original_y1 = pymupdf_bbox
    page_width = page.rect.width
    page_height = page.rect.height

    # Start with original bbox
    expanded_bbox = list(pymupdf_bbox)

    # Get question/answer text blocks to avoid
    qa_text_blocks = _get_qa_text_blocks(text_blocks, ai_categories, expanded_bbox)
    print(f"📸 Found {len(qa_text_blocks)} Q&A text blocks to avoid")

    # Find the maximum expansion boundaries
    max_left, max_right, max_top, max_bottom = _find_expansion_boundaries(
        expanded_bbox, qa_text_blocks, page_width, page_height
    )

    # Apply the expansion
    expanded_bbox[0] = max_left
    expanded_bbox[2] = max_right
    expanded_bbox[1] = max_top
    expanded_bbox[3] = max_bottom

    print(
        f"📸 Expansion boundaries: left={max_left}, right={max_right}, "
        f"top={max_top}, bottom={max_bottom}"
    )

    # Log expansion stats
    _log_expansion_stats(
        original_x0, original_y0, original_x1, original_y1, expanded_bbox
    )

    return expanded_bbox


def _get_qa_text_blocks(
    text_blocks: list[dict[str, Any]],
    ai_categories: dict[int, str] | None,
    expanded_bbox: list[float],
) -> list[list[float]]:
    """Get question/answer text blocks to avoid during expansion."""
    qa_text_blocks: list[list[float]] = []

    for i, block in enumerate(text_blocks):
        if block.get("type") != 0:
            continue

        block_bbox = block.get("bbox")
        if not block_bbox or len(block_bbox) < 4:
            continue

        block_num = i + 1
        is_qa_text = False
        category_info = ""

        if ai_categories and block_num in ai_categories:
            category = ai_categories[block_num]
            is_qa_text = category in ["question_text", "answer_choice"]
            category_info = f"AI:{category}"

            # Image-related text should NOT be avoided
            if category in ["visual_content_title", "visual_content_label", "other_label"]:
                print(f"📸 Block {block_num} is part of image ({category}) - will expand through it")
                continue
        else:
            # Conservative fallback: only avoid very large text blocks
            block_area = (block_bbox[2] - block_bbox[0]) * (block_bbox[3] - block_bbox[1])
            is_qa_text = block_area > 2000
            category_info = f"fallback:area={block_area:.0f}"

        if is_qa_text:
            qa_text_blocks.append(block_bbox)
            print(f"📸 Block {block_num} will be avoided during expansion ({category_info})")

    return qa_text_blocks


def _find_expansion_boundaries(
    expanded_bbox: list[float],
    qa_text_blocks: list[list[float]],
    page_width: float,
    page_height: float,
) -> tuple[float, float, float, float]:
    """Find the maximum expansion boundaries in each direction."""
    safety_margin = 10

    max_left = 0.0
    max_right = page_width
    max_top = 0.0
    max_bottom = page_height

    for qa_bbox in qa_text_blocks:
        qa_x0, qa_y0, qa_x1, qa_y1 = qa_bbox

        # For left expansion: find rightmost text to the left
        if qa_x1 <= expanded_bbox[0]:
            if not (qa_y1 <= expanded_bbox[1] or qa_y0 >= expanded_bbox[3]):
                max_left = max(max_left, qa_x1 + safety_margin)

        # For right expansion: find leftmost text to the right
        if qa_x0 >= expanded_bbox[2]:
            if not (qa_y1 <= expanded_bbox[1] or qa_y0 >= expanded_bbox[3]):
                max_right = min(max_right, qa_x0 - safety_margin)

        # For top expansion: find bottommost text above
        if qa_y1 <= expanded_bbox[1]:
            if not (qa_x1 <= expanded_bbox[0] or qa_x0 >= expanded_bbox[2]):
                max_top = max(max_top, qa_y1 + safety_margin)

        # For bottom expansion: find topmost text below
        if qa_y0 >= expanded_bbox[3]:
            if not (qa_x1 <= expanded_bbox[0] or qa_x0 >= expanded_bbox[2]):
                max_bottom = min(max_bottom, qa_y0 - safety_margin)

    return max_left, max_right, max_top, max_bottom


def _log_expansion_stats(
    original_x0: float,
    original_y0: float,
    original_x1: float,
    original_y1: float,
    expanded_bbox: list[float],
) -> None:
    """Log expansion statistics."""
    original_width = original_x1 - original_x0
    original_height = original_y1 - original_y0
    new_width = expanded_bbox[2] - expanded_bbox[0]
    new_height = expanded_bbox[3] - expanded_bbox[1]

    expansion_factor_x = new_width / original_width if original_width > 0 else 1
    expansion_factor_y = new_height / original_height if original_height > 0 else 1

    print("📸 Smart expansion completed:")
    print(f"   Original: {original_width:.0f}x{original_height:.0f}")
    print(f"   Expanded: {new_width:.0f}x{new_height:.0f}")
    print(f"   Expansion: {expansion_factor_x:.1f}x horizontally, {expansion_factor_y:.1f}x vertically")
    print(f"   Final bbox: {expanded_bbox}")


def bbox_overlaps_with_qa_text(
    test_bbox: list[float],
    qa_text_blocks: list[list[float]],
    safety_margin: float,
) -> bool:
    """Check if a test bbox overlaps with any Q&A text blocks (with safety margin)."""
    test_x0, test_y0, test_x1, test_y1 = test_bbox

    for qa_bbox in qa_text_blocks:
        qa_x0, qa_y0, qa_x1, qa_y1 = qa_bbox

        # Add safety margin to Q&A text bbox
        margin_qa_x0 = qa_x0 - safety_margin
        margin_qa_y0 = qa_y0 - safety_margin
        margin_qa_x1 = qa_x1 + safety_margin
        margin_qa_y1 = qa_y1 + safety_margin

        # Check for overlap
        if not (
            test_x1 <= margin_qa_x0
            or test_x0 >= margin_qa_x1
            or test_y1 <= margin_qa_y0
            or test_y0 >= margin_qa_y1
        ):
            return True

    return False
