"""
Choice Region Utilities

Functions for finding and calculating bounding box regions for answer choices
in multiple choice questions with diagram options. Handles spatial analysis,
boundary calculation, and region creation.
"""

from __future__ import annotations

import re
from typing import Any

import fitz  # type: ignore


def find_choice_regions(
    page: fitz.Page,
    text_blocks: list[dict[str, Any]],
    ai_categories: dict[int, str] | None = None
) -> list[dict[str, Any]]:
    """
    Find the bounding box regions for each answer choice using spatial grouping.

    Strategy:
    1. Find all potential choice labels (letters/numbers)
    2. For each choice label, find nearby text blocks that are part of the same choice
    3. Create bounding boxes that encompass the choice label AND its diagram text

    Args:
        page: PDF page object
        text_blocks: All text blocks from the page
        ai_categories: AI categorization of text blocks

    Returns:
        List of choice region dictionaries with bbox, letter, and metadata
    """
    choice_regions = []

    # Find question/answer text to avoid
    qa_blocks = []
    all_text_blocks = []  # All blocks with their metadata

    for i, block in enumerate(text_blocks):
        if block.get("type") != 0:  # Only text blocks
            continue

        block_bbox = block.get("bbox")
        if not block_bbox or len(block_bbox) < 4:
            continue

        block_num = i + 1
        category = ai_categories.get(block_num) if ai_categories else None

        # Extract text to look for choice labels
        block_text = _extract_block_text(block)

        block_info = {
            'block_num': block_num,
            'bbox': block_bbox,
            'text': block_text,
            'category': category,
            'is_choice_label': False,
            'choice_letter': None
        }

        # Categorize main question/answer blocks to avoid
        if category == "question_text":
            qa_blocks.append(block_bbox)
        elif category == "answer_choice" and len(block_text) > 20:
            # Only avoid answer_choice blocks that are clearly full answer text
            qa_blocks.append(block_bbox)

        # Check if this block contains a choice label
        _detect_choice_label(block_info, category, block_text)

        all_text_blocks.append(block_info)

    # Find choice labels
    choice_labels = [block for block in all_text_blocks if block['is_choice_label']]

    print(f"🎯 Found {len(qa_blocks)} Q&A blocks, {len(all_text_blocks)} total text blocks")
    print(f"🎯 Found {len(choice_labels)} choice labels: {[c['choice_letter'] for c in choice_labels]}")

    if not choice_labels:
        print("🎯 No choice labels found, cannot create choice regions without fallback.")
        return []

    # Sort choice labels by position (top to bottom, left to right)
    choice_labels.sort(key=lambda c: (c['bbox'][1], c['bbox'][0]))

    # Process choices sequentially to ensure proper non-overlapping boundaries
    previous_choice_bottom = 0  # Start from top of page

    for i, choice_label_block in enumerate(choice_labels):
        letter = choice_label_block['choice_letter']
        label_bbox = choice_label_block['bbox']

        # Calculate spatial boundaries imposed by neighboring choices
        boundaries = calculate_choice_boundaries(i, choice_labels, page)

        # Override top boundary to start after previous choice (if not first choice)
        if i > 0:
            boundaries['top'] = previous_choice_bottom + 5

        # Find all text blocks that are part of this choice's diagram
        choice_related_blocks = find_blocks_near_choice_constrained(
            choice_label_block, all_text_blocks, qa_blocks, boundaries
        )

        # Create a region that encompasses all related blocks
        region_bbox = create_comprehensive_choice_bbox(choice_related_blocks, page)

        if region_bbox:
            choice_regions.append({
                'choice_letter': letter,
                'bbox': region_bbox,
                'label_bbox': label_bbox,
                'related_blocks': len(choice_related_blocks),
                'boundaries': boundaries
            })
            print(
                f"🎯 Choice {letter}: found {len(choice_related_blocks)} "
                f"related blocks within boundaries {boundaries}"
            )

            # Update previous_choice_bottom for next iteration
            previous_choice_bottom = region_bbox[3]  # bottom coordinate

    # Sort by position (top to bottom, left to right)
    choice_regions.sort(key=lambda r: (r['bbox'][1], r['bbox'][0]))

    return choice_regions


