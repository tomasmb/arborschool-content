"""
LLM-powered visual content analyzer.

This module contains all the LLM-related functionality for analyzing and categorizing
visual content in educational materials.
"""

import base64
from typing import Any, Dict, List

import fitz  # type: ignore

from .choice_extractor import extract_choice_images
from .image_area_detector import construct_image_area_from_gaps_flexible, construct_multiple_image_areas
from .utils import get_page_image


def analyze_visual_content_with_llm(page: fitz.Page, text_blocks: List[Dict[str, Any]], question_text: str, openai_api_key: str) -> Dict[str, Any]:
    """
    Use LLM to analyze and separate prompt vs choice visual content.
    """
    print("🔍 🧠 Preparing LLM analysis request...")

    import openai
    from pydantic import BaseModel

    class TextBlockCategory(BaseModel):
        block_number: int
        category: str
        reasoning: str

    class VisualContentAnalysis(BaseModel):
        has_prompt_visuals: bool
        has_choice_visuals: bool
        prompt_visual_description: str
        choice_visual_description: str
        text_block_categories: List[TextBlockCategory]
        separation_confidence: float
        reasoning: str

    # Prepare text blocks info
    block_info = []
    text_block_count = 0
    for i, block in enumerate(text_blocks):
        if block.get("type") == 0:  # Text block
            block_text = ""
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    block_text += span.get("text", "") + " "

            # Include all text blocks, even those with empty text
            # Empty text blocks may contain visual elements like axis labels
            text_block_count += 1
            bbox = block.get("bbox", [0, 0, 0, 0])

            if block_text.strip():
                block_info.append(
                    {
                        "block_number": i + 1,
                        "text": block_text.strip()[:200],  # Limit for efficiency
                        "bbox": bbox,
                        "position": f"({bbox[0]:.0f}, {bbox[1]:.0f}) to ({bbox[2]:.0f}, {bbox[3]:.0f})",
                    }
                )
            else:
                # For empty text blocks, provide position info so LLM can categorize based on location
                block_info.append(
                    {
                        "block_number": i + 1,
                        "text": "[Empty text block - likely contains visual elements]",
                        "bbox": bbox,
                        "position": f"({bbox[0]:.0f}, {bbox[1]:.0f}) to ({bbox[2]:.0f}, {bbox[3]:.0f})",
                    }
                )

    print(f"🔍 📋 Prepared {text_block_count} text blocks for LLM analysis")

    # Get page image for visual context
    print("🔍 📸 Capturing page image for LLM visual context...")
    try:
        page_image_bytes = get_page_image(page, scale=1.5)
        page_image_base64 = base64.b64encode(page_image_bytes).decode("utf-8")
        print(f"🔍 📸 Page image captured: {len(page_image_base64)} base64 chars")
    except Exception as e:
        print(f"🔍 ❌ Failed to capture page image: {e}")
        return {"success": False, "error": f"Page image capture failed: {e}"}

    prompt = f"""Analyze this educational question to separate prompt visuals from \
choice visuals and categorize each text block. The question may have multiple \
parts (e.g., Part A, Part B).

QUESTION TEXT:
{question_text}

TEXT BLOCKS ON PAGE:
{block_info}

PAGE DIMENSIONS: {page.rect.width} x {page.rect.height}

TASKS:
1. Determine if there are PROMPT VISUALS (part of the question) vs. CHOICE VISUALS (part of the answer options).
2. Categorize EACH text block accurately to help with image extraction.

VISUAL CONTENT TYPES:
- PROMPT VISUALS: Visuals essential for understanding the question (e.g., a diagram the question refers to).
- CHOICE VISUALS: Visuals that are the answer options (e.g., diagrams for choices A, B, C, D).

TEXT BLOCK CATEGORIES:
- "question_part_header": Identifier for a part of a multi-part question
  (e.g., "A.", "B.", "Part C"). This is separate from the question text itself.
- "question_text": The main text of a question or sub-question, instructions,
  and introductions that are NOT directly describing visual content.
- "answer_choice": A multiple choice option identifier (e.g., "A", "B", "C", "D").
  This may be a standalone letter or text that starts with the choice letter
  (e.g., "A) Diagram 1"). An answer choice is often located near its corresponding visual.
- "visual_content_title": A title or overall caption for a visual element.
- "visual_content_label": Labels ON or pointing to parts of a diagram or image that are
  part of the PROMPT/QUESTION visuals. **IMPORTANT: This also includes descriptive text
  that explains what is shown in the diagrams (e.g., "The field is raised up and has a
  rounded surface to allow rainwater to run off into the drains"). Empty blocks that are
  clearly part of visual content (like embedded figures, charts, or diagrams) should also
  be categorized as visual_content_label, even if they contain no extractable text.**
- "choice_visual_label": Labels ON or pointing to parts of diagrams that are part of
  the ANSWER CHOICE visuals (e.g., labels within choice A, B, C, D diagrams).
- "other_label": Any other text like source citations, page numbers, or legends that
  are NOT part of visual content.

IMPORTANT GUIDELINES:
- A block containing just "A." or "Part A" should be "question_part_header".
- For multiple-choice questions with visual answers, the choice identifiers (A, B, C, D)
  are often near the visuals. Categorize the block containing the identifier as
  "answer_choice". If the choice letter is combined with other text in the same block,
  it's still an "answer_choice".
- **CRITICAL**: Empty blocks that are positioned where visual content (figures, charts,
  diagrams) must be categorized as "visual_content_label", NOT "other_label". These
  blocks represent embedded visual elements that failed to extract as text.
- Text that describes or explains what is shown in diagrams should be categorized as
  "visual_content_label" to ensure it's included in the image extraction. This prevents
  cutting off important explanatory text that is part of the visual content.
- EXCEPTION: Text that introduces or transitions to a new diagram (e.g., "The model
  below shows...", "The diagram below...") should be "question_text" as it separates
  visual elements.
- The goal is to separate text that's part of an image from text that is not, to allow
  for clean image extraction.
- **Tables are NOT choice visuals**. If choices are presented in a table format, the
  table structure itself is not a visual choice. Do not identify `has_choice_visuals`
  as true just because choices are in a table.

Categorize each block to help identify where visual content is located."""

    try:
        print("🔍 🧠 Sending request to OpenAI...")
        client = openai.OpenAI(api_key=openai_api_key)

        response = client.beta.chat.completions.parse(
            model="gpt-5.1",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert in educational content analysis. "
                        "Analyze visual content to separate prompt elements from "
                        "choice elements, and categorize each text block to help "
                        "with image extraction."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{page_image_base64}"}},
                    ],
                },
            ],
            response_format=VisualContentAnalysis,
            reasoning_effort="medium",  # visual analysis, moderate complexity
        )

        print("🔍 ✅ Received response from OpenAI")
        analysis = response.choices[0].message.parsed

        print("🔍 🧠 LLM ANALYSIS RESULTS:")
        print("🔍 " + "=" * 50)
        print(f"🔍 Prompt visuals detected: {analysis.has_prompt_visuals}")
        print(f"🔍 Choice visuals detected: {analysis.has_choice_visuals}")
        print(f"🔍 Confidence score: {analysis.separation_confidence:.2f}")
        print(f"🔍 Overall reasoning: {analysis.reasoning}")
        print(f"🔍 Prompt description: {analysis.prompt_visual_description}")
        print(f"🔍 Choice description: {analysis.choice_visual_description}")
        print("🔍 " + "=" * 50)

        # Process block categories
        block_categories = {}
        print("🔍 📋 TEXT BLOCK CATEGORIZATIONS:")
        for cat_info in analysis.text_block_categories:
            block_categories[cat_info.block_number] = cat_info.category
            print(f"🔍 Block {cat_info.block_number:2d} -> {cat_info.category:20s} | {cat_info.reasoning}")

        print(f"🔍 📋 Categorized {len(block_categories)} blocks total")

        # Process the analysis results using gap detection with block categories
        print("🔍 🔄 Processing LLM results with gap detection...")
        result = process_llm_analysis_with_gaps(analysis, page, text_blocks, block_categories)
        result["success"] = True
        result["confidence"] = analysis.separation_confidence
        result["ai_categories"] = block_categories

        return result

    except Exception as e:
        print(f"🔍 ❌ LLM analysis request failed: {str(e)}")
        import traceback

        print(f"🔍 📋 Full traceback: {traceback.format_exc()}")
        return {"success": False, "error": str(e)}


