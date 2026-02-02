"""
PDF Visual Content Pipeline

Orchestrates the extraction of images and visual content from PDF pages.
Uses AI-powered analysis for intelligent content categorization.
"""

from __future__ import annotations

import base64
from typing import Any

import fitz  # type: ignore

from .ai_processing import analyze_pdf_content_with_ai
from .image_processing import (
    assess_pymupdf_image_adequacy,
    detect_and_extract_choice_diagrams,
    detect_images_with_ai,
    expand_image_bbox_to_boundaries,
    expand_pymupdf_bbox_intelligently,
    should_use_ai_image_detection,
    shrink_image_bbox_away_from_text,
)
from .image_processing.bbox_utils import bbox_overlap_percentage
from .image_processing.multipart_images import (
    detect_multipart_question_images,
    detect_part_specific_images_with_ai,
    filter_images_for_multipart_question,
)
from .pdf_image_utils import is_meaningful_image, render_image_area
from .pdf_table_extraction import extract_tables_with_pymupdf, try_reconstruct_table_from_blocks
from .pdf_text_processing import split_choice_blocks
from .pdf_visual_separation import (
    extract_question_text_from_blocks,
    process_visual_separation,
)
from .utils import get_page_image


def extract_images_and_tables(
    page: fitz.Page,
    structured_data: dict[str, Any],
    openai_api_key: str | None = None,
) -> dict[str, Any]:
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
    # Split choice blocks before processing
    structured_data = split_choice_blocks(structured_data)
    all_blocks = structured_data.get("blocks", [])

    # Step 1: Extract tables
    tables_info = _extract_tables(page, all_blocks)

    # Step 2: AI content analysis
    ai_result = _run_ai_analysis(page, structured_data, all_blocks, openai_api_key)
    ai_categories = ai_result["ai_categories"]
    has_visual_content = ai_result["has_visual_content"]
    ai_analysis_result = ai_result["ai_analysis_result"]

    # Step 3: Process visual separation (prompt vs choice images)
    if has_visual_content:
        separation_result = process_visual_separation(page, all_blocks, ai_analysis_result, ai_categories, openai_api_key)
        if separation_result:
            separation_result["tables"] = tables_info
            return separation_result

    # Step 4: Try choice diagram detection (fallback)
    if has_visual_content and ai_categories:
        choice_result = _try_choice_diagram_detection(page, all_blocks, ai_categories, tables_info, ai_analysis_result, has_visual_content)
        if choice_result:
            return choice_result

    # Step 5: Handle multi-part questions
    multipart_result = _try_multipart_detection(page, all_blocks, ai_categories, tables_info, ai_analysis_result, has_visual_content, openai_api_key)
    if multipart_result:
        return multipart_result

    # Step 6: Regular image processing
    images = _process_regular_images(page, all_blocks, ai_categories, has_visual_content, tables_info, openai_api_key)

    # Step 7: Apply multipart filtering if applicable
    images = _apply_multipart_filtering(images, all_blocks)

    print(f"📸 ✅ Final results: {len(images)} images, {len(tables_info)} tables")

    return {
        "images": images,
        "tables": tables_info,
        "ai_categories": ai_categories,
        "ai_analysis": ai_analysis_result,
        "has_visual_content": has_visual_content,
    }


