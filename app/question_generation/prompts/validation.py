"""Prompts for the validation phases (Phase 6 solvability check).

The solvability prompt asks the model to independently solve a
QTI question and return its answer for comparison with the
declared correct option.
"""

from __future__ import annotations

SOLVABILITY_PROMPT = """\
You are a mathematics expert. Solve the following PAES-style \
multiple-choice question step by step.

## QTI Question XML

{qti_xml}

## Instructions

1. Read the question stem and all four options (A-D).
2. Solve the problem independently, showing your reasoning.
3. Determine which option is correct.

## Output Format (strict JSON)

Return ONLY a JSON object:
```json
{{
  "answer": "<letter A, B, C, or D>",
  "steps": "<brief step-by-step reasoning>"
}}
```
"""


def build_solvability_prompt(qti_xml: str) -> str:
    """Build the solvability check prompt for a QTI question.

    Args:
        qti_xml: The QTI XML to solve.

    Returns:
        Formatted prompt string.
    """
    return SOLVABILITY_PROMPT.format(qti_xml=qti_xml)
