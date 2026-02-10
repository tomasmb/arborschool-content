"""
AI Content Analyzer

This module implements the two-step LLM approach from converter guidelines:
1. Analyze PDF content to determine QTI 3.0 compatibility
2. Provide intelligent content categorization for image extraction

Follows guideline #13: Prefer LLM analysis over text matching or 'dumb' methods.
"""

from __future__ import annotations

import base64
import json
from typing import Any

import fitz  # type: ignore

from .ai_analysis_parsers import (
    parse_categorization_response,
    parse_compatibility_response,
    process_comprehensive_result,
)
from .ai_analysis_prompts import (
    CATEGORIZATION_SYSTEM_PROMPT,
    COMPATIBILITY_SYSTEM_PROMPT,
    COMPREHENSIVE_SYSTEM_PROMPT,
    build_categorization_prompt,
    build_compatibility_prompt,
    build_comprehensive_analysis_prompt,
)
from .llm_client import chat_completion


def analyze_pdf_content_with_ai(page: fitz.Page, structured_data: dict[str, Any], openai_api_key: str) -> dict[str, Any]:
    """Complete AI-powered analysis of PDF content following converter guidelines.

    OPTIMIZED: Uses a single comprehensive API call instead of multiple separate calls.

    Args:
        page: PyMuPDF page object
        structured_data: PyMuPDF structured text data
        openai_api_key: OpenAI API key

    Returns:
        Dictionary with compatibility assessment and content categorization
    """
    try:
        # Extract text blocks for analysis
        text_blocks = extract_text_blocks_for_analysis(structured_data)

        # Extract question text for comprehensive analysis
        question_text = " ".join(block.get("text", "") for block in text_blocks)
        if len(question_text) > 2000:
            question_text = question_text[:2000] + "..."

        # Get page image for visual context
        page_image_bytes = get_page_image_for_ai(page)
        page_image_base64 = base64.b64encode(page_image_bytes).decode("utf-8")

        # OPTIMIZATION: Use comprehensive analysis (single API call)
        comprehensive_result = comprehensive_content_analysis(text_blocks, page_image_base64, openai_api_key, question_text=question_text)

        if comprehensive_result.get("success", False):
            return comprehensive_result

        # Fallback: Use original two-step approach
        print("🧠 ⚠️ Comprehensive analysis failed, falling back to two-step approach")
        return _fallback_two_step_analysis(text_blocks, page_image_base64, openai_api_key)

    except Exception as e:
        print(f"🧠 ⚠️ AI content analysis failed: {e}")
        return _create_error_result(str(e))


def _fallback_two_step_analysis(text_blocks: list[dict[str, Any]], page_image_base64: str, openai_api_key: str) -> dict[str, Any]:
    """Fallback to original two-step approach if comprehensive fails."""
    compatibility_result = assess_qti_compatibility(text_blocks, page_image_base64, openai_api_key)

    categorization_result = {}
    if compatibility_result.get("visual_content_required", False):
        categorization_result = categorize_content_blocks(text_blocks, page_image_base64, openai_api_key)

    return {
        "success": True,
        "compatibility": compatibility_result,
        "categorization": categorization_result,
        "ai_categories": categorization_result.get("block_categories", {}),
        "has_visual_content": compatibility_result.get("visual_content_required", False),
    }


def _create_error_result(error: str) -> dict[str, Any]:
    """Create standardized error result."""
    return {"success": False, "error": error, "compatibility": {}, "categorization": {}, "ai_categories": {}, "has_visual_content": False}


def comprehensive_content_analysis(
    text_blocks: list[dict[str, Any]], page_image_base64: str, openai_api_key: str, question_text: str | None = None
) -> dict[str, Any]:
    """OPTIMIZED: Comprehensive analysis in a single API call.

    This reduces API calls from 3 to 1 for questions with visual content.

    Args:
        text_blocks: List of text blocks from PDF
        page_image_base64: Base64 encoded page image
        openai_api_key: API key for LLM
        question_text: Optional question text (extracted if not provided)

    Returns:
        Dictionary with all analysis results
    """
    try:
        # Extract question text if not provided
        if not question_text:
            question_text = " ".join(block.get("text", "") for block in text_blocks)
            if len(question_text) > 2000:
                question_text = question_text[:2000] + "..."

        # Prepare block information
        block_info = _prepare_block_info(text_blocks)
        content_summary = prepare_content_summary(text_blocks)

        # Build prompt
        prompt = build_comprehensive_analysis_prompt(question_text, content_summary, block_info)

        messages = [
            {"role": "system", "content": COMPREHENSIVE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{page_image_base64}"}},
                ],
            },
        ]

        print("🧠 ⚡ Using OPTIMIZED comprehensive analysis (single API call)")
        response_text = chat_completion(
            messages=messages,
            api_key=openai_api_key,
            json_only=True,
            thinking_level="high",
        )

        # Parse and process response
        result = json.loads(response_text)
        return process_comprehensive_result(result, text_blocks)

    except Exception as e:
        print(f"🧠 ⚠️ Comprehensive analysis failed: {e}")
        return {"success": False, "error": str(e)}


