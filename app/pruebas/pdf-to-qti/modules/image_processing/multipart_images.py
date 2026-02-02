"""
Multi-part Question Image Processing

This module handles the special case where multi-part questions (Part A, B, C, etc.)
have images that belong to specific parts rather than the whole question.

Key features:
1. Detects if a question is multi-part
2. Uses specialized AI detection for part-specific images
3. Filters images to only include those relevant to parts with visual content
4. Avoids affecting regular questions without part-specific images
"""

import re
from typing import Any, Dict, List, Optional

import fitz


def detect_multipart_question_images(
    text_blocks: List[Dict[str, Any]],
    ai_categories: Optional[Dict[int, str]] = None,
    question_text: str = ""
) -> List[Dict[str, Any]]:
    """
    Detect if this is a multi-part question with part-specific images.

    This function works WITH the existing image detection pipeline to identify
    which images belong to which parts, rather than replacing it entirely.

    Args:
        text_blocks: All text blocks from PyMuPDF
        ai_categories: AI categorization of blocks
        question_text: Combined question text

    Returns:
        List of part info with image indicators, empty if not applicable
    """

    # Step 1: Check if this is a multi-part question
    if not _is_multipart_question(text_blocks, question_text):
        return []

    # Step 2: Check if any parts have visual content
    parts_with_visual_content = _find_parts_with_visual_references(text_blocks, question_text)

    if not parts_with_visual_content:
        return []

    print(f"🎯 Found parts with visual content: {parts_with_visual_content}")

    # Step 3: Return indication that this needs special AI detection
    return [{
        "needs_special_ai_detection": True,
        "parts_with_visuals": parts_with_visual_content,
        "method": "multipart_ai_detection"
    }]


def detect_part_specific_images_with_ai(
    page: fitz.Page,
    text_blocks: List[Dict[str, Any]],
    parts_with_visuals: List[str],
    openai_api_key: str
) -> List[Dict[str, Any]]:
    """
    Use AI to specifically locate images for parts that have visual content.

    This creates intelligent bboxes by finding text boundaries around visual content.

    Args:
        page: PyMuPDF page object
        text_blocks: All text blocks from the page
        parts_with_visuals: List of part names that have visual references
        openai_api_key: OpenAI API key

    Returns:
        List of detected image areas with part context
    """

    detected_images = []

    for part_name in parts_with_visuals:
        # Find text boundaries for this part's visual content
        bbox = _find_visual_content_boundaries(text_blocks, part_name)

        if bbox:
            page_rect = page.rect

            # Validate bbox is within page bounds
            if (0 <= bbox[0] < bbox[2] <= page_rect.width and
                0 <= bbox[1] < bbox[3] <= page_rect.height):

                detected_images.append({
                    "bbox": bbox,
                    "part_context": part_name,
                    "confidence": 0.9,  # High confidence for boundary-based detection
                    "description": f"Visual content for Part {part_name}",
                    "detection_method": "text_boundary",
                    "method_details": "area between text references"
                })

                print(f"📸 ✅ Text boundary detection for Part {part_name}: {bbox}")

    return detected_images


def _find_visual_content_boundaries(
    text_blocks: List[Dict[str, Any]],
    part_name: str
) -> Optional[List[float]]:
    """
    Find the boundaries of visual content by locating the text that references it
    and the text that follows it.

    Args:
        text_blocks: All text blocks from the page
        part_name: The part name (e.g., 'C') to find visual content for

    Returns:
        Bounding box [x1, y1, x2, y2] or None if not found
    """

    # Find the reference text (e.g., "the model shown", "diagram", etc.)
    reference_block = None
    follow_up_block = None

    # Patterns for visual content references
    reference_patterns = [
        r'the\s+model\s+shown',
        r'the\s+diagram\s+shows?',
        r'the\s+figure\s+shows?',
        r'the\s+image\s+shows?',
        r'shown\s+(?:in\s+)?(?:the\s+)?(?:model|diagram|figure)',
    ]

    # Patterns for follow-up text that uses the visual content
    followup_patterns = [
        r'based\s+on\s+the\s+(?:model|diagram|figure)',
        r'using\s+the\s+(?:model|diagram|figure)',
        r'from\s+the\s+(?:model|diagram|figure)',
        r'according\s+to\s+the\s+(?:model|diagram|figure)',
    ]

    for i, block in enumerate(text_blocks):
        if block.get("type") == 0:  # Text block
            block_text = _extract_block_text(block).lower()

            # Check if this block contains the visual reference
            if any(re.search(pattern, block_text) for pattern in reference_patterns):
                reference_block = block
                print(f"🎯 Found visual reference in block {i}: '{block_text[:60]}...'")

            # Check if this block contains follow-up text
            if any(re.search(pattern, block_text) for pattern in followup_patterns):
                follow_up_block = block
                print(f"🎯 Found follow-up text in block {i}: '{block_text[:60]}...'")

    # If we found both boundaries, create bbox between them
    if reference_block and follow_up_block:
        return _create_bbox_between_text_blocks(reference_block, follow_up_block, text_blocks)

    # Fallback: if we only found reference, look for a reasonable area below it
    elif reference_block:
        return _create_bbox_after_reference(reference_block, text_blocks)

    return None


