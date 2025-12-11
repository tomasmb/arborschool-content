"""
QTI Extraction Validation Prompts.

AI-powered validation that the QTI XML was correctly extracted/parsed from a source PDF.
Focus: Completeness of extraction, NOT assessment completeness.

VALIDATES:
- Question stem is present and readable
- All interactive elements have content (choices, match items, etc.)
- No parsing artifacts (encoding issues, garbled text, placeholders)
- Images match the question context (not wrong/placeholder images)
- Text is coherent (not truncated, no contamination from adjacent questions)
- MathML/equations are properly formed

DOES NOT VALIDATE:
- responseDeclaration / correctResponse presence
- Answer key correctness
- Distractor quality
- Feedback presence
- Rubrics or scoring guidance
- Question adequacy or pedagogy
"""

from __future__ import annotations

import re
import logging

logger = logging.getLogger(__name__)


def strip_base64_images_from_xml(qti_xml: str) -> str:
    """
    Strip base64 image data from QTI XML to reduce token usage.
    
    Base64 images embedded in XML (e.g., src="data:image/png;base64,...")
    consume massive amounts of tokens when sent as text. A single image
    can be 100K-500K+ tokens as text!
    
    This function replaces base64 data URLs with a short placeholder,
    preserving the structure for validation while dramatically reducing tokens.
    
    Args:
        qti_xml: QTI XML string potentially containing base64 images
        
    Returns:
        QTI XML with base64 images replaced by placeholders
    """
    # Pattern matches: data:image/TYPE;base64,HUGE_BASE64_STRING
    # Uses [^;]+ to match ANY MIME subtype including svg+xml, jpeg, png, etc.
    pattern = r'data:image/([^;]+);base64,[A-Za-z0-9+/=\s]+'
    
    def replacement(match):
        image_type = match.group(1).replace("+", "_").replace("/", "_").upper()
        return f'[BASE64_IMAGE_{image_type}_STRIPPED]'
    
    stripped_xml = re.sub(pattern, replacement, qti_xml)
    
    # Log if we stripped anything (for debugging)
    original_len = len(qti_xml)
    stripped_len = len(stripped_xml)
    if stripped_len < original_len:
        reduction = original_len - stripped_len
        logger.info(
            f"Stripped {reduction:,} chars of base64 data from QTI XML "
            f"({original_len:,} -> {stripped_len:,})"
        )
    
    return stripped_xml


# JSON output schema - focused on extraction quality
# IMPORTANT: Booleans MUST be consistent with scores (score >= 90 means true)
OUTPUT_SCHEMA = """{
  "is_complete": true/false,       // MUST be true if content_score >= 90, false otherwise
  "content_score": 0-100,
  "content_issues": ["issue1", "issue2"],
  "structure_valid": true/false,   // MUST be true if structure_score >= 90, false otherwise
  "structure_score": 0-100,
  "structure_issues": ["issue1", "issue2"],
  "parse_clean": true/false,       // MUST be true if parse_score >= 90, false otherwise
  "parse_score": 0-100,
  "parse_issues": ["issue1", "issue2"],
  "images_contextual": true/false/null,  // MUST be true if images_score >= 90, false otherwise
  "images_score": 0-100,
  "images_issues": ["issue1", "issue2"],
  "detected_type": "choiceInteraction|textEntryInteraction|etc",
  "reasoning": "Brief explanation of overall assessment"
}"""


