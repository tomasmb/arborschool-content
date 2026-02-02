"""qti_configs.py
----------------
Contains the configuration snippets that the transformer uses for each
supported QTI 3.0 interaction. Updated to match the comprehensive
configurations from the JavaScript SDK implementation.

* No line exceeds 150 characters.
* Complete example XML for all question types.
* Detailed prompt instructions imported from qti_prompt_instructions.py.
* The module stays under 500 lines to respect workspace guidelines.
"""

from __future__ import annotations

import os
import re
from typing import Callable, Dict, List, Optional

from .qti_prompt_instructions import (
    CHOICE_INSTRUCTIONS,
    COMPOSITE_INSTRUCTIONS,
    EXTENDED_TEXT_INSTRUCTIONS,
    GAP_MATCH_INSTRUCTIONS,
    GENERIC_INSTRUCTIONS,
    GRAPHIC_GAP_MATCH_INSTRUCTIONS,
    HOT_TEXT_INSTRUCTIONS,
    HOTSPOT_INSTRUCTIONS,
    INLINE_CHOICE_INSTRUCTIONS,
    MATCH_INSTRUCTIONS,
    MEDIA_INTERACTION_INSTRUCTIONS,
    ORDER_INSTRUCTIONS,
    SELECT_POINT_INSTRUCTIONS,
    TEXT_ENTRY_INSTRUCTIONS,
)

# NOTE: Do **not** import heavy dependencies here – this file must stay
# lightweight so it can be imported very early without side-effects.


class QuestionConfig:
    """Configuration for a QTI question type."""

    def __init__(self, type: str, example_xml: str, prompt_instructions: str, post_process: Optional[Callable[[str], str]] = None):
        self.type = type
        self.example_xml = example_xml
        self.prompt_instructions = prompt_instructions
        self.post_process = post_process


def extract_example_xml(examples_xml: str, type: str, index: int = 0) -> str:
    """Extract example XML from the examples file."""
    # Default examples if extraction fails
    default_examples = {
        "choice": """<qti-assessment-item
    xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.imsglobal.org/xsd/imsqtiasi_v3p0
        https://purl.imsglobal.org/spec/qti/v3p0/schema/xsd/imsqti_asiv3p0_v1p0.xsd"
    identifier="choice-example" title="Choice Example"
    adaptive="false" time-dependent="false">
      <qti-response-declaration identifier="RESPONSE" cardinality="single"
          base-type="identifier">
        <qti-correct-response><qti-value>ChoiceA</qti-value></qti-correct-response>
      </qti-response-declaration>
      <qti-outcome-declaration identifier="SCORE" cardinality="single" base-type="float">
        <qti-default-value><qti-value>0</qti-value></qti-default-value>
      </qti-outcome-declaration>
      <qti-item-body>
        <p>Example question text</p>
        <qti-choice-interaction max-choices="1" response-identifier="RESPONSE">
          <qti-prompt>What is the correct answer?</qti-prompt>
          <qti-simple-choice identifier="ChoiceA">Option A</qti-simple-choice>
          <qti-simple-choice identifier="ChoiceB">Option B</qti-simple-choice>
          <qti-simple-choice identifier="ChoiceC">Option C</qti-simple-choice>
        </qti-choice-interaction>
      </qti-item-body>
      <qti-response-processing
          template="https://purl.imsglobal.org/spec/qti/v3p0/rptemplates/match_correct.xml"/>
    </qti-assessment-item>"""
    }

    # Return default example if examples file couldn't be read
    if not examples_xml:
        return default_examples.get(type, default_examples["choice"])

    # Try to find the comment marking the start of the example
    type_markers = {
        "choice": ["<!-- Choice Interaction", "<!-- Multiple Choice"],
        "match": ["<!-- Match -->"],
        "text-entry": ["<!-- Text Entry -->"],
        "hotspot": ["<!-- Hotspot Single", "<!-- Hotspot Multiple"],
        "extended-text": ["<!-- Extended Text Input -->"],
        "hot-text": ["<!-- HotText Single", "<!-- HotText Multiple"],
        "gap-match": ["<!-- Gap Match -->"],
        "order": ["<!-- Order -->"],
        "graphic-gap-match": ["<!-- Graphic Gap Match -->"],
        "inline-choice": ["<!-- Inline Choice", "<!-- Inline Choice Multiple"],
        "select-point": ["<!-- Select Point -->"],
        "media-interaction": ["<!-- Media Interaction Video", "<!-- Media Interaction Audio"],
    }

    markers = type_markers.get(type, [])
    marker_to_use = None
    if markers:
        marker_to_use = markers[min(index, len(markers) - 1)]

    if not marker_to_use:
        return default_examples.get(type, default_examples["choice"])

    # Find the start of the example
    start_index = examples_xml.find(marker_to_use)
    if start_index == -1:
        return default_examples.get(type, default_examples["choice"])

    # Find the next comment which would mark the end
    end_index = examples_xml.find("<!--", start_index + len(marker_to_use))
    if end_index == -1:
        # If no next comment, extract to the end of the file
        return examples_xml[start_index:].strip()

    # Extract the XML between the markers
    extracted_xml = examples_xml[start_index:end_index].strip()

    # Try to isolate just the qti-assessment-item tag
    item_match = re.search(r"<qti-assessment-item[\s\S]*?</qti-assessment-item>", extracted_xml)
    if item_match:
        return item_match.group(0)

    return extracted_xml


