"""
Feedback generation and validation prompts.

Contains prompt building functions for QTI feedback generation.
Customize the grade level and subject by editing the prompts below.
"""

import json
from typing import Any


def get_interaction_specific_guidance(interaction_type: str) -> str:
    """Get interaction-specific guidance for feedback generation."""
    guidance = {
        "choice_interaction_single": """
- Include inline rationale for EVERY choice (explain why it's right or why it's tempting but wrong)
- DO NOT start with "Correct!" or "Incorrect." - just provide the explanation
- Worked example: 2-5 steps showing the reasoning to identify the correct answer""",
        "choice_interaction_multi": """
- Include inline rationale for EVERY choice
- DO NOT start with "Correct!" or "Incorrect." - just provide the explanation
- State which options belong in the correct set for this specific question
- Worked example: explain the full correct set, justifying each member""",
        "text_entry_interaction": """
- Pattern-targeted inline feedback for common wrong answers only if relevant
- Worked example: show the reasoning to produce the correct answer""",
        "extended_text_interaction": """
- FRQ rubric: 3-5 concise criteria bullets focused on this specific prompt
- Exemplar outline: 3-5 steps showing how to structure a strong response
- Rubric should guide graders; exemplar should teach students""",
        "inline_choice_interaction": """
- Per-blank inline rationale tied to the sentence meaning
- Worked example: reconstruct the full sentence and justify each blank""",
        "match_interaction": """
- Inline rationale per pair (what makes it right for this item)
- Worked example: final mapping/sequence with one-sentence justifications""",
        "order_interaction": """
- Inline rationale per position in sequence
- Worked example: correct sequence with justification for the ordering""",
    }

    return guidance.get(
        interaction_type,
        """
- Provide inline feedback appropriate to the interaction type
- Worked example: 2-5 steps showing how to solve this specific question""",
    )


def build_generation_prompt(qti_xml: str, question_info: dict[str, Any], image_urls: list[str] = None) -> str:
    """Build prompt for single question feedback generation."""
    interaction_type = question_info.get("interaction_type", "unknown")
    specific_guidance = get_interaction_specific_guidance(interaction_type)

    images_note = ""
    if image_urls:
        images_note = f"\n- Images: {len(image_urls)} image(s) provided below for visual context"

    if interaction_type == "extended_text_interaction":
        output_rules = """- rubric_criteria: focus on THIS specific prompt only (not generic)
- exemplar: show how to structure a strong response to THIS prompt (not a full sample answer)"""
    else:
        output_rules = """- correct_response: identify the scientifically accurate answer(s)
- per_choice_feedback: include ALL interactive elements; each rationale explains why right/wrong
- worked_solution: 2-5 clear steps showing the reasoning path for THIS specific item"""

    return f"""You are an expert educational content creator specializing in QTI 3.0 assessment items.

TASK: Generate comprehensive, student-friendly feedback for this QTI 3.0 assessment item.

AUDIENCE:
- Grade: 4-5
- Reading level: G4-G5 (plain language, kid-clear)
- Context: Formative assessment with inline and block feedback

GROUNDING:
- Use ONLY the provided QTI XML and images for item context
- All explanations must reference only this specific stem/stimulus/options/images{images_note}

QTI ITEM:
```xml
{qti_xml}
```

EXTRACTED METADATA:
- Interaction Type: {interaction_type}{
        f'''
- Choices: {json.dumps(question_info.get("choices", []), indent=2)}'''
        if question_info.get("choices")
        else ""
    }

REQUIREMENTS:
Core rules:
- NO modal feedback - use ONLY inline and block feedback
- Each feedback element MUST be completely self-contained
- All feedback must be on-item only (tied to this specific stem/stimulus/options/images)
- Keep language neutral and accessible (G4-G5 reading level)
- DO NOT start feedback with "Correct!" or "Incorrect." - this will be added programmatically

Interaction-specific requirements for {interaction_type}:
{specific_guidance}

Output requirements:
{output_rules}
- No cross-references, no hints, no global feedback
- All content must be self-contained and tied to this specific item"""


