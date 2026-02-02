"""Image adequacy assessment.

Provides functions to assess whether detected images are adequate
for the visual content requirements.
"""

from __future__ import annotations

import base64
from typing import Any

import fitz  # type: ignore

from .image_detection_helpers import extract_all_text_from_blocks


def assess_pymupdf_image_adequacy(
    image_blocks: list[dict[str, Any]],
    page: fitz.Page,
    text_blocks: list[dict[str, Any]],
    openai_api_key: str | None = None,
) -> dict[str, Any]:
    """
    Assess whether PyMuPDF detected images are adequate for visual content requirements.

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
            "ai_adequate": False,
        }

    # Step 1: Size-based heuristics
    size_result = _assess_size_adequacy(image_blocks, page)
    size_adequate = size_result["size_adequate"]
    largest_image_area = size_result["largest_image_area"]
    largest_image_side = size_result["largest_image_side"]
    image_area_ratio = size_result["image_area_ratio"]

    print(f"📸 Size assessment: area={largest_image_area:.0f}, side={largest_image_side:.0f}, ratio={image_area_ratio:.3f}")
    print(f"📸 Size adequate: {size_adequate}")

    # Step 2: AI-based assessment if available
    ai_adequate = True
    ai_reasoning = "No AI assessment performed"

    if openai_api_key:
        try:
            ai_assessment = assess_image_completeness_with_ai(image_blocks, page, text_blocks, openai_api_key)
            ai_adequate = ai_assessment.get("adequate", False)
            ai_reasoning = ai_assessment.get("reasoning", "AI assessment failed")

            print(f"🧠 AI assessment: {ai_adequate} - {ai_reasoning}")
        except Exception as e:
            print(f"🧠 ⚠️ AI assessment failed: {e}")
            ai_adequate = True

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
        "ai_reasoning": ai_reasoning,
    }

    print(f"📸 Overall adequacy: {overall_adequate} - {result['reason']}")
    return result


def _assess_size_adequacy(image_blocks: list[dict[str, Any]], page: fitz.Page) -> dict[str, Any]:
    """Assess image adequacy based on size heuristics."""
    total_image_area = 0.0
    page_area = page.rect.width * page.rect.height
    largest_image_area = 0.0
    largest_image_side = 0.0

    for image_block in image_blocks:
        bbox = image_block.get("bbox", [0, 0, 0, 0])
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        area = width * height

        total_image_area += area
        largest_image_area = max(largest_image_area, area)
        largest_image_side = max(largest_image_side, max(width, height))

    image_area_ratio = total_image_area / page_area if page_area > 0 else 0

    # Size adequacy check
    size_adequate = (
        largest_image_area > 2000  # At least 2000 sq pixels
        and largest_image_side > 50  # At least 50px on largest side
        and image_area_ratio > 0.05  # At least 5% of page area
    )

    return {
        "size_adequate": size_adequate,
        "largest_image_area": largest_image_area,
        "largest_image_side": largest_image_side,
        "image_area_ratio": image_area_ratio,
    }


def assess_image_completeness_with_ai(
    image_blocks: list[dict[str, Any]],
    page: fitz.Page,
    text_blocks: list[dict[str, Any]],
    openai_api_key: str,
) -> dict[str, Any]:
    """Use AI to assess if detected images capture complete visual content."""
    try:
        import openai
        from pydantic import BaseModel

        class ImageCompletenessAssessment(BaseModel):
            adequate: bool
            confidence: float
            reasoning: str
            missing_elements: list[str]
            detected_elements: list[str]

        # Prepare context
        all_text = extract_all_text_from_blocks(text_blocks)

        # Get image bbox info
        image_info = []
        for i, img_block in enumerate(image_blocks):
            bbox = img_block.get("bbox", [0, 0, 0, 0])
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            image_info.append(f"Image {i + 1}: {width:.0f}x{height:.0f} at position ({bbox[0]:.0f}, {bbox[1]:.0f})")

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
            response_format=ImageCompletenessAssessment,
            reasoning_effort="high",
        )

        assessment = response.choices[0].message.parsed
        return {
            "adequate": assessment.adequate and assessment.confidence >= 0.7,
            "confidence": assessment.confidence,
            "reasoning": assessment.reasoning,
            "missing_elements": assessment.missing_elements,
            "detected_elements": assessment.detected_elements,
        }

    except Exception as e:
        print(f"🧠 ⚠️ AI image completeness assessment error: {e}")
        return {
            "adequate": True,  # Default to adequate on error
            "reasoning": f"AI assessment failed: {str(e)}",
            "confidence": 0.0,
        }
