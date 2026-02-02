"""Image bounding box construction from text gaps.

Provides functions to construct image bounding boxes by finding gaps
between question/answer text blocks.
"""

from __future__ import annotations

from typing import Any

import fitz  # type: ignore


def construct_image_bbox_from_gaps(
    page: fitz.Page,
    question_answer_blocks: list[list[float]],
    image_label_blocks: list[list[float]],
    all_page_text_bboxes: list[list[float]],
) -> list[float] | None:
    """Construct image bbox by finding gaps between question/answer text blocks."""
    if not question_answer_blocks:
        return None

    qa_blocks_sorted = sorted(question_answer_blocks, key=lambda bbox: bbox[1])
    page_width = page.rect.width
    page_height = page.rect.height
    margin = 10

    # Collect all potential gaps with metadata
    potential_gaps = _find_potential_gaps(qa_blocks_sorted, page_height, margin)

    # Adjust for footer content
    effective_page_bottom = _calculate_effective_bottom(
        qa_blocks_sorted, all_page_text_bboxes, page_height, margin
    )

    # Add bottom gap if space available
    if qa_blocks_sorted[-1][3] < effective_page_bottom:
        gap_start_y = qa_blocks_sorted[-1][3] + margin
        gap_end_y = effective_page_bottom

        if gap_end_y > gap_start_y:
            gap_size = gap_end_y - gap_start_y
            potential_gaps.append({
                "size": gap_size,
                "start": gap_start_y,
                "end": gap_end_y,
                "type": "bottom",
                "priority": 1,
            })

    # Filter and select best gap
    valid_gaps = [gap for gap in potential_gaps if gap["size"] >= 100]

    if not valid_gaps:
        print("🧠 ⚠️ No gaps larger than 100px found")
        return None

    # Sort by priority first, then by size (descending)
    valid_gaps.sort(key=lambda g: (-g["priority"], -g["size"]))

    best_gap = valid_gaps[0]
    print(
        f"🧠 ✅ Selected {best_gap['type']} gap: {best_gap['size']:.0f}px "
        f"(priority {best_gap['priority']})"
    )

    # Calculate horizontal bounds
    left_bound, right_bound = _calculate_horizontal_bounds(
        qa_blocks_sorted, best_gap, page_width, margin
    )

    if right_bound <= left_bound:
        print("🧠 ⚠️ No valid horizontal space for image")
        return None

    image_bbox = [left_bound, best_gap["start"], right_bound, best_gap["end"]]
    width = right_bound - left_bound
    height = best_gap["end"] - best_gap["start"]

    print(f"🧠 ✅ Constructed image bbox: {image_bbox}, size: {width:.0f}x{height:.0f}")
    return image_bbox


def _find_potential_gaps(
    qa_blocks_sorted: list[list[float]], page_height: float, margin: float
) -> list[dict[str, Any]]:
    """Find potential gaps between Q&A blocks."""
    potential_gaps: list[dict[str, Any]] = []

    # Check gap from top of page to first block
    if qa_blocks_sorted[0][1] > margin:
        gap_size = qa_blocks_sorted[0][1] - margin
        potential_gaps.append({
            "size": gap_size,
            "start": margin,
            "end": qa_blocks_sorted[0][1] - margin,
            "type": "top",
            "priority": 2,
        })

    # Check gaps between consecutive blocks
    for i in range(len(qa_blocks_sorted) - 1):
        current_bottom = qa_blocks_sorted[i][3]
        next_top = qa_blocks_sorted[i + 1][1]
        gap_size = next_top - current_bottom
        potential_gaps.append({
            "size": gap_size,
            "start": current_bottom + margin,
            "end": next_top - margin,
            "type": "between",
            "priority": 3,
        })

    return potential_gaps


def _calculate_effective_bottom(
    qa_blocks_sorted: list[list[float]],
    all_page_text_bboxes: list[list[float]],
    page_height: float,
    margin: float,
) -> float:
    """Calculate effective page bottom considering footer content."""
    effective_page_bottom = page_height - margin
    last_qa_block_bottom = qa_blocks_sorted[-1][3]

    for text_bbox in all_page_text_bboxes:
        # Consider text blocks strictly below the last QA block
        if text_bbox[1] > last_qa_block_bottom + (margin / 2):
            potential_new_bottom = text_bbox[1] - margin
            if potential_new_bottom < effective_page_bottom:
                effective_page_bottom = potential_new_bottom

    return effective_page_bottom


def _calculate_horizontal_bounds(
    qa_blocks_sorted: list[list[float]],
    best_gap: dict[str, Any],
    page_width: float,
    margin: float,
) -> tuple[float, float]:
    """Calculate horizontal bounds for image bbox."""
    left_bound = margin
    right_bound = page_width - margin

    # Adjust for overlapping blocks
    for bbox in qa_blocks_sorted:
        if not (bbox[3] <= best_gap["start"] or bbox[1] >= best_gap["end"]):
            if bbox[0] > page_width / 2:
                right_bound = min(right_bound, bbox[0] - margin)
            else:
                left_bound = max(left_bound, bbox[2] + margin)

    return left_bound, right_bound


def detect_potential_image_areas(
    page: fitz.Page, text_blocks: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Detect potential image areas by looking for large empty spaces between text blocks."""
    potential_images: list[dict[str, Any]] = []
    page_width = page.rect.width

    text_bboxes: list[list[float]] = []
    for block in text_blocks:
        if block.get("type") == 0:
            bbox = block.get("bbox", [])
            if len(bbox) >= 4:
                text_bboxes.append(bbox)

    if not text_bboxes:
        return potential_images

    text_bboxes.sort(key=lambda bbox: bbox[1])

    for i in range(len(text_bboxes) - 1):
        current_bottom = text_bboxes[i][3]
        next_top = text_bboxes[i + 1][1]
        gap_height = next_top - current_bottom

        if gap_height > 50:
            margin = 20
            potential_bbox = [
                margin,
                current_bottom + 5,
                page_width - margin,
                next_top - 5,
            ]

            area_width = potential_bbox[2] - potential_bbox[0]
            area_height = potential_bbox[3] - potential_bbox[1]
            area = area_width * area_height

            if area > 5000 and area_width > 100 and area_height > 50:
                print(
                    f"📸 Potential image area detected: {potential_bbox}, "
                    f"size: {area_width:.1f}x{area_height:.1f}"
                )
                potential_images.append({
                    "type": 1,
                    "bbox": potential_bbox,
                    "number": f"fallback_{len(potential_images) + 1}",
                })

    return potential_images