def _extract_block_text(block: dict[str, Any]) -> str:
    """Extract all text from a block's lines and spans."""
    block_text = ""
    spans = block.get("lines", [])
    for line in spans:
        line_spans = line.get("spans", [])
        for span in line_spans:
            text = span.get("text", "").strip()
            block_text += " " + text
    return block_text.strip()


def _detect_choice_label(
    block_info: dict[str, Any],
    category: str | None,
    block_text: str
) -> None:
    """
    Detect if a block contains a choice label and update block_info in place.

    Uses AI categorization as priority, falls back to regex patterns.
    """
    # Priority 1: Use AI categorization if available
    if category == "answer_choice":
        choice_match = re.search(r'(?:^|\s)([A-Z]|[1-9])(?:[.,):;\s])', block_text.upper())
        if choice_match:
            block_info['is_choice_label'] = True
            block_info['choice_letter'] = choice_match.group(1)
            print(
                f"🎯 AI detected choice label '{choice_match.group(1)}' "
                f"in block {block_info['block_num']}: '{block_text}'"
            )
            return

    # Priority 2: Regex fallback
    # Match patterns like: "A. some text", "A some text", "A)", "B:", etc.
    # But exclude multi-part patterns like "Part A"
    if not re.search(r'\bpart\s+[a-z]', block_text, re.IGNORECASE):
        choice_match = re.search(r'(?:^|\s)([A-Z]|[1-9])(?:[.,):;]|\s+\w)', block_text.upper())
        if choice_match:
            block_info['is_choice_label'] = True
            block_info['choice_letter'] = choice_match.group(1)
            print(
                f"🎯 Regex detected choice label '{choice_match.group(1)}' "
                f"in block {block_info['block_num']}: '{block_text}'"
            )


def calculate_choice_boundaries(
    choice_index: int,
    choice_labels: list[dict[str, Any]],
    page: fitz.Page
) -> dict[str, float]:
    """
    Calculate spatial boundaries for a choice based on neighboring choices.

    Uses layout-aware logic: vertical constraints from neighbors,
    generous horizontal if no side neighbors.

    Args:
        choice_index: Index of the current choice in the sorted list
        choice_labels: All choice labels sorted by position
        page: PDF page object

    Returns:
        Dictionary with 'left', 'right', 'top', 'bottom' boundaries
    """
    current_choice = choice_labels[choice_index]
    current_bbox = current_choice['bbox']
    current_x0, current_y0, current_x1, current_y1 = current_bbox

    # Start with page boundaries
    boundaries = {
        'left': 0,
        'right': page.rect.width,
        'top': 0,
        'bottom': page.rect.height
    }

    # Track if we find neighbors in each direction
    has_left_neighbor = False
    has_right_neighbor = False

    # Adjust boundaries based on neighboring choices
    for i, other_choice in enumerate(choice_labels):
        if i == choice_index:
            continue

        other_bbox = other_choice['bbox']
        other_x0, other_y0, other_x1, other_y1 = other_bbox

        # Check for horizontal neighbors (side-by-side choices)
        vertical_overlap = not (other_y1 <= current_y0 or other_y0 >= current_y1)

        if other_x0 > current_x1 and vertical_overlap:  # Right neighbor
            boundaries['right'] = min(boundaries['right'], (other_x0 + current_x1) / 2)
            has_right_neighbor = True
        elif other_x1 < current_x0 and vertical_overlap:  # Left neighbor
            boundaries['left'] = max(boundaries['left'], (other_x1 + current_x0) / 2)
            has_left_neighbor = True

        # Check for vertical neighbors (stacked choices)
        horizontal_overlap = not (other_x1 <= current_x0 or other_x0 >= current_x1)

        if other_y0 > current_y1 and horizontal_overlap:  # Below
            boundaries['bottom'] = min(boundaries['bottom'], other_y0 - 10)
        elif other_y1 < current_y0 and horizontal_overlap:  # Above
            boundaries['top'] = max(boundaries['top'], other_y1 + 10)

    # For vertical layouts (no side neighbors), be more generous horizontally
    if not has_left_neighbor and not has_right_neighbor:
        boundaries['left'] = min(boundaries['left'], current_x0)
        boundaries['right'] = page.rect.width

    return boundaries


