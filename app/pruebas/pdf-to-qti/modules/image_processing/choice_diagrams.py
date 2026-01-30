"""
Choice Diagrams Processor

Specialized module for handling multiple choice questions with diagram options.
Detects when a question has multiple visual choices (A, B, C, D) and extracts
each choice region separately, avoiding the over-expansion issue that occurs
with single-diagram logic.
"""

import re
from typing import Any, Dict, List, Optional

import fitz  # type: ignore


class ChoiceDiagramExtractionError(Exception):
    """Custom exception for errors during choice diagram extraction."""
    pass


def detect_and_extract_choice_diagrams(
    page: fitz.Page,
    text_blocks: List[Dict[str, Any]],
    ai_categories: Optional[Dict[int, str]] = None,
    question_text: str = ""
) -> Optional[List[Dict[str, Any]]]:
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
    """
    print("🎯 Checking if this is a choice diagram question...")

    # Step 1: Detect if this is a multiple choice visual question
    if not _is_choice_diagram_question(text_blocks, ai_categories, question_text):
        print("🎯 Not a choice diagram question")
        return None

    print("🎯 ✅ Detected choice diagram question")

    # Step 2: Find answer choice regions
    choice_regions = _find_choice_regions(page, text_blocks, ai_categories)

    if not choice_regions:
        print("🎯 ⚠️ Could not identify choice regions")
        raise ChoiceDiagramExtractionError(
            "Detected a choice diagram question, but failed to identify the specific regions for each choice. "
            "This is likely because the choice labels (e.g., A, B, C, D) could not be found."
        )

    print(f"🎯 Found {len(choice_regions)} choice regions")

    # Step 3: Extract each choice region as a separate image
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

    if not choice_images:
        raise ChoiceDiagramExtractionError(
            "Detected a choice diagram question and found choice regions, "
            "but failed to render the images for the choices."
        )

    return choice_images if choice_images else None


def _is_choice_diagram_question(
    text_blocks: List[Dict[str, Any]],
    ai_categories: Optional[Dict[int, str]] = None,
    question_text: str = ""
) -> bool:
    """
    Determine if this is a multiple choice question with diagram options.
    
    Looks for:
    1. Question text asking about visual elements ("shows", "diagram", "appears", etc.)
    2. Multiple answer choices with visual indicators
    3. AI categorization indicating visual content
    
    IMPORTANT: Distinguishes between actual multiple choice questions and multi-part questions
    where A, B, C are question parts (e.g., "Part A", "A. Identify the three characteristics")
    
    UPDATED: More conservative to avoid misidentifying prompt visual elements as choices
    """

    # Extract all text content
    all_text = question_text.lower()
    for block in text_blocks:
        if block.get("type") == 0:  # Text block
            spans = block.get("lines", [])
            for line in spans:
                line_spans = line.get("spans", [])
                for span in line_spans:
                    text = span.get("text", "").strip()
                    if text:
                        all_text += " " + text.lower()

    # Check for multi-part question indicators (this should NOT be a choice diagram)
    multi_part_indicators = [
        "part a", "part b", "part c", "part d",
        "a.", "b.", "c.", "d.",
        "a)", "b)", "c)", "d)",
        "identify", "explain", "describe", "analyze",
        "based on the model", "the model shown",
        "three parts", "two parts", "four parts",
        "label each part", "name the parts", "list the components"
    ]

    has_multi_part_indicators = any(indicator in all_text for indicator in multi_part_indicators)

    if has_multi_part_indicators:
        print("🎯 Multi-part question detected - NOT a choice diagram")
        return False

    # NEW: Check for prompt visual indicators that suggest the visual content is part of the question setup
    prompt_visual_indicators = [
        "hydrogen peroxide", "water", "oxygen",  # Molecule names
        "molecule", "molecular", "atoms", "compound", "element",
        "diagram shows", "diagrams shown", "shown above", "image above",
        "in the diagram", "from the diagram", "the diagram", "the model",
        "conservation of mass", "chemical reaction", "breaks apart"
    ]

    has_prompt_visuals = any(indicator in all_text for indicator in prompt_visual_indicators)

    if has_prompt_visuals:
        print("🎯 Prompt visual content detected - likely NOT a choice diagram question")
        # Don't immediately return False, but be more conservative in the final decision

    # Visual question indicators - generalized for any subject
    visual_indicators = [
        "which of the following best shows",
        "which diagram", "which figure", "which image", "which picture",
        "which model shows", "which correctly shows", "which accurately depicts"
    ]

    has_visual_question = any(indicator in all_text for indicator in visual_indicators)

    # Look for explicit choice option structure - be more strict
    # Real multiple choice questions should have clear option structure
    choice_option_patterns = [
        r'([A-D])\s*[\.:\)]\s*[A-Z]',  # A. Something, A) Something, A: Something
        r'([A-D])\s+Reactants\s+Products',  # A Reactants Products (table headers)
        r'([A-D])\s*[\.:\)]\s*\w{3,}'  # A. word, but word must be at least 3 chars
    ]

    total_choice_matches = 0
    for pattern in choice_option_patterns:
        matches = re.findall(pattern, all_text.upper())
        total_choice_matches += len(matches)

    has_actual_choice_options = total_choice_matches >= 2

    # Check AI categorization for visual content
    has_ai_visual_indicators = False
    if ai_categories:
        visual_categories = ["visual_content_title", "visual_content_label", "other_label"]
        has_ai_visual_indicators = any(cat in visual_categories for cat in ai_categories.values())

    # NEW LOGIC: Be much more conservative
    # Only consider it a choice diagram if:
    # 1. It has explicit visual choice question language ("which of the following shows") AND
    # 2. It has clear choice option structure AND
    # 3. It's not detected as having prompt visuals AND
    # 4. It's not a multi-part question

    explicit_choice_question = any([
        "which of the following" in all_text,
        "which diagram shows" in all_text,
        "which model shows" in all_text,
        "which figure shows" in all_text
    ])

    result = (explicit_choice_question and
              has_actual_choice_options and
              not has_prompt_visuals and
              not has_multi_part_indicators)

    print(f"🎯 Visual question: {has_visual_question}")
    print(f"🎯 Explicit choice question: {explicit_choice_question}")
    print(f"🎯 Actual choice options: {has_actual_choice_options} (found {total_choice_matches} matches)")
    print(f"🎯 Prompt visuals detected: {has_prompt_visuals}")
    print(f"🎯 Multi-part indicators: {has_multi_part_indicators}")
    print(f"🎯 AI visual indicators: {has_ai_visual_indicators}")
    print(f"🎯 Is choice diagram question: {result}")

    return result


def _find_choice_regions(
    page: fitz.Page,
    text_blocks: List[Dict[str, Any]],
    ai_categories: Optional[Dict[int, str]] = None
) -> List[Dict[str, Any]]:
    """
    Find the bounding box regions for each answer choice using spatial grouping.
    
    Strategy:
    1. Find all potential choice labels (letters/numbers)
    2. For each choice label, find nearby text blocks that are part of the same choice
    3. Create bounding boxes that encompass the choice label AND its diagram text
    """

    choice_regions = []
    page_width = page.rect.width
    page_height = page.rect.height

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
        block_text = ""
        spans = block.get("lines", [])
        for line in spans:
            line_spans = line.get("spans", [])
            for span in line_spans:
                text = span.get("text", "").strip()
                block_text += " " + text

        block_text = block_text.strip()

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
        elif category == "answer_choice" and len(block_text) > 20:  # Only long answer text, not choice labels
            # Only avoid answer_choice blocks that are clearly full answer text, not just labels
            qa_blocks.append(block_bbox)

        # Check if this block contains a choice label
        # Priority 1: Use AI categorization if available
        if category == "answer_choice":
            # Extract the choice letter from AI-detected answer choice blocks
            choice_match = re.search(r'(?:^|\s)([A-Z]|[1-9])(?:[.,):;\s])', block_text.upper())
            if choice_match:
                block_info['is_choice_label'] = True
                block_info['choice_letter'] = choice_match.group(1)
                print(f"🎯 AI detected choice label '{choice_match.group(1)}' in block {block_num}: '{block_text}'")

        # Priority 2: Regex fallback for when AI categorization isn't available or missed some
        elif not block_info['is_choice_label']:
            # Match patterns like: "A. some text", "A some text", "A)", "B:", etc.
            # But exclude multi-part patterns like "Part A"
            if not re.search(r'\bpart\s+[a-z]', block_text, re.IGNORECASE):
                choice_match = re.search(r'(?:^|\s)([A-Z]|[1-9])(?:[.,):;]|\s+\w)', block_text.upper())
                if choice_match:
                    block_info['is_choice_label'] = True
                    block_info['choice_letter'] = choice_match.group(1)
                    print(f"🎯 Regex detected choice label '{choice_match.group(1)}' in block {block_num}: '{block_text}'")

        all_text_blocks.append(block_info)

    # Find choice labels
    choice_labels = [block for block in all_text_blocks if block['is_choice_label']]

    print(f"🎯 Found {len(qa_blocks)} Q&A blocks, {len(all_text_blocks)} total text blocks")
    print(f"🎯 Found {len(choice_labels)} choice labels: {[c['choice_letter'] for c in choice_labels]}")

    if not choice_labels:
        print("🎯 No choice labels found, cannot create choice regions without fallback.")
        return []

    # Sort choice labels by position (top to bottom, left to right) for boundary calculation
    choice_labels.sort(key=lambda c: (c['bbox'][1], c['bbox'][0]))

    # Process choices sequentially to ensure proper non-overlapping boundaries
    previous_choice_bottom = 0  # Start from top of page

    for i, choice_label_block in enumerate(choice_labels):
        letter = choice_label_block['choice_letter']
        label_bbox = choice_label_block['bbox']

        # Calculate spatial boundaries imposed by neighboring choices
        boundaries = _calculate_choice_boundaries(i, choice_labels, page)

        # Override top boundary to start after previous choice (if not first choice)
        if i > 0:
            boundaries['top'] = previous_choice_bottom + 5  # Start 5px after previous choice ends

        # Find all text blocks that are part of this choice's diagram within boundaries
        choice_related_blocks = _find_blocks_near_choice_constrained(
            choice_label_block, all_text_blocks, qa_blocks, boundaries
        )

        # Create a region that encompasses all related blocks
        region_bbox = _create_comprehensive_choice_bbox(choice_related_blocks, page)

        if region_bbox:
            choice_regions.append({
                'choice_letter': letter,
                'bbox': region_bbox,
                'label_bbox': label_bbox,
                'related_blocks': len(choice_related_blocks),
                'boundaries': boundaries
            })
            print(f"🎯 Choice {letter}: found {len(choice_related_blocks)} related blocks within boundaries {boundaries}")

            # Update previous_choice_bottom for next iteration
            previous_choice_bottom = region_bbox[3]  # bottom coordinate

    # Sort by position (top to bottom, left to right)
    choice_regions.sort(key=lambda r: (r['bbox'][1], r['bbox'][0]))

    return choice_regions


def _calculate_choice_boundaries(
    choice_index: int,
    choice_labels: List[Dict[str, Any]],
    page: fitz.Page
) -> Dict[str, float]:
    """
    Calculate spatial boundaries for a choice based on neighboring choices.
    Uses layout-aware logic: vertical constraints from neighbors, generous horizontal if no side neighbors.
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
    has_top_neighbor = False
    has_bottom_neighbor = False

    # Adjust boundaries based on neighboring choices
    for i, other_choice in enumerate(choice_labels):
        if i == choice_index:
            continue

        other_bbox = other_choice['bbox']
        other_x0, other_y0, other_x1, other_y1 = other_bbox

        # Check for horizontal neighbors (side-by-side choices)
        # Only constrain horizontally if there are actual side neighbors
        vertical_overlap = not (other_y1 <= current_y0 or other_y0 >= current_y1)

        if other_x0 > current_x1 and vertical_overlap:  # Other choice is to the right
            boundaries['right'] = min(boundaries['right'], (other_x0 + current_x1) / 2)
            has_right_neighbor = True
        elif other_x1 < current_x0 and vertical_overlap:  # Other choice is to the left
            boundaries['left'] = max(boundaries['left'], (other_x1 + current_x0) / 2)
            has_left_neighbor = True

        # Check for vertical neighbors (stacked choices)
        # Always constrain vertically when choices are stacked
        horizontal_overlap = not (other_x1 <= current_x0 or other_x0 >= current_x1)

        if other_y0 > current_y1 and horizontal_overlap:  # Other choice is below
            # Stop before the next choice to prevent overlap
            boundaries['bottom'] = min(boundaries['bottom'], other_y0 - 10)  # Stop 10px before next choice
            has_bottom_neighbor = True
        elif other_y1 < current_y0 and horizontal_overlap:  # Other choice is above
            # Start after the previous choice to prevent overlap
            boundaries['top'] = max(boundaries['top'], other_y1 + 10)  # Start 10px after previous choice
            has_top_neighbor = True

    # For vertical layouts (no side neighbors), be more generous horizontally
    if not has_left_neighbor and not has_right_neighbor:
        # Extend horizontally from choice label to right edge for better diagram capture
        boundaries['left'] = min(boundaries['left'], current_x0)
        boundaries['right'] = page.rect.width

    return boundaries


