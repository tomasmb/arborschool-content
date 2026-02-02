"""
Prompt Builder

This module handles the creation of sophisticated prompts for:
- Question type detection
- QTI XML transformation
- Error correction and feedback

Similar to the HTML transformer's prompt creation logic
"""

from __future__ import annotations

from typing import Any

from .content_processing.content_processor import create_content_summary
from .prompt_image_helpers import build_image_info
from .prompt_templates import (
    CHARACTER_ENCODING_INSTRUCTIONS,
    CHOICE_LABEL_INSTRUCTIONS,
    CONTENT_FIDELITY_CHECKLIST,
    DESCRIPTION_REQUIREMENTS,
    DETECTION_QUESTION_TYPES,
    IMAGE_QTI_INSTRUCTIONS,
    QTI_STRUCTURE_RULES,
    RESPONSE_FORMAT_SPEC,
    SHARED_CONTEXT_INSTRUCTIONS,
    TABLE_HANDLING_INSTRUCTIONS,
    TEXT_IN_IMAGES_INSTRUCTIONS,
    VISUAL_COMPARISON_PROMPT,
    XML_VALIDATION_CHECKLIST,
)


def create_detection_prompt(pdf_content: dict[str, Any]) -> str:
    """Create a sophisticated prompt for question type detection.

    Args:
        pdf_content: Extracted PDF content

    Returns:
        Detection prompt string
    """
    content_summary = create_content_summary(pdf_content)
    combined_text = pdf_content.get("combined_text", "")
    text_length = len(combined_text)

    has_images = bool(pdf_content.get("image_base64") or any(page.get("image_base64") for page in pdf_content.get("pages", [])))

    prompt = f"""
You are an expert in educational assessment formats, particularly QTI (Question and Test Interoperability).

Your task is to analyze the PDF question content and determine the most appropriate QTI 3.0 interaction type.

## PDF Content Analysis

### Extracted Text:
{combined_text}

### Content Summary:
{content_summary}

### Basic Info:
- Text length: {text_length} characters
- Has visual content: {has_images}

{DETECTION_QUESTION_TYPES}

## Instructions
1. Analyze both the image and the extracted text to understand the question type and interactivity requirements
2. Apply the special classification rules for gap-match vs match interactions with tables
3. For multi-part questions, identify the DOMINANT interaction type or return "composite" as the question type
4. If the question cannot be properly represented by any of these types, indicate it as unsupported
5. Return your analysis in a JSON format ONLY:

{{
  "can_represent": true/false,
  "question_type": "one of the supported types, 'composite' for multi-part questions, or null if unsupported",
  "confidence": 0.0-1.0,
  "reason": "brief explanation of your decision",
  "key_elements": ["list", "of", "key", "interactive", "elements", "identified"],
  "potential_issues": ["any", "concerns", "about", "representation"]
}}

Your response should ONLY contain this JSON.
"""

    return prompt


def create_transformation_prompt(
    pdf_content: dict[str, Any],
    question_type: str,
    question_config: dict[str, str],
    validation_feedback: str | None = None,
    correct_answer: str | None = None,
) -> str:
    """Create a sophisticated prompt for QTI XML transformation.

    Args:
        pdf_content: Extracted PDF content
        question_type: Detected question type
        question_config: Configuration for the question type
        validation_feedback: Optional validation feedback for corrections
        correct_answer: Optional correct answer to include

    Returns:
        Transformation prompt string
    """
    content_summary = create_content_summary(pdf_content)
    image_info = build_image_info(pdf_content)
    retry_context = _build_retry_context(validation_feedback)
    image_context_instructions = _build_image_context_instructions(pdf_content)
    visual_choice_instructions = _build_visual_choice_instructions(pdf_content)
    correct_answer_instruction = _build_correct_answer_instruction(correct_answer)

    prompt = f"""You are an expert at converting educational content into QTI 3.0 XML format.

## Task
Convert the provided question content into valid QTI 3.0 XML format using the "{question_type}" interaction type.

{CHARACTER_ENCODING_INSTRUCTIONS}

{SHARED_CONTEXT_INSTRUCTIONS}

{retry_context}

## Content to Convert
{content_summary}

NOTE: Exclude page headers/footers, question numbers, test instructions or directions, fragments from other questions, and navigation elements.
IMPORTANT: Include any question-specific formatting or response instructions
(e.g., "use complete sentences", "no bulleted lists").
IMPORTANT: If instructions refer to physical answering methods (e.g., "fill in the
circles on the answer grid"), adapt or remove them to match the digital QTI
interaction, as the physical answering elements have likely been removed.

{image_info}

## Question Type: {question_type}
{question_config.get("promptInstructions", "")}{visual_choice_instructions}

{CHOICE_LABEL_INSTRUCTIONS}

{TABLE_HANDLING_INSTRUCTIONS}

{TEXT_IN_IMAGES_INSTRUCTIONS}

{DESCRIPTION_REQUIREMENTS}

{IMAGE_QTI_INSTRUCTIONS}

## CRITICAL: Correct Answer Specification
{correct_answer_instruction}

{QTI_STRUCTURE_RULES}

{XML_VALIDATION_CHECKLIST}

{CONTENT_FIDELITY_CHECKLIST}

{RESPONSE_FORMAT_SPEC}

{image_context_instructions}

Example QTI XML for reference:
{question_config.get("exampleXml", "")}

Ensure your QTI XML follows QTI 3.0 standards exactly and includes proper namespaces, identifiers, and response processing."""

    return prompt