# Try to read the QTI examples XML file
examples_xml_path = os.path.join(os.path.dirname(__file__), "..", "EXAMPLES_QTI3_XML.xml")
examples_xml = ""
try:
    if os.path.exists(examples_xml_path):
        with open(examples_xml_path, "r", encoding="utf-8") as f:
            examples_xml = f.read()
except Exception as error:
    print(f"Error reading QTI examples XML file: {error}")


def hotspot_post_process(xml: str) -> str:
    """Post-process function for hotspot interactions.

    NOTE: This function NO LONGER converts SVG to base64.
    Base64 encoding is NOT ALLOWED - all images must use S3 URLs.
    """
    return xml


def select_point_post_process(xml: str) -> str:
    """Post-process function for select-point interactions.

    NOTE: This function NO LONGER converts SVG to base64.
    Base64 encoding is NOT ALLOWED - all images must use S3 URLs.
    """
    return xml


# Composite example XML (inline since it's custom, not from examples file)
COMPOSITE_EXAMPLE_XML = """<qti-assessment-item
    xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.imsglobal.org/xsd/imsqtiasi_v3p0
        https://purl.imsglobal.org/spec/qti/v3p0/schema/xsd/imsqti_asiv3p0_v1p0.xsd"
    identifier="composite-example" title="Multi-part Question Example"
    time-dependent="false">
      <qti-response-declaration identifier="RESPONSE_A" cardinality="single"
          base-type="identifier">
        <qti-correct-response>
          <qti-value>ChoiceB</qti-value>
        </qti-correct-response>
      </qti-response-declaration>
      <qti-response-declaration identifier="RESPONSE_B" cardinality="single"
          base-type="string"/>
      <qti-item-body>
        <p>This is a two-part question. Answer both parts.</p>
        <p><strong>Part A</strong></p>
        <p>What is the capital of France?</p>
        <qti-choice-interaction response-identifier="RESPONSE_A" max-choices="1">
          <qti-simple-choice identifier="ChoiceA">London</qti-simple-choice>
          <qti-simple-choice identifier="ChoiceB">Paris</qti-simple-choice>
          <qti-simple-choice identifier="ChoiceC">Berlin</qti-simple-choice>
        </qti-choice-interaction>
        <hr/>
        <p><strong>Part B</strong></p>
        <p>Explain why it is the capital.</p>
        <qti-extended-text-interaction response-identifier="RESPONSE_B" expected-lines="5"/>
      </qti-item-body>
      <qti-response-processing
          template="https://purl.imsglobal.org/spec/qti/v3p0/rptemplates/match_correct.xml"/>
    </qti-assessment-item>"""

# ============================================================================
# Question Type Configurations
# ============================================================================

choice_config = QuestionConfig(type="choice", example_xml=extract_example_xml(examples_xml, "choice", 0), prompt_instructions=CHOICE_INSTRUCTIONS)

