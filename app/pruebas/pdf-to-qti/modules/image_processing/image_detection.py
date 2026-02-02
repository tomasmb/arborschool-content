"""image_detection.py
---------------------
AI-powered visual content detection helpers. This module provides fallback
image detection when the main AI content analyzer is not available or when
additional image area detection is needed.

Following converter guidelines: prefer AI analysis over heuristics.
"""

from __future__ import annotations

import base64
from typing import Any, Dict, List, Optional

import fitz  # type: ignore

__all__ = [
    "should_use_ai_image_detection",
    "detect_images_with_ai",
    "detect_potential_image_areas",
    "construct_image_bbox_from_gaps",
    "assess_pymupdf_image_adequacy",
    "expand_pymupdf_bbox_intelligently",
]


def should_use_ai_image_detection(text_blocks: List[Dict[str, Any]], openai_api_key: Optional[str] = None) -> bool:
    """
    Determine if AI-powered image detection should be used.

    This is a fallback function when the main AI content analyzer is not available.
    Prefers LLM analysis over keyword matching following converter guidelines.
    """
    if openai_api_key is None:
        print("🧠 ⚠️ OpenAI API key not provided, using conservative fallback")
        return use_conservative_visual_indicators(text_blocks)

    try:
        import openai
        from pydantic import BaseModel

        class VisualContentAssessment(BaseModel):
            needs_visual_content: bool
            confidence: float
            reasoning: str
            key_indicators: List[str]

        all_text = extract_all_text_from_blocks(text_blocks)

        prompt = f"""Analyze this educational question text to determine if visual content is needed.

QUESTION TEXT:
{all_text}

Determine if this question requires visual content to be fully understood and answered correctly.
Use high confidence only when there are clear visual indicators."""

        client = openai.OpenAI(api_key=openai_api_key)
        response = client.beta.chat.completions.parse(
            model="gpt-5.1",
            messages=[
                {"role": "system", "content": "You are an expert in educational assessment."},
                {"role": "user", "content": prompt}
            ],
            response_format=VisualContentAssessment,
            reasoning_effort="high",
        )

        assessment = response.choices[0].message.parsed
        print(f"🧠 LLM Visual Assessment: {assessment.needs_visual_content}")
        print(f"   Confidence: {assessment.confidence:.2f}")
        return assessment.needs_visual_content and assessment.confidence >= 0.7

    except Exception as e:
        print(f"🧠 ⚠️ LLM visual assessment error: {e}, using fallback")
        return use_conservative_visual_indicators(text_blocks)