def _create_bbox_between_text_blocks(
    reference_block: Dict[str, Any],
    follow_up_block: Dict[str, Any],
    all_blocks: List[Dict[str, Any]]
) -> List[float]:
    """
    Create a bounding box that captures the area between two text blocks.

    Args:
        reference_block: Block containing visual reference text
        follow_up_block: Block containing follow-up text that uses the visual
        all_blocks: All text blocks for context

    Returns:
        Bounding box [x1, y1, x2, y2]
    """

    ref_bbox = reference_block["bbox"]
    followup_bbox = follow_up_block["bbox"]

    # Get the page width by looking at all blocks
    page_x_min = min(block["bbox"][0] for block in all_blocks if block.get("type") == 0)
    page_x_max = max(block["bbox"][2] for block in all_blocks if block.get("type") == 0)

    # Find all text blocks that might be part of the reference section
    # Look for blocks that are close to the reference block vertically
    reference_end_y = ref_bbox[3]
    related_blocks = []

    for block in all_blocks:
        if block.get("type") == 0:  # Text block
            block_bbox = block["bbox"]
            # Include blocks that are within reasonable distance of the reference
            if abs(block_bbox[1] - ref_bbox[1]) < 50:  # Within 50pts vertically
                related_blocks.append(block)

    # Find the actual end of all related text content
    if related_blocks:
        actual_text_end = max(block["bbox"][3] for block in related_blocks)
    else:
        actual_text_end = reference_end_y

    # Add padding to ensure we don't overlap with text
    padding = 10  # 10pt padding to avoid any overlap

    # Create bbox that spans from after all related text to before follow-up text
    x1 = page_x_min  # Full width
    y1 = actual_text_end + padding  # After all related text + padding
    x2 = page_x_max   # Full width
    y2 = followup_bbox[1] - padding  # Before follow-up text - padding

    # Ensure valid bbox with minimum height
    if y2 <= y1:
        # If blocks are too close, use a reasonable area after reference
        y2 = y1 + 80  # 80pt height as minimum for diagrams

    bbox = [x1, y1, x2, y2]

    print("🎯 Text boundary analysis:")
    print(f"   Reference block end: {ref_bbox[3]:.1f}")
    print(f"   Related text end: {actual_text_end:.1f}")
    print(f"   Follow-up start: {followup_bbox[1]:.1f}")
    print(f"   Final bbox: {bbox} (size: {x2-x1:.0f}x{y2-y1:.0f})")

    return bbox


def _create_bbox_after_reference(
    reference_block: Dict[str, Any],
    all_blocks: List[Dict[str, Any]]
) -> List[float]:
    """
    Create a bounding box after the reference text when no clear follow-up is found.

    Args:
        reference_block: Block containing visual reference text
        all_blocks: All text blocks for context

    Returns:
        Bounding box [x1, y1, x2, y2]
    """

    ref_bbox = reference_block["bbox"]

    # Get the page width
    page_x_min = min(block["bbox"][0] for block in all_blocks if block.get("type") == 0)
    page_x_max = max(block["bbox"][2] for block in all_blocks if block.get("type") == 0)

    # Find all text blocks that might be continuation of the reference
    related_blocks = []
    for block in all_blocks:
        if block.get("type") == 0:  # Text block
            block_bbox = block["bbox"]
            # Include blocks that are close to the reference block
            if abs(block_bbox[1] - ref_bbox[1]) < 50:  # Within 50pts vertically
                related_blocks.append(block)

    # Find the actual end of all related text
    if related_blocks:
        actual_text_end = max(block["bbox"][3] for block in related_blocks)
    else:
        actual_text_end = ref_bbox[3]

    # Add padding and create reasonable area
    padding = 10
    x1 = page_x_min
    y1 = actual_text_end + padding  # After all related text + padding
    x2 = page_x_max
    y2 = y1 + 120  # 120pt height as reasonable default for diagrams

    bbox = [x1, y1, x2, y2]

    print(f"🎯 Fallback bbox after all related text end ({actual_text_end:.1f}): {bbox}")

    return bbox


