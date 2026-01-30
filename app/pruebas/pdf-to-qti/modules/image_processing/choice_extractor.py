"""
Choice image extractor.

This module contains functions for extracting individual choice images
from answer choices in educational materials.
"""

from typing import Any, Dict, List

import fitz  # type: ignore

from .utils import detect_mixed_choice_content, extract_choice_identifier, get_block_text_from_bbox


def extract_choice_images(
    page: fitz.Page,
    text_blocks: List[Dict[str, Any]],
    block_categories: Dict[int, str],
    all_text_bboxes: List[List[float]],
    question_answer_blocks: List[List[float]],
    choice_image_labels: List[List[float]]
) -> Dict[str, Any]:
    """
    Extract individual choice images by finding visual areas around each answer choice block.

    For each answer choice (A, B, C, D), look for visual content below or around it.
    """
    print("🔍 🎯 EXTRACTING CHOICE IMAGES")

    choice_bboxes = []
    page_width = page.rect.width
    page_height = page.rect.height

    # Dynamic margins based on page size
    margin = max(10, min(page_width, page_height) * 0.02)  # 2% of smaller dimension, min 10px

    # Find all answer choice blocks
    choice_blocks = []
    for block_num, category in block_categories.items():
        if category == "answer_choice":
            if block_num <= len(text_blocks):
                original_block = text_blocks[block_num - 1]
                if original_block.get("type") == 0:
                    bbox = original_block.get("bbox")
                    if bbox and len(bbox) == 4:
                        choice_blocks.append({
                            "block_num": block_num,
                            "bbox": bbox,
                            "text": get_block_text_from_bbox(page, bbox)
                        })

    print(f"🔍 📋 Found {len(choice_blocks)} answer choice blocks")

    if not choice_blocks:
        return {"extracted_images": [], "total_choices_found": 0}

    # --- Start of new layout-aware boundary logic ---

    # 1. Sort choices by their actual choice letter (A, B, C, D) instead of spatial position
    # This ensures correct ordering even when spatial extraction is inconsistent
    if len(choice_blocks) > 1:
        # Extract choice identifier for each block first
        for choice_block in choice_blocks:
            choice_identifier = extract_choice_identifier(choice_block['text'], 0)  # index not used in current implementation
            choice_block['choice_identifier'] = choice_identifier

        # Sort by choice identifier (A, B, C, D)
        choice_blocks.sort(key=lambda cb: cb.get('choice_identifier', 'Z'))

    print("🔍 📋 Choice blocks in reading order:")
    for i, choice_block in enumerate(choice_blocks):
        choice_id = choice_block.get('choice_identifier', 'Unknown')
        print(f"🔍   {i+1}. Block {choice_block['block_num']}: '{choice_block['text'].strip()}' -> Choice {choice_id}")

    # 2. Detect layout type (Vertical vs. Grid).
    x_coords = [(cb['bbox'][0] + cb['bbox'][2]) / 2 for cb in choice_blocks]
    x_std_dev = (sum([(x - sum(x_coords) / len(x_coords))**2 for x in x_coords]) / len(x_coords))**0.5
    layout_type = "Vertical" if x_std_dev < (page_width * 0.1) else "Grid"
    print(f"🔍 🧐 Detected layout type: {layout_type} (X-coord std dev: {x_std_dev:.1f})")

    # 3. Apply layout-specific rules to calculate bounding boxes.
    for i, choice_block in enumerate(choice_blocks):
        block_num = choice_block["block_num"]
        block_bbox = choice_block["bbox"]
        block_text = choice_block["text"]

        print(f"🔍 🎯 Processing choice {i+1}: Block {block_num}")

        choice_image_bbox = None
        if layout_type == "Vertical":
            # --- Definitive Vertical Layout Logic ---

            # 1. Top of image area starts at the top of the choice text block itself.
            top = block_bbox[1]

            # 2. Left and right are full page width to capture wide diagrams.
            left = margin
            right = page_width - margin

            # 3. Bottom of image area is the top of the next choice's text block.
            if i < len(choice_blocks) - 1:
                bottom = choice_blocks[i+1]['bbox'][1] - margin
            else:
                # For the last choice, find the footer and end before it.
                footer_y_start = page_height
                for block in all_text_bboxes:
                    # A footer block is typically low on the page.
                    if block[1] > (page_height * 0.9):
                         footer_y_start = min(footer_y_start, block[1])
                bottom = footer_y_start - margin

            choice_image_bbox = [left, top, right, bottom]

        else: # Grid Layout
            # The existing quadrant-based logic is robust for grid layouts.
            x_coords = sorted([(cb['bbox'][0] + cb['bbox'][2]) / 2 for cb in choice_blocks])
            y_coords = sorted([(cb['bbox'][1] + cb['bbox'][3]) / 2 for cb in choice_blocks])
            median_x = x_coords[len(x_coords) // 2]
            median_y = y_coords[len(y_coords) // 2]

            def get_quadrant(bbox):
                x = (bbox[0] + bbox[2]) / 2; y = (bbox[1] + bbox[3]) / 2
                if y < median_y: return "top_left" if x < median_x else "top_right"
                else: return "bottom_left" if x < median_x else "bottom_right"

            choice_in_quadrant = {get_quadrant(cb['bbox']): cb for cb in choice_blocks}

            visual_labels_by_choice = {cb['block_num']: [] for cb in choice_blocks}

            print(f"🔍 🔬 Analyzing {len(choice_image_labels)} choice-specific labels...")
            for label_bbox in choice_image_labels:
                label_quadrant = get_quadrant(label_bbox)
                if (target_choice := choice_in_quadrant.get(label_quadrant)):
                    visual_labels_by_choice[target_choice['block_num']].append(label_bbox)

            associated_labels = visual_labels_by_choice.get(block_num, [])

            print(f"🔍 🔬 Associating visual labels with choice {i+1} (Block {block_num}):")
            if not associated_labels:
                print("🔍      No labels associated.")
            for label_idx, label_bbox in enumerate(associated_labels):
                label_text = get_block_text_from_bbox(page, label_bbox).replace('\n', ' ')
                print(f"🔍      - Label {label_idx+1}: '{label_text}'")

            all_content_bboxes = [block_bbox] + associated_labels
            if not all_content_bboxes: continue

            # --- Adaptive Padding Logic ---
            content_min_x = min(b[0] for b in all_content_bboxes)
            content_min_y = min(b[1] for b in all_content_bboxes)
            content_max_x = max(b[2] for b in all_content_bboxes)
            content_max_y = max(b[3] for b in all_content_bboxes)

            # --- Find top boundary to prevent capturing question text ---
            top_boundary = margin
            q_blocks_above = [b for b in question_answer_blocks if b[3] < content_min_y]
            if q_blocks_above:
                closest_q_block = max(q_blocks_above, key=lambda b: b[3])
                top_boundary = closest_q_block[3] + (margin / 2)
                print(f"🔍      Top boundary set by question text ending at {closest_q_block[3]:.1f}")

            # --- Find bottom boundary to prevent capturing text below ---
            bottom_boundary = page_height - margin
            # Consider both other choices and general Q&A text as potential boundaries
            all_potential_boundaries_below = [b for b in (question_answer_blocks + [cb['bbox'] for cb in choice_blocks]) if b[1] > content_max_y]
            if all_potential_boundaries_below:
                closest_boundary_below = min(all_potential_boundaries_below, key=lambda b: b[1])
                bottom_boundary = closest_boundary_below[1] - (margin / 2)
                print(f"🔍      Bottom boundary set by content starting at {closest_boundary_below[1]:.1f}")

            content_width = content_max_x - content_min_x
            content_height = content_max_y - content_min_y

            # Per user feedback, be more intelligent about horizontal boundaries
            print(f"🔍      Content box: w={content_width:.1f}, h={content_height:.1f}")

            top = content_min_y - margin
            if top < top_boundary:
                print(f"🔍      Correcting top from {top:.1f} to {top_boundary:.1f} to avoid capturing question text.")
                top = top_boundary

            # Start left boundary at the content edge, not with large padding
            left = content_min_x - margin
            # Initially extend right boundary generously; it will be clipped later
            right = page_width - margin
            # Use the structurally-determined floor for the bottom boundary
            bottom = bottom_boundary
            print(f"🔍      Setting bottom to structural boundary at {bottom_boundary:.1f}")

            choice_image_bbox = [left, top, right, bottom]
            print(f"🔍      Initial Bbox (structural boundaries): [{left:.1f}, {top:.1f}, {right:.1f}, {bottom:.1f}]")

        if choice_image_bbox:
            # Add boundary-aware clipping for grid layouts to prevent overlap
            if layout_type == "Grid":
                my_pos_in_reading_order = i
                # Simple but effective heuristic for 2-column grids
                is_left_column = my_pos_in_reading_order % 2 == 0

                if is_left_column and (my_pos_in_reading_order + 1) < len(choice_blocks):
                    next_choice_block = choice_blocks[my_pos_in_reading_order + 1]
                    # Ensure the next choice is actually to the right
                    if next_choice_block['bbox'][0] > choice_block['bbox'][0]:
                        right_boundary = next_choice_block['bbox'][0] - margin
                        if choice_image_bbox[2] > right_boundary:
                            print(f"🔍    CLIPPING right edge from {choice_image_bbox[2]:.1f} to {right_boundary:.1f} (boundary from choice {i+2})")
                            choice_image_bbox[2] = right_boundary
                        else:
                            print(f"🔍    Right edge {choice_image_bbox[2]:.1f} is already within boundary {right_boundary:.1f}")

            # Final clipping and validation
            choice_image_bbox[0] = max(0, choice_image_bbox[0])
            choice_image_bbox[1] = max(0, choice_image_bbox[1])
            choice_image_bbox[2] = min(page_width, choice_image_bbox[2])
            choice_image_bbox[3] = min(page_height, choice_image_bbox[3])

            choice_width = choice_image_bbox[2] - choice_image_bbox[0]
            choice_height = choice_image_bbox[3] - choice_image_bbox[1]

            min_width = max(50, page_width * 0.08)
            min_height = max(30, page_height * 0.04)

            if choice_width > min_width and choice_height > min_height:
                # Use pre-computed choice identifier to ensure consistency
                choice_identifier = choice_block.get('choice_identifier', extract_choice_identifier(block_text, i))
                text_mask_areas = detect_mixed_choice_content(block_text, block_bbox, choice_identifier)

                choice_info = { "bbox": choice_image_bbox, "choice_letter": choice_identifier, "description": f"Choice {choice_identifier} visual diagram", "block_num": block_num, "text_mask_areas": text_mask_areas }
                choice_bboxes.append(choice_info)

                print(f"🔍 ✅ Found choice image for {choice_info['choice_letter']}")
                print(f"🔍    Bbox: [{choice_image_bbox[0]:.1f}, {choice_image_bbox[1]:.1f}, {choice_image_bbox[2]:.1f}, {choice_image_bbox[3]:.1f}]")
                print(f"🔍    Size: {choice_width:.1f} x {choice_height:.1f}")
            else:
                print(f"🔍 ❌ Choice area too small: {choice_width:.1f} x {choice_height:.1f} (min: {min_width:.1f} x {min_height:.1f})")

    print("🔍 📊 CHOICE EXTRACTION SUMMARY:")
    print(f"🔍    Total choice blocks found: {len(choice_blocks)}")
    print(f"🔍    Choice images extracted: {len(choice_bboxes)}")

    return {
        "extracted_images": choice_bboxes,
        "total_choices_found": len(choice_blocks)
    }