def detect_images_with_ai(page: fitz.Page, text_blocks: List[Dict[str, Any]], openai_api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Use AI to categorize text blocks and construct image areas intelligently.

    This is a fallback when the main AI content analyzer is not available.
    """
    if openai_api_key is None:
        print("🧠 ⚠️ OpenAI API key not found, using gap-based fallback")
        return detect_potential_image_areas(page, text_blocks)

    try:
        import openai
        from pydantic import BaseModel

        class TextBlockCategory(BaseModel):
            block_number: int
            category: str
            reasoning: str

        class ContentAnalysisResponse(BaseModel):
            has_visual_content: bool
            visual_content_description: str
            text_block_categories: List[TextBlockCategory]
            image_area_description: str

        block_info = prepare_block_info_for_ai(text_blocks)

        prompt = f"""Analyze a PDF page to identify visual content and categorize text blocks.

TEXT BLOCKS ON PAGE:
{block_info}

Page dimensions: {page.rect.width} x {page.rect.height}

Categorize each text block as:
- "question_text": Question stems, introductory text
- "answer_choice": Multiple choice options (A, B, C, D)
- "visual_content_title": Actual title of visual content
- "visual_content_label": Geographic labels, numbers on maps
- "other_label": Source citations, compass directions"""

        client = openai.OpenAI(api_key=openai_api_key)

        # Get page image for context
        from ..utils import get_page_image
        page_image_bytes = get_page_image(page, scale=1.5)
        page_image_base64 = base64.b64encode(page_image_bytes).decode('utf-8')

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{page_image_base64}"}}
                ]
            }
        ]

        response = client.beta.chat.completions.parse(
            model="gpt-5.1",
            messages=messages,
            response_format=ContentAnalysisResponse,
            reasoning_effort="high",
        )

        analysis = response.choices[0].message.parsed
        print(f"🧠 AI Content Analysis: {analysis.visual_content_description}")

        if not analysis.has_visual_content:
            print("🧠 No visual content detected by AI")
            return []

        # Categorize blocks for image boundary construction
        categorization_result = process_ai_categorization(analysis, text_blocks)

        qa_bboxes = categorization_result["question_answer_blocks"]
        strict_label_bboxes = categorization_result["strict_label_bboxes"]
        # other_label_bboxes = categorization_result["other_label_bboxes"] # Available if needed elsewhere
        all_image_labels_for_gaps = categorization_result["all_image_associated_text_bboxes"]

        # Create sets of bbox tuples for efficient lookup for footer avoidance list construction
        qa_bboxes_set = {tuple(bbox) for bbox in qa_bboxes}
        strict_label_bboxes_set = {tuple(bbox) for bbox in strict_label_bboxes}

        # This list is passed to construct_image_bbox_from_gaps for footer avoidance.
        # It should include anything that isn't QA or a strict image label (e.g., actual footers,
        # "other_label" blocks which might be footers or image-related source notes).
        potential_footer_check_bboxes = []
        for block in text_blocks: # Iterate through the original text_blocks from PyMuPDF
            if block.get("type") == 0: # Text block
                bbox = block.get("bbox")
                if bbox and len(bbox) == 4:
                    bbox_tuple = tuple(bbox)
                    # Only exclude QA and STRICT image labels. Others (incl. other_labels) remain for footer check.
                    if bbox_tuple not in qa_bboxes_set and bbox_tuple not in strict_label_bboxes_set:
                        potential_footer_check_bboxes.append(bbox)

        image_bbox = construct_image_bbox_from_gaps(
            page,
            qa_bboxes,
            all_image_labels_for_gaps, # All bboxes AI thought were image-related
            potential_footer_check_bboxes # Bboxes for footer avoidance (includes other_labels)
        )

        if image_bbox:
            return [{
                "type": 1,
                "bbox": image_bbox,
                "number": "ai_content_analysis",
                "description": analysis.image_area_description,
                "confidence": 0.95,
                "ai_categories": categorization_result["ai_categories"]
            }]
        else:
            print("🧠 ⚠️ Could not construct valid image bbox from text gaps")
            return []

    except Exception as e:
        print(f"🧠 ⚠️ AI content analysis error: {e}, using gap-based fallback")
        return detect_potential_image_areas(page, text_blocks)


def detect_potential_image_areas(page: fitz.Page, text_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detect potential image areas by looking for large empty spaces between text blocks."""
    potential_images = []
    page_width = page.rect.width

    text_bboxes = []
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
                next_top - 5
            ]

            area_width = potential_bbox[2] - potential_bbox[0]
            area_height = potential_bbox[3] - potential_bbox[1]
            area = area_width * area_height

            if area > 5000 and area_width > 100 and area_height > 50:
                print(f"📸 Potential image area detected: {potential_bbox}, size: {area_width:.1f}x{area_height:.1f}")
                potential_images.append({
                    "type": 1,
                    "bbox": potential_bbox,
                    "number": f"fallback_{len(potential_images) + 1}"
                })

    return potential_images


