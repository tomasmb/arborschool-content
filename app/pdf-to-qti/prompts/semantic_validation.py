"""Prompts for semantic validation."""

from typing import Literal

SourceFormat = Literal["markdown", "html"]

SEMANTIC_VALIDATION_PROMPT = """<role>
You are a strict QA Judge for educational content conversion. Your job is to catch ANY content loss.
</role>

<task>
Verify that the generated QTI XML FAITHFULLY preserves ALL content from the original Markdown.
</task>

###
VALIDATION CHECKLIST - Check each item:
###

<checklist>
1. QUESTION NUMBERS: It is CORRECT to remove test-specific numbers like "5." or "Question 7"
2. ANSWER CHOICE ORDER: Choices must be in EXACT same sequence as source (NEVER reorder or alphabetize)
3. POST-IMAGE TEXT: Any descriptive text after images must be preserved
4. CREDITS/ATTRIBUTIONS: Photo credits like "© Paul Hakimata/Dreamstime.com" must be preserved
5. CORRECT ANSWER: If answer key in Markdown, must be in <qti-correct-response>
</checklist>

<rules>
1. Content Fidelity: Question content must be preserved in XML
2. No Hallucinations: No invented content in XML
3. Correct Answer Handling:
   - If answer key IS in Markdown → it MUST be in <qti-correct-response>
   - If answer key is NOT in Markdown → <qti-correct-response> must be OMITTED
4. Option Preservation: All answer choices present AND in EXACT original order
5. Formatting: Mathematical notation preserved
6. VISUAL CHOICES: If choices are shown in an image, it's VALID to use labels as choice text
7. ALT TEXT FLEXIBILITY: Alt text can be simplified (acceptable, do not penalize)
8. TEST-SPECIFIC REMOVAL (acceptable, do NOT penalize):
   - Question numbers ("5.", "Question 7", etc.)
   - Answer sheet instructions
   - Test-specific formatting instructions
</rules>

<output_format>
Return ONLY valid JSON with this schema:
{{
  "is_valid": boolean,
  "fidelity_score": 0-100,
  "errors": ["error1", "error2"],
  "warnings": ["warning1"]
}}
</output_format>

<scoring_penalties>
- Removed question number: NO PENALTY (this is correct behavior)
- Reordered answer choices: -15 points (FAIL if original order matters)
- Missing post-image description: -10 points
- Missing credits/attributions: -5 points
- Missing correct answer (when in source): -20 points (FAIL)
- Invented content: -30 points (FAIL)
</scoring_penalties>

<scoring_guide>
- 100: Perfect match
- 95-99: Minor formatting differences (acceptable)
- 90-94: Minor omissions like simplified alt text (acceptable)
- <90: Significant content errors (FAIL)
</scoring_guide>

<context>
Original {format_label}:
{source_content}

Generated QTI XML:
{xml}
</context>

<final_instruction>
Based on the {format_label} and XML above, validate content fidelity. Return JSON with is_valid, fidelity_score, errors, and warnings.
</final_instruction>
"""

FORMAT_LABELS = {
    "markdown": "Markdown",
    "html": "HTML",
}


def create_semantic_validation_prompt(
    source_content: str,
    xml: str,
    source_format: SourceFormat = "markdown",
) -> str:
    """Create semantic validation prompt."""
    format_label = FORMAT_LABELS.get(source_format, "Content")
    return SEMANTIC_VALIDATION_PROMPT.format(
        source_content=source_content,
        xml=xml,
        format_label=format_label,
    )