def _find_blocks_near_choice_constrained(
    choice_label_block: Dict[str, Any],
    all_text_blocks: List[Dict[str, Any]],
    qa_blocks: List[List[float]],
    boundaries: Dict[str, float]
) -> List[Dict[str, Any]]:
    """
    Find text blocks that are spatially related to a choice label within given boundaries.
    This includes the choice label itself and nearby diagram text.
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
        if (boundaries['left'] <= block_center_x <= boundaries['right'] and
            boundaries['top'] <= block_center_y <= boundaries['bottom']):

            # Generalized check for likely diagram text (short labels that could be diagram elements)
            text = block['text'].strip()

            # Pattern-based detection for diagram labels:
            # 1. Short text (likely labels, not full sentences)
            # 2. Contains mostly letters/numbers (not punctuation heavy)
            # 3. Exclude obvious non-diagram text patterns
            is_likely_diagram_text = (
                len(text) <= 20 and  # Short labels
                len(text.split()) <= 3 and  # Max 3 words
                not text.endswith('.') and  # Not a sentence
                not text.startswith('(') and  # Not parenthetical notes
                not any(word in text.lower() for word in ['question', 'answer', 'choice', 'option', 'select']) and  # Not meta-text
                re.search(r'[a-zA-Z]', text)  # Contains letters (not just numbers/symbols)
            )

            if is_likely_diagram_text:
                # Calculate distance for logging
                horizontal_distance = abs(block_center_x - choice_center_x)
                vertical_distance = abs(block_center_y - choice_center_y)
                related_blocks.append(block)
                print(f"🎯   Found related block for {choice_label_block['choice_letter']}: '{text}' at ({horizontal_distance:.0f}, {vertical_distance:.0f})")

    return related_blocks


def _create_comprehensive_choice_bbox(
    related_blocks: List[Dict[str, Any]],
    page: fitz.Page
) -> Optional[List[float]]:
    """
    Create a bounding box that encompasses all blocks related to a choice.
    Excludes the choice label itself to prevent text overlap.
    """

    if not related_blocks:
        return None

    # Filter out choice labels - only include diagram elements
    diagram_blocks = [block for block in related_blocks if not block.get('is_choice_label', False)]

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
