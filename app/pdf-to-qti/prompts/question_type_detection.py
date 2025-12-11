"""Prompts for question type detection."""

from __future__ import annotations

from typing import Literal

SourceFormat = Literal["markdown", "html"]

QUESTION_TYPE_DETECTION_PROMPT = """<role>
You are an expert in educational assessment formats, particularly QTI 3.0 specification.
</role>

<task>
Analyze the question content and determine the most appropriate QTI 3.0 interaction type.
</task>

<supported_types>
- choice: Single or multiple-choice questions
- match: Questions where items from two sets need to be paired
- text-entry: Questions requiring short text input
- hotspot: Questions requiring clicking on a specific area of an image
- extended-text: Questions requiring longer text input/essay responses
- hot-text: Questions where specific text needs to be selected
- gap-match: Questions where text must be dragged to fill gaps (NOT for tables)
- order: Questions requiring ordering/ranking items
- graphic-gap-match: Questions matching items to locations on an image
- inline-choice: Questions with dropdown selections within text
- select-point: Questions requiring clicking specific points on an image
- media-interaction: Questions involving audio or video media
- composite: Multi-part questions with different interaction types
</supported_types>

<rules>
1. If gap-match has table structure, use "match" instead (QTI 3.0 doesn't support gaps in table cells)
2. For multi-part questions (Part A, Part B), return "composite"
3. If question cannot be represented, set can_represent=false
</rules>

<unsupported>
- Dragging bars to heights
- Dividing shapes into sections
- Placing shapes on coordinate grids
- Custom drawing/sketching
- Complex mathematical input editors
- Interactive simulations
</unsupported>

<output_format>
Return ONLY valid JSON with this schema:
{{
  "can_represent": true/false,
  "question_type": "type or null if unsupported",
  "confidence": 0.0-1.0,
  "reason": "brief explanation",
  "key_elements": ["list", "of", "key", "elements"],
  "potential_issues": ["any", "concerns"]
}}
</output_format>

<context>
Source Format: {source_format}
{format_note}

Question Content:
{question_content}
</context>

<final_instruction>
Based on the question content above, determine the QTI 3.0 interaction type. Return JSON with can_represent, question_type, confidence, reason, key_elements, and potential_issues.
</final_instruction>
"""

FORMAT_NOTES = {
    "markdown": "",
    "html": "Note: Content is in HTML format. Parse HTML tags to understand structure.",
}


def create_detection_prompt(
    question_content: str,
    source_format: SourceFormat = "markdown",
) -> str:
    """Create question type detection prompt with question content."""
    format_note = FORMAT_NOTES.get(source_format, "")
    return QUESTION_TYPE_DETECTION_PROMPT.format(
        question_content=question_content,
        source_format=source_format,
        format_note=format_note,
    )

