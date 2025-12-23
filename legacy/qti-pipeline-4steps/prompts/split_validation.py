"""Prompts for split validation."""

from __future__ import annotations

import json

# Import from parent package
try:
    from models import QuestionChunk, SharedContext
except ImportError:
    from ..models import QuestionChunk, SharedContext

SPLIT_VALIDATION_PROMPT = """<role>
You are an expert QA validator for educational question segmentation.
</role>

<task>
Validate that each question is self-contained, complete, and free of contamination.
</task>

<rules>
1. Has question stem (not just options)
2. Has all answer choices for MCQ (in text, image captions, or figure descriptions)
3. No contamination from adjacent questions
4. No internal splits (single question not split)
5. Referenced resources present (passage, figure, table in content or shared_context)
6. Multi-part questions must have all declared parts
7. Visual content valid if image URL or descriptive content exists
8. Ignore page headers/footers when judging contamination
9. Minor OCR glitches acceptable if options are understandable
</rules>

<output_schema>
{{
  "is_valid": boolean,
  "validation_results": [{{
    "question_id": "Q1",
    "is_self_contained": boolean,
    "errors": ["error1"],
    "warnings": ["warning1"]
  }}]
}}
</output_schema>

<examples>
Valid MCQ with image:
{{"id": "Q1", "content": "See triangle below.\\n![Triangle](url)\\nAngle A?\\nA. 30°\\nB. 45°\\nC. 60°\\nD. 90°"}}
→ {{"is_self_contained": true, "errors": [], "warnings": []}}

Missing image:
{{"id": "Q1", "content": "See triangle below.\\nAngle A?\\nA. 30°\\nB. 45°"}}
→ {{"is_self_contained": false, "errors": ["References 'triangle below' but no image"], "warnings": []}}

ASCII art graph (valid):
{{"id": "Q7", "content": "This graph...\\ny\\n5\\n4\\n3\\n2\\n1\\n0 1 2 3 x\\nSlope?\\nA. 1\\nB. 2"}}
→ {{"is_self_contained": true, "errors": [], "warnings": ["ASCII art graph instead of image"]}}

Complete 4-part:
{{"id": "Q6", "content": "This question has four parts.\\n6 Prices...\\nA. Range?\\nB. Median?\\nC. New magazines...\\nD. New median?"}}
→ {{"is_self_contained": true, "errors": [], "warnings": []}}

Incomplete 4-part:
{{"id": "Q6", "content": "This question has four parts.\\n6 Prices...\\nA. Range?\\nB. Median?\\nC. New magazines..."}}
→ {{"is_self_contained": false, "errors": ["States 'four parts' but missing Part D"], "warnings": []}}
</examples>

<constraints>
- FAIL if incomplete (missing stem, options, or parts)
- FAIL if contaminated with other questions
- FAIL if references missing content
- PASS if visual content exists (image, URL marker, or descriptive content)
- PASS if distinct labeled options are present anywhere in content
- Output ONLY valid JSON - no markdown, no explanations
</constraints>

<context>
Questions:
{questions_json}

Shared Contexts:
{shared_contexts_json}
</context>

<final_instruction>
Based on the questions and contexts above, validate each question.
Return JSON with validation results. Be strict - incomplete questions must fail.
</final_instruction>
"""


def create_split_validation_prompt(
    questions: list[QuestionChunk], 
    shared_contexts: list[SharedContext] | None = None
) -> str:
    """Create validation prompt with context at end."""
    questions_json = json.dumps([q.model_dump() for q in questions], indent=2)
    shared_contexts_json = json.dumps(
        [ctx.model_dump() for ctx in (shared_contexts or [])], 
        indent=2
    )
    return SPLIT_VALIDATION_PROMPT.format(
        questions_json=questions_json,
        shared_contexts_json=shared_contexts_json
    )

