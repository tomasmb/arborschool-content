"""
Choice Diagram Detection

Functions to determine if a question is a multiple choice question with diagram options.
Analyzes text patterns, AI categorization, and question structure.
"""

from __future__ import annotations

import re
from typing import Any


def is_choice_diagram_question(text_blocks: list[dict[str, Any]], ai_categories: dict[int, str] | None = None, question_text: str = "") -> bool:
    """
    Determine if this is a multiple choice question with diagram options.

    Looks for:
    1. Question text asking about visual elements ("shows", "diagram", "appears", etc.)
    2. Multiple answer choices with visual indicators
    3. AI categorization indicating visual content

    IMPORTANT: Distinguishes between actual multiple choice questions and multi-part questions
    where A, B, C are question parts (e.g., "Part A", "A. Identify the three characteristics")

    UPDATED: More conservative to avoid misidentifying prompt visual elements as choices

    Args:
        text_blocks: All text blocks from the page
        ai_categories: AI categorization of text blocks
        question_text: The question text for additional context

    Returns:
        True if this appears to be a choice diagram question
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
    if _has_multi_part_indicators(all_text):
        print("🎯 Multi-part question detected - NOT a choice diagram")
        return False

    # Check for prompt visual indicators
    has_prompt_visuals = _has_prompt_visual_indicators(all_text)
    if has_prompt_visuals:
        print("🎯 Prompt visual content detected - likely NOT a choice diagram question")

    # Check for visual question indicators
    has_visual_question = _has_visual_question_indicators(all_text)

    # Check for explicit choice question language
    explicit_choice_question = _has_explicit_choice_question(all_text)

    # Check for actual choice options
    has_actual_choice_options, total_choice_matches = _has_choice_options(all_text)

    # Check AI categorization for visual content
    has_ai_visual_indicators = _has_ai_visual_indicators(ai_categories)

    # Final decision: Be conservative
    # Only consider it a choice diagram if:
    # 1. It has explicit visual choice question language AND
    # 2. It has clear choice option structure AND
    # 3. It's not detected as having prompt visuals
    result = explicit_choice_question and has_actual_choice_options and not has_prompt_visuals

    print(f"🎯 Visual question: {has_visual_question}")
    print(f"🎯 Explicit choice question: {explicit_choice_question}")
    print(f"🎯 Actual choice options: {has_actual_choice_options} (found {total_choice_matches} matches)")
    print(f"🎯 Prompt visuals detected: {has_prompt_visuals}")
    print(f"🎯 AI visual indicators: {has_ai_visual_indicators}")
    print(f"🎯 Is choice diagram question: {result}")

    return result


def _has_multi_part_indicators(all_text: str) -> bool:
    """Check for multi-part question indicators that indicate NOT a choice diagram."""
    multi_part_indicators = [
        "part a",
        "part b",
        "part c",
        "part d",
        "a.",
        "b.",
        "c.",
        "d.",
        "a)",
        "b)",
        "c)",
        "d)",
        "identify",
        "explain",
        "describe",
        "analyze",
        "based on the model",
        "the model shown",
        "three parts",
        "two parts",
        "four parts",
        "label each part",
        "name the parts",
        "list the components",
    ]
    return any(indicator in all_text for indicator in multi_part_indicators)


def _has_prompt_visual_indicators(all_text: str) -> bool:
    """Check for indicators that visual content is part of the question setup, not choices."""
    prompt_visual_indicators = [
        "hydrogen peroxide",
        "water",
        "oxygen",  # Molecule names
        "molecule",
        "molecular",
        "atoms",
        "compound",
        "element",
        "diagram shows",
        "diagrams shown",
        "shown above",
        "image above",
        "in the diagram",
        "from the diagram",
        "the diagram",
        "the model",
        "conservation of mass",
        "chemical reaction",
        "breaks apart",
    ]
    return any(indicator in all_text for indicator in prompt_visual_indicators)


def _has_visual_question_indicators(all_text: str) -> bool:
    """Check for visual question indicators - generalized for any subject."""
    visual_indicators = [
        "which of the following best shows",
        "which diagram",
        "which figure",
        "which image",
        "which picture",
        "which model shows",
        "which correctly shows",
        "which accurately depicts",
    ]
    return any(indicator in all_text for indicator in visual_indicators)


def _has_explicit_choice_question(all_text: str) -> bool:
    """Check for explicit choice question language."""
    return any(
        ["which of the following" in all_text, "which diagram shows" in all_text, "which model shows" in all_text, "which figure shows" in all_text]
    )


def _has_choice_options(all_text: str) -> tuple[bool, int]:
    """
    Check for explicit choice option structure.

    Returns:
        Tuple of (has_actual_choice_options, total_matches)
    """
    choice_option_patterns = [
        r"([A-D])\s*[\.:\)]\s*[A-Z]",  # A. Something, A) Something, A: Something
        r"([A-D])\s+Reactants\s+Products",  # A Reactants Products (table headers)
        r"([A-D])\s*[\.:\)]\s*\w{3,}",  # A. word, but word must be at least 3 chars
    ]

    total_choice_matches = 0
    for pattern in choice_option_patterns:
        matches = re.findall(pattern, all_text.upper())
        total_choice_matches += len(matches)

    return total_choice_matches >= 2, total_choice_matches


def _has_ai_visual_indicators(ai_categories: dict[int, str] | None) -> bool:
    """Check AI categorization for visual content indicators."""
    if not ai_categories:
        return False

    visual_categories = ["visual_content_title", "visual_content_label", "other_label"]
    return any(cat in visual_categories for cat in ai_categories.values())
