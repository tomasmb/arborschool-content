"""QTI extraction helpers for variant validation."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher

from app.utils.mathml_parser import process_mathml
from app.utils.qti_extractor import extract_choices_from_qti, get_correct_answer_text


def extract_question_text(xml_content: str) -> str:
    """Extract question text while ignoring embedded feedback."""
    try:
        root = ET.fromstring(xml_content)
        item_body = root.find(".//{*}qti-item-body")
        if item_body is None:
            item_body = root.find(".//{*}itemBody")
        if item_body is not None:
            return _element_to_text(item_body)
        return ""
    except Exception:
        return ""


def extract_choices(xml_content: str) -> list[str]:
    """Extract visible choice texts from QTI XML."""
    try:
        root = ET.fromstring(xml_content)
        raw_choices = root.findall(".//{*}qti-simple-choice")
        if not raw_choices:
            raw_choices = root.findall(".//{*}simpleChoice")

        return [_choice_text_without_feedback(choice) for choice in raw_choices]
    except Exception:
        choices, _ = extract_choices_from_qti(xml_content)
        return choices


def find_correct_answer(xml_content: str) -> str:
    """Find the visible correct-answer text from QTI XML."""
    return get_correct_answer_text(xml_content)


def validate_choice_interaction_integrity(xml_content: str) -> tuple[bool, str]:
    """Validate that a choice-interaction item has a usable correct answer wiring."""
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        return False, f"XML inválido: {exc}"

    interaction = root.find(".//{*}qti-choice-interaction")
    if interaction is None:
        interaction = root.find(".//{*}choiceInteraction")

    choice_nodes = root.findall(".//{*}qti-simple-choice")
    if not choice_nodes:
        choice_nodes = root.findall(".//{*}simpleChoice")

    # If the item is not a choice interaction, leave the rest of the pipeline alone.
    if interaction is None and not choice_nodes:
        return True, ""
    if interaction is None:
        return False, "La variante tiene alternativas, pero no incluye qti-choice-interaction."

    response_identifier = interaction.attrib.get("response-identifier") or interaction.attrib.get("responseIdentifier")
    if not response_identifier:
        return False, "La variante no declara responseIdentifier en qti-choice-interaction."

    if not choice_nodes:
        return False, "La variante no incluye alternativas válidas dentro de qti-choice-interaction."

    choice_ids = {
        (choice.attrib.get("identifier") or "").strip()
        for choice in choice_nodes
        if (choice.attrib.get("identifier") or "").strip()
    }
    if not choice_ids:
        return False, "La variante no declara identifiers válidos para las alternativas."

    declaration = root.find(".//{*}qti-response-declaration")
    if declaration is None:
        declaration = root.find(".//{*}responseDeclaration")
    if declaration is None:
        return False, "La variante no incluye qti-response-declaration para marcar la respuesta correcta."

    declaration_identifier = (declaration.attrib.get("identifier") or "").strip()
    if not declaration_identifier:
        return False, "La variante incluye qti-response-declaration, pero no declara identifier."
    if declaration_identifier != response_identifier:
        return False, "La variante tiene identifiers inconsistentes entre qti-choice-interaction y qti-response-declaration."

    correct_response = declaration.find(".//{*}qti-correct-response")
    if correct_response is None:
        correct_response = declaration.find(".//{*}correctResponse")
    if correct_response is None:
        return False, "La variante no incluye qti-correct-response en la declaración de respuesta."

    value_node = correct_response.find(".//{*}qti-value")
    if value_node is None:
        value_node = correct_response.find(".//{*}value")
    correct_identifier = (value_node.text or "").strip() if value_node is not None and value_node.text else ""
    if not correct_identifier:
        return False, "La variante tiene qti-response-declaration, pero la respuesta correcta marcada está vacía."
    if correct_identifier not in choice_ids:
        return False, "La variante marca una respuesta correcta que no corresponde a ninguna alternativa."

    return True, ""


def surface_similarity(left: str, right: str) -> float:
    """Compute a relaxed similarity score for semantic guardrails."""
    return SequenceMatcher(None, _normalize_for_similarity(left), _normalize_for_similarity(right)).ratio()


def _element_to_text(element: ET.Element) -> str:
    parts = []
    tag_name = element.tag.split("}")[-1].lower()

    if tag_name == "img":
        alt = element.attrib.get("alt", "").strip()
        return alt
    if tag_name == "object":
        return (
            element.attrib.get("aria-label", "").strip()
            or element.attrib.get("label", "").strip()
            or element.attrib.get("title", "").strip()
        )

    if element.text:
        parts.append(element.text.strip())

    for child in element:
        tag = child.tag.split("}")[-1].lower()

        if tag in ("qti-feedback-inline", "feedbackinline", "qti-feedback-block", "feedbackblock"):
            continue

        if tag == "math":
            parts.append(process_mathml(child))
        elif tag in ("qti-simple-choice", "simplechoice"):
            pass
        else:
            parts.append(_element_to_text(child))

        if child.tail:
            parts.append(child.tail.strip())

    return " ".join(filter(None, parts))


def _choice_text_without_feedback(element: ET.Element) -> str:
    parts: list[str] = []
    if element.text:
        parts.append(element.text.strip())

    for child in element:
        tag = child.tag.split("}")[-1].lower()
        if tag in ("qti-feedback-inline", "feedbackinline"):
            continue
        if tag == "math":
            parts.append(process_mathml(child))
        else:
            parts.append(_element_to_text(child))
        if child.tail:
            parts.append(child.tail.strip())

    return " ".join(filter(None, parts))


def _normalize_for_similarity(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"\d+(?:[.,]\d+)?", " <num> ", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()
