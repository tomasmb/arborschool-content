"""
PDF Content Processor

This module extracts structured content and images from PDF files
for use in QTI conversion. Uses PyMuPDF for structured data and 
GPT-5.1 vision for intelligent content categorization, following
converter guidelines to avoid overfitting and leverage AI capabilities.
"""

import base64
import io
from json import JSONEncoder
from typing import Any, Dict, List, Optional

import fitz  # type: ignore
from PIL import Image, ImageChops

from .ai_processing import analyze_pdf_content_with_ai
from .content_processing.table_reconstructor import detect_scattered_table_blocks, reconstruct_table_from_blocks

# Import organized modules
from .image_processing import (
    assess_pymupdf_image_adequacy,
    detect_and_extract_choice_diagrams,
    detect_images_with_ai,
    expand_image_bbox_to_boundaries,
    expand_pymupdf_bbox_intelligently,
    separate_prompt_and_choice_images,
    should_use_ai_image_detection,
    shrink_image_bbox_away_from_text,
)
from .image_processing.bbox_utils import (
    MIN_IMAGE_HEIGHT,
    MIN_IMAGE_WIDTH,
    bbox_overlap_percentage,
)
from .image_processing.multipart_images import (
    detect_multipart_question_images,
    detect_part_specific_images_with_ai,
    filter_images_for_multipart_question,
)
from .utils import (
    combine_structured_data,
    convert_table_to_html,
    create_combined_image,
    get_page_image,
)


class CustomJSONEncoder(JSONEncoder):
    """Custom JSON encoder that can handle bytes objects."""
    def default(self, obj):
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode('utf-8')
        return JSONEncoder.default(self, obj)