def process_llm_analysis_with_gaps(analysis, page: fitz.Page, text_blocks: List[Dict[str, Any]], block_categories: Dict[int, str]) -> Dict[str, Any]:
    """
    Process LLM analysis results and use gap detection to find visual areas.
    """
    print("🔍 🔄 PROCESSING LLM RESULTS WITH GAP DETECTION")
    print("🔍 " + "-" * 50)

    # Initialize variables that will be used throughout the function
    prompt_bboxes = []
    choice_bboxes = []
    question_answer_blocks = []
    image_label_blocks = []
    all_text_bboxes = []

    # Build text bbox list and categorize blocks - needed for both prompt and choice processing
    print("🔍 📋 Categorizing blocks for gap detection:")
    for i, block in enumerate(text_blocks):
        if block.get("type") == 0:  # Text block
            bbox = block.get("bbox")
            if bbox and len(bbox) == 4:
                all_text_bboxes.append(bbox)

                block_num = i + 1
                category = block_categories.get(block_num, "unknown")

                # Extract block text for logging
                block_text = ""
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        block_text += span.get("text", "") + " "
                block_text = block_text.strip()[:50] + "..." if len(block_text.strip()) > 50 else block_text.strip()

                # Use LLM categories for more precise separation
                if category in ["question_text", "answer_choice", "question_part_header"]:
                    question_answer_blocks.append(bbox)
                    print(f"🔍   Block {block_num:2d} ({category:20s}): SEPARATE from images | {block_text}")
                elif category in ["visual_content_title", "visual_content_label"]:
                    # Only prompt visual labels go to image_label_blocks
                    image_label_blocks.append(bbox)
                    print(f"🔍   Block {block_num:2d} ({category:20s}): PART OF prompt image | {block_text}")
                elif category == "choice_visual_label":
                    # Choice visual labels are handled separately - don't include in prompt detection
                    print(f"🔍   Block {block_num:2d} ({category:20s}): PART OF choice image | {block_text}")
                    # Don't add to image_label_blocks - will be handled by choice extraction
                elif category == "other_label":
                    # LLM categorized as other_label - trust its judgment and exclude from images
                    question_answer_blocks.append(bbox)  # Treat as separate from image
                    print(f"🔍   Block {block_num:2d} ({category:15s}): LLM-excluded (separate) | {block_text}")
                else:
                    # Fallback for uncategorized blocks
                    question_answer_blocks.append(bbox)  # Be conservative - separate from images
                    print(f"🔍   Block {block_num:2d} ({category:15s}): FALLBACK handling | {block_text}")

    print("🔍 📊 Gap detection inputs:")
    print(f"🔍    Question/Answer blocks: {len(question_answer_blocks)}")
    print(f"🔍    Image label blocks: {len(image_label_blocks)}")
    print(f"🔍    All text blocks: {len(all_text_bboxes)}")

    # CRITICAL FIX: If LLM says "choice visuals" but no answer choice blocks exist,
    # this is likely a misclassification - the visual content is actually part of the prompt
    if not analysis.has_prompt_visuals and analysis.has_choice_visuals:
        actual_answer_choice_blocks = [cat for cat in block_categories.values() if cat == "answer_choice"]
        if len(actual_answer_choice_blocks) == 0:
            print("🔍 🔄 CORRECTION: LLM said 'choice visuals' but no answer choice blocks found")
            print("🔍    This visual content is likely part of the question prompt, not choices")
            print("🔍    Reclassifying as PROMPT visuals")
            analysis.has_prompt_visuals = True
            analysis.has_choice_visuals = False
            analysis.prompt_visual_description = analysis.choice_visual_description
            analysis.choice_visual_description = ""

    # If LLM detects prompt visuals, use gap detection to find them
    if analysis.has_prompt_visuals:
        print("🔍 📸 LLM detected prompt visuals - starting gap detection...")

        prompt_image_labels = list(image_label_blocks)

        if analysis.has_choice_visuals:
            print("🔍 🧠 Separating prompt labels from choice labels...")
            answer_choice_bboxes = []
            for block_num, category in block_categories.items():
                if category == "answer_choice":
                    if block_num - 1 < len(text_blocks):
                        block = text_blocks[block_num - 1]
                        if block.get("type") == 0 and block.get("bbox"):
                            answer_choice_bboxes.append(block["bbox"])

            if answer_choice_bboxes:
                first_choice_y = min(bbox[1] for bbox in answer_choice_bboxes)
                print(f"🔍    Choice area identified to start at y={first_choice_y:.1f}")

                separated_prompt_labels = [label_bbox for label_bbox in image_label_blocks if label_bbox[3] < first_choice_y]

                if separated_prompt_labels and len(separated_prompt_labels) < len(image_label_blocks):
                    prompt_image_labels = separated_prompt_labels
                    print(f"🔍    Found {len(prompt_image_labels)} prompt-specific labels based on position.")
                else:
                    print("🔍 ⚠️  Could not find distinct prompt labels above the choice area. Using all labels for prompt detection.")

        # Collect choice visual labels (both leftover prompt labels and dedicated choice labels)
        choice_image_labels = [bbox for bbox in image_label_blocks if bbox not in prompt_image_labels]

        # Add explicitly categorized choice visual labels
        for block_num, category in block_categories.items():
            if category == "choice_visual_label":
                if block_num - 1 < len(text_blocks):
                    block = text_blocks[block_num - 1]
                    if block.get("type") == 0 and block.get("bbox"):
                        choice_image_labels.append(block["bbox"])

        if analysis.has_choice_visuals:
            print(f"🔍    Found {len(choice_image_labels)} choice-specific labels for extraction.")

        # Use custom image area detection that includes image labels
        print("🔍 🔍 Running custom image area detection...")
        try:
            prompt_bboxes = construct_multiple_image_areas(page, question_answer_blocks, prompt_image_labels)

            # If label-based detection failed (no labels), try gap detection with flexible thresholds
            if not prompt_bboxes and image_label_blocks:
                print("🔍 🔄 Label-based detection failed, trying improved gap detection...")
                from .image_area_detector import construct_image_bbox_from_gaps

                prompt_bbox_single = construct_image_bbox_from_gaps(page, question_answer_blocks, image_label_blocks, all_text_bboxes)
                if prompt_bbox_single:
                    prompt_bboxes = [prompt_bbox_single]

            elif not prompt_bboxes:
                print("🔍 🔄 No image labels found, using flexible gap detection...")
                # Updated fallback: use only question_text blocks for flexible gap detection
                question_text_bboxes = []
                for block_num, category in block_categories.items():
                    if category == "question_text":
                        if block_num - 1 < len(text_blocks):
                            block = text_blocks[block_num - 1]
                            bbox = block.get("bbox")
                            if bbox and len(bbox) == 4:
                                question_text_bboxes.append(bbox)
                print(f"🔍    Using {len(question_text_bboxes)} question_text blocks for flexible gap detection")
                # Determine source bboxes for gap detection
                bbox_source = question_text_bboxes if question_text_bboxes else question_answer_blocks
                prompt_bbox_single = construct_image_area_from_gaps_flexible(page, bbox_source, all_text_bboxes)
                if prompt_bbox_single:
                    prompt_bboxes = [prompt_bbox_single]

            if prompt_bboxes:
                for i, p_bbox in enumerate(prompt_bboxes):
                    width = p_bbox[2] - p_bbox[0]
                    height = p_bbox[3] - p_bbox[1]
                    print(f"🔍 ✅ FOUND prompt visual area #{i + 1}:")
                    print(f"🔍    Bbox: [{p_bbox[0]:.1f}, {p_bbox[1]:.1f}, {p_bbox[2]:.1f}, {p_bbox[3]:.1f}]")
                    print(f"🔍    Size: {width:.1f} x {height:.1f} pixels")
                    print(f"🔍    Area: {width * height:.0f} square pixels")
            else:
                print("🔍 ❌ All image area detection methods failed")
                print("🔍 🔍 Debugging detection failure...")
                # Add debug info about why detection might have failed
                if not question_answer_blocks:
                    print("🔍 ⚠️  No question/answer blocks identified")
                if not image_label_blocks:
                    print("🔍 ⚠️  No image label blocks identified")
                print(f"🔍 ⚠️  Total text blocks: {len(all_text_bboxes)}")

        except Exception as e:
            print(f"🔍 ❌ Image area detection failed with exception: {e}")
            import traceback

            print(f"🔍 📋 Image area detection traceback: {traceback.format_exc()}")
            prompt_bboxes = []
    else:
        print("🔍 📸 LLM did not detect prompt visuals - skipping gap detection")
        prompt_bboxes = []
        choice_image_labels = list(image_label_blocks)
        if choice_image_labels:
            print(f"🔍    Assigning all {len(choice_image_labels)} image labels to choices.")

    # For choice visuals, extract individual choice images based on answer choice blocks
    if analysis.has_choice_visuals:
        print("🔍 🎯 LLM detected choice visuals - extracting individual choice images...")
        choice_extraction_result = extract_choice_images(
            page, text_blocks, block_categories, all_text_bboxes, question_answer_blocks, choice_image_labels
        )
        choice_bboxes = choice_extraction_result["extracted_images"]
        total_choice_blocks = choice_extraction_result["total_choices_found"]

        print(f"🔍 ✅ Extracted {len(choice_bboxes)} of {total_choice_blocks} choice images")
    else:
        print("🔍 🎯 LLM did not detect choice visuals")
        choice_bboxes = []
        total_choice_blocks = 0

    # Build choice regions from extracted choice bboxes
    choice_regions = []
    if choice_bboxes:
        for choice_info in choice_bboxes:
            choice_regions.append(
                {"bbox": choice_info["bbox"], "description": choice_info["description"], "choice_letter": choice_info["choice_letter"]}
            )

    prompt_regions = []
    if prompt_bboxes:
        for bbox in prompt_bboxes:
            prompt_regions.append({"bbox": bbox, "description": analysis.prompt_visual_description})

    result = {
        "has_prompt_visuals": analysis.has_prompt_visuals,
        "has_choice_visuals": analysis.has_choice_visuals,
        "prompt_visual_description": analysis.prompt_visual_description,
        "choice_visual_description": analysis.choice_visual_description,
        "prompt_bboxes": prompt_bboxes,
        "choice_bboxes": choice_bboxes,  # Keep full choice info dictionaries
        "total_choice_blocks": total_choice_blocks,
        "prompt_regions": prompt_regions,
        "choice_regions": choice_regions,
        "reasoning": analysis.reasoning,
        "block_categories": block_categories,
    }

    print("🔍 📊 FINAL SEPARATION RESULTS:")
    print(f"🔍    Prompt visuals: {result['has_prompt_visuals']}")
    print(f"🔍    Choice visuals: {result['has_choice_visuals']}")
    print(f"🔍    Prompt bboxes found: {len(result.get('prompt_bboxes', []))}")
    print(f"🔍    Choice bboxes found: {len(result['choice_bboxes'])}")
    print(f"🔍    Total choice blocks: {result.get('total_choice_blocks', 'N/A')}")
    print(f"🔍    Block categories: {len(result['block_categories'])}")
    print("🔍 " + "=" * 60)

    return result
