"""
Validation prompts and response parsing for QTI validation.

This module contains the GPT-5.1 validation prompt and response
parsing logic for comprehensive QTI validation.
"""

from __future__ import annotations

import json
from typing import Any


def create_validation_prompt() -> str:
    """Create comprehensive validation prompt for GPT-5.1.

    Returns:
        Detailed validation prompt string
    """
    return """You are a QTI question validation expert. You will receive two images:
1. ORIGINAL PDF: The source question from a PDF document
2. RENDERED QTI: The same question rendered in a QTI testing platform

Your task is to validate if the rendered QTI question is functionally complete and correct \
for assessment purposes.

VALIDATION FOCUS - ONLY CHECK THESE:
□ QUESTION CONTENT: Is the core question text present and correct?
□ ANSWER ELEMENTS: Are all answer choices, input fields, or response areas working?
□ VISUAL CONTENT: Are essential images, diagrams, charts, or tables displayed properly?
□ INSTRUCTIONS: Are the question instructions clear and complete?
□ FUNCTIONALITY: Do interactive elements (inputs, buttons) work as expected?
□ SEMANTIC COMPLETENESS: Does the question make sense and is answerable?

IGNORE THESE (NOT QTI VALIDITY CONCERNS):
✗ Page numbers, headers, footers
✗ "GO ON" or navigation indicators
✗ PDF document formatting artifacts
✗ Minor spacing or font differences
✗ Test booklet metadata
✗ Page layout variations that don't affect question clarity

CRITICAL ISSUES TO FLAG:
- Missing or corrupted question text
- Missing answer choices or input fields
- Essential images/diagrams not displaying
- Broken interactive elements
- Question is unanswerable due to missing information
- Weird rendering that affects question understanding

RESPONSE FORMAT:
Provide your response in this JSON format:

{
  "validation_passed": true/false,
  "overall_score": 0-100,
  "completeness_score": 0-100,
  "accuracy_score": 0-100,
  "visual_score": 0-100,
  "functionality_score": 0-100,
  "issues_found": [
    "Only list issues that affect QTI question validity"
  ],
  "missing_elements": [
    "Only essential question elements, not document artifacts"
  ],
  "recommendations": [
    "Suggestions for fixing actual QTI problems"
  ],
  "validation_summary": "Brief summary focusing on QTI assessment validity"
}

VALIDATION CRITERIA:
- PASS: Overall score ≥ 80 AND no critical question content missing
- FAIL: Overall score < 80 OR essential question elements missing

Focus on whether a student can properly understand and answer the question, \
not exact PDF replication."""


def parse_validation_response(response_text: str) -> dict[str, Any]:
    """Parse GPT-5.1 validation response into structured result.

    Args:
        response_text: Raw response from GPT-5.1

    Returns:
        Structured validation result dictionary
    """
    try:
        # Look for JSON in the response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1

        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            validation_data = json.loads(json_str)

            # Ensure required fields exist
            validation_passed = validation_data.get("validation_passed", False)
            overall_score = validation_data.get("overall_score", 0)

            return {
                "success": True,
                "validation_passed": validation_passed,
                "overall_score": overall_score,
                "completeness_score": validation_data.get("completeness_score", 0),
                "accuracy_score": validation_data.get("accuracy_score", 0),
                "visual_score": validation_data.get("visual_score", 0),
                "functionality_score": validation_data.get("functionality_score", 0),
                "issues_found": validation_data.get("issues_found", []),
                "missing_elements": validation_data.get("missing_elements", []),
                "recommendations": validation_data.get("recommendations", []),
                "validation_summary": validation_data.get("validation_summary", ""),
                "raw_response": response_text,
                "validation_details": validation_data
            }
        else:
            # Fallback parsing if JSON not found
            response_lower = response_text.lower()
            validation_passed = (
                "validation_passed\": true" in response_lower
                or "pass" in response_lower
            )

            return {
                "success": True,
                "validation_passed": validation_passed,
                "overall_score": 50 if validation_passed else 25,
                "issues_found": ["Could not parse detailed validation results"],
                "validation_summary": "Validation completed but response parsing failed",
                "raw_response": response_text,
                "validation_details": {}
            }

    except Exception as e:
        # Error handling - assume validation failed
        return {
            "success": False,
            "validation_passed": False,
            "overall_score": 0,
            "error": f"Failed to parse validation response: {str(e)}",
            "raw_response": response_text,
            "validation_details": {}
        }


def should_proceed_with_qti(validation_result: dict[str, Any]) -> bool:
    """Determine if QTI should be returned based on validation results.

    Focus on semantic correctness rather than perfect visual reproduction.

    Args:
        validation_result: Result from comprehensive validation

    Returns:
        Boolean indicating whether to proceed with QTI
    """
    if not validation_result.get("success", False):
        return False

    if not validation_result.get("validation_passed", False):
        return False

    # More lenient score threshold - focus on educational validity
    overall_score = validation_result.get("overall_score", 0)
    if overall_score < 60:  # Lowered from 80 to 60
        return False

    # Check for critical missing elements (only truly essential ones)
    missing_elements = validation_result.get("missing_elements", [])
    if missing_elements:
        # Only block for truly critical missing content
        critical_keywords = ["question text", "answer choices", "essential", "critical", "main"]

        for missing in missing_elements:
            missing_lower = missing.lower()
            # Only consider it critical if it contains specific critical terms
            if any(keyword in missing_lower for keyword in critical_keywords):
                return False

    # If completeness and functionality scores are reasonable, proceed
    completeness = validation_result.get("completeness_score", 0)
    functionality = validation_result.get("functionality_score", 0)

    # Allow if content is mostly complete and functional, even if formatting isn't perfect
    if completeness >= 65 and functionality >= 65:
        return True

    return False
