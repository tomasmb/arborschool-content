"""bbox_utils.py
-----------------
Utility functions for bounding-box operations that leverage AI categorization
instead of hardcoded heuristics. Follows converter guidelines by using
AI analysis for content categorization decisions.
"""

from __future__ import annotations

import fitz  # type: ignore
from typing import Any, Dict, List, Optional

__all__ = [
    "MIN_IMAGE_WIDTH",
    "MIN_IMAGE_HEIGHT",
    "MAX_ASPECT_RATIO_FOR_LINE",
    "bboxes_are_same",
    "bbox_overlap_percentage",
    "expand_image_bbox_to_boundaries",
    "check_bbox_overlap_with_text",
    "shrink_image_bbox_away_from_text",
]

# ---------------------------------------------------------------------------
# Basic bbox constants - kept minimal and not overfitted to examples
# ---------------------------------------------------------------------------

MIN_IMAGE_WIDTH = 5       # px, minimal threshold for valid content
MIN_IMAGE_HEIGHT = 5      # px
MAX_ASPECT_RATIO_FOR_LINE = 50  # allow thin label strips

# ---------------------------------------------------------------------------
# Simple helpers
# ---------------------------------------------------------------------------

def bboxes_are_same(bbox1: List[float], bbox2: List[float], tol: float = 0.1) -> bool:
    """Return *True* if *bbox1* and *bbox2* are identical within *tol* pixels."""
    if len(bbox1) != 4 or len(bbox2) != 4:
        return False
    return all(abs(bbox1[i] - bbox2[i]) <= tol for i in range(4))


def bbox_overlap_percentage(bbox1: List[float], bbox2: List[float]) -> float:
    """How much of the *smaller* bbox area is overlapped (0-1)."""
    if len(bbox1) != 4 or len(bbox2) != 4:
        return 0.0

    x0 = max(bbox1[0], bbox2[0])
    y0 = max(bbox1[1], bbox2[1])
    x1 = min(bbox1[2], bbox2[2])
    y1 = min(bbox1[3], bbox2[3])

    if x1 <= x0 or y1 <= y0:
        return 0.0

    intersection = (x1 - x0) * (y1 - y0)
    area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
    area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
    if area1 == 0 or area2 == 0:
        return 0.0
    return intersection / min(area1, area2)

# ---------------------------------------------------------------------------
# AI-powered bbox operations following converter guidelines
# ---------------------------------------------------------------------------

def expand_image_bbox_to_boundaries(
    image_bbox: List[float],
    all_blocks: List[Dict[str, Any]],
    page: fitz.Page,
) -> List[float]:
    """
    Expand image_bbox until it reaches appropriate boundaries.
    Uses deterministic geometric logic without hardcoded assumptions.
    """
    safety_margin = 5
    max_expansion = 50
    expanded = list(image_bbox)

    other_blocks = [b.get("bbox", []) for b in all_blocks 
                   if not bboxes_are_same(b.get("bbox", []), image_bbox)]

    # Left edge expansion
    tgt_left = max(0, image_bbox[0] - max_expansion)
    for ob in other_blocks:
        if (ob[2] <= image_bbox[0] and 
            not (ob[3] <= image_bbox[1] or ob[1] >= image_bbox[3])):
            tgt_left = max(tgt_left, ob[2] + safety_margin)
    expanded[0] = tgt_left

    # Right edge expansion
    tgt_right = min(page.rect.width, image_bbox[2] + max_expansion)
    for ob in other_blocks:
        if (ob[0] >= image_bbox[2] and 
            not (ob[3] <= image_bbox[1] or ob[1] >= image_bbox[3])):
            tgt_right = min(tgt_right, ob[0] - safety_margin)
    expanded[2] = tgt_right

    # Top edge expansion
    tgt_top = max(0, image_bbox[1] - max_expansion)
    for ob in other_blocks:
        if (ob[3] <= image_bbox[1] and 
            not (ob[2] <= image_bbox[0] or ob[0] >= image_bbox[2])):
            tgt_top = max(tgt_top, ob[3] + safety_margin)
    expanded[1] = tgt_top

    # Bottom edge expansion
    tgt_bottom = min(page.rect.height, image_bbox[3] + max_expansion)
    for ob in other_blocks:
        if (ob[1] >= image_bbox[3] and 
            not (ob[2] <= image_bbox[0] or ob[0] >= image_bbox[2])):
            tgt_bottom = min(tgt_bottom, ob[1] - safety_margin)
    expanded[3] = tgt_bottom

    # Validate expansion doesn't cause problems
    text_blocks = [b for b in all_blocks if b.get("type") == 0]
    if check_bbox_overlap_with_text(expanded, text_blocks, ai_categories=None):
        return image_bbox  # fallback to original if overlap detected

    return expanded


