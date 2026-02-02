"""
AI Analysis prompts for content analysis.

This module contains the prompt templates used by the AI content analyzer
for QTI compatibility assessment and content categorization.
"""

from __future__ import annotations


def build_comprehensive_analysis_prompt(question_text: str, content_summary: str, block_info: list[dict]) -> str:
    """Build prompt for comprehensive content analysis.

    Args:
        question_text: Extracted question text
        content_summary: Content summary for analysis
        block_info: List of block information dicts

    Returns:
        Formatted prompt string
    """
    return f"""Perform a comprehensive analysis of this educational question content.

QUESTION TEXT:
{question_text}

CONTENT SUMMARY:
{content_summary}

TEXT BLOCKS ON PAGE:
{block_info}

ANALYSIS TASKS:

1. QTI COMPATIBILITY ASSESSMENT:
   - Can this be represented accurately in QTI 3.0 standard interaction types?
   - Supported types: choice, match, text-entry, hotspot, extended-text, hot-text,
     gap-match, order, graphic-gap-match, inline-choice, select-point,
     media-interaction, composite
   - Does it contain visual content (images, diagrams, maps)? Tables are NOT visual content.

2. VISUAL CONTENT SEPARATION:
   - Are there PROMPT VISUALS (essential for question understanding)?
   - Are there CHOICE VISUALS (part of answer options A, B, C, D)?

3. TEXT BLOCK CATEGORIZATION:
   Categorize each text block as one of:
   - "question_part_header": Part identifiers (e.g., "A.", "B.", "Part C")
   - "question_text": Main question text, instructions, introductions
   - "answer_choice": Multiple choice identifiers (A, B, C, D)
   - "visual_content_title": Titles/captions for visual content
   - "visual_content_label": Labels ON prompt visuals (including descriptive text explaining diagrams, empty blocks where visuals must be)
   - "choice_visual_label": Labels ON choice visuals (labels within A, B, C, D diagrams)
   - "other_label": Source citations, page numbers, legends NOT part of visuals

CRITICAL RULES:
- Empty blocks positioned where visual content must be should be "visual_content_label"
- Text describing what's shown in diagrams should be "visual_content_label" to ensure inclusion
- Tables are NOT choice visuals - don't mark has_choice_visuals=true just for table formats

Respond with JSON in this exact format:
{{
    "qti_compatibility": {{
        "can_represent": boolean,
        "visual_content_required": boolean,
        "question_type": "string or null",
        "confidence": number,
        "reasoning": "string"
    }},
    "visual_separation": {{
        "has_prompt_visuals": boolean,
        "has_choice_visuals": boolean,
        "prompt_visual_description": "string",
        "choice_visual_description": "string",
        "separation_confidence": number,
        "reasoning": "string"
    }},
    "block_categories": {{
        "1": "category_name",
        "2": "category_name"
    }}
}}"""


def build_compatibility_prompt(content_summary: str) -> str:
    """Build prompt for QTI compatibility assessment.

    Args:
        content_summary: Content summary for analysis

    Returns:
        Formatted prompt string
    """
    return f"""Analyze this educational content to determine QTI 3.0 compatibility.

CONTENT SUMMARY:
{content_summary}

ASSESSMENT CRITERIA:
1. Can this be represented accurately in QTI 3.0 standard interaction types?
2. Does it contain any visual content (images, diagrams, maps)? If so, this visual
   content should be required. Tables are not considered visual content.
3. What interaction type would be most appropriate?
4. How complex is the content structure?

Supported QTI types: choice, match, text-entry, hotspot, extended-text,
hot-text, gap-match, order, graphic-gap-match, inline-choice, select-point, media-interaction,
composite

Provide assessment with confidence score (0.0-1.0).

Respond with JSON in this format:
{{
    "can_represent": boolean,
    "visual_content_required": boolean,
    "question_type": "string or null",
    "confidence": number,
    "reasoning": "string explanation"
}}"""


def build_categorization_prompt(block_info: list[dict]) -> str:
    """Build prompt for content block categorization.

    Args:
        block_info: List of block information dicts

    Returns:
        Formatted prompt string
    """
    return f"""Categorize text blocks on this educational page for intelligent image extraction.

TEXT BLOCKS:
{block_info}

CATEGORIES:
- "question_text": Main question stems, instructions, introductory text
- "answer_choice": Multiple choice options (A, B, C, D, etc.)
- "visual_content_title": Titles or captions for visual content
- "visual_content_label": Geographic labels, numbers, annotations on visual content
- "other_label": Source citations, compass directions, legends

GOAL: Identify which blocks are separate from visual content (question_text, answer_choice)
vs. which are part of visual content (visual_content_title, visual_content_label, other_label).

Respond with JSON in this format:
{{
    "has_visual_content": boolean,
    "visual_description": "string",
    "block_categories": {{
        "1": "category_name",
        "2": "category_name"
    }}
}}"""


# Valid QTI question types
VALID_QTI_TYPES = [
    "choice",
    "match",
    "text-entry",
    "hotspot",
    "extended-text",
    "hot-text",
    "gap-match",
    "order",
    "graphic-gap-match",
    "inline-choice",
    "select-point",
    "media-interaction",
    "composite",
]

# Valid block categories for categorization
VALID_BLOCK_CATEGORIES = [
    "question_part_header",
    "question_text",
    "answer_choice",
    "visual_content_title",
    "visual_content_label",
    "choice_visual_label",
    "other_label",
]

# System prompts for different analysis types
COMPREHENSIVE_SYSTEM_PROMPT = (
    "You are an expert in educational assessment and QTI 3.0 standards. "
    "Perform comprehensive content analysis combining compatibility assessment, "
    "visual separation, and block categorization. Respond only with valid JSON."
)

COMPATIBILITY_SYSTEM_PROMPT = (
    "You are an expert in educational assessment and QTI 3.0 standards. Analyze content for QTI compatibility. Respond only with valid JSON."
)

CATEGORIZATION_SYSTEM_PROMPT = (
    "You are an expert in educational content analysis. Categorize text blocks for intelligent image extraction. Respond only with valid JSON."
)
