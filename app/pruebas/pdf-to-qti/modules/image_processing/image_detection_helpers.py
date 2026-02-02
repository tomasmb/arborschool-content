"""Helper functions for image detection.

Provides text extraction and categorization processing utilities.
"""

from __future__ import annotations

from typing import Any


def extract_all_text_from_blocks(text_blocks: list[dict[str, Any]]) -> str:
    """Extract all text from blocks for analysis."""
    all_text = ""
    for block in text_blocks:
        if block.get("type") == 0:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    all_text += span.get("text", "") + " "
    return all_text.strip()


def use_conservative_visual_indicators(text_blocks: list[dict[str, Any]]) -> bool:
    """Conservative fallback using minimal indicators."""
    all_text = extract_all_text_from_blocks(text_blocks).lower()
    # Use minimal, non-overfitted indicators
    indicators = ["map", "diagram", "chart", "graph", "figure", "image", "shown", "displays"]
    return any(indicator in all_text for indicator in indicators)


def prepare_block_info_for_ai(text_blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prepare block information for AI analysis."""
    block_info = []
    for i, block in enumerate(text_blocks):
        if block.get("type") != 0:
            continue
        bbox = block.get("bbox", [])
        if len(bbox) < 4:
            continue

        block_text = ""
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                block_text += span.get("text", "") + " "
        block_text = block_text.strip()

        if block_text:
            text_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
            block_info.append(
                {
                    "block_number": i + 1,
                    "text": block_text,
                    "bbox": bbox,
                    "area": text_area,
                }
            )

    return block_info


def process_ai_categorization(analysis: Any, text_blocks: list[dict[str, Any]]) -> dict[str, Any]:
    """Process AI categorization results into usable format."""
    question_answer_blocks: list[list[float]] = []
    strict_label_bboxes: list[list[float]] = []
    other_label_bboxes: list[list[float]] = []
    all_image_associated_text_bboxes: list[list[float]] = []
    ai_categories: dict[int, str] = {}

    # Create mapping from prepared block_number to original block index
    prepared_to_original_map: dict[int, int] = {}
    current_prepared_idx = 1
    for i, block in enumerate(text_blocks):
        if block.get("type") != 0:
            continue
        bbox = block.get("bbox", [])
        if len(bbox) < 4:
            continue
        block_text = ""
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                block_text += span.get("text", "") + " "
        if block_text.strip():
            prepared_to_original_map[current_prepared_idx] = i
            current_prepared_idx += 1

    for cat_info in analysis.text_block_categories:
        ai_block_num = cat_info.block_number
        category = cat_info.category

        original_block_idx = prepared_to_original_map.get(ai_block_num)
        if original_block_idx is None:
            print(f"🧠 ⚠️ AI category for unknown block number {ai_block_num}, skipping.")
            continue

        ai_categories[ai_block_num] = category
        block = text_blocks[original_block_idx]
        bbox = block.get("bbox")

        if category in ["question_text", "answer_choice"]:
            question_answer_blocks.append(bbox)
            print(f"🧠 Block {ai_block_num} ({category}): separate text")
        elif category in ["visual_content_title", "visual_content_label"]:
            strict_label_bboxes.append(bbox)
            all_image_associated_text_bboxes.append(bbox)
            print(f"🧠 Block {ai_block_num} ({category}): strict image label")
        elif category == "other_label":
            other_label_bboxes.append(bbox)
            all_image_associated_text_bboxes.append(bbox)
            print(f"🧠 Block {ai_block_num} ({category}): other label (image part or footer?)")
        else:
            all_image_associated_text_bboxes.append(bbox)
            print(f"🧠 Block {ai_block_num} ({category}): unknown category, assumed image part")

    return {
        "question_answer_blocks": question_answer_blocks,
        "strict_label_bboxes": strict_label_bboxes,
        "other_label_bboxes": other_label_bboxes,
        "all_image_associated_text_bboxes": all_image_associated_text_bboxes,
        "ai_categories": ai_categories,
    }