def build_validation_prompt(qti_xml: str, has_images: bool = False) -> str:
    """
    Build prompt for QTI extraction validation.
    
    Follows Gemini 3 Pro best practices:
    - Context (QTI XML) placed FIRST
    - Instructions placed AFTER context
    - Uses anchor phrase to connect context to task
    
    Args:
        qti_xml: The QTI 3.0 XML to validate
        has_images: Whether images will be provided separately
        
    Returns:
        Complete prompt for AI validation
    """
    # Strip base64 images from XML to avoid massive token usage
    clean_xml = strip_base64_images_from_xml(qti_xml)
    
    image_note = (
        "Images provided separately for visual validation."
        if has_images
        else "No images provided."
    )
    
    return f"""---
QTI XML TO VALIDATE
---

{clean_xml}

---

<role>
You are a QTI extraction validator. Verify that a question was correctly extracted from a
standardized test PDF into QTI 3.0 XML format.
</role>

<task>
Validate extraction quality across four categories. Return a JSON report.
</task>

<rules>
CHECK these (extraction quality):
1. CONTENT: Question stem present and complete. All interactive elements populated:
   - Choice interactions: qti-simple-choice elements have text
   - Text entry / extended text: prompt text complete
   - Match / order: all items have content
   - Hottext / gap-match: all elements present with text
   - MathML/equations properly formed (not garbled)

2. STRUCTURE: Has qti-item-body with content. Correct interaction element for question type.

3. PARSE QUALITY: No encoding artifacts (â€™, Ã©). No placeholders ([IMAGE], [TODO]).
   No contamination from adjacent questions. No page headers/footers mixed in.

4. MEDIA: {image_note} Img elements have src attributes.

DO NOT CHECK these (not relevant):
- responseDeclaration, correctResponse, feedback (answer key elements)
- Distractor quality or pedagogical soundness
- Optional QTI elements
</rules>

<scoring>
100: Perfect extraction | 90-99: Minor cosmetic issues | 70-89: Noticeable but usable
50-69: Significant (missing content, garbled math) | 0-49: Critical (missing stem, empty elements)

CRITICAL: Booleans MUST match scores:
- is_complete = true IFF content_score >= 90
- structure_valid = true IFF structure_score >= 90
- parse_clean = true IFF parse_score >= 90
</scoring>

<constraints>
- CRITICAL failures: missing stem, empty interactive elements, garbled content
- Missing responseDeclaration is NOT a failure
- Set images_contextual to null (no images to validate visually)
- Boolean flags MUST be consistent with scores (see scoring rules)
</constraints>

<output_format>
{OUTPUT_SCHEMA}
</output_format>

Based on the QTI XML above, validate extraction quality and return the JSON report."""


def build_image_validation_prompt(
    qti_xml: str,
    image_count: int,
    image_descriptions: list[str] | None = None
) -> str:
    """
    Build prompt for multimodal extraction validation (QTI + images).
    
    Follows Gemini 3 Pro best practices:
    - Context (QTI XML + image info) placed FIRST
    - Instructions placed AFTER context
    - Uses anchor phrase to connect context to task
    
    Args:
        qti_xml: The QTI 3.0 XML containing the question
        image_count: Number of images being provided
        image_descriptions: Optional alt text/descriptions for each image
        
    Returns:
        Complete prompt for multimodal AI validation
    """
    # Strip base64 images from XML - they're validated via image content blocks
    clean_xml = strip_base64_images_from_xml(qti_xml)
    
    desc_section = ""
    if image_descriptions:
        desc_lines = [f"- {desc}" for desc in image_descriptions]
        desc_section = "Image metadata from QTI:\n" + "\n".join(desc_lines)

    return f"""---
QTI XML CONTEXT
---

{clean_xml}

---
IMAGE CONTEXT
---

{image_count} image(s) provided for visual validation.
{desc_section}

---

<role>
You are a QTI extraction validator with vision capabilities. Verify that a question AND its
images were correctly extracted from a standardized test PDF.
</role>

<task>
Validate extraction quality of both XML content and images. Return a JSON report.
</task>

<rules>
CHECK these (extraction quality):
1. CONTENT: Question stem present. Interactive elements populated by type:
   - Choice: all choices have text
   - Text entry / extended text: prompt complete
   - Match / order / hottext / gap-match: all items have content

2. STRUCTURE: Has qti-item-body. Correct interaction element for question type.

3. PARSE: No encoding artifacts (â€™, Ã©). No placeholders. No contamination.

4. IMAGES: For each image verify:
   - Matches what the question asks about
   - Referenced elements (labels, diagrams) are visible
   - Is actual content (not placeholder or stock photo)
   - Is readable and not corrupted/blurry

DO NOT CHECK:
- responseDeclaration, correctResponse, feedback
- Distractor quality or pedagogical soundness
- Image aesthetic quality
</rules>

<scoring>
100: Perfect | 90-99: Minor issues | 70-89: Noticeable | 50-69: Significant | 0-49: Critical

CRITICAL: Booleans MUST match scores:
- is_complete = true IFF content_score >= 90
- structure_valid = true IFF structure_score >= 90
- parse_clean = true IFF parse_score >= 90
- images_contextual = true IFF images_score >= 90
</scoring>

<constraints>
- images_contextual = false if ANY image is wrong, placeholder, missing labels, or corrupted
- Per-image issues go in images_issues array
- Missing responseDeclaration is NOT a failure
- Boolean flags MUST be consistent with scores (see scoring rules)
</constraints>

<output_format>
{OUTPUT_SCHEMA}
</output_format>

Based on the QTI XML and {image_count} image(s) above, validate extraction quality and return the JSON report."""