def _build_retry_context(validation_feedback: str | None) -> str:
    """Build retry context section."""
    if not validation_feedback:
        return ""

    return (
        "\n\n## RETRY ATTEMPT CONTEXT\n"
        "This is correction attempt. Previous attempt failed validation. Please:\n"
        "- Pay extra attention to the specific validation errors listed below\n"
        "- Be more conservative in your changes - make only the minimal fixes needed\n"
        "- Double-check that all QTI 3.0 namespace and element requirements are met\n"
        "- Ensure all attributes are properly quoted and elements properly closed\n"
        "- THIS IS THE FINAL ATTEMPT - be extra careful and thorough\n"
    )


def _build_image_context_instructions(pdf_content: dict[str, Any]) -> str:
    """Build image context instructions if needed."""
    combined_text = pdf_content.get("combined_text", "").lower()

    if "img" in combined_text or "__IMAGE_PLACEHOLDER_" in pdf_content.get("combined_text", ""):
        return (
            "\n\n## Image Handling:\n"
            "- Preserve all <img> tags and their structure exactly as they appear\n"
            "- Do NOT modify image src attributes or placeholders\n"
            "- Keep multiple images separate if they exist\n"
        )
    return ""


def _build_visual_choice_instructions(pdf_content: dict[str, Any]) -> str:
    """Build visual choice instructions if question has choice images."""
    has_choice_images = pdf_content.get("is_choice_diagram", False) or any(
        img.get("is_choice_diagram", False) for img in pdf_content.get("all_images", [])
    )

    if not has_choice_images:
        return ""

    return """
## CRITICAL: Visual Choice Handling
**This question has CHOICE IMAGES (visual answer options):**
- Each choice should contain ONLY an image, NO text content
- Use format: `<qti-simple-choice identifier="ChoiceA"><img src="choice_image_placeholder"
  alt="Descriptive alt text for choice A"/></qti-simple-choice>`
- Alt text should describe what the choice shows (e.g., "Graph showing linear relationship between mass and kinetic energy")
- Do NOT mix text and images in choices - choices should be image-only
"""


def _build_correct_answer_instruction(correct_answer: str | None) -> str:
    """Build correct answer instruction section."""
    if correct_answer:
        return (
            f"**The correct answer for this question is: {correct_answer}**\n"
            f"- You MUST include this in the <qti-correct-response> element\n"
            f"- Use the exact identifier format: <qti-value>{correct_answer}</qti-value>\n"
            f"- Ensure the answer identifier matches one of the choice identifiers "
            f"(ChoiceA, ChoiceB, ChoiceC, ChoiceD)\n"
        )
    else:
        return "- Determine the correct answer from the question content and include it in <qti-correct-response>"