def filter_images_for_multipart_question(
    detected_images: List[Dict[str, Any]],
    text_blocks: List[Dict[str, Any]],
    question_text: str = ""
) -> List[Dict[str, Any]]:
    """
    Filter detected images to only include those relevant to parts with visual content.

    This is now mainly used as a fallback when specialized AI detection isn't available.
    """

    if not detected_images:
        return []

    # Find parts that reference visual content
    parts_with_visuals = _find_parts_with_visual_references(text_blocks, question_text)

    if not parts_with_visuals:
        return detected_images  # Return all if no specific parts identified

    print(f"🎯 Fallback filtering for parts with visuals: {parts_with_visuals}")

    # Simple fallback: prefer larger images that are likely substantial content
    substantial_images = []

    for img in detected_images:
        width = img.get("width", 0)
        height = img.get("height", 0)
        area = width * height

        # Consider images substantial if they're reasonably large
        if area > 30000:  # Reasonable threshold for diagrams
            img["part_context"] = parts_with_visuals[0]  # Assign to first part with visuals
            substantial_images.append(img)
            print(f"📸 ✅ Fallback: substantial image for {parts_with_visuals[0]}: {width}x{height}")

    return substantial_images if substantial_images else detected_images


def _is_multipart_question(text_blocks: List[Dict[str, Any]], question_text: str) -> bool:
    """Determine if this is a multi-part question."""

    # Combine all text for analysis
    all_text = question_text.lower()
    for block in text_blocks:
        if block.get("type") == 0:  # Text block
            block_text = _extract_block_text(block).lower()
            all_text += " " + block_text

    # Multi-part question patterns
    multipart_patterns = [
        r'\bpart\s+[a-d]\b',  # "Part A", "Part B"
        r'\b[a-d]\.\s+\w+',   # "A. Identify", "B. Explain"
    ]

    # Content-based indicators
    content_indicators = [
        "three parts", "two parts", "four parts",
        "label each part", "each part of your response",
    ]

    # Check for patterns
    has_multipart_structure = any(
        re.search(pattern, all_text) for pattern in multipart_patterns
    )

    has_multipart_content = any(
        indicator in all_text for indicator in content_indicators
    )

    is_multipart = has_multipart_structure or has_multipart_content

    if is_multipart:
        print("🎯 Multi-part question detected")

    return is_multipart


def _find_parts_with_visual_references(
    text_blocks: List[Dict[str, Any]],
    question_text: str = ""
) -> List[str]:
    """
    Find which parts of the multi-part question have visual content references.

    Returns:
        List of part names (e.g., ['C']) that have visual references
    """

    parts_with_visuals = []

    # Group blocks by parts (A, B, C, D)
    part_groups = _group_blocks_by_parts(text_blocks)

    for part_name, part_blocks in part_groups.items():
        # Extract text from this part
        part_text = " ".join(_extract_block_text(block) for block in part_blocks).lower()

        # Visual content indicators - focus on explicit references
        visual_indicators = [
            "model shown", "diagram", "figure", "image", "picture",
            "the model", "based on the model", "from the model",
            "shown", "represents", "illustrates", "displays"
        ]

        has_visual_reference = any(indicator in part_text for indicator in visual_indicators)

        if has_visual_reference:
            parts_with_visuals.append(part_name)
            print(f"🎯 Part {part_name} has visual references")

    return parts_with_visuals


def _group_blocks_by_parts(text_blocks: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group text blocks by question parts (A, B, C, D)."""

    part_groups = {}
    current_part = None

    for block in text_blocks:
        if block.get("type") == 0:  # Text block
            block_text = _extract_block_text(block)

            # Check if this block starts a new part
            part_match = re.match(r'^([A-D])\.\s+(.+)', block_text.strip())
            if part_match:
                current_part = part_match.group(1)
                if current_part not in part_groups:
                    part_groups[current_part] = []
                part_groups[current_part].append(block)
            elif current_part and block_text.strip():
                # Add to current part if we have text content
                part_groups[current_part].append(block)

    return part_groups


def _extract_block_text(block: Dict[str, Any]) -> str:
    """Extract text content from a PyMuPDF block."""
    if block.get("type") != 0:  # Not a text block
        return ""

    text_parts = []
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            text = span.get("text", "").strip()
            if text:
                text_parts.append(text)

    return " ".join(text_parts)


