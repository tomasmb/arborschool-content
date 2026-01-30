"""
Utility functions for prompt choice separator.

This module contains utility functions used by other modules in the
prompt choice separator system.
"""

from typing import Any, Dict, List

import fitz  # type: ignore


def get_page_image(page: fitz.Page, scale: float = 1.5) -> bytes:
    """Get page image for LLM analysis."""
    matrix = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    return pix.tobytes("png")


def get_block_text_from_bbox(page: fitz.Page, bbox: List[float]) -> str:
    """Get text content from a specific bbox area."""
    try:
        text_rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
        text = page.get_text("text", clip=text_rect)
        return text.strip()
    except Exception:
        return ""


def extract_choice_identifier(text: str, block_index: int) -> str:
    """
    Extract choice identifier from text - but since LLM already categorized this as answer_choice,
    we can be more flexible and just use the first meaningful character or a sequential identifier.
    """
    text = text.strip()

    # Simple approach: just take the first alphanumeric character
    # The LLM already knows this is a choice, so we don't need complex parsing
    for char in text:
        if char.isalnum():
            return char.upper()

    # If no alphanumeric found, use sequential numbering based on position
    # This handles cases like "First choice", "Option one", etc.
    choice_labels = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
    if block_index < len(choice_labels):
        return choice_labels[block_index]

    return f"Choice{block_index + 1}"


def bbox_overlap_area(bbox1: List[float], bbox2: List[float]) -> float:
    """Calculate the overlapping area between two bounding boxes."""
    x1 = max(bbox1[0], bbox2[0])
    y1 = max(bbox1[1], bbox2[1])
    x2 = min(bbox1[2], bbox2[2])
    y2 = min(bbox1[3], bbox2[3])

    if x2 <= x1 or y2 <= y1:
        return 0.0

    return (x2 - x1) * (y2 - y1)


def detect_mixed_choice_content(text: str, bbox: List[float], choice_identifier: str) -> List[Dict[str, Any]]:
    """
    Since we're now always including the choice text block in the image,
    we always need to mask the choice letter to keep only the visual content clean.
    """
    mask_areas = []

    # Always mask the choice identifier since we're including the choice text block
    choice_letter_pos = text.lower().find(choice_identifier.lower())
    if choice_letter_pos >= 0:
        # More precise estimation: only mask the exact choice letter area
        # Look for the choice letter at the beginning of the text (most common case)
        text_stripped = text.strip()

        if text_stripped.lower().lstrip().startswith(choice_identifier.lower()):
            # Choice letter is at the start - mask just the beginning
            # Estimate based on typical choice formats: "A.", "A)", "A ", etc.

            # Find where the choice identifier ends (look for punctuation or space)
            identifier_end = len(choice_identifier)
            if identifier_end < len(text_stripped):
                next_char = text_stripped[identifier_end]
                if next_char in '.):':
                    identifier_end += 1  # Include the punctuation

            # Calculate a more conservative mask area
            total_width = bbox[2] - bbox[0]
            char_count = len(text_stripped)

            if char_count > 0:
                # More conservative: only mask the choice identifier + punctuation
                mask_chars = identifier_end
                char_width = total_width / char_count
                mask_width = char_width * mask_chars + 5  # Small buffer

                # Ensure we don't mask too much
                max_mask_width = total_width * 0.2  # Never mask more than 20% of the text width
                mask_width = min(mask_width, max_mask_width)

                mask_area = {
                    "bbox": [bbox[0], bbox[1], bbox[0] + mask_width, bbox[3]],
                    "text_to_mask": text_stripped[:identifier_end],
                    "reason": "precise_choice_letter_masking"
                }
                mask_areas.append(mask_area)

                print(f"🎭 Will precisely mask '{text_stripped[:identifier_end]}' (width: {mask_width:.1f}px)")
            else:
                print(f"🎭 Cannot estimate mask area for '{choice_identifier}' - text too short")
        else:
            print(f"🎭 Choice identifier '{choice_identifier}' not at text start, skipping mask")

    return mask_areas