def build_composite_generation_prompt(
    qti_xml: str, parts_info: list[dict[str, Any]], image_urls: list[str] = None
) -> str:
    """Build prompt for composite question with multiple parts."""
    images_note = ""
    if image_urls:
        images_note = f"\n- Images: {len(image_urls)} image(s) provided below for visual context"

    parts_metadata = []
    for part in parts_info:
        part_meta = f"""Part {part["part_id"]}:
  - Response Identifier: {part["response_identifier"]}
  - Interaction Type: {part["interaction_type"]}"""
        if part.get("choices"):
            part_meta += f"\n  - Choices: {json.dumps(part['choices'], indent=4)}"
        parts_metadata.append(part_meta)

    parts_metadata_str = "\n\n".join(parts_metadata)

    parts_guidance = []
    for part in parts_info:
        interaction_type = part["interaction_type"]
        specific_guidance = get_interaction_specific_guidance(interaction_type)
        parts_guidance.append(f"**Part {part['part_id']}** ({interaction_type}):{specific_guidance}")

    parts_guidance_str = "\n\n".join(parts_guidance)

    return f"""You are an expert educational content creator specializing in QTI 3.0 assessment items.

TASK: Generate feedback for a COMPOSITE QTI 3.0 assessment item with {len(parts_info)} parts.
Each part must be treated independently with its own feedback.

AUDIENCE:
- Grade: 4-5
- Reading level: G4-G5 (plain language, kid-clear)

GROUNDING:
- Use ONLY the provided QTI XML and images for item context{images_note}

QTI ITEM:
```xml
{qti_xml}
```

EXTRACTED METADATA:
This is a COMPOSITE question with {len(parts_info)} parts:

{parts_metadata_str}

REQUIREMENTS:
Core rules:
- NO modal feedback - use ONLY inline and block feedback
- Each feedback element MUST be completely self-contained
- All feedback must be on-item only
- Keep language neutral and accessible (G4-G5 reading level)
- DO NOT start feedback with "Correct!" or "Incorrect." - added programmatically

Interaction-specific requirements for each part:

{parts_guidance_str}

Output requirements:
- Generate feedback for ALL {len(parts_info)} parts
- Each part must have its own independent feedback
- For FRQs: rubric_criteria + exemplar
- For MCQs: correct_response + per_choice_feedback + worked_solution"""


def build_validation_prompt(
    qti_xml: str,
    qti_xml_with_feedback: str,
    feedback_data: dict[str, Any],
    question_info: dict[str, Any],
    image_urls: list[str] = None,
) -> str:
    """Build validation prompt for single question feedback."""
    interaction_type = question_info.get("interaction_type", "unknown")
    images_note = ""
    if image_urls:
        images_note = f"\n- Images: {len(image_urls)} image(s) provided below for visual validation"

    if interaction_type == "extended_text_interaction":
        metadata_section = f"- Interaction Type: {interaction_type}"
        validation_checks = """VALIDATION CHECKS:
1. RUBRIC VALIDATION
   - Are rubric criteria specific to this prompt (not generic)?
   - Do criteria focus on content/evidence/reasoning/clarity relevant to this question?

2. EXEMPLAR VALIDATION
   - Is the exemplar outline specific to this prompt?
   - Does it show how to structure a response (not provide a full answer)?

3. QUALITY & PEDAGOGY VALIDATION
   - Is content self-contained (no cross-references)?
   - Is language appropriate for Grade 4-5 reading level?"""
    else:
        metadata_section = f"""- Interaction Type: {interaction_type}
- Marked Correct Response: {question_info.get("correct_response", "unknown")}{
            f'''
- Choices: {json.dumps(question_info.get("choices", []), indent=2)}'''
            if question_info.get("choices")
            else ""
        }"""
        validation_checks = """VALIDATION CHECKS:
1. CORRECT ANSWER VALIDATION
   - Does the marked correct answer actually answer the question correctly?
   - For multi-choice, are ALL marked correct answers actually correct?
   - Is the scientific/factual content of the correct answer accurate?

2. FEEDBACK CORRECTNESS VALIDATION
   - Does the feedback for the correct answer accurately explain why it's correct?
   - Does the feedback for each incorrect choice accurately explain why it's wrong?
   - Are there any factual errors in any feedback?
   - Does the worked solution lead to the correct answer?

3. QUALITY & PEDAGOGY VALIDATION
   - Is feedback self-contained (no cross-references)?
   - Is language appropriate for Grade 4-5 reading level?
   - Are worked solution steps clear and logical?"""

    return f"""You are an expert educational assessment validator.

TASK: Validate a QTI 3.0 assessment item with feedback across three dimensions:
1. Correct Answer Validation: Verify the marked correct answer(s) are actually correct
2. Feedback Correctness: Verify feedback is accurate and explains why answers are right/wrong
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
{metadata_section}

{validation_checks}

OUTPUT REQUIREMENTS:
- validation_result is "pass" if all applicable checks pass
- issues arrays should be empty if status is "pass"
- reasoning should be specific and reference the actual content"""