# Question type specific EXTRACTION requirements (not assessment requirements)
QUESTION_TYPE_EXTRACTION_CHECKS = {
    "choiceInteraction": {
        "required_content": [
            "qti-choice-interaction element present",
            "At least 2 qti-simple-choice elements",
            "Each choice has visible text content",
        ],
        "common_extraction_issues": [
            "Missing choice text (empty elements)",
            "Truncated choice content",
            "Choice labels (A, B, C) not separated from text",
            "Math expressions garbled in choices",
        ]
    },
    "textEntryInteraction": {
        "required_content": [
            "qti-text-entry-interaction element present",
            "Clear prompt text surrounding the interaction",
        ],
        "common_extraction_issues": [
            "Interaction element missing from extraction",
            "Prompt text truncated or garbled",
            "Blank/placeholder where interaction should be",
        ]
    },
    "extendedTextInteraction": {
        "required_content": [
            "qti-extended-text-interaction element present",
            "Clear prompt/question text",
        ],
        "common_extraction_issues": [
            "Prompt text incomplete",
            "Instructions cut off mid-sentence",
        ]
    },
    "matchInteraction": {
        "required_content": [
            "qti-match-interaction element present",
            "Two sets of matchable items",
            "Each item has visible content",
        ],
        "common_extraction_issues": [
            "Missing items in one or both sets",
            "Empty match item elements",
            "Items from wrong question mixed in",
        ]
    },
    "orderInteraction": {
        "required_content": [
            "qti-order-interaction element present",
            "Multiple qti-simple-choice elements to order",
            "Each choice has content",
        ],
        "common_extraction_issues": [
            "Missing items to order",
            "Order numbers mixed into item text",
        ]
    },
    "hottextInteraction": {
        "required_content": [
            "qti-hottext-interaction element present",
            "qti-hottext elements within surrounding text",
        ],
        "common_extraction_issues": [
            "Hottext boundaries incorrectly placed",
            "Surrounding text missing or corrupted",
        ]
    },
    "inlineChoiceInteraction": {
        "required_content": [
            "qti-inline-choice-interaction element present",
            "qti-inline-choice options",
        ],
        "common_extraction_issues": [
            "Inline choices missing from extraction",
            "Surrounding sentence context lost",
        ]
    },
    "gapMatchInteraction": {
        "required_content": [
            "qti-gap-match-interaction element present",
            "qti-gap elements marking gaps",
            "qti-gap-text choices to fill gaps",
        ],
        "common_extraction_issues": [
            "Gap positions lost in extraction",
            "Gap text choices missing",
            "Text around gaps corrupted",
        ]
    }
}

