"""Prompts for QTI XML generation."""

from typing import Optional

# Import from parent package
try:
    from models import QuestionChunk, SharedContext, SourceFormat
except ImportError:
    from ..models import QuestionChunk, SharedContext, SourceFormat


QTI_GENERATION_PROMPT = """<role>
You are an expert QTI 3.0 XML developer. Convert markdown to valid QTI XML while preserving all original content.
</role>

<task>
Convert the question into valid QTI 3.0 XML using the "{question_type}" interaction type.
</task>

<rules>
1. Use namespace: xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0"
2. Root element: <qti-assessment-item>
3. Required attributes: identifier, title, adaptive="false", time-dependent="false"
4. Body: Use <qti-item-body> for content
5. Include <qti-response-declaration> (identifier="RESPONSE")
6. Include <qti-outcome-declaration> with BOTH identifier="SCORE" AND cardinality="single" AND base-type="float"
7. Remove choice labels from choice text but use them in identifiers
8. IMAGE PLACEMENT (CRITICAL):
   - Images MUST be inside block elements (<p>, <div>, or <figure>)
   - NEVER place <img> directly inside <qti-item-body>
   - Correct: <qti-item-body><p><img src="..." alt="..."/></p></qti-item-body>
   - Wrong: <qti-item-body><img src="..." alt="..."/></qti-item-body>
9. IMAGE ALT TEXT: Use a brief, descriptive alt text (can be simplified from original)
10. VISUAL CHOICES: If choices are shown in an image, keep the image and use labels as choice text
</rules>

<output_format>
Return ONLY raw XML. No markdown blocks (```xml), no XML declaration (<?xml), no explanatory text.
</output_format>

<constraints>
TEST-SPECIFIC CONTENT TO REMOVE (questions should be reusable):
- Remove question numbers ("5.", "Question 7", etc.)
- Remove answer sheet instructions ("Record your answer and fill in the bubbles...")

CONTENT TO PRESERVE:
- Answer choice ORDER (e.g., A, B, C, D or F, G, H, J - output must match source order, NEVER reorder or alphabetize)
- Descriptive text after images
- Photo credits and attributions (e.g., "© Paul Hakimata/Dreamstime.com")

STRICT RULES:
- NEVER add content not in the original question
- NEVER invent or guess the correct answer
- ONLY include <qti-correct-response> if answer key is EXPLICITLY in the source (e.g., "Answer: B")
- If NO answer key provided, OMIT <qti-correct-response> entirely
- NEVER place <img> directly inside <qti-item-body> (wrap in <p> or <div>)
- All elements must be properly closed
</constraints>

<type_instructions>
{type_instructions}
</type_instructions>

<example>
{example_xml}
</example>

<context>
{shared_context_section}Question ID: {question_id}
Question Type: {question_type}
Source Format: {source_format}
{format_instructions}

QUESTION CONTENT:
{question_content}
</context>

<final_instruction>
Based on the question content above, generate valid QTI 3.0 XML. Follow all rules and constraints. Return only the raw XML string.
</final_instruction>
"""

FORMAT_INSTRUCTIONS = {
    "markdown": "",
    "html": """
HTML PARSING NOTES:
- Parse HTML tags to extract content (e.g., <p>, <div>, <span>, <table>, <img>)
- Convert HTML structure to equivalent QTI elements
- Preserve image src attributes as QTI img src
- Handle HTML entities (e.g., &nbsp;, &amp;) appropriately
- Extract text content from nested HTML elements""",
}


def create_qti_generation_prompt(
    question: QuestionChunk,
    shared_context: Optional[SharedContext] = None,
    question_type: str = "choice",
    type_instructions: str = "",
    example_xml: str = "",
    source_format: SourceFormat = "markdown",
) -> str:
    """Create QTI generation prompt with question and optional shared context."""
    shared_context_section = ""
    if shared_context:
        shared_context_section = f"SHARED CONTEXT:\n{shared_context.content}\n\n"

    format_instructions = FORMAT_INSTRUCTIONS.get(source_format, "")

    return QTI_GENERATION_PROMPT.format(
        shared_context_section=shared_context_section,
        question_id=question.id,
        question_type=question_type,
        question_content=question.content,
        type_instructions=type_instructions,
        example_xml=example_xml,
        source_format=source_format,
        format_instructions=format_instructions,
    )