def find_blocks_near_choice_constrained(
    choice_label_block: dict[str, Any],
    all_text_blocks: list[dict[str, Any]],
    qa_blocks: list[list[float]],
    boundaries: dict[str, float]
) -> list[dict[str, Any]]:
    """
    Find text blocks that are spatially related to a choice label within given boundaries.

    Includes the choice label itself and nearby diagram text.

    Args:
        choice_label_block: The choice label block info
        all_text_blocks: All text blocks with metadata
        qa_blocks: Bounding boxes of question/answer blocks to avoid
        boundaries: Spatial boundaries for this choice

    Returns:
        List of related block info dictionaries
    """
    choice_bbox = choice_label_block['bbox']
    choice_x0, choice_y0, choice_x1, choice_y1 = choice_bbox
    choice_center_x = (choice_x0 + choice_x1) / 2
    choice_center_y = (choice_y0 + choice_y1) / 2

    related_blocks = [choice_label_block]  # Always include the choice label itself

    for block in all_text_blocks:
        if block == choice_label_block:
            continue

        # Skip main question/answer blocks
        if block['bbox'] in qa_blocks:
            continue

        # Skip other choice labels
        if block['is_choice_label']:
            continue

        block_bbox = block['bbox']
        block_x0, block_y0, block_x1, block_y1 = block_bbox
        block_center_x = (block_x0 + block_x1) / 2
        block_center_y = (block_y0 + block_y1) / 2

        # Check if block is within the boundaries
        if not (boundaries['left'] <= block_center_x <= boundaries['right'] and
                boundaries['top'] <= block_center_y <= boundaries['bottom']):
            continue

        # Check if it's likely diagram text
        if _is_likely_diagram_text(block['text']):
            horizontal_distance = abs(block_center_x - choice_center_x)
            vertical_distance = abs(block_center_y - choice_center_y)
            related_blocks.append(block)
            print(
                f"🎯   Found related block for {choice_label_block['choice_letter']}: "
                f"'{block['text']}' at ({horizontal_distance:.0f}, {vertical_distance:.0f})"
            )

    return related_blocks


def _is_likely_diagram_text(text: str) -> bool:
    """
    Determine if text is likely a diagram label.

    Pattern-based detection:
    1. Short text (likely labels, not full sentences)
    2. Contains mostly letters/numbers (not punctuation heavy)
    3. Exclude obvious non-diagram text patterns
    """
    text = text.strip()
    return (
        len(text) <= 20 and  # Short labels
        len(text.split()) <= 3 and  # Max 3 words
        not text.endswith('.') and  # Not a sentence
        not text.startswith('(') and  # Not parenthetical notes
        not any(
            word in text.lower()
            for word in ['question', 'answer', 'choice', 'option', 'select']
        ) and
        re.search(r'[a-zA-Z]', text) is not None  # Contains letters
    )


def create_comprehensive_choice_bbox(
    related_blocks: list[dict[str, Any]],
    page: fitz.Page
) -> list[float] | None:
    """
    Create a bounding box that encompasses all blocks related to a choice.

    Excludes the choice label itself to prevent text overlap.

    Args:
        related_blocks: List of block info dictionaries
        page: PDF page object

    Returns:
        Bounding box as [x0, y0, x1, y1] or None if invalid
    """
    if not related_blocks:
        return None

    # Filter out choice labels - only include diagram elements
    diagram_blocks = [
        block for block in related_blocks
        if not block.get('is_choice_label', False)
    ]

    if not diagram_blocks:
        return None

    # Find the overall bounding box of diagram blocks only
    min_x = float('inf')
    min_y = float('inf')
    max_x = float('-inf')
    max_y = float('-inf')

    for block in diagram_blocks:
        bbox = block['bbox']
        x0, y0, x1, y1 = bbox

        min_x = min(min_x, x0)
        min_y = min(min_y, y0)
        max_x = max(max_x, x1)
        max_y = max(max_y, y1)

    # Add padding around the combined region
    padding = 20
    final_x0 = max(0, min_x - padding)
    final_y0 = max(0, min_y - padding)
    final_x1 = min(page.rect.width, max_x + padding)
    final_y1 = min(page.rect.height, max_y + padding)

    # Validate the region
    if final_x1 <= final_x0 or final_y1 <= final_y0:
        return None

    if (final_x1 - final_x0) < 30 or (final_y1 - final_y0) < 30:
        return None

    return [final_x0, final_y0, final_x1, final_y1]
