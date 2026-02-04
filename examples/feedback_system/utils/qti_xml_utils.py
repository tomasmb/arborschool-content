"""
QTI XML parsing utilities.

Provides functions to extract question metadata from QTI 3.0 XML.
"""

import re
from typing import Any
from xml.etree import ElementTree as ET


def extract_image_urls(qti_xml: str) -> list[str]:
    """Extract image URLs from QTI XML."""
    img_pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
    picture_pattern = r'<picture[^>]*>.*?<img[^>]+src=["\']([^"\']+)["\']'

    urls = []
    urls.extend(re.findall(img_pattern, qti_xml))
    urls.extend(re.findall(picture_pattern, qti_xml, re.DOTALL))

    return [url for url in urls if url.startswith("http")]


QTI_INTERACTION_TYPES = [
    "qti-choice-interaction",
    "qti-inline-choice-interaction",
    "qti-text-entry-interaction",
    "qti-extended-text-interaction",
    "qti-hotspot-interaction",
    "qti-match-interaction",
    "qti-order-interaction",
    "qti-slider-interaction",
]


def detect_interaction_type(root, ns: str) -> str:
    """Detect the interaction type from QTI XML root element."""
    for itype in QTI_INTERACTION_TYPES:
        elem = root.find(f".//{ns}{itype}")
        if elem is None:
            elem = root.find(f".//{itype}")
        if elem is not None:
            return itype.replace("qti-", "").replace("-", "_")
    return "unknown"


def count_interactions(root, ns: str) -> int:
    """Count total number of interactions in QTI XML."""
    count = 0
    for itype in QTI_INTERACTION_TYPES:
        interactions = root.findall(f".//{ns}{itype}")
        if not interactions:
            interactions = root.findall(f".//{itype}")
        count += len(interactions)
    return count


def is_composite(qti_xml: str) -> bool:
    """Check if QTI XML has multiple interactions (composite question)."""
    try:
        root = ET.fromstring(qti_xml)
        ns = "{http://www.imsglobal.org/xsd/imsqtiasi_v3p0}"
        return count_interactions(root, ns) > 1
    except Exception:
        return False


def extract_composite_parts_info(qti_xml: str) -> list[dict[str, Any]]:
    """Extract information for each part of a composite question."""
    try:
        root = ET.fromstring(qti_xml)
        ns = "{http://www.imsglobal.org/xsd/imsqtiasi_v3p0}"

        all_interactions = []
        for itype in QTI_INTERACTION_TYPES:
            interactions = root.findall(f".//{ns}{itype}")
            all_interactions.extend(interactions)

        if len(all_interactions) <= 1:
            return []

        parts = []
        for interaction in all_interactions:
            resp_id = interaction.get("response-identifier", "")
            if not resp_id:
                continue

            part_id = resp_id.replace("RESPONSE_", "")
            interaction_tag = interaction.tag.split("}")[-1]
            interaction_type = interaction_tag.replace("qti-", "").replace("-", "_")

            choices = []
            if "choice-interaction" in interaction_tag:
                max_choices = interaction.get("max-choices", "1")
                interaction_type = f"choice_interaction_{'multi' if max_choices != '1' else 'single'}"

                simple_choices = interaction.findall(f".//{ns}qti-simple-choice")
                for choice in simple_choices:
                    choices.append({
                        "identifier": choice.get("identifier"),
                        "text": ET.tostring(choice, encoding="unicode", method="text").strip(),
                    })

            correct_response = None
            resp_decl = root.find(f".//{ns}qti-response-declaration[@identifier='{resp_id}']")
            if resp_decl is not None:
                correct_values = resp_decl.findall(f".//{ns}qti-correct-response/{ns}qti-value")
                if correct_values:
                    if len(correct_values) == 1:
                        correct_response = correct_values[0].text
                    else:
                        correct_response = [v.text for v in correct_values]

            parts.append({
                "part_id": part_id,
                "response_identifier": resp_id,
                "interaction_type": interaction_type,
                "choices": choices,
                "correct_response": correct_response,
            })

        return parts

    except Exception as e:
        print(f"Error extracting composite parts info: {e}")
        return []


def extract_question_info(qti_xml: str) -> dict[str, Any]:
    """Extract question metadata from QTI XML."""
    try:
        root = ET.fromstring(qti_xml)
        ns = "{http://www.imsglobal.org/xsd/imsqtiasi_v3p0}"

        interaction_type = detect_interaction_type(root, ns)

        item_body = root.find(f".//{ns}qti-item-body")
        if item_body is None:
            item_body = root.find(".//qti-item-body")

        body_text = ET.tostring(item_body, encoding="unicode", method="text") if item_body is not None else ""

        choices = []
        correct_response = None

        if interaction_type == "choice_interaction":
            choice_interaction = root.find(f".//{ns}qti-choice-interaction")
            if choice_interaction is None:
                choice_interaction = root.find(".//qti-choice-interaction")

            if choice_interaction is not None:
                max_choices = choice_interaction.get("max-choices", "1")
                interaction_type = f"choice_interaction_{'multi' if max_choices != '1' else 'single'}"

                simple_choices = choice_interaction.findall(f".//{ns}qti-simple-choice")
                if not simple_choices:
                    simple_choices = choice_interaction.findall(".//qti-simple-choice")

                for choice in simple_choices:
                    choices.append({
                        "identifier": choice.get("identifier"),
                        "text": ET.tostring(choice, encoding="unicode", method="text").strip(),
                    })

        response_decl = root.find(f".//{ns}qti-response-declaration")
        if response_decl is None:
            response_decl = root.find(".//qti-response-declaration")

        if response_decl is not None:
            correct_values = response_decl.findall(f".//{ns}qti-correct-response/{ns}qti-value")
            if not correct_values:
                correct_values = response_decl.findall(".//qti-correct-response/qti-value")

            if len(correct_values) == 1:
                correct_response = correct_values[0].text
            elif len(correct_values) > 1:
                correct_response = [v.text for v in correct_values]

        return {
            "interaction_type": interaction_type,
            "body_text": body_text.strip(),
            "choices": choices,
            "correct_response": correct_response,
        }
    except Exception as e:
        print(f"Error extracting question info: {e}")
        return {}
