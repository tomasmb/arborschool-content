"""AI-powered image detection.

Provides functions for using AI to detect and categorize visual content.
"""

from __future__ import annotations

import base64
from typing import Any

import fitz  # type: ignore

from .image_bbox_construction import construct_image_bbox_from_gaps, detect_potential_image_areas
from .image_detection_helpers import (
    extract_all_text_from_blocks,
    prepare_block_info_for_ai,
    process_ai_categorization,
    use_conservative_visual_indicators,
)


def should_use_ai_image_detection(
    text_blocks: list[dict[str, Any]], openai_api_key: str | None = None
) -> bool:
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
            key_indicators: list[str]

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
                {"role": "user", "content": prompt},
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


def detect_images_with_ai(
    page: fitz.Page, text_blocks: list[dict[str, Any]], openai_api_key: str | None = None
) -> list[dict[str, Any]]:
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
            text_block_categories: list[TextBlockCategory]
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
        page_image_base64 = base64.b64encode(page_image_bytes).decode("utf-8")

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{page_image_base64}"},
                    },
                ],
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
        all_image_labels_for_gaps = categorization_result["all_image_associated_text_bboxes"]

        # Build footer avoidance list
        qa_bboxes_set = {tuple(bbox) for bbox in qa_bboxes}
        strict_label_bboxes_set = {tuple(bbox) for bbox in strict_label_bboxes}

        potential_footer_check_bboxes: list[list[float]] = []
        for block in text_blocks:
            if block.get("type") == 0:
                bbox = block.get("bbox")
                if bbox and len(bbox) == 4:
                    bbox_tuple = tuple(bbox)
                    if bbox_tuple not in qa_bboxes_set and bbox_tuple not in strict_label_bboxes_set:
                        potential_footer_check_bboxes.append(bbox)

        image_bbox = construct_image_bbox_from_gaps(
            page,
            qa_bboxes,
            all_image_labels_for_gaps,
            potential_footer_check_bboxes,
        )

        if image_bbox:
            return [
                {
                    "type": 1,
                    "bbox": image_bbox,
                    "number": "ai_content_analysis",
                    "description": analysis.image_area_description,
                    "confidence": 0.95,
                    "ai_categories": categorization_result["ai_categories"],
                }
            ]
        else:
            print("🧠 ⚠️ Could not construct valid image bbox from text gaps")
            return []

    except Exception as e:
        print(f"🧠 ⚠️ AI content analysis error: {e}, using gap-based fallback")
        return detect_potential_image_areas(page, text_blocks)
