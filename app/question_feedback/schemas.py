"""JSON schemas for structured LLM output."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Feedback Review Schema (used during enrichment pipeline)
# ---------------------------------------------------------------------------
FEEDBACK_REVIEW_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "review_result": {
            "type": "string",
            "enum": ["pass", "fail"],
            "description": "Overall result: pass if all checks pass",
        },
        "feedback_accuracy": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["pass", "fail"]},
                "issues": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of factual/mathematical errors in feedback",
                },
                "reasoning": {"type": "string"},
            },
            "required": ["status", "issues", "reasoning"],
        },
        "feedback_clarity": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["pass", "fail"]},
                "issues": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of clarity/pedagogical issues",
                },
                "reasoning": {"type": "string"},
            },
            "required": ["status", "issues", "reasoning"],
        },
        "formatting_check": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["pass", "fail"]},
                "issues": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of formatting issues (LaTeX, number separators)",
                },
                "reasoning": {"type": "string"},
            },
            "required": ["status", "issues", "reasoning"],
        },
        "overall_reasoning": {"type": "string"},
    },
    "required": [
        "review_result",
        "feedback_accuracy",
        "feedback_clarity",
        "formatting_check",
        "overall_reasoning",
    ],
}


# ---------------------------------------------------------------------------
# Final Validation Schema (comprehensive, used as separate validation step)
# ---------------------------------------------------------------------------
FINAL_VALIDATION_SCHEMA: dict = {
    "type": "object",
    "properties": {
        # Checks come FIRST so the model reasons before committing to a verdict
        "correct_answer_check": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["pass", "fail"]},
                "marked_answer": {
                    "type": "string",
                    "description": "The Choice marked in qti-correct-response",
                },
                "verification_steps": {
                    "type": "string",
                    "description": "Step-by-step solution to verify the answer",
                },
                "issues": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["status", "marked_answer", "verification_steps", "issues"],
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
        # Verdict comes LAST — must match the checks above
        "validation_result": {
            "type": "string",
            "enum": ["pass", "fail"],
            "description": "Must match individual check statuses",
        },
    },
    "required": [
        "correct_answer_check",
        "feedback_check",
        "content_quality_check",
        "image_check",
        "math_validity_check",
        "overall_reasoning",
        "validation_result",
    ],
}