def _prepare_block_info(text_blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prepare block information for AI analysis."""
    block_info = []
    for i, block in enumerate(text_blocks):
        block_text = block.get("text", "")[:200]  # Limit for efficiency
        bbox = block.get("bbox", [])
        area = block.get("area", 0)

        position = ""
        if len(bbox) >= 4:
            position = f"({bbox[0]:.0f}, {bbox[1]:.0f}) to ({bbox[2]:.0f}, {bbox[3]:.0f})"

        block_info.append({"block_number": i + 1, "text": block_text, "bbox": bbox, "area": area, "position": position})

    return block_info


def assess_qti_compatibility(text_blocks: list[dict[str, Any]], page_image_base64: str, openai_api_key: str) -> dict[str, Any]:
    """Step 1: Use GPT-5.1 to assess if content can be represented in QTI 3.0.

    Following guideline #7: Two-step LLM approach.
    """
    content_summary = prepare_content_summary(text_blocks)
    prompt = build_compatibility_prompt(content_summary)

    try:
        messages = [
            {"role": "system", "content": COMPATIBILITY_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{page_image_base64}"}},
                ],
            },
        ]

        response_text = chat_completion(
            messages=messages,
            api_key=openai_api_key,
            json_only=True,
            reasoning_effort="medium",  # structured analysis
        )

        analysis = parse_compatibility_response(response_text)

        print(f"🧠 QTI Compatibility: {analysis.get('can_represent', False)}")
        print(f"   Visual content required: {analysis.get('visual_content_required', False)}")

        return analysis

    except Exception as e:
        print(f"🧠 ⚠️ QTI compatibility assessment failed: {e}")
        return {"can_represent": False, "visual_content_required": False}


def categorize_content_blocks(text_blocks: list[dict[str, Any]], page_image_base64: str, openai_api_key: str) -> dict[str, Any]:
    """Step 2: Intelligently categorize text blocks for image extraction.

    Following guideline #3: Build image BBOX using surrounding blocks with AI.
    """
    import openai

    # Prepare block information for AI
    block_info = []
    for i, block in enumerate(text_blocks):
        block_info.append({"block_number": i + 1, "text": block["text"][:200], "bbox": block["bbox"], "area": block["area"]})

    prompt = build_categorization_prompt(block_info)

    try:
        messages = [
            {"role": "system", "content": CATEGORIZATION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{page_image_base64}"}},
                ],
            },
        ]

        client = openai.OpenAI(api_key=openai_api_key)
        response = client.chat.completions.create(
            model="gpt-5.1",
            messages=messages,
            response_format={"type": "json_object"},
            reasoning_effort="medium",  # structured analysis
            seed=42,
        )

        response_text = response.choices[0].message.content
        categorization = parse_categorization_response(response_text, len(text_blocks))

        print(f"🧠 Content categorization: {len(categorization)} blocks categorized")

        return {
            "block_categories": categorization,
            "question_answer_blocks": [i for i, cat in categorization.items() if cat in ["question_text", "answer_choice"]],
            "image_related_blocks": [
                i for i, cat in categorization.items() if cat in ["visual_content_title", "visual_content_label", "other_label"]
            ],
        }

    except Exception as e:
        print(f"🧠 ⚠️ Content categorization failed: {e}")
        return {"block_categories": {}, "question_answer_blocks": [], "image_related_blocks": []}


def extract_text_blocks_for_analysis(structured_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract and prepare text blocks for AI analysis."""
    blocks = structured_data.get("blocks", [])
    text_blocks = []

    for i, block in enumerate(blocks):
        if block.get("type") == 0:  # Text block
            bbox = block.get("bbox", [])
            if len(bbox) >= 4:
                # Extract text content
                block_text = ""
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        block_text += span.get("text", "") + " "
                block_text = block_text.strip()

                if block_text:  # Only include blocks with actual text
                    text_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                    text_blocks.append({"block_number": i + 1, "text": block_text, "bbox": bbox, "area": text_area})

    return text_blocks


def get_page_image_for_ai(page: fitz.Page, scale: float = 1.5) -> bytes:
    """Get page image optimized for AI analysis."""
    try:
        matrix = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        return pix.tobytes("png")
    except Exception as e:
        print(f"⚠️ Error getting page image: {e}")
        return b""


def prepare_content_summary(text_blocks: list[dict[str, Any]]) -> str:
    """Prepare a concise summary of content for AI analysis."""
    if not text_blocks:
        return "No text content found."

    all_text = " ".join(block["text"] for block in text_blocks)

    if len(all_text) > 2000:
        all_text = all_text[:2000] + "..."

    return f"""Text content ({len(text_blocks)} blocks):
{all_text}

Block count: {len(text_blocks)}
Total text length: {len(all_text)} characters"""
