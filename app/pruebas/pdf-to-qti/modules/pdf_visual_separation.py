"""
PDF Visual Separation Module

Handles separation of prompt images from choice images in PDF questions.
Uses AI-powered analysis to distinguish between question visuals and answer visuals.
"""

from __future__ import annotations

import base64
import traceback
from typing import Any

import fitz  # type: ignore

from .image_processing import separate_prompt_and_choice_images
from .pdf_image_utils import render_image_area
from .pdf_text_processing import extract_block_text, extract_text_blocks
from .utils import get_page_image


def process_visual_separation(
    page: fitz.Page,
    all_blocks: list[dict[str, Any]],
    ai_analysis_result: dict[str, Any],
    ai_categories: dict[str, Any],
    openai_api_key: str | None,
) -> dict[str, Any] | None:
    """
    Process visual separation (prompt vs choice images).

    Args:
        page: PyMuPDF page object
        all_blocks: All blocks from structured data
        ai_analysis_result: Result from AI content analysis
        ai_categories: AI-assigned categories for blocks
        openai_api_key: OpenAI API key

    Returns:
        Separation result dict, or None if separation not applicable
    """
    # Robust handling: ensure ai_analysis_result is a dict
    if not isinstance(ai_analysis_result, dict):
        print(f"⚠️  Warning: ai_analysis_result is not a dict, type: {type(ai_analysis_result)}")
        ai_analysis_result = {}

    # Check if comprehensive analysis already included visual separation
    visual_separation = _extract_visual_separation(ai_analysis_result)

    prompt_choice_analysis = None

    if visual_separation and visual_separation.get("has_prompt_visuals") is not None:
        print("📸 Step 3: Using visual separation from comprehensive analysis (OPTIMIZED)")
        prompt_choice_analysis = _process_from_comprehensive_analysis(page, all_blocks, visual_separation, ai_categories)
    else:
        # Fallback: Separate call to analyze visual content
        print("📸 Step 3: Analyzing prompt vs choice visual content (fallback API call)...")
        question_text = extract_question_text_from_blocks(all_blocks)
        prompt_choice_analysis = separate_prompt_and_choice_images(page, all_blocks, question_text, ai_categories, openai_api_key)
        _print_analysis_results(prompt_choice_analysis, "fallback")

    # Process the analysis results
    if prompt_choice_analysis and prompt_choice_analysis.get("success", False):
        return build_separation_result(page, all_blocks, prompt_choice_analysis, ai_categories, ai_analysis_result)

    return None


def _extract_visual_separation(ai_analysis_result: dict[str, Any]) -> dict[str, Any] | None:
    """Extract visual separation data from AI analysis result."""
    if not ai_analysis_result.get("success"):
        return None

    visual_separation_raw = ai_analysis_result.get("visual_separation")
    if not visual_separation_raw:
        return None

    if isinstance(visual_separation_raw, dict):
        return visual_separation_raw
    elif isinstance(visual_separation_raw, list):
        for item in visual_separation_raw:
            if isinstance(item, dict):
                return item
        print("⚠️  Warning: visual_separation is a list but no dict found inside")

    return None


def _process_from_comprehensive_analysis(
    page: fitz.Page,
    all_blocks: list[dict[str, Any]],
    visual_separation: dict[str, Any],
    ai_categories: dict[str, Any],
) -> dict[str, Any] | None:
    """Process visual separation data from comprehensive analysis."""
    try:
        from .image_processing.llm_analyzer import process_llm_analysis_with_gaps

        # Create a mock analysis object for process_llm_analysis_with_gaps
        class MockAnalysis:
            def __init__(self, visual_sep_data: dict[str, Any]):
                if not isinstance(visual_sep_data, dict):
                    visual_sep_data = {}
                self.has_prompt_visuals = visual_sep_data.get("has_prompt_visuals", False)
                self.has_choice_visuals = visual_sep_data.get("has_choice_visuals", False)
                self.prompt_visual_description = visual_sep_data.get("prompt_visual_description", "")
                self.choice_visual_description = visual_sep_data.get("choice_visual_description", "")
                self.separation_confidence = visual_sep_data.get("separation_confidence", 0.8)
                self.reasoning = visual_sep_data.get("reasoning", "")

        mock_analysis = MockAnalysis(visual_separation)
        text_blocks_for_gaps = extract_text_blocks({"blocks": all_blocks})

        prompt_choice_analysis = process_llm_analysis_with_gaps(mock_analysis, page, text_blocks_for_gaps, ai_categories)
        prompt_choice_analysis["success"] = True
        prompt_choice_analysis["confidence"] = visual_separation.get("separation_confidence", 0.8)
        prompt_choice_analysis["ai_categories"] = ai_categories

        _print_analysis_results(prompt_choice_analysis, "comprehensive analysis")
        return prompt_choice_analysis

    except Exception as e:
        print(f"⚠️  Error procesando visual separation del análisis comprehensivo: {e}")
        traceback.print_exc()
        return None