def extract_pdf_content(doc: fitz.Document, openai_api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract comprehensive content from a PDF document using AI-powered analysis.
    
    Following converter guidelines:
    - Use PyMuPDF first for structured data
    - Fallback to GPT-5.1 vision for image detection
    - Leverage AI categorization throughout the pipeline
    
    Args:
        doc: PyMuPDF document object
        openai_api_key: OpenAI API key for AI-powered content analysis
        
    Returns:
        Dictionary containing structured text, images, and metadata
    """
    content = {
        "page_count": doc.page_count,
        "pages": [],
        "combined_text": "",
        "image_base64": None,
        "structured_data": None,
        "all_images": []
    }

    # Process each page with AI-powered analysis
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)

        # Extract structured text data using PyMuPDF
        structured_text = page.get_text("dict", sort=True)

        # Extract plain text
        plain_text = page.get_text()

        # Get page image for AI analysis
        page_image = get_page_image(page)

        # Extract images and tables with AI categorization
        extracted_content = extract_images_and_tables(
            page, structured_text, openai_api_key
        )

        # Add page info to extracted images
        for img in extracted_content["images"]:
            img["page_number"] = page_num

        page_content = {
            "page_number": page_num,
            "structured_text": structured_text,
            "plain_text": plain_text,
            "page_image_base64": extracted_content.get("page_image_base64") or base64.b64encode(page_image).decode('utf-8'),
            "bbox": [page.rect.x0, page.rect.y0, page.rect.x1, page.rect.y1],
            "width": page.rect.width,
            "height": page.rect.height,
            "extracted_images": extracted_content["images"],
            "extracted_tables": extracted_content["tables"],
            "ai_categories": extracted_content.get("ai_categories", {})  # Include AI categories
        }

        content["pages"].append(page_content)
        content["combined_text"] += plain_text + "\n"
        content["all_images"].extend(extracted_content["images"])

    # Set main image based on content structure and ensure it's always available for validation
    content["has_extracted_images"] = bool(content["all_images"])

    # CRITICAL FIX: Always provide the image_base64 for validation.
    # The presence of extracted images should not nullify the main page image.
    if doc.page_count == 1:
        content["image_base64"] = content["pages"][0]["page_image_base64"]
    else:
        # For multi-page docs, a combined image is the best representation for validation.
        content["image_base64"] = create_combined_image(doc)

    # Set structured data
    if doc.page_count == 1:
        content["structured_data"] = content["pages"][0]["structured_text"]
    else:
        content["structured_data"] = combine_structured_data(content["pages"])

    return content


def extract_text_blocks(structured_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract text blocks from structured data.
    
    Args:
        structured_data: PyMuPDF structured text data
        
    Returns:
        List of text blocks with extracted text content
    """
    blocks = structured_data.get("blocks", [])
    text_blocks = []

    for i, block in enumerate(blocks):
        if block.get("type") == 0:  # Text block
            block_copy = block.copy()
            block_copy["text"] = extract_block_text(block)
            block_copy["number"] = i
            text_blocks.append(block_copy)

    return text_blocks


def extract_block_text(block: Dict[str, Any]) -> str:
    """
    Extract text from a PyMuPDF text block.
    
    Args:
        block: PyMuPDF block dictionary
        
    Returns:
        Extracted text string
    """
    text_parts = []

    for line in block.get('lines', []):
        line_text = ""
        for span in line.get('spans', []):
            line_text += span.get('text', '')
        text_parts.append(line_text)

    return " ".join(text_parts).strip()


def extract_question_text(text_blocks: List[Dict[str, Any]]) -> str:
    """
    Extract combined question text from all text blocks for choice diagram detection.
    
    Args:
        text_blocks: List of text blocks from PyMuPDF
        
    Returns:
        Combined text string
    """
    combined_text = ""

    for block in text_blocks:
        if block.get("type") == 0:  # Text block
            block_text = extract_block_text(block)
            if block_text.strip():
                combined_text += " " + block_text.strip()

    return combined_text.strip()


def split_choice_blocks(structured_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Split blocks that contain multiple answer choices into separate blocks.
    
    This fixes the issue where PyMuPDF groups multiple choice letters (e.g., "A B") 
    into a single block, which causes problems with choice image extraction.
    
    Args:
        structured_data: PyMuPDF structured text data containing blocks
        
    Returns:
        Modified structured data with choice blocks split appropriately
    """
    blocks = structured_data.get("blocks", [])
    new_blocks = []

    for block in blocks:
        if block.get("type") != 0:  # Not a text block
            new_blocks.append(block)
            continue

        # Extract text from the block to check for multiple choices
        block_text = extract_block_text(block)

        # Check if this block contains multiple choice letters
        # Pattern: Look for blocks that have multiple choice letters (A, B, C, D) separated by whitespace
        import re
        choice_pattern = r'(?:^|\s)([A-D])(?:\s|$)'
        choice_matches = re.findall(choice_pattern, block_text)

        # Only split if we find exactly 2 choice letters (common grouping pattern)
        # and the block is relatively short (to avoid splitting long text blocks)
        if len(choice_matches) == 2 and len(block_text.strip()) < 50:
            print(f"🔧 Splitting choice block: '{block_text.strip()}' -> {choice_matches}")

            # More precise splitting: split based on which spans contain each choice letter
            lines = block.get("lines", [])
            first_choice_lines = []
            second_choice_lines = []

            # Analyze each line to see which choice it belongs to
            for line in lines:
                line_text = ""
                for span in line.get("spans", []):
                    line_text += span.get("text", "")

                # Check which choice letter this line contains
                if choice_matches[0] in line_text and choice_matches[1] not in line_text:
                    # Line contains only first choice
                    first_choice_lines.append(line)
                elif choice_matches[1] in line_text and choice_matches[0] not in line_text:
                    # Line contains only second choice
                    second_choice_lines.append(line)
                elif choice_matches[0] in line_text and choice_matches[1] in line_text:
                    # Line contains both - this is the tricky case
                    # We need to split the line itself based on horizontal position
                    spans = line.get("spans", [])
                    first_choice_spans = []
                    second_choice_spans = []

                    # Find approximate horizontal middle of the line
                    if spans:
                        line_left = min(span.get("bbox", [0, 0, 0, 0])[0] for span in spans if span.get("bbox"))
                        line_right = max(span.get("bbox", [0, 0, 0, 0])[2] for span in spans if span.get("bbox"))
                        line_middle = (line_left + line_right) / 2

                        for span in spans:
                            span_bbox = span.get("bbox", [0, 0, 0, 0])
                            span_center = (span_bbox[0] + span_bbox[2]) / 2

                            if span_center < line_middle:
                                first_choice_spans.append(span)
                            else:
                                second_choice_spans.append(span)

                        # Create separate lines for each choice
                        if first_choice_spans:
                            first_line = line.copy()
                            first_line["spans"] = first_choice_spans
                            first_choice_lines.append(first_line)

                        if second_choice_spans:
                            second_line = line.copy()
                            second_line["spans"] = second_choice_spans
                            second_choice_lines.append(second_line)
                else:
                    # Line doesn't contain either choice - could be shared content
                    # Add to both (this handles things like "rgy" that might be shared)
                    first_choice_lines.append(line)
                    second_choice_lines.append(line)

            # Create the two new blocks
            if first_choice_lines and second_choice_lines:
                # First block
                first_block = block.copy()
                first_block["lines"] = first_choice_lines

                # Second block
                second_block = block.copy()
                second_block["lines"] = second_choice_lines

                # Adjust bounding boxes based on the actual content
                if "bbox" in block and len(block["bbox"]) >= 4:
                    original_bbox = block["bbox"]

                    # Calculate bboxes for each choice based on their spans
                    first_spans_bboxes = []
                    second_spans_bboxes = []

                    for line in first_choice_lines:
                        for span in line.get("spans", []):
                            if span.get("bbox"):
                                first_spans_bboxes.append(span["bbox"])

                    for line in second_choice_lines:
                        for span in line.get("spans", []):
                            if span.get("bbox"):
                                second_spans_bboxes.append(span["bbox"])

                    # Set first block bbox
                    if first_spans_bboxes:
                        first_block["bbox"] = [
                            min(bbox[0] for bbox in first_spans_bboxes),
                            min(bbox[1] for bbox in first_spans_bboxes),
                            max(bbox[2] for bbox in first_spans_bboxes),
                            max(bbox[3] for bbox in first_spans_bboxes)
                        ]

                    # Set second block bbox
                    if second_spans_bboxes:
                        second_block["bbox"] = [
                            min(bbox[0] for bbox in second_spans_bboxes),
                            min(bbox[1] for bbox in second_spans_bboxes),
                            max(bbox[2] for bbox in second_spans_bboxes),
                            max(bbox[3] for bbox in second_spans_bboxes)
                        ]

                new_blocks.append(first_block)
                new_blocks.append(second_block)
            else:
                # Fallback: keep original block if we can't split properly
                new_blocks.append(block)
        else:
            # Keep original block unchanged
            new_blocks.append(block)

    # Return modified structured data
    result = structured_data.copy()
    result["blocks"] = new_blocks
    return result


def extract_images_and_tables(
    page: fitz.Page,
    structured_data: Dict[str, Any],
    openai_api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract images and tables using AI-powered analysis and PyMuPDF.
    
    Following converter guidelines:
    1. Use PyMuPDF first for table detection  
    2. Use GPT-5.1 for two-step LLM approach: compatibility + categorization
    3. Build image BBOX using AI categorization results
    4. Ensure deterministic and explainable logic
    
    Args:
        page: PyMuPDF page object
        structured_data: PyMuPDF structured text data
        openai_api_key: OpenAI API key for AI-powered analysis
        
    Returns:
        Dictionary with images, tables, and AI analysis results
    """
    # TARGETED FIX: Split choice blocks before processing
    structured_data = split_choice_blocks(structured_data)

    images = []
    tables_info = []
    ai_analysis_result = {}

    all_blocks = structured_data.get("blocks", [])
    image_blocks = [block for block in all_blocks if block.get("type") == 1]

    # Step 1: Use PyMuPDF's built-in table detection (guideline #1)
    print("📊 Step 1: PyMuPDF table detection...")
    detected_tables = extract_tables_with_pymupdf(page)
    tables_info.extend(detected_tables)

    # Step 1.5: If PyMuPDF failed, try to reconstruct tables from scattered blocks
    if not detected_tables:
        print("📊 Step 1.5: PyMuPDF found no tables, trying reconstruction...")
        table_structure = detect_scattered_table_blocks(all_blocks)
        if table_structure:
            reconstructed_table = reconstruct_table_from_blocks(table_structure)
            if reconstructed_table:
                tables_info.append(reconstructed_table)
                print("📊 ✅ Reconstructed table from scattered blocks")

    # Step 2: AI-powered content analysis (OPTIMIZED: single comprehensive call)
    if openai_api_key:
        print("🧠 Step 2: AI-powered content analysis...")
        ai_analysis_result = analyze_pdf_content_with_ai(page, structured_data, openai_api_key)

        if ai_analysis_result.get("success", False):
            ai_categories = ai_analysis_result.get("ai_categories", {})
            has_visual_content = ai_analysis_result.get("has_visual_content", False)

            print("🧠 ✅ AI Analysis complete:")
            print(f"   Visual content required: {has_visual_content}")
            print(f"   Categories assigned: {len(ai_categories)} blocks")
        else:
            print("🧠 ⚠️ AI analysis failed, falling back to PyMuPDF only")
            ai_categories = {}
            has_visual_content = should_use_ai_image_detection(all_blocks, openai_api_key)
    else:
        print("🧠 No OpenAI API key, using fallback image detection")
        ai_categories = {}
        has_visual_content = should_use_ai_image_detection(all_blocks, None)

    # Step 3: OPTIMIZED - Use visual separation from comprehensive analysis if available
    prompt_choice_analysis = None
    if has_visual_content:
        # Check if comprehensive analysis already included visual separation
        # Robust handling: ensure ai_analysis_result is a dict
        if not isinstance(ai_analysis_result, dict):
            print(f"⚠️  Warning: ai_analysis_result is not a dict, type: {type(ai_analysis_result)}")
            ai_analysis_result = {}

        visual_separation_raw = None
        if ai_analysis_result.get("success"):
            visual_separation_raw = ai_analysis_result.get("visual_separation")

        # Ensure visual_separation is a dict, not a list
        visual_separation = None
        if visual_separation_raw:
            if isinstance(visual_separation_raw, dict):
                visual_separation = visual_separation_raw
            elif isinstance(visual_separation_raw, list):
                # If it's a list, try to extract dict from it
                for item in visual_separation_raw:
                    if isinstance(item, dict):
                        visual_separation = item
                        break
                if visual_separation is None:
                    print("⚠️  Warning: visual_separation is a list but no dict found inside")

        if visual_separation and isinstance(visual_separation, dict) and visual_separation.get("has_prompt_visuals") is not None:
            print("📸 Step 3: Using visual separation from comprehensive analysis (OPTIMIZED - no extra API call)")
            # Need to process this through gap detection to get bboxes
            # Create a mock analysis object for process_llm_analysis_with_gaps
            class MockAnalysis:
                def __init__(self, visual_sep_data: dict):
                    # Ensure visual_sep_data is a dict
                    if not isinstance(visual_sep_data, dict):
                        visual_sep_data = {}
                    self.has_prompt_visuals = visual_sep_data.get("has_prompt_visuals", False)
                    self.has_choice_visuals = visual_sep_data.get("has_choice_visuals", False)
                    self.prompt_visual_description = visual_sep_data.get("prompt_visual_description", "")
                    self.choice_visual_description = visual_sep_data.get("choice_visual_description", "")
                    self.separation_confidence = visual_sep_data.get("separation_confidence", 0.8)
                    self.reasoning = visual_sep_data.get("reasoning", "")

            try:
                from .image_processing.llm_analyzer import process_llm_analysis_with_gaps
                # Ensure visual_separation is a dict before passing to MockAnalysis
                if not isinstance(visual_separation, dict):
                    raise ValueError(f"visual_separation must be a dict, got {type(visual_separation)}")

                mock_analysis = MockAnalysis(visual_separation)
                # extract_text_blocks expects a dict with "blocks" key, not a list
                text_blocks_for_gaps = extract_text_blocks({"blocks": all_blocks})
                prompt_choice_analysis = process_llm_analysis_with_gaps(
                    mock_analysis, page, text_blocks_for_gaps, ai_categories
                )
                prompt_choice_analysis["success"] = True
                prompt_choice_analysis["confidence"] = visual_separation.get("separation_confidence", 0.8) if isinstance(visual_separation, dict) else 0.8
                prompt_choice_analysis["ai_categories"] = ai_categories

                # Only print results if processing was successful
                print("🔍 Analysis results (from comprehensive analysis):")
                print(f"   Prompt visuals: {prompt_choice_analysis.get('has_prompt_visuals', False)}")
                print(f"   Choice visuals: {prompt_choice_analysis.get('has_choice_visuals', False)}")
                print(f"   Confidence: {prompt_choice_analysis.get('confidence', 0):.2f}")
            except Exception as e:
                print(f"⚠️  Error procesando visual separation del análisis comprehensivo: {e}")
                import traceback
                traceback.print_exc()
                prompt_choice_analysis = None  # Force fallback - will trigger separate API call below

            # If processing failed, activate fallback (requires separate API call)
            if prompt_choice_analysis is None:
                print("📸 Step 3: Fallback - Analyzing prompt vs choice visual content (separate API call)...")
                prompt_choice_analysis = separate_prompt_and_choice_images(
                    page, all_blocks, extract_question_text(all_blocks), ai_categories, openai_api_key
                )

                print("🔍 Analysis results (from fallback):")
                print(f"   Prompt visuals: {prompt_choice_analysis.get('has_prompt_visuals', False)}")
                print(f"   Choice visuals: {prompt_choice_analysis.get('has_choice_visuals', False)}")
                print(f"   Confidence: {prompt_choice_analysis.get('confidence', 0):.2f}")
        else:
            # Fallback: Separate call to analyze visual content
            print("📸 Step 3: Analyzing prompt vs choice visual content (fallback API call)...")
            prompt_choice_analysis = separate_prompt_and_choice_images(
                page, all_blocks, extract_question_text(all_blocks), ai_categories, openai_api_key
            )

            print("🔍 Analysis results:")
            print(f"   Prompt visuals: {prompt_choice_analysis.get('has_prompt_visuals', False)}")
            print(f"   Choice visuals: {prompt_choice_analysis.get('has_choice_visuals', False)}")
            print(f"   Confidence: {prompt_choice_analysis.get('confidence', 0):.2f}")

    # Step 4: Process images based on separation analysis
    if prompt_choice_analysis and prompt_choice_analysis.get('success', False):
        # Use new intelligent separation approach
        images = []
        choice_images = []

        # Update ai_categories with the separator's analysis if available
        if prompt_choice_analysis.get('ai_categories'):
            ai_categories.update(prompt_choice_analysis['ai_categories'])
            print(f"🔍 Updated AI categories with {len(prompt_choice_analysis['ai_categories'])} classifications")

        # Process prompt images (essential for question understanding)
        if prompt_choice_analysis.get('has_prompt_visuals') and prompt_choice_analysis.get('prompt_bboxes'):
            prompt_bboxes = prompt_choice_analysis['prompt_bboxes']
            # Ensure prompt_bboxes is a list
            if not isinstance(prompt_bboxes, list):
                print(f"⚠️  Warning: prompt_bboxes is not a list, type: {type(prompt_bboxes)}")
                prompt_bboxes = []

            print(f"📸 Processing {len(prompt_bboxes)} prompt image(s)...")

            for i, prompt_bbox in enumerate(prompt_bboxes):
                # Ensure prompt_bbox is a list, not a dict
                if isinstance(prompt_bbox, dict):
                    prompt_bbox = prompt_bbox.get('bbox', [0, 0, 0, 0])
                elif not isinstance(prompt_bbox, list) or len(prompt_bbox) < 4:
                    print(f"⚠️  Warning: Invalid prompt_bbox format at index {i}, skipping")
                    continue

                print(f"📸  - Processing prompt image #{i+1}: {prompt_bbox}")
                # Render prompt image
                rendered_prompt_image = render_image_area(page, prompt_bbox, prompt_bbox, i)
                if rendered_prompt_image:
                    rendered_prompt_image["is_prompt_image"] = True
                    rendered_prompt_image["description"] = prompt_choice_analysis.get('prompt_visual_description', 'Question prompt visual content')
                    rendered_prompt_image["detection_method"] = "llm_separation"
                    images.append(rendered_prompt_image)
                    print(f"📸 ✅ Rendered prompt image #{i+1}: {rendered_prompt_image['width']}x{rendered_prompt_image['height']}")

        # Process choice images (answer options)
        if prompt_choice_analysis.get('has_choice_visuals') and prompt_choice_analysis.get('choice_bboxes'):
            choice_bboxes = prompt_choice_analysis['choice_bboxes']
            total_choices = prompt_choice_analysis.get('total_choice_blocks', len(choice_bboxes))

            # CRITICAL CHECK: Ensure we have an image for every choice detected
            if total_choices > 0 and len(choice_bboxes) != total_choices:
                error_msg = f"Mismatch between detected choices ({total_choices}) and extracted choice images ({len(choice_bboxes)}). Aborting to prevent incorrect QTI."
                print(f"📸 ❌ ERROR: {error_msg}")
                raise ValueError(error_msg)

            print(f"📸 Processing {len(choice_bboxes)} choice images")

            for i, choice_info in enumerate(choice_bboxes):
                choice_bbox = choice_info['bbox']
                choice_letter = choice_info.get('choice_letter', f'Choice{i+1}')
                mask_areas = choice_info.get('text_mask_areas', [])

                rendered_choice_image = render_image_area(page, choice_bbox, choice_bbox, len(images), mask_areas)
                if rendered_choice_image:
                    rendered_choice_image["is_choice_diagram"] = True
                    rendered_choice_image["choice_letter"] = choice_letter
                    rendered_choice_image["description"] = choice_info.get('description', f'Choice {choice_letter} diagram')
                    rendered_choice_image["detection_method"] = "llm_separation"
                    choice_images.append(rendered_choice_image)
                    images.append(rendered_choice_image)
                    print(f"📸 ✅ Rendered choice {choice_letter}: {rendered_choice_image['width']}x{rendered_choice_image['height']}")

        # If we have choice images, include page image for validation
        if choice_images:
            page_image_base64 = base64.b64encode(get_page_image(page)).decode('utf-8')
            return {
                "images": images,
                "tables": tables_info,
                "ai_categories": ai_categories,
                "ai_analysis": ai_analysis_result,
                "has_visual_content": has_visual_content,
                "is_choice_diagram": len(choice_images) > 0,
                "is_prompt_and_choice": len(images) > len(choice_images),
                "page_image_base64": page_image_base64,
                "prompt_choice_analysis": prompt_choice_analysis
            }

        # If we have prompt images but no choice images, continue with regular processing
        if images:
            return {
                "images": images,
                "tables": tables_info,
                "ai_categories": ai_categories,
                "ai_analysis": ai_analysis_result,
                "has_visual_content": has_visual_content,
                "is_choice_diagram": False,
                "is_prompt_and_choice": False,
                "prompt_choice_analysis": prompt_choice_analysis
            }

    # FALLBACK: Use old approach if new separation fails or isn't confident enough
    print("📸 Step 3 (Fallback): Using original choice diagram detection...")

    # OLD APPROACH - Check for specialized choice diagram questions
    if has_visual_content and ai_categories:
        print("📸 Step 3: Checking for choice diagram questions...")

        # Try to detect and extract choice diagrams
        choice_images = detect_and_extract_choice_diagrams(
            page, all_blocks, ai_categories, extract_question_text(all_blocks)
        )

        if choice_images:
            print(f"🎯 ✅ Detected choice diagram question with {len(choice_images)} choices")
            # For choice diagrams, return immediately - don't use regular image processing

            # CRITICAL FIX: Ensure full page image is still available for validation
            page_image_base64 = base64.b64encode(get_page_image(page)).decode('utf-8')

            return {
                "images": choice_images,
                "tables": tables_info,
                "ai_categories": ai_categories,
                "ai_analysis": ai_analysis_result,
                "has_visual_content": has_visual_content,
                "is_choice_diagram": True,
                "page_image_base64": page_image_base64
            }

    # Step 3.5: Handle multi-part questions with part-specific images
    multipart_info = detect_multipart_question_images(
        all_blocks, ai_categories, extract_question_text(all_blocks)
    )

    # If this needs specialized AI detection for part-specific images
    if multipart_info and multipart_info[0].get("needs_special_ai_detection"):
        parts_with_visuals = multipart_info[0]["parts_with_visuals"]
        print(f"🎯 Running specialized AI detection for parts: {parts_with_visuals}")

        part_specific_images = detect_part_specific_images_with_ai(
            page, all_blocks, parts_with_visuals, openai_api_key
        )

        if part_specific_images:
            print(f"🎯 Specialized AI found {len(part_specific_images)} part-specific images")
            images = []

            # Render the part-specific images
            for img_info in part_specific_images:
                bbox = img_info["bbox"]
                part_context = img_info["part_context"]

                rendered_image = render_image_area(page, bbox, bbox, len(images))
                if rendered_image:
                    rendered_image["part_context"] = part_context
                    rendered_image["detection_method"] = "multipart_ai"
                    rendered_image["description"] = img_info.get("description", "")
                    images.append(rendered_image)
                    print(f"📸 ✅ Rendered Part {part_context} image: {rendered_image['width']}x{rendered_image['height']}")

            if images:
                return {
                    "images": images,
                    "tables": tables_info,
                    "ai_categories": ai_categories,
                    "ai_analysis": ai_analysis_result,
                    "has_visual_content": has_visual_content,
                    "is_multipart_with_images": True
                }

    # If this is a multi-part question with visual content, let the regular pipeline
    # detect images, but we'll filter them afterwards for the right context

    # Step 4: Regular image processing (if not a choice diagram question)
    meaningful_images = []

    if image_blocks:
        print("📸 Step 4a: Processing PyMuPDF image blocks...")
        # Filter meaningful images (avoid table areas)
        candidate_images = []
        for i, image_block in enumerate(image_blocks):
            bbox = image_block.get("bbox", [0, 0, 0, 0])

            # Check if this overlaps with detected tables
            is_table_area = any(
                bbox_overlap_percentage(bbox, table["bbox"]) > 0.5
                for table in detected_tables
            )

            if not is_table_area and is_meaningful_image(bbox):
                candidate_images.append((i, image_block))
                print(f"📸 ✅ Image {i+1} is meaningful and separate from tables")

        # Step 4b: Assess if PyMuPDF images are adequate for the content
        if candidate_images and has_visual_content:
            print("📸 Step 4b: Assessing PyMuPDF image adequacy...")

            # Extract just the image blocks for assessment
            image_blocks_only = [img_block for _, img_block in candidate_images]
            adequacy_result = assess_pymupdf_image_adequacy(
                image_blocks_only, page, all_blocks, openai_api_key
            )

            if adequacy_result["adequate"]:
                print(f"📸 ✅ PyMuPDF images are adequate: {adequacy_result['reason']}")
                meaningful_images = candidate_images
            else:
                print(f"📸 ⚠️ PyMuPDF images inadequate: {adequacy_result['reason']}")
                print("📸 Step 4c: Using smart expansion of PyMuPDF bbox...")

                # Use smart expansion instead of AI gap method
                for i, image_block in candidate_images:
                    original_bbox = image_block.get("bbox", [0, 0, 0, 0])

                    # Expand the PyMuPDF bbox intelligently
                    expanded_bbox = expand_pymupdf_bbox_intelligently(
                        original_bbox, page, all_blocks, ai_categories
                    )

                    # Create expanded image block
                    expanded_image_block = image_block.copy()
                    expanded_image_block["bbox"] = expanded_bbox
                    expanded_image_block["original_bbox"] = original_bbox
                    expanded_image_block["expansion_method"] = "smart_expansion"

                    meaningful_images.append((i, expanded_image_block))

                print(f"📸 ✅ Smart expansion applied to {len(meaningful_images)} images")
        elif candidate_images:
            # If we have images but AI doesn't think visual content is needed,
            # trust PyMuPDF detection
            meaningful_images = candidate_images

    # Step 5: Use AI detection only if no PyMuPDF images found at all
    if not meaningful_images and has_visual_content:
        print("📸 Step 5: No PyMuPDF images found, using AI-powered detection...")
        ai_detected_images = detect_images_with_ai(page, all_blocks, openai_api_key)

        if ai_detected_images:
            print(f"📸 AI detection found {len(ai_detected_images)} potential image areas")
            for i, img_area in enumerate(ai_detected_images):
                meaningful_images.append((i, img_area))
                # Update AI categories if not already set
                if 'ai_categories' in img_area and not ai_categories:
                    ai_categories = img_area['ai_categories']
                    print("📸 ✅ Using AI categories from image detection")

    # Step 6: Process each meaningful image with AI-guided bbox operations
    for idx, (original_idx, image_block) in enumerate(meaningful_images):
        original_bbox = image_block.get("bbox", [0, 0, 0, 0])

        print(f"📸 Processing image {idx+1}/{len(meaningful_images)}: {original_bbox}")

        # Expand bbox using deterministic logic (guideline #6)
        expanded_bbox = expand_image_bbox_to_boundaries(original_bbox, all_blocks, page)

        # Shrink away from question/answer text using AI categorization (guideline #3)
        final_bbox = shrink_image_bbox_away_from_text(
            expanded_bbox, all_blocks, page, ai_categories
        )

        # Render the final image area
        rendered_image = render_image_area(page, final_bbox, original_bbox, idx)
        if rendered_image:
            images.append(rendered_image)

    print(f"📸 ✅ Final results: {len(images)} images, {len(tables_info)} tables")

    # Step 7: Apply multipart filtering if applicable
    if multipart_info and images:
        filtered_images = filter_images_for_multipart_question(
            images, all_blocks, extract_question_text(all_blocks)
        )
        if filtered_images != images:
            images = filtered_images
            print(f"📸 ✅ Multipart filtering applied: {len(images)} relevant images retained")

    # Return comprehensive results including AI analysis
    return {
        "images": images,
        "tables": tables_info,
        "ai_categories": ai_categories,
        "ai_analysis": ai_analysis_result,
        "has_visual_content": has_visual_content
    }


def extract_tables_with_pymupdf(page: fitz.Page) -> List[Dict[str, Any]]:
    """Extract tables using PyMuPDF's built-in detection."""
    detected_tables = []

    try:
        table_finder = page.find_tables()
        tables = list(table_finder)  # Convert TableFinder to list

        if tables:
            print(f"📊 PyMuPDF detected {len(tables)} tables")

            for i, table in enumerate(tables):
                table_data = table.extract()
                table_bbox = table.bbox

                structured_table = {
                    "type": "detected_table",
                    "table_index": i,
                    "bbox": list(table_bbox),
                    "rows": len(table_data) if table_data else 0,
                    "cols": len(table_data[0]) if table_data and len(table_data) > 0 else 0,
                    "content": table_data,
                    "html_content": convert_table_to_html(table_data)
                }

                detected_tables.append(structured_table)
                print(f"📊 ✅ Table {i+1}: {structured_table['rows']}x{structured_table['cols']}")
        else:
            print("📊 No tables detected by PyMuPDF")

    except Exception as e:
        print(f"⚠️ PyMuPDF table detection failed: {e}")

    return detected_tables


def is_meaningful_image(bbox: List[float]) -> bool:
    """
    Check if an image bbox represents meaningful content.
    Uses conservative thresholds to avoid overfitting.
    """
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    area = width * height
    aspect_ratio = max(width, height) / min(width, height) if min(width, height) > 0 else float('inf')

    # Conservative criteria without overfitted thresholds
    return (area > 100 and
            aspect_ratio < 30 and
            width >= MIN_IMAGE_WIDTH and
            height >= MIN_IMAGE_HEIGHT)


def _trim_whitespace(image_bytes: bytes) -> bytes:
    """Trims whitespace from an image."""
    try:
        image = Image.open(io.BytesIO(image_bytes))

        # Get the background color of the top-left pixel
        bg_color = image.getpixel((0, 0))

        # Create a background image of the same size
        bg = Image.new(image.mode, image.size, bg_color)

        # Find the difference between the image and the background
        diff = ImageChops.difference(image, bg)

        # Find the bounding box of the non-background area
        bbox = diff.getbbox()

        if bbox:
            # Crop the image to the bounding box
            trimmed_image = image.crop(bbox)

            # Save the trimmed image back to bytes
            buf = io.BytesIO()
            trimmed_image.save(buf, format='PNG')
            return buf.getvalue()

    except Exception as e:
        print(f"⚠️ Error trimming whitespace: {e}")

    # If anything fails, return the original image bytes
    return image_bytes


def render_image_area(
    page: fitz.Page,
    final_bbox: List[float],
    original_bbox: List[float],
    idx: int,
    mask_areas: Optional[List[Dict[str, Any]]] = None
) -> Optional[Dict[str, Any]]:
    """
    Render the final image area with optional text masking.
    
    Args:
        page: PyMuPDF page object
        final_bbox: Final bounding box for the image
        original_bbox: Original bounding box (for reference)
        idx: Image index
        mask_areas: Optional list of text areas to mask (for choice letters in diagrams)
    """
    try:
        render_rect = fitz.Rect(final_bbox)

        if not render_rect.is_empty and render_rect.width > 1 and render_rect.height > 1:
            scale = 2.0
            matrix = fitz.Matrix(scale, scale)

            # If we have mask areas, create a temporary page with masked text
            if mask_areas:
                # Create a copy of the page for masking
                temp_doc = fitz.open()
                temp_page = temp_doc.new_page(width=page.rect.width, height=page.rect.height)

                # Copy the page content
                temp_page.show_pdf_page(page.rect, page.parent, page.number)

                # Apply text masks by drawing background-colored rectangles over choice letters
                for mask_area in mask_areas:
                    mask_bbox = mask_area.get("bbox", [])
                    if len(mask_bbox) == 4:
                        mask_rect = fitz.Rect(mask_bbox)

                        # Get the background color at this location by sampling a nearby pixel
                        # For most PDFs, white (1,1,1) works, but let's be much more aggressive
                        # to ensure complete coverage of choice letters
                        expanded_rect = fitz.Rect(
                            mask_rect.x0 - 10, mask_rect.y0 - 5,
                            mask_rect.x1 + 10, mask_rect.y1 + 5
                        )

                        # Draw white rectangle to mask the text with slight expansion
                        temp_page.draw_rect(expanded_rect, color=(1, 1, 1), fill=(1, 1, 1))
                        print(f"🎭 Masked text area: {mask_area.get('text_to_mask', 'unknown')} at {mask_bbox}")

                # Render from the masked page
                pix = temp_page.get_pixmap(matrix=matrix, clip=render_rect, alpha=False)
                temp_doc.close()
            else:
                # Regular rendering without masking
                pix = page.get_pixmap(matrix=matrix, clip=render_rect, alpha=False)

            img_bytes = pix.tobytes("png")

            # Trim whitespace from the rendered image
            trimmed_bytes = _trim_whitespace(img_bytes)

            # Get new dimensions from trimmed image
            trimmed_img_pil = Image.open(io.BytesIO(trimmed_bytes))
            new_width, new_height = trimmed_img_pil.size

            # Convert image bytes to base64 string for consistent processing
            image_base64 = base64.b64encode(trimmed_bytes).decode('utf-8')

            result = {
                "bbox": final_bbox,
                "width": new_width,
                "height": new_height,
                "ext": "png",
                "image_base64": image_base64,  # Store as base64 string for content processor
                "is_table": False,
                "is_grouped": False,
                "is_expanded": True,
                "original_bbox": original_bbox,
                "has_text_masking": bool(mask_areas)
            }

            if mask_areas:
                print(f"📸 ✅ Rendered and trimmed masked image {idx+1}: {new_width}x{new_height} (masked {len(mask_areas)} areas)")
            else:
                print(f"📸 ✅ Rendered and trimmed image {idx+1}: {new_width}x{new_height}")

            return result

    except Exception as e:
        print(f"⚠️ Error rendering image {idx+1}: {e}")

    return None