def _extract_tables(page: fitz.Page, all_blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Step 1: Extract tables using PyMuPDF and reconstruction."""
    print("📊 Step 1: PyMuPDF table detection...")
    tables_info = extract_tables_with_pymupdf(page)

    # If PyMuPDF failed, try reconstruction
    if not tables_info:
        reconstructed = try_reconstruct_table_from_blocks(all_blocks)
        if reconstructed:
            tables_info.append(reconstructed)

    return tables_info


def _run_ai_analysis(
    page: fitz.Page,
    structured_data: dict[str, Any],
    all_blocks: list[dict[str, Any]],
    openai_api_key: str | None,
) -> dict[str, Any]:
    """Step 2: Run AI-powered content analysis."""
    ai_analysis_result: dict[str, Any] = {}
    ai_categories: dict[str, Any] = {}
    has_visual_content = False

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
            has_visual_content = should_use_ai_image_detection(all_blocks, openai_api_key)
    else:
        print("🧠 No OpenAI API key, using fallback image detection")
        has_visual_content = should_use_ai_image_detection(all_blocks, None)

    return {
        "ai_analysis_result": ai_analysis_result,
        "ai_categories": ai_categories,
        "has_visual_content": has_visual_content,
    }


def _try_choice_diagram_detection(
    page: fitz.Page,
    all_blocks: list[dict[str, Any]],
    ai_categories: dict[str, Any],
    tables_info: list[dict[str, Any]],
    ai_analysis_result: dict[str, Any],
    has_visual_content: bool,
) -> dict[str, Any] | None:
    """Try to detect and extract choice diagrams (fallback approach)."""
    print("📸 Step 3 (Fallback): Using original choice diagram detection...")

    question_text = extract_question_text_from_blocks(all_blocks)
    choice_images = detect_and_extract_choice_diagrams(page, all_blocks, ai_categories, question_text)

    if choice_images:
        print(f"🎯 ✅ Detected choice diagram question with {len(choice_images)} choices")
        page_image_base64 = base64.b64encode(get_page_image(page)).decode("utf-8")

        return {
            "images": choice_images,
            "tables": tables_info,
            "ai_categories": ai_categories,
            "ai_analysis": ai_analysis_result,
            "has_visual_content": has_visual_content,
            "is_choice_diagram": True,
            "page_image_base64": page_image_base64,
        }

    return None


def _try_multipart_detection(
    page: fitz.Page,
    all_blocks: list[dict[str, Any]],
    ai_categories: dict[str, Any],
    tables_info: list[dict[str, Any]],
    ai_analysis_result: dict[str, Any],
    has_visual_content: bool,
    openai_api_key: str | None,
) -> dict[str, Any] | None:
    """Handle multi-part questions with part-specific images (Step 3.5)."""
    question_text = extract_question_text_from_blocks(all_blocks)
    multipart_info = detect_multipart_question_images(all_blocks, ai_categories, question_text)

    if not multipart_info:
        return None

    # Check if this needs specialized AI detection
    if not multipart_info[0].get("needs_special_ai_detection"):
        return None

    parts_with_visuals = multipart_info[0]["parts_with_visuals"]
    print(f"🎯 Running specialized AI detection for parts: {parts_with_visuals}")

    part_specific_images = detect_part_specific_images_with_ai(page, all_blocks, parts_with_visuals, openai_api_key)

    if not part_specific_images:
        return None

    print(f"🎯 Specialized AI found {len(part_specific_images)} part-specific images")
    images: list[dict[str, Any]] = []

    for img_info in part_specific_images:
        bbox = img_info["bbox"]
        part_context = img_info["part_context"]

        rendered = render_image_area(page, bbox, bbox, len(images))
        if rendered:
            rendered["part_context"] = part_context
            rendered["detection_method"] = "multipart_ai"
            rendered["description"] = img_info.get("description", "")
            images.append(rendered)
            print(f"📸 ✅ Rendered Part {part_context} image: {rendered['width']}x{rendered['height']}")

    if images:
        return {
            "images": images,
            "tables": tables_info,
            "ai_categories": ai_categories,
            "ai_analysis": ai_analysis_result,
            "has_visual_content": has_visual_content,
            "is_multipart_with_images": True,
        }

    return None


def _process_regular_images(
    page: fitz.Page,
    all_blocks: list[dict[str, Any]],
    ai_categories: dict[str, Any],
    has_visual_content: bool,
    tables_info: list[dict[str, Any]],
    openai_api_key: str | None,
) -> list[dict[str, Any]]:
    """Process regular images using PyMuPDF and AI detection."""
    image_blocks = [block for block in all_blocks if block.get("type") == 1]
    meaningful_images: list[tuple[int, dict[str, Any]]] = []
    images: list[dict[str, Any]] = []

    # Step 4a: Process PyMuPDF image blocks
    if image_blocks:
        print("📸 Step 4a: Processing PyMuPDF image blocks...")
        meaningful_images = _filter_meaningful_images(image_blocks, tables_info)

        # Step 4b: Assess adequacy and potentially expand
        if meaningful_images and has_visual_content:
            meaningful_images = _assess_and_expand_images(meaningful_images, page, all_blocks, ai_categories, openai_api_key)

    # Step 5: Use AI detection if no PyMuPDF images found
    if not meaningful_images and has_visual_content:
        print("📸 Step 5: No PyMuPDF images found, using AI-powered detection...")
        ai_detected = detect_images_with_ai(page, all_blocks, openai_api_key)
        if ai_detected:
            print(f"📸 AI detection found {len(ai_detected)} potential image areas")
            for i, img_area in enumerate(ai_detected):
                meaningful_images.append((i, img_area))
                if "ai_categories" in img_area and not ai_categories:
                    ai_categories.update(img_area["ai_categories"])
                    print("📸 ✅ Using AI categories from image detection")

    # Step 6: Process each meaningful image with AI-guided bbox operations
    for idx, (original_idx, image_block) in enumerate(meaningful_images):
        original_bbox = image_block.get("bbox", [0, 0, 0, 0])
        print(f"📸 Processing image {idx + 1}/{len(meaningful_images)}: {original_bbox}")

        # Expand bbox using deterministic logic
        expanded_bbox = expand_image_bbox_to_boundaries(original_bbox, all_blocks, page)

        # Shrink away from question/answer text using AI categorization
        final_bbox = shrink_image_bbox_away_from_text(expanded_bbox, all_blocks, page, ai_categories)

        # Render the final image area
        rendered = render_image_area(page, final_bbox, original_bbox, idx)
        if rendered:
            images.append(rendered)

    return images


def _filter_meaningful_images(image_blocks: list[dict[str, Any]], tables_info: list[dict[str, Any]]) -> list[tuple[int, dict[str, Any]]]:
    """Filter image blocks to find meaningful ones that don't overlap with tables."""
    candidate_images: list[tuple[int, dict[str, Any]]] = []

    for i, image_block in enumerate(image_blocks):
        bbox = image_block.get("bbox", [0, 0, 0, 0])

        # Check if this overlaps with detected tables
        is_table_area = any(bbox_overlap_percentage(bbox, table["bbox"]) > 0.5 for table in tables_info)

        if not is_table_area and is_meaningful_image(bbox):
            candidate_images.append((i, image_block))
            print(f"📸 ✅ Image {i + 1} is meaningful and separate from tables")

    return candidate_images


def _assess_and_expand_images(
    candidate_images: list[tuple[int, dict[str, Any]]],
    page: fitz.Page,
    all_blocks: list[dict[str, Any]],
    ai_categories: dict[str, Any],
    openai_api_key: str | None,
) -> list[tuple[int, dict[str, Any]]]:
    """Assess if PyMuPDF images are adequate and expand if needed."""
    print("📸 Step 4b: Assessing PyMuPDF image adequacy...")

    image_blocks_only = [img_block for _, img_block in candidate_images]
    adequacy_result = assess_pymupdf_image_adequacy(image_blocks_only, page, all_blocks, openai_api_key)

    if adequacy_result["adequate"]:
        print(f"📸 ✅ PyMuPDF images are adequate: {adequacy_result['reason']}")
        return candidate_images

    print(f"📸 ⚠️ PyMuPDF images inadequate: {adequacy_result['reason']}")
    print("📸 Step 4c: Using smart expansion of PyMuPDF bbox...")

    expanded_images: list[tuple[int, dict[str, Any]]] = []

    for i, image_block in candidate_images:
        original_bbox = image_block.get("bbox", [0, 0, 0, 0])

        # Expand the PyMuPDF bbox intelligently
        expanded_bbox = expand_pymupdf_bbox_intelligently(original_bbox, page, all_blocks, ai_categories)

        # Create expanded image block
        expanded_block = image_block.copy()
        expanded_block["bbox"] = expanded_bbox
        expanded_block["original_bbox"] = original_bbox
        expanded_block["expansion_method"] = "smart_expansion"

        expanded_images.append((i, expanded_block))

    print(f"📸 ✅ Smart expansion applied to {len(expanded_images)} images")
    return expanded_images


def _apply_multipart_filtering(images: list[dict[str, Any]], all_blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply multipart filtering if applicable (Step 7)."""
    if not images:
        return images

    question_text = extract_question_text_from_blocks(all_blocks)
    multipart_info = detect_multipart_question_images(all_blocks, {}, question_text)

    if multipart_info:
        filtered = filter_images_for_multipart_question(images, all_blocks, question_text)
        if filtered != images:
            print(f"📸 ✅ Multipart filtering applied: {len(filtered)} relevant images retained")
            return filtered

    return images