def build_separation_result(
    page: fitz.Page,
    all_blocks: list[dict[str, Any]],
    prompt_choice_analysis: dict[str, Any],
    ai_categories: dict[str, Any],
    ai_analysis_result: dict[str, Any],
) -> dict[str, Any] | None:
    """Build result dictionary from visual separation analysis."""
    images: list[dict[str, Any]] = []
    choice_images: list[dict[str, Any]] = []

    # Update ai_categories with the separator's analysis if available
    if prompt_choice_analysis.get("ai_categories"):
        ai_categories.update(prompt_choice_analysis["ai_categories"])
        print(f"🔍 Updated AI categories with {len(prompt_choice_analysis['ai_categories'])} classifications")

    # Process prompt images
    if prompt_choice_analysis.get("has_prompt_visuals") and prompt_choice_analysis.get("prompt_bboxes"):
        images.extend(render_prompt_images(page, prompt_choice_analysis))

    # Process choice images
    if prompt_choice_analysis.get("has_choice_visuals") and prompt_choice_analysis.get("choice_bboxes"):
        rendered_choice_images = render_choice_images(page, prompt_choice_analysis, len(images))
        choice_images.extend(rendered_choice_images)
        images.extend(rendered_choice_images)

    # If we have choice images, return with page image for validation
    if choice_images:
        page_image_base64 = base64.b64encode(get_page_image(page)).decode("utf-8")
        return {
            "images": images,
            "tables": [],  # Will be filled by caller
            "ai_categories": ai_categories,
            "ai_analysis": ai_analysis_result,
            "has_visual_content": True,
            "is_choice_diagram": len(choice_images) > 0,
            "is_prompt_and_choice": len(images) > len(choice_images),
            "page_image_base64": page_image_base64,
            "prompt_choice_analysis": prompt_choice_analysis,
        }

    # If we have prompt images but no choice images
    if images:
        return {
            "images": images,
            "tables": [],  # Will be filled by caller
            "ai_categories": ai_categories,
            "ai_analysis": ai_analysis_result,
            "has_visual_content": True,
            "is_choice_diagram": False,
            "is_prompt_and_choice": False,
            "prompt_choice_analysis": prompt_choice_analysis,
        }

    return None


def render_prompt_images(page: fitz.Page, prompt_choice_analysis: dict[str, Any]) -> list[dict[str, Any]]:
    """Render prompt images from analysis."""
    images: list[dict[str, Any]] = []
    prompt_bboxes = prompt_choice_analysis.get("prompt_bboxes", [])

    if not isinstance(prompt_bboxes, list):
        print(f"⚠️  Warning: prompt_bboxes is not a list, type: {type(prompt_bboxes)}")
        return images

    print(f"📸 Processing {len(prompt_bboxes)} prompt image(s)...")

    for i, prompt_bbox in enumerate(prompt_bboxes):
        # Ensure prompt_bbox is a list, not a dict
        if isinstance(prompt_bbox, dict):
            prompt_bbox = prompt_bbox.get("bbox", [0, 0, 0, 0])
        elif not isinstance(prompt_bbox, list) or len(prompt_bbox) < 4:
            print(f"⚠️  Warning: Invalid prompt_bbox format at index {i}, skipping")
            continue

        print(f"📸  - Processing prompt image #{i + 1}: {prompt_bbox}")
        rendered = render_image_area(page, prompt_bbox, prompt_bbox, i)
        if rendered:
            rendered["is_prompt_image"] = True
            rendered["description"] = prompt_choice_analysis.get("prompt_visual_description", "Question prompt visual content")
            rendered["detection_method"] = "llm_separation"
            images.append(rendered)
            print(f"📸 ✅ Rendered prompt image #{i + 1}: {rendered['width']}x{rendered['height']}")

    return images


def render_choice_images(page: fitz.Page, prompt_choice_analysis: dict[str, Any], start_idx: int) -> list[dict[str, Any]]:
    """Render choice images from analysis."""
    choice_images: list[dict[str, Any]] = []
    choice_bboxes = prompt_choice_analysis.get("choice_bboxes", [])
    total_choices = prompt_choice_analysis.get("total_choice_blocks", len(choice_bboxes))

    # CRITICAL CHECK: Ensure we have an image for every choice detected
    if total_choices > 0 and len(choice_bboxes) != total_choices:
        error_msg = (
            f"Mismatch between detected choices ({total_choices}) and "
            f"extracted choice images ({len(choice_bboxes)}). Aborting to prevent incorrect QTI."
        )
        print(f"📸 ❌ ERROR: {error_msg}")
        raise ValueError(error_msg)

    print(f"📸 Processing {len(choice_bboxes)} choice images")

    for i, choice_info in enumerate(choice_bboxes):
        choice_bbox = choice_info["bbox"]
        choice_letter = choice_info.get("choice_letter", f"Choice{i + 1}")
        mask_areas = choice_info.get("text_mask_areas", [])

        rendered = render_image_area(page, choice_bbox, choice_bbox, start_idx + i, mask_areas)
        if rendered:
            rendered["is_choice_diagram"] = True
            rendered["choice_letter"] = choice_letter
            rendered["description"] = choice_info.get("description", f"Choice {choice_letter} diagram")
            rendered["detection_method"] = "llm_separation"
            choice_images.append(rendered)
            print(f"📸 ✅ Rendered choice {choice_letter}: {rendered['width']}x{rendered['height']}")

    return choice_images


def extract_question_text_from_blocks(all_blocks: list[dict[str, Any]]) -> str:
    """Extract question text from blocks for detection functions."""
    combined_text = ""
    for block in all_blocks:
        if block.get("type") == 0:
            block_text = extract_block_text(block)
            if block_text.strip():
                combined_text += " " + block_text.strip()
    return combined_text.strip()


def _print_analysis_results(analysis: dict[str, Any] | None, source: str) -> None:
    """Print analysis results for debugging."""
    if not analysis:
        return

    print(f"🔍 Analysis results (from {source}):")
    print(f"   Prompt visuals: {analysis.get('has_prompt_visuals', False)}")
    print(f"   Choice visuals: {analysis.get('has_choice_visuals', False)}")
    print(f"   Confidence: {analysis.get('confidence', 0):.2f}")