match_config = QuestionConfig(type="match", example_xml=extract_example_xml(examples_xml, "match", 0), prompt_instructions=MATCH_INSTRUCTIONS)

text_entry_config = QuestionConfig(
    type="text-entry", example_xml=extract_example_xml(examples_xml, "text-entry", 0), prompt_instructions=TEXT_ENTRY_INSTRUCTIONS
)

composite_config = QuestionConfig(type="composite", example_xml=COMPOSITE_EXAMPLE_XML, prompt_instructions=COMPOSITE_INSTRUCTIONS)

hotspot_config = QuestionConfig(
    type="hotspot",
    example_xml=extract_example_xml(examples_xml, "hotspot", 0),
    prompt_instructions=HOTSPOT_INSTRUCTIONS,
    post_process=hotspot_post_process,
)

extended_text_config = QuestionConfig(
    type="extended-text", example_xml=extract_example_xml(examples_xml, "extended-text", 0), prompt_instructions=EXTENDED_TEXT_INSTRUCTIONS
)

hot_text_config = QuestionConfig(
    type="hot-text", example_xml=extract_example_xml(examples_xml, "hot-text", 0), prompt_instructions=HOT_TEXT_INSTRUCTIONS
)

gap_match_config = QuestionConfig(
    type="gap-match", example_xml=extract_example_xml(examples_xml, "gap-match", 0), prompt_instructions=GAP_MATCH_INSTRUCTIONS
)

order_config = QuestionConfig(type="order", example_xml=extract_example_xml(examples_xml, "order", 0), prompt_instructions=ORDER_INSTRUCTIONS)

graphic_gap_match_config = QuestionConfig(
    type="graphic-gap-match",
    example_xml=extract_example_xml(examples_xml, "graphic-gap-match", 0),
    prompt_instructions=GRAPHIC_GAP_MATCH_INSTRUCTIONS,
)

inline_choice_config = QuestionConfig(
    type="inline-choice", example_xml=extract_example_xml(examples_xml, "inline-choice", 0), prompt_instructions=INLINE_CHOICE_INSTRUCTIONS
)

select_point_config = QuestionConfig(
    type="select-point",
    example_xml=extract_example_xml(examples_xml, "select-point", 0),
    prompt_instructions=SELECT_POINT_INSTRUCTIONS,
    post_process=select_point_post_process,
)

media_interaction_config = QuestionConfig(
    type="media-interaction",
    example_xml=extract_example_xml(examples_xml, "media-interaction", 0),
    prompt_instructions=MEDIA_INTERACTION_INSTRUCTIONS,
)

# ============================================================================
# Question Configs Registry
# ============================================================================

question_configs: Dict[str, QuestionConfig] = {
    "choice": choice_config,
    "match": match_config,
    "text-entry": text_entry_config,
    "composite": composite_config,
    "hotspot": hotspot_config,
    "extended-text": extended_text_config,
    "hot-text": hot_text_config,
    "gap-match": gap_match_config,
    "order": order_config,
    "graphic-gap-match": graphic_gap_match_config,
    "inline-choice": inline_choice_config,
    "select-point": select_point_config,
    "media-interaction": media_interaction_config,
    "unknown": QuestionConfig(type="unknown", prompt_instructions=GENERIC_INSTRUCTIONS, example_xml=extract_example_xml(examples_xml, "choice", 0)),
}


def get_question_config(question_type: str) -> QuestionConfig:
    """Get the configuration for a specific question type.

    Args:
        question_type: The question type to get configuration for

    Returns:
        The question type configuration or the unknown type config if not found
    """
    return question_configs.get(question_type, question_configs["unknown"])


def get_available_question_types() -> List[str]:
    """Get all available question types.

    Returns:
        List of question type names
    """
    return [t for t in question_configs.keys() if t != "unknown"]


# Backward compatibility: Keep the old QTI_TYPE_CONFIGS format for existing code
QTI_TYPE_CONFIGS = {
    c.type: {"type": c.type, "promptInstructions": c.prompt_instructions.strip(), "exampleXml": c.example_xml}
    for c in question_configs.values()
    if c.type != "unknown"
}
