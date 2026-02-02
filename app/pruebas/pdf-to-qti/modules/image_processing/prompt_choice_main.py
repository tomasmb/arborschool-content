"""
Main orchestration for prompt vs choice visual content separation.

This module contains the primary entry point and high-level logic for separating
visual content that belongs to the question prompt from visual content that belongs
to answer choices.
"""

from typing import Any, Dict, List, Optional

import fitz  # type: ignore

from .llm_analyzer import analyze_visual_content_with_llm


def separate_prompt_and_choice_images(
    page: fitz.Page,
    text_blocks: List[Dict[str, Any]],
    question_text: str,
    ai_categories: Optional[Dict[int, str]] = None,
    openai_api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Use LLM to separate visual content that belongs to the question prompt
    from visual content that belongs to answer choices.

    Args:
        page: PDF page object
        text_blocks: All text blocks from the page
        question_text: The question text
        ai_categories: AI categorization of text blocks
        openai_api_key: OpenAI API key for LLM analysis

    Returns:
        Dictionary with separated prompt and choice image information
    """
    print("🔍 =" * 60)
    print("🔍 STARTING PROMPT vs CHOICE VISUAL SEPARATION")
    print(f"🔍 Page dimensions: {page.rect.width}x{page.rect.height}")
    print(f"🔍 Text blocks: {len(text_blocks)} total")
    print(f"🔍 Question text length: {len(question_text)} chars")
    print(f"🔍 Existing AI categories: {len(ai_categories) if ai_categories else 0}")
    print("🔍 =" * 60)

    if not openai_api_key:
        print("🔍 ⚠️ No OpenAI API key provided - using fallback separation")
        return _fallback_separation(page, text_blocks, question_text, ai_categories)

    try:
        # Analyze visual content with LLM
        print("🔍 🧠 Starting LLM-powered visual content analysis...")
        analysis_result = analyze_visual_content_with_llm(page, text_blocks, question_text, openai_api_key)

        if not analysis_result.get("success", False):
            print(f"🔍 ❌ LLM analysis failed: {analysis_result.get('error', 'Unknown error')}")
            print("🔍 🔄 Falling back to heuristic separation...")
            return _fallback_separation(page, text_blocks, question_text, ai_categories)

        print("🔍 ✅ LLM analysis completed successfully")
        return analysis_result

    except Exception as e:
        print(f"🔍 ❌ Exception in LLM separation: {str(e)}")
        print("🔍 🔄 Falling back to heuristic separation...")
        return _fallback_separation(page, text_blocks, question_text, ai_categories)


def _fallback_separation(
    page: fitz.Page, text_blocks: List[Dict[str, Any]], question_text: str, ai_categories: Optional[Dict[int, str]] = None
) -> Dict[str, Any]:
    """
    Fallback separation logic when LLM is not available.
    """
    print("🔍 🔄 USING FALLBACK SEPARATION LOGIC")
    print("🔍 " + "-" * 40)

    # Simple heuristic: if question text references visual content, assume prompt visuals exist
    prompt_indicators = ["shown", "diagram", "model", "figure", "image", "illustration", "appears", "displays", "represents", "depicts"]

    has_prompt_visuals = any(indicator in question_text.lower() for indicator in prompt_indicators)
    print(f"🔍 Prompt visual indicators found: {has_prompt_visuals}")
    if has_prompt_visuals:
        found_indicators = [ind for ind in prompt_indicators if ind in question_text.lower()]
        print(f"🔍    Indicators: {found_indicators}")

    # Look for explicit choice indicators
    choice_indicators = ["a)", "b)", "c)", "d)", "which of the following"]
    has_choice_visuals = any(indicator in question_text.lower() for indicator in choice_indicators)
    print(f"🔍 Choice visual indicators found: {has_choice_visuals}")
    if has_choice_visuals:
        found_choice_indicators = [ind for ind in choice_indicators if ind in question_text.lower()]
        print(f"🔍    Indicators: {found_choice_indicators}")

    result = {
        "success": True,
        "confidence": 0.6,  # Lower confidence for fallback
        "has_prompt_visuals": has_prompt_visuals,
        "has_choice_visuals": has_choice_visuals,
        "prompt_visual_description": "Visual content referenced in question text" if has_prompt_visuals else "",
        "choice_visual_description": "Multiple choice options with visual content" if has_choice_visuals else "",
        "prompt_bboxes": [],  # Changed from singular to plural to match main function
        "choice_bboxes": [],
        "total_choice_blocks": 0,  # Added missing field to match main function
        "prompt_regions": [],
        "choice_regions": [],
        "block_categories": ai_categories or {},
        "ai_categories": ai_categories or {},  # Added missing field to match main function
        "reasoning": "Fallback heuristic analysis",
    }

    print("🔍 📊 FALLBACK RESULTS:")
    print(f"🔍    Prompt visuals: {result['has_prompt_visuals']}")
    print(f"🔍    Choice visuals: {result['has_choice_visuals']}")
    print(f"🔍    Confidence: {result['confidence']}")
    print("🔍 " + "=" * 60)

    return result
