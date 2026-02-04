"""
Feedback Validator for QTI 3.0 assessment items.

Uses LLM to validate that generated feedback is accurate, appropriate,
and pedagogically sound.
"""

import json
import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from feedback_system.prompts import build_validation_prompt
from feedback_system.utils.openai_retry import call_with_retry

load_dotenv()


class FeedbackValidator:
    """Validates generated feedback using LLM."""

    def __init__(self, api_key: str = None):
        """Initialize with OpenAI API key (from param or env)."""
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"), timeout=300.0)

    def validate_feedback(
        self,
        qti_xml: str,
        qti_xml_with_feedback: str,
        feedback_data: dict[str, Any],
        question_info: dict[str, Any],
        image_urls: list[str] = None,
    ) -> dict[str, Any]:
        """Validate generated feedback."""
        if "parts" in feedback_data:
            return self._validate_composite_feedback(qti_xml, qti_xml_with_feedback, feedback_data, image_urls)

        prompt = build_validation_prompt(qti_xml, qti_xml_with_feedback, feedback_data, question_info, image_urls)
        schema = self._get_validation_schema()
        default_error = {"validation_result": "fail", "issues": ["Validation failed"]}

        return call_with_retry(
            client=self.client,
            prompt=prompt,
            schema=schema,
            schema_name="feedback_validation",
            image_urls=image_urls,
            default_on_error=default_error,
        )

    def _get_validation_schema(self) -> dict[str, Any]:
        """Return the validation schema for single question feedback."""
        return {
            "type": "object",
            "properties": {
                "validation_result": {"type": "string", "enum": ["pass", "fail"]},
                "correct_answer_check": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["pass", "fail", "insufficient_information"]},
                        "issues": {"type": "array", "items": {"type": "string"}},
                        "reasoning": {"type": "string"},
                    },
                    "required": ["status", "issues", "reasoning"],
                    "additionalProperties": False,
                },
                "feedback_correctness_check": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["pass", "fail", "insufficient_information"]},
                        "issues": {"type": "array", "items": {"type": "string"}},
                        "reasoning": {"type": "string"},
                    },
                    "required": ["status", "issues", "reasoning"],
                    "additionalProperties": False,
                },
                "quality_pedagogy_check": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["pass", "fail"]},
                        "issues": {"type": "array", "items": {"type": "string"}},
                        "reasoning": {"type": "string"},
                    },
                    "required": ["status", "issues", "reasoning"],
                    "additionalProperties": False,
                },
                "overall_reasoning": {"type": "string"},
            },
            "required": [
                "validation_result",
                "correct_answer_check",
                "feedback_correctness_check",
                "quality_pedagogy_check",
                "overall_reasoning",
            ],
            "additionalProperties": False,
        }

    def _validate_composite_feedback(
        self,
        qti_xml: str,
        qti_xml_with_feedback: str,
        feedback_data: dict[str, Any],
        image_urls: list[str] = None,
    ) -> dict[str, Any]:
        """Validate composite question feedback with multiple parts."""
        from feedback_system.utils.qti_xml_utils import extract_composite_parts_info

        parts_info = extract_composite_parts_info(qti_xml)
        if not parts_info:
            return {"validation_result": "fail", "issues": ["Failed to extract composite parts info"]}

        prompt = self._build_composite_validation_prompt(
            qti_xml, qti_xml_with_feedback, feedback_data, parts_info, image_urls
        )
        schema = self._get_composite_validation_schema(parts_info)
        default_error = {"validation_result": "fail", "issues": ["Validation failed"]}

        return call_with_retry(
            client=self.client,
            prompt=prompt,
            schema=schema,
            schema_name="composite_feedback_validation",
            image_urls=image_urls,
            default_on_error=default_error,
        )

    def _build_composite_validation_prompt(
        self,
        qti_xml: str,
        qti_xml_with_feedback: str,
        feedback_data: dict[str, Any],
        parts_info: list[dict[str, Any]],
        image_urls: list[str] = None,
    ) -> str:
        """Build validation prompt for composite question."""
        images_note = ""
        if image_urls:
            images_note = f"\n- Images: {len(image_urls)} image(s) provided below for visual validation"

        parts_metadata = []
        for part_info in parts_info:
            part_meta = f"""Part {part_info["part_id"]}:
  - Response Identifier: {part_info["response_identifier"]}
  - Interaction Type: {part_info["interaction_type"]}"""
            if part_info.get("correct_response"):
                part_meta += f"\n  - Marked Correct Response: {part_info['correct_response']}"
            if part_info.get("choices"):
                part_meta += f"\n  - Choices: {json.dumps(part_info['choices'], indent=4)}"
            parts_metadata.append(part_meta)

        parts_metadata_str = "\n\n".join(parts_metadata)

        return f"""You are an expert educational assessment validator.

TASK: Validate a COMPOSITE QTI 3.0 assessment item with {len(parts_info)} parts.
Each part must be validated independently across three dimensions:
1. Correct Answer Validation (MCQ parts): Verify the marked correct answer(s) are correct
2. Feedback Correctness: Verify feedback is accurate
3. Quality & Pedagogy: Verify feedback is grade-appropriate and pedagogically sound

GROUNDING:
- Use ONLY the provided QTI XML and images for item context{images_note}

ORIGINAL QTI:
```xml
{qti_xml}
```

QTI WITH FEEDBACK:
```xml
{qti_xml_with_feedback}
```

FEEDBACK DATA:
```json
{json.dumps(feedback_data, indent=2)}
```

EXTRACTED METADATA:
This is a COMPOSITE question with {len(parts_info)} parts:

{parts_metadata_str}

VALIDATION CHECKS (for each part):
1. CORRECT ANSWER VALIDATION
   - For MCQ parts: Verify the marked correct answer is actually correct
   - For FRQ parts: Return "insufficient_information" (no keyed answer exists)

2. FEEDBACK CORRECTNESS VALIDATION
   - For MCQ: Does feedback accurately explain why answers are right/wrong?
   - For FRQ: Is the rubric/exemplar specific and instructive?

3. QUALITY & PEDAGOGY VALIDATION (all parts)
   - Is feedback self-contained?
   - Is language appropriate for Grade 4-5?
   - Are solution/exemplar steps clear and logical?

OUTPUT REQUIREMENTS:
- validation_result is "pass" if ALL parts pass ALL applicable checks
- For each part, provide separate validation results
- issues arrays should be empty if status is "pass"
- reasoning should be specific and reference the actual content"""

    def _get_composite_validation_schema(self, parts_info: list[dict[str, Any]]) -> dict:
        """Return validation schema for composite question."""
        part_validation_schema = {
            "type": "object",
            "properties": {
                "part_id": {"type": "string"},
                "correct_answer_check": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["pass", "fail", "insufficient_information"]},
                        "issues": {"type": "array", "items": {"type": "string"}},
                        "reasoning": {"type": "string"},
                    },
                    "required": ["status", "issues", "reasoning"],
                    "additionalProperties": False,
                },
                "feedback_correctness_check": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["pass", "fail", "insufficient_information"]},
                        "issues": {"type": "array", "items": {"type": "string"}},
                        "reasoning": {"type": "string"},
                    },
                    "required": ["status", "issues", "reasoning"],
                    "additionalProperties": False,
                },
                "quality_pedagogy_check": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["pass", "fail"]},
                        "issues": {"type": "array", "items": {"type": "string"}},
                        "reasoning": {"type": "string"},
                    },
                    "required": ["status", "issues", "reasoning"],
                    "additionalProperties": False,
                },
            },
            "required": ["part_id", "correct_answer_check", "feedback_correctness_check", "quality_pedagogy_check"],
            "additionalProperties": False,
        }

        return {
            "type": "object",
            "properties": {
                "validation_result": {"type": "string", "enum": ["pass", "fail"]},
                "parts": {"type": "array", "items": part_validation_schema, "minItems": len(parts_info)},
                "overall_reasoning": {"type": "string"},
            },
            "required": ["validation_result", "parts", "overall_reasoning"],
            "additionalProperties": False,
        }