def construct_image_bbox_from_gaps(
    page: fitz.Page,
    question_answer_blocks: List[List[float]],
    image_label_blocks: List[List[float]],
    all_page_text_bboxes: List[List[float]]
) -> Optional[List[float]]:
    """Construct image bbox by finding gaps between question/answer text blocks."""
    if not question_answer_blocks:
        return None

    qa_blocks_sorted = sorted(question_answer_blocks, key=lambda bbox: bbox[1])
    page_width = page.rect.width
    page_height = page.rect.height
    margin = 10

    # Collect all potential gaps with metadata
    potential_gaps = []

    # Check gap from top of page to first block
    if qa_blocks_sorted[0][1] > margin:
        gap_size = qa_blocks_sorted[0][1] - margin
        potential_gaps.append({
            "size": gap_size,
            "start": margin,
            "end": qa_blocks_sorted[0][1] - margin,
            "type": "top",
            "priority": 2
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
            "priority": 3
        })

    # Determine effective page bottom considering all text blocks to avoid footer overlap
    effective_page_bottom_for_image = page_height - margin
    # qa_blocks_sorted is guaranteed to be non-empty here due to the early return.
    last_qa_block_bottom = qa_blocks_sorted[-1][3]
    for text_bbox in all_page_text_bboxes:
        # Consider text blocks that are strictly below the last QA block
        # Use a small buffer (margin / 2) to ensure clear separation before considering a block as "below"
        if text_bbox[1] > last_qa_block_bottom + (margin / 2):
            potential_new_image_bottom = text_bbox[1] - margin # Image should end above this block
            if potential_new_image_bottom < effective_page_bottom_for_image:
                effective_page_bottom_for_image = potential_new_image_bottom

    # Check gap from last block to determined effective bottom
    if qa_blocks_sorted[-1][3] < effective_page_bottom_for_image: # Check if there's any space left
        gap_start_y = qa_blocks_sorted[-1][3] + margin
        gap_end_y = effective_page_bottom_for_image

        if gap_end_y > gap_start_y:  # Ensure there's a valid positive-sized gap
            gap_size = gap_end_y - gap_start_y
            potential_gaps.append({
                "size": gap_size,
                "start": gap_start_y,
                "end": gap_end_y,
                "type": "bottom",
                "priority": 1
            })

    # Filter gaps that are large enough
    valid_gaps = [gap for gap in potential_gaps if gap["size"] >= 100]

    if not valid_gaps:
        print("🧠 ⚠️ No gaps larger than 100px found")
        return None

    # Sort by priority first, then by size (descending)
    # This ensures we prefer "between" gaps over "bottom" gaps even if bottom is larger
    valid_gaps.sort(key=lambda g: (-g["priority"], -g["size"]))

    best_gap = valid_gaps[0]
    print(f"🧠 ✅ Selected {best_gap['type']} gap: {best_gap['size']:.0f}px "
          f"(priority {best_gap['priority']})")

    left_bound = margin
    right_bound = page_width - margin

    # Adjust for overlapping blocks
    for bbox in qa_blocks_sorted:
        if not (bbox[3] <= best_gap["start"] or bbox[1] >= best_gap["end"]):
            if bbox[0] > page_width / 2:
                right_bound = min(right_bound, bbox[0] - margin)
            else:
                left_bound = max(left_bound, bbox[2] + margin)

    if right_bound <= left_bound:
        print("🧠 ⚠️ No valid horizontal space for image")
        return None

    image_bbox = [left_bound, best_gap["start"], right_bound, best_gap["end"]]
    width = right_bound - left_bound
    height = best_gap["end"] - best_gap["start"]

    print(f"🧠 ✅ Constructed image bbox: {image_bbox}, size: {width:.0f}x{height:.0f}")
    return image_bbox


# Helper functions

def extract_all_text_from_blocks(text_blocks: List[Dict[str, Any]]) -> str:
    """Extract all text from blocks for analysis."""
    all_text = ""
    for block in text_blocks:
        if block.get("type") == 0:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    all_text += span.get("text", "") + " "
    return all_text.strip()


def use_conservative_visual_indicators(text_blocks: List[Dict[str, Any]]) -> bool:
    """Conservative fallback using minimal indicators."""
    all_text = extract_all_text_from_blocks(text_blocks).lower()
    # Use minimal, non-overfitted indicators
    indicators = ["map", "diagram", "chart", "graph", "figure", "image", "shown", "displays"]
    return any(indicator in all_text for indicator in indicators)