def create_error_correction_prompt(qti_xml: str, validation_errors: str, question_type: str, retry_attempt: int = 1, max_attempts: int = 3) -> str:
    """Create a prompt for correcting QTI XML validation errors.

    Args:
        qti_xml: Invalid QTI XML
        validation_errors: Validation error messages
        question_type: Question type for context
        retry_attempt: Current attempt number (1-based)
        max_attempts: Maximum number of attempts

    Returns:
        Error correction prompt
    """
    image_context_instructions = _build_error_correction_image_instructions(qti_xml)
    retry_context = _build_error_correction_retry_context(retry_attempt, max_attempts)

    prompt = f"""
You are an expert in QTI 3.0 XML. You will be given an invalid QTI XML document and a list of validation error messages.

Your task is to fix the XML to make it valid according to the QTI 3.0 schema while preserving all content and functionality.

## Question Type Context
This is a "{question_type}" type question.
{retry_context}
## Invalid QTI XML
```xml
{qti_xml}
```

## Validation Errors
{validation_errors}
{image_context_instructions}
## Instructions
1. Carefully analyze the validation errors and the XML structure.
2. **CRITICAL XML STRUCTURE FIXES**:
   - If the error mentions "qti-assessment-item must be terminated", check that the
     root element is properly closed with </qti-assessment-item> at the very end
   - Ensure ALL opening tags have matching closing tags
   - The <qti-response-processing> element should be self-closed with /> (e.g., <qti-response-processing template="..."/>)
   - Check for any missing or malformed closing tags
   - Verify proper XML hierarchy and nesting
3. PRESERVE image placeholders (like __IMAGE_PLACEHOLDER_N__) exactly as they appear.
4. Correct ONLY the specific validation errors reported. Do NOT restructure or simplify other parts of the XML unless an error forces you to.
5. Ensure all original text, choices, image data (if any), and interactive elements are preserved EXACTLY as they were.
6. The goal is minimal valid changes. If multiple images were present, keep them separate.
7. **XML VALIDATION CHECKLIST** - Before finalizing, verify:
   - [ ] Root element <qti-assessment-item> is properly opened and closed
   - [ ] All nested elements are properly closed
   - [ ] Self-closing elements use /> syntax correctly
   - [ ] No unclosed tags remain
   - [ ] All attributes are properly quoted
   - [ ] Image placeholders remain unchanged from the input XML
   - [ ] Changes directly address the listed validation errors
8. **SPECIFIC FIX FOR "must be terminated" ERRORS**:
   - Count opening and closing tags to ensure they match
   - Look for any truncated or incomplete XML at the end
   - Ensure the very last characters of your XML are ></qti-assessment-item>
   - Check for any hidden characters or formatting issues
9. Return a JSON object containing the corrected QTI XML:

{{
  "qti_xml": "The corrected and valid QTI 3.0 XML as a string"
}}

Make sure your response ONLY contains this JSON.
"""

    return prompt


def _build_error_correction_image_instructions(qti_xml: str) -> str:
    """Build image handling instructions for error correction."""
    if "img" in qti_xml.lower() or "__IMAGE_PLACEHOLDER_" in qti_xml:
        return (
            "\n\n## EXTREMELY CRITICAL: Image Handling:\n"
            "- Preserve all <img> tags and their structure exactly as they appear\n"
            "- Do NOT modify image src attributes or placeholders\n"
            "- Keep multiple images separate if they exist\n"
        )
    return ""


def _build_error_correction_retry_context(retry_attempt: int, max_attempts: int) -> str:
    """Build retry context for error correction."""
    if retry_attempt <= 1:
        return ""

    context = (
        f"\n\n## RETRY ATTEMPT CONTEXT\n"
        f"This is correction attempt {retry_attempt} of {max_attempts}. "
        f"Previous attempt(s) failed validation. Please:\n"
        "- Pay extra attention to the specific validation errors listed below\n"
        "- Be more conservative in your changes - make only the minimal fixes needed\n"
        "- Double-check that all QTI 3.0 namespace and element requirements are met\n"
        "- Ensure all attributes are properly quoted and elements properly closed\n"
    )

    if retry_attempt == max_attempts:
        context += "- THIS IS THE FINAL ATTEMPT - be extra careful and thorough\n"

    return context


def create_visual_comparison_prompt() -> str:
    """Create a prompt for visual comparison between original PDF and rendered QTI.

    Returns:
        Visual comparison prompt string
    """
    return VISUAL_COMPARISON_PROMPT