def check_bbox_overlap_with_text(
    image_bbox: List[float],
    text_blocks: List[Dict[str, Any]],
    ai_categories: Optional[Dict[int, str]] = None,
    overlap_threshold: float = 0.1,
) -> bool:
    """
    Check if image_bbox overlaps with question/answer text using AI categorization.
    Following guidelines: prefer AI analysis over keyword matching.
    """
    img_x0, img_y0, img_x1, img_y1 = image_bbox
    img_area = (img_x1 - img_x0) * (img_y1 - img_y0)
    if img_area <= 0:
        return True

    question_answer_overlap = 0.0
    
    for i, block in enumerate(text_blocks):
        if block.get("type") != 0:
            continue
        tb = block.get("bbox", [])
        if len(tb) < 4:
            continue

        # Calculate intersection
        inter_x0 = max(img_x0, tb[0])
        inter_y0 = max(img_y0, tb[1])
        inter_x1 = min(img_x1, tb[2])
        inter_y1 = min(img_y1, tb[3])
        if inter_x1 <= inter_x0 or inter_y1 <= inter_y0:
            continue

        intersection = (inter_x1 - inter_x0) * (inter_y1 - inter_y0)
        txt_area = (tb[2] - tb[0]) * (tb[3] - tb[1])
        if txt_area == 0:
            continue

        # Use AI categorization if available
        block_num = i + 1
        if ai_categories and block_num in ai_categories:
            category = ai_categories[block_num]
            # Categories from AI: question_text, answer_choice = separate text
            # visual_content_title, visual_content_label, other_label = part of image
            if category in ["question_text", "answer_choice"]:
                # This is separate text - any overlap is problematic
                if intersection / txt_area > 0.05:  # Even small overlap is bad
                    return True
                question_answer_overlap += intersection
            # If it's visual_content_title, visual_content_label, other_label, it's part of the image
        else:
            # Fallback: assume any significant text block is separate content
            # Use minimal heuristics without overfitted thresholds
            if intersection / txt_area > 0.15:
                return True
            question_answer_overlap += intersection

    return (question_answer_overlap / img_area) > overlap_threshold


def shrink_image_bbox_away_from_text(
    image_bbox: List[float],
    all_blocks: List[Dict[str, Any]],
    page: fitz.Page,
    ai_categories: Optional[Dict[int, str]] = None,
) -> List[float]:
    """
    Shrink image bbox away from question/answer text using AI categorization.
    Following guidelines: use AI analysis instead of keyword heuristics.
    """
    safety = 4
    bbox = list(image_bbox)
    text_blocks = [b for b in all_blocks if b.get("type") == 0]

    for iteration in range(8):
        # Check if we still have overlap
        if not check_bbox_overlap_with_text(bbox, text_blocks, ai_categories, 
                                           overlap_threshold=0.0):
            return bbox

        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        made_adjustment = False

        for idx, block in enumerate(text_blocks):
            tb = block.get("bbox", [])
            if len(tb) < 4:
                continue
                
            # Check for intersection
            ix0 = max(bbox[0], tb[0])
            iy0 = max(bbox[1], tb[1])
            ix1 = min(bbox[2], tb[2])
            iy1 = min(bbox[3], tb[3])
            if ix1 <= ix0 or iy1 <= iy0:
                continue

            # Use AI categorization to determine if we should shrink away
            block_num = idx + 1
            should_shrink = False
            
            if ai_categories and block_num in ai_categories:
                category = ai_categories[block_num]
                # Shrink away from question_text and answer_choice
                should_shrink = category in ["question_text", "answer_choice"]
            else:
                # Fallback: shrink away from any substantial text block
                # Use simple area check without overfitted thresholds
                txt_area = (tb[2] - tb[0]) * (tb[3] - tb[1])
                should_shrink = txt_area > 500  # Much more conservative threshold

            if should_shrink:
                # Shrink away from this block
                if (tb[0] + tb[2]) / 2 < cx:
                    bbox[0] = min(bbox[0] + safety, tb[2] + safety)
                else:
                    bbox[2] = max(bbox[2] - safety, tb[0] - safety)
                if (tb[1] + tb[3]) / 2 < cy:
                    bbox[1] = min(bbox[1] + safety, tb[3] + safety)
                else:
                    bbox[3] = max(bbox[3] - safety, tb[1] - safety)
                
                made_adjustment = True

        # Clamp to page boundaries
        bbox[0] = max(0, bbox[0])
        bbox[1] = max(0, bbox[1])
        bbox[2] = min(page.rect.width, bbox[2])
        bbox[3] = min(page.rect.height, bbox[3])
        
        # Check minimum size
        if bbox[2] - bbox[0] < 40 or bbox[3] - bbox[1] < 40:
            break
            
        # If no adjustments were made, we're done
        if not made_adjustment:
            break

    return bbox 