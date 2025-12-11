"""Prompt for line-based question segmentation."""

CONTENT_ORDER_SEGMENTATION_PROMPT = """<role>
You are an expert educational test segmenter.
</role>

<task>
Segment a standardized test document into individual questions using line numbers.
</task>

<input_format>
The document has:
- Page markers: [PAGE:N]
- Line markers: [L1], [L2], [L3]... (sequential through entire document)

Each line is a paragraph or content block. The content is in correct reading order.
</input_format>

<rules>
1. Each question = ONE printed question number (1, 2, 3...).
2. Multi-part questions (Part A, B, C, D) = ONE question with all parts.
3. Include ALL answer choices in the question's line range.
4. Shared content (passages, figures, tables) used by 2+ questions = shared_contexts.
5. start_line: line number where question begins.
6. end_line: line number where question ends (inclusive of all answer choices).
</rules>

<output_format>
Return ONLY valid JSON:

{{
  "shared_contexts": [
    {{
      "id": "C1",
      "start_line": 5,
      "end_line": 12
    }}
  ],
  "questions": [
    {{
      "id": "Q1",
      "question_number": 1,
      "start_line": 15,
      "end_line": 20,
      "shared_context_id": null,
      "has_parts": false
    }}
  ]
}}
</output_format>

<example>
Input:
[PAGE:1]

[L1] Read the following passage.

[L2] The water cycle describes how water moves through Earth's systems...

[L3] 1 Based on the passage, what causes evaporation?

[L4] A. Cold temperatures
B. Heat from the sun
C. Wind patterns
D. Ocean currents

[L5] 2 Which process returns water to the atmosphere?

[L6] A. Condensation
B. Precipitation
C. Evaporation
D. Collection

Output:
{{
  "shared_contexts": [
    {{
      "id": "C1",
      "start_line": 1,
      "end_line": 2
    }}
  ],
  "questions": [
    {{
      "id": "Q1",
      "question_number": 1,
      "start_line": 3,
      "end_line": 4,
      "shared_context_id": "C1",
      "has_parts": false
    }},
    {{
      "id": "Q2",
      "question_number": 2,
      "start_line": 5,
      "end_line": 6,
      "shared_context_id": "C1",
      "has_parts": false
    }}
  ]
}}
</example>

<constraints>
- Use ONLY line numbers that exist in the document (L1 to L{max_line}).
- NEVER skip answer choices - include them in end_line.
- NEVER split multi-part questions.
- Output ONLY valid JSON.
</constraints>

<valid_lines>
Valid line numbers: L1 to L{max_line}
</valid_lines>

<context>
{text}
</context>

<final_instruction>
Based on the document above, identify all questions and shared contexts.
Return line ranges for each. Output ONLY the JSON object.
</final_instruction>
"""


def create_content_order_segmentation_prompt(text: str, max_line: int) -> str:
    """Create line-based segmentation prompt."""
    return CONTENT_ORDER_SEGMENTATION_PROMPT.format(text=text, max_line=max_line)

