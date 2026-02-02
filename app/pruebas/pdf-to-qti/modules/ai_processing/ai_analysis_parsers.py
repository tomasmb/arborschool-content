"""
AI Analysis response parsers.

This module contains functions to parse AI responses for content analysis.
"""

from __future__ import annotations

import json
from typing import Any

from .ai_analysis_prompts import VALID_BLOCK_CATEGORIES, VALID_QTI_TYPES


def parse_compatibility_response(response_text: str) -> dict[str, Any]:
    """Parse AI compatibility assessment response from structured JSON."""
    try:
        result = json.loads(response_text)

        can_represent = result.get("can_represent", False)
        visual_required = result.get("visual_content_required", False)
        question_type = result.get("question_type")
        confidence = result.get("confidence", 0.8)
        reasoning = result.get("reasoning", "")

        # Validate question type
        if question_type and question_type not in VALID_QTI_TYPES:
            question_type = None
            can_represent = False

        return {
            "can_represent": can_represent,
            "visual_content_required": visual_required,
            "question_type": question_type,
            "confidence": confidence,
            "reasoning": reasoning
        }

    except json.JSONDecodeError as e:
        print(f"🧠 ⚠️ Failed to parse compatibility JSON: {e}")
        return {
            "can_represent": False,
            "visual_content_required": False,
            "question_type": None,
            "confidence": 0.0,
            "reasoning": "Failed to parse AI response"
        }


def parse_categorization_response(response_text: str, num_blocks: int) -> dict[int, str]:
    """Parse AI categorization response from structured JSON."""
    # Valid categories for basic categorization (subset of VALID_BLOCK_CATEGORIES)
    valid_categories = [
        "question_text", "answer_choice", "visual_content_title",
        "visual_content_label", "other_label"
    ]

    try:
        result = json.loads(response_text)
        block_categories = result.get("block_categories", {})
        categorization = {}

        for block_str, category in block_categories.items():
            try:
                block_num = int(block_str)
                if 1 <= block_num <= num_blocks and category in valid_categories:
                    categorization[block_num] = category
            except (ValueError, TypeError):
                continue

        # Fill in any missing blocks with default category
        for i in range(1, num_blocks + 1):
            if i not in categorization:
                categorization[i] = "other_label"

        return categorization

    except json.JSONDecodeError as e:
        print(f"🧠 ⚠️ Failed to parse categorization JSON: {e}")
        return {i: "other_label" for i in range(1, num_blocks + 1)}


def validate_block_categories(
    block_cats: dict[str, str],
    num_blocks: int
) -> dict[int, str]:
    """Validate and convert block categories to integers."""
    block_categories = {}

    for block_str, category in block_cats.items():
        try:
            block_num = int(block_str)
            if 1 <= block_num <= num_blocks and category in VALID_BLOCK_CATEGORIES:
                block_categories[block_num] = category
        except (ValueError, TypeError):
            continue

    # Fill missing blocks with default
    for i in range(1, num_blocks + 1):
        if i not in block_categories:
            block_categories[i] = "other_label"

    return block_categories


def process_comprehensive_result(
    result: dict[str, Any],
    text_blocks: list[dict[str, Any]]
) -> dict[str, Any]:
    """Process comprehensive analysis result into standard format."""
    qti_compat = result.get("qti_compatibility", {})
    visual_sep = result.get("visual_separation", {})
    block_cats = result.get("block_categories", {})

    # Validate and convert block categories
    block_categories = validate_block_categories(block_cats, len(text_blocks))

    # Build categorization result format (compatible with old code)
    question_answer_blocks = [
        i for i, cat in block_categories.items()
        if cat in ["question_text", "answer_choice", "question_part_header"]
    ]
    image_related_blocks = [
        i for i, cat in block_categories.items()
        if cat in ["visual_content_title", "visual_content_label"]
    ]

    _log_comprehensive_result(qti_compat, visual_sep, block_categories)

    return {
        "success": True,
        "compatibility": qti_compat,
        "categorization": {
            "block_categories": block_categories,
            "question_answer_blocks": question_answer_blocks,
            "image_related_blocks": image_related_blocks
        },
        "visual_separation": visual_sep,
        "ai_categories": block_categories,
        "has_visual_content": qti_compat.get('visual_content_required', False)
    }


def _log_comprehensive_result(
    qti_compat: dict[str, Any],
    visual_sep: dict[str, Any],
    block_categories: dict[int, str]
) -> None:
    """Log comprehensive analysis results."""
    print("🧠 ✅ Comprehensive analysis complete:")
    print(f"   QTI compatible: {qti_compat.get('can_represent', False)}")
    print(f"   Visual content required: {qti_compat.get('visual_content_required', False)}")
    print(f"   Prompt visuals: {visual_sep.get('has_prompt_visuals', False)}")
    print(f"   Choice visuals: {visual_sep.get('has_choice_visuals', False)}")
    print(f"   Blocks categorized: {len(block_categories)}")