def prepare_block_info_for_ai(text_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
            block_info.append({
                "block_number": i + 1,
                "text": block_text,
                "bbox": bbox,
                "area": text_area
            })

    return block_info


def process_ai_categorization(analysis, text_blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Process AI categorization results into usable format."""
    question_answer_blocks = []
    strict_label_bboxes = []  # For visual_content_title, visual_content_label
    other_label_bboxes = []   # For other_label
    # Ensure all_image_associated_text_bboxes includes all text AI thinks is part of an image
    # This will be passed as the 'image_label_blocks' argument to construct_image_bbox_from_gaps
    all_image_associated_text_bboxes = []
    ai_categories = {}

    # Create a mapping from prepared block_number to original block index for robustness
    # prepare_block_info_for_ai filters blocks, so its block_number (1-indexed)
    # needs to map back to the original text_blocks list (0-indexed).
    prepared_to_original_map = {}
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
        ai_block_num = cat_info.block_number # This is the 1-indexed number from prepare_block_info_for_ai
        category = cat_info.category

        original_block_idx = prepared_to_original_map.get(ai_block_num)
        if original_block_idx is None:
            print(f"🧠 ⚠️ AI category for unknown block number {ai_block_num}, skipping.")
            continue

        # Store the category for the original block index (or its AI-assigned number if preferred for debugging)
        # Using ai_block_num as key for consistency with how it was logged before.
        ai_categories[ai_block_num] = category

        block = text_blocks[original_block_idx]
        # We already know it's a text block with a valid bbox from the map creation
        bbox = block.get("bbox") # Should be valid

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
            # Fallback for any unknown categories, treat as potentially image-related
            all_image_associated_text_bboxes.append(bbox)
            print(f"🧠 Block {ai_block_num} ({category}): unknown category, assumed image part")

    return {
        "question_answer_blocks": question_answer_blocks,
        "strict_label_bboxes": strict_label_bboxes,
        "other_label_bboxes": other_label_bboxes,
        "all_image_associated_text_bboxes": all_image_associated_text_bboxes,
        "ai_categories": ai_categories # This maps ai_block_num to category string
    }


def expand_pymupdf_bbox_intelligently(
    pymupdf_bbox: List[float],
    page: fitz.Page,
    text_blocks: List[Dict[str, Any]],
    ai_categories: Optional[Dict[int, str]] = None
) -> List[float]:
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
    qa_text_blocks = []
    for i, block in enumerate(text_blocks):
        if block.get("type") != 0:  # Only text blocks
            continue

        block_bbox = block.get("bbox")
        if not block_bbox or len(block_bbox) < 4:
            continue

        # Use AI categorization if available
        block_num = i + 1
        is_qa_text = False
        category_info = ""

        if ai_categories and block_num in ai_categories:
            category = ai_categories[block_num]
            is_qa_text = category in ["question_text", "answer_choice"]
            category_info = f"AI:{category}"

            # Image-related text should NOT be avoided during expansion
            if category in ["visual_content_title", "visual_content_label", "other_label"]:
                print(f"📸 Block {block_num} is part of image ({category}) - will expand through it")
                continue
        else:
            # Conservative fallback: only avoid very large text blocks that are likely Q&A
            block_area = (block_bbox[2] - block_bbox[0]) * (block_bbox[3] - block_bbox[1])
            # More conservative threshold - only avoid really large blocks
            is_qa_text = block_area > 2000  # Much higher threshold
            category_info = f"fallback:area={block_area:.0f}"

        if is_qa_text:
            qa_text_blocks.append(block_bbox)
            print(f"📸 Block {block_num} will be avoided during expansion ({category_info})")

    print(f"📸 Found {len(qa_text_blocks)} Q&A text blocks to avoid")

    # Expansion parameters
    safety_margin = 10   # Margin to keep from text

    # Find the maximum expansion boundaries in each direction
    # Start with page boundaries
    max_left = 0
    max_right = page_width
    max_top = 0
    max_bottom = page_height

    # Find the closest text boundaries in each direction
    for qa_bbox in qa_text_blocks:
        qa_x0, qa_y0, qa_x1, qa_y1 = qa_bbox

        # For left expansion: find rightmost text that's to the left of our bbox
        if qa_x1 <= expanded_bbox[0]:  # Text is to the left
            # Check if this text is in our vertical range
            if not (qa_y1 <= expanded_bbox[1] or qa_y0 >= expanded_bbox[3]):
                max_left = max(max_left, qa_x1 + safety_margin)

        # For right expansion: find leftmost text that's to the right of our bbox
        if qa_x0 >= expanded_bbox[2]:  # Text is to the right
            # Check if this text is in our vertical range
            if not (qa_y1 <= expanded_bbox[1] or qa_y0 >= expanded_bbox[3]):
                max_right = min(max_right, qa_x0 - safety_margin)

        # For top expansion: find bottommost text that's above our bbox
        if qa_y1 <= expanded_bbox[1]:  # Text is above
            # Check if this text is in our horizontal range
            if not (qa_x1 <= expanded_bbox[0] or qa_x0 >= expanded_bbox[2]):
                max_top = max(max_top, qa_y1 + safety_margin)

        # For bottom expansion: find topmost text that's below our bbox
        if qa_y0 >= expanded_bbox[3]:  # Text is below
            # Check if this text is in our horizontal range
            if not (qa_x1 <= expanded_bbox[0] or qa_x0 >= expanded_bbox[2]):
                max_bottom = min(max_bottom, qa_y0 - safety_margin)

    # Apply the expansion all the way to the boundaries
    expanded_bbox[0] = max_left      # Left edge
    expanded_bbox[2] = max_right     # Right edge
    expanded_bbox[1] = max_top       # Top edge
    expanded_bbox[3] = max_bottom    # Bottom edge

    print(f"📸 Expansion boundaries: left={max_left}, right={max_right}, top={max_top}, bottom={max_bottom}")

    # Calculate expansion stats
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

    return expanded_bbox


def _bbox_overlaps_with_qa_text(
    test_bbox: List[float],
    qa_text_blocks: List[List[float]],
    safety_margin: float
) -> bool:
    """
    Check if a test bbox overlaps with any Q&A text blocks (with safety margin).
    """
    test_x0, test_y0, test_x1, test_y1 = test_bbox

    for qa_bbox in qa_text_blocks:
        qa_x0, qa_y0, qa_x1, qa_y1 = qa_bbox

        # Add safety margin to Q&A text bbox
        margin_qa_x0 = qa_x0 - safety_margin
        margin_qa_y0 = qa_y0 - safety_margin
        margin_qa_x1 = qa_x1 + safety_margin
        margin_qa_y1 = qa_y1 + safety_margin

        # Check for overlap
        if not (test_x1 <= margin_qa_x0 or test_x0 >= margin_qa_x1 or
                test_y1 <= margin_qa_y0 or test_y0 >= margin_qa_y1):
            return True  # Overlap detected

    return False


def assess_pymupdf_image_adequacy(
    image_blocks: List[Dict[str, Any]],
    page: fitz.Page,
    text_blocks: List[Dict[str, Any]],
    openai_api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Assess whether PyMuPDF detected images are adequate for the visual content requirements.

    Uses AI analysis and size heuristics to determine if detected images capture
    the complete visual content or just partial elements.

    Args:
        image_blocks: PyMuPDF detected image blocks
        page: The PDF page
        text_blocks: All text blocks from the page
        openai_api_key: OpenAI API key for AI assessment

    Returns:
        Dictionary with adequacy assessment results
    """
    if not image_blocks:
        return {
            "adequate": False,
            "reason": "No images detected",
            "should_use_ai_fallback": True,
            "size_adequate": False,
            "ai_adequate": False
        }

    # Step 1: Size-based heuristics
    total_image_area = 0
    page_area = page.rect.width * page.rect.height
    largest_image_area = 0
    smallest_image_area = float('inf')

    for image_block in image_blocks:
        bbox = image_block.get("bbox", [0, 0, 0, 0])
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        area = width * height

        total_image_area += area
        largest_image_area = max(largest_image_area, area)
        smallest_image_area = min(smallest_image_area, area)

    # Heuristic thresholds
    image_area_ratio = total_image_area / page_area if page_area > 0 else 0
    largest_image_side = max(
        max(bbox[2] - bbox[0], bbox[3] - bbox[1])
        for bbox in [img.get("bbox", [0, 0, 0, 0]) for img in image_blocks]
    )

    # Size adequacy check
    size_adequate = (
        largest_image_area > 2000 and  # At least 2000 sq pixels
        largest_image_side > 50 and    # At least 50px on largest side
        image_area_ratio > 0.05        # At least 5% of page area
    )

    print(f"📸 Size assessment: area={largest_image_area:.0f}, side={largest_image_side:.0f}, ratio={image_area_ratio:.3f}")
    print(f"📸 Size adequate: {size_adequate}")

    # Step 2: AI-based assessment if available
    ai_adequate = True  # Default to True if no AI available
    ai_reasoning = "No AI assessment performed"

    if openai_api_key:
        try:
            ai_assessment = assess_image_completeness_with_ai(
                image_blocks, page, text_blocks, openai_api_key
            )
            ai_adequate = ai_assessment.get("adequate", False)
            ai_reasoning = ai_assessment.get("reasoning", "AI assessment failed")

            print(f"🧠 AI assessment: {ai_adequate} - {ai_reasoning}")
        except Exception as e:
            print(f"🧠 ⚠️ AI assessment failed: {e}")
            ai_adequate = True  # Don't block on AI failure

    # Step 3: Combined decision
    overall_adequate = size_adequate and ai_adequate

    should_use_ai_fallback = not overall_adequate

    reason = []
    if not size_adequate:
        reason.append(f"Image too small (area={largest_image_area:.0f}, side={largest_image_side:.0f})")
    if not ai_adequate:
        reason.append(f"AI assessment: {ai_reasoning}")

    result = {
        "adequate": overall_adequate,
        "reason": "; ".join(reason) if reason else "Images appear adequate",
        "should_use_ai_fallback": should_use_ai_fallback,
        "size_adequate": size_adequate,
        "ai_adequate": ai_adequate,
        "largest_image_area": largest_image_area,
        "image_area_ratio": image_area_ratio,
        "ai_reasoning": ai_reasoning
    }

    print(f"📸 Overall adequacy: {overall_adequate} - {result['reason']}")
    return result


def assess_image_completeness_with_ai(
    image_blocks: List[Dict[str, Any]],
    page: fitz.Page,
    text_blocks: List[Dict[str, Any]],
    openai_api_key: str
) -> Dict[str, Any]:
    """
    Use AI to assess if detected images capture complete visual content.
    """
    try:
        import openai
        from pydantic import BaseModel

        class ImageCompletenessAssessment(BaseModel):
            adequate: bool
            confidence: float
            reasoning: str
            missing_elements: List[str]
            detected_elements: List[str]

        # Prepare context
        all_text = extract_all_text_from_blocks(text_blocks)

        # Get image bbox info
        image_info = []
        for i, img_block in enumerate(image_blocks):
            bbox = img_block.get("bbox", [0, 0, 0, 0])
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            image_info.append(f"Image {i+1}: {width:.0f}x{height:.0f} at position ({bbox[0]:.0f}, {bbox[1]:.0f})")

        prompt = f"""Analyze whether the detected images adequately capture the visual content needed for this educational question.

QUESTION TEXT:
{all_text}

DETECTED IMAGES:
{chr(10).join(image_info)}

PAGE DIMENSIONS: {page.rect.width:.0f}x{page.rect.height:.0f}

Assess if the detected images are sufficient to answer the question. Consider:
1. Does the question text reference visual elements (diagrams, charts, maps, etc.)?
2. Are the detected image areas large enough to contain meaningful visual content?
3. Based on the question context, what visual elements should be present?
4. Do the detected images likely capture complete diagrams or just small parts?

Be conservative - if you suspect the images might be partial (like just a small piece of a larger diagram), mark as inadequate."""

        client = openai.OpenAI(api_key=openai_api_key)

        # Get page image for visual context
        from ..utils import get_page_image
        page_image_bytes = get_page_image(page, scale=1.5)
        page_image_base64 = base64.b64encode(page_image_bytes).decode('utf-8')

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{page_image_base64}"}}
                ]
            }
        ]

        response = client.beta.chat.completions.parse(
            model="gpt-5.1",
            messages=messages,
            response_format=ImageCompletenessAssessment,
            reasoning_effort="high",
        )

        assessment = response.choices[0].message.parsed
        return {
            "adequate": assessment.adequate and assessment.confidence >= 0.7,
            "confidence": assessment.confidence,
            "reasoning": assessment.reasoning,
            "missing_elements": assessment.missing_elements,
            "detected_elements": assessment.detected_elements
        }

    except Exception as e:
        print(f"🧠 ⚠️ AI image completeness assessment error: {e}")
        return {
            "adequate": True,  # Default to adequate on error
            "reasoning": f"AI assessment failed: {str(e)}",
            "confidence": 0.0
        }
