"""
PAES Optimizer

Optimizations specifically for PAES M1 format:
- All questions are choice (4 alternatives)
- All questions are mathematics
- 65 questions total
- Consistent format

This module provides optimized functions and configurations for PAES.
"""

from __future__ import annotations

from typing import Any, Dict


def get_paes_question_type() -> Dict[str, Any]:
    """
    Return fixed question type for PAES (always choice).
    Skips AI detection entirely.
    """
    return {
        "success": True,
        "question_type": "choice",
        "can_represent": True,
        "confidence": 1.0,
        "source": "paes_optimizer",
        "reason": "PAES format: all questions are choice with 4 alternatives",
    }


def optimize_prompt_for_math(prompt: str) -> str:
    """
    Optimize prompt specifically for mathematics questions.

    Adds instructions for:
    - Better MathML handling
    - Mathematical notation preservation
    - Formula recognition
    """
    math_instructions = """

IMPORTANT FOR MATHEMATICS QUESTIONS:
- Preserve all mathematical notation exactly (√, ², ³, fractions, etc.)
- Use MathML for all mathematical expressions
- Keep alternative labels (A, B, C, D) clearly separated
- Ensure 4 alternatives are always present
- Mathematical symbols must be properly encoded
"""
    return prompt + math_instructions


def get_paes_choice_config() -> Dict[str, Any]:
    """
    Get optimized QTI config for PAES choice questions.
    Ensures exactly 4 alternatives.
    """
    return {
        "type": "choice",
        "max_choices": 1,
        "min_choices": 1,
        "expected_alternatives": 4,
        "alternative_labels": ["A", "B", "C", "D"],
        "subject": "mathematics",
    }


def should_skip_validation_step(step: str, paes_mode: bool = True) -> bool:
    """
    Determine if a validation step can be skipped in PAES mode.

    NOTE: Currently, no validation steps are skipped in PAES mode to ensure
    quality, especially for questions with images, tables, and graphs.

    Args:
        step: Validation step name
        paes_mode: Whether PAES optimizations are enabled

    Returns:
        True if step can be skipped (currently always False)
    """
    # Don't skip validation - PAES questions can have images, tables, graphs
    # that need to be validated
    return False


def optimize_content_processing_for_paes(processed_content: Dict[str, Any]) -> Dict[str, Any]:
    """
    Optimize content processing for PAES format.

    - Assumes no complex tables (just question text + 4 alternatives)
    - Focuses on mathematical notation
    - Simplifies image processing
    """
    # Mark as PAES content
    processed_content["paes_mode"] = True
    processed_content["expected_format"] = "choice_4_alternatives"
    processed_content["subject"] = "mathematics"

    # Optimize: Skip table reconstruction if not needed
    if "tables" in processed_content:
        # Only keep tables if they're actually present and relevant
        tables = processed_content.get("tables", [])
        if not tables or len(tables) == 0:
            processed_content.pop("tables", None)

    return processed_content
