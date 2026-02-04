"""JSON schemas for structured LLM output."""

from __future__ import annotations

FINAL_VALIDATION_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "validation_result": {
            "type": "string",
            "enum": ["pass", "fail"],
        },
        "correct_answer_check": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["pass", "fail"]},
                "expected_answer": {"type": "string"},
                "marked_answer": {"type": "string"},
                "verification_steps": {"type": "string"},
                "issues": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "status",
                "expected_answer",
                "marked_answer",
                "verification_steps",
                "issues",
            ],
        },
        "feedback_check": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["pass", "fail"]},
                "issues": {"type": "array", "items": {"type": "string"}},
                "reasoning": {"type": "string"},
            },
            "required": ["status", "issues", "reasoning"],
        },
        "content_quality_check": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["pass", "fail"]},
                "typos_found": {"type": "array", "items": {"type": "string"}},
                "character_issues": {"type": "array", "items": {"type": "string"}},
                "clarity_issues": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "status",
                "typos_found",
                "character_issues",
                "clarity_issues",
            ],
        },
        "image_check": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["pass", "fail", "not_applicable"],
                },
                "issues": {"type": "array", "items": {"type": "string"}},
                "reasoning": {"type": "string"},
            },
            "required": ["status", "issues", "reasoning"],
        },
        "math_validity_check": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["pass", "fail"]},
                "issues": {"type": "array", "items": {"type": "string"}},
                "reasoning": {"type": "string"},
            },
            "required": ["status", "issues", "reasoning"],
        },
        "overall_reasoning": {"type": "string"},
    },
    "required": [
        "validation_result",
        "correct_answer_check",
        "feedback_check",
        "content_quality_check",
        "image_check",
        "math_validity_check",
        "overall_reasoning",
    ],
}
