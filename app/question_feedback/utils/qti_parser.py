"""Utilities for parsing QTI XML."""

from __future__ import annotations

from xml.etree import ElementTree as ET


def extract_correct_answer(qti_xml: str) -> str | None:
    """Extract correct answer identifier from QTI XML.

    Looks for the correct response value in the response declaration.

    Args:
        qti_xml: QTI XML string.

    Returns:
        Correct answer identifier (e.g., "ChoiceB") or None if not found.
    """
    try:
        root = ET.fromstring(qti_xml)

        # Try with namespace
        ns = {"qti": "http://www.imsglobal.org/xsd/imsqtiasi_v3p0"}
        correct = root.find(
            ".//qti:qti-correct-response/qti:qti-value", ns
        ) or root.find(".//qti-correct-response/qti-value")

        if correct is not None and correct.text:
            return correct.text.strip()

        # Try alternative structure
        correct = root.find(".//correctResponse/value")
        if correct is not None and correct.text:
            return correct.text.strip()

        return None
    except ET.ParseError:
        return None


def extract_title(qti_xml: str) -> str | None:
    """Extract title from QTI XML.

    Args:
        qti_xml: QTI XML string.

    Returns:
        Title attribute value or None if not found.
    """
    try:
        root = ET.fromstring(qti_xml)
        return root.get("title")
    except ET.ParseError:
        return None


def has_feedback(qti_xml: str) -> bool:
    """Check if QTI XML contains feedback elements.

    Checks for both inline feedback (per-option) and block feedback (solution).

    Args:
        qti_xml: QTI XML string.

    Returns:
        True if any feedback elements are found.
    """
    return (
        "<qti-feedback-inline" in qti_xml or "<qti-feedback-block" in qti_xml
    )


def extract_stem(qti_xml: str) -> str | None:
    """Extract the question stem text from QTI XML.

    Args:
        qti_xml: QTI XML string.

    Returns:
        Question stem text or None if not found.
    """
    try:
        root = ET.fromstring(qti_xml)
        ns = {"qti": "http://www.imsglobal.org/xsd/imsqtiasi_v3p0"}

        # Try to find itemBody
        item_body = root.find(".//qti:itemBody", ns) or root.find(".//itemBody")

        if item_body is not None:
            # Extract stem from prompt or first p/div
            prompt = item_body.find(".//qti:prompt", ns) or item_body.find(
                ".//prompt"
            )
            if prompt is not None:
                return "".join(prompt.itertext()).strip()

            # Try first text element
            for elem in item_body:
                text = "".join(elem.itertext()).strip()
                if text:
                    return text

        return None
    except ET.ParseError:
        return None


def extract_choices(qti_xml: str) -> list[dict[str, str]]:
    """Extract answer choices from QTI XML.

    Args:
        qti_xml: QTI XML string.

    Returns:
        List of dicts with 'id' and 'text' keys.
    """
    choices: list[dict[str, str]] = []

    try:
        root = ET.fromstring(qti_xml)
        ns = {"qti": "http://www.imsglobal.org/xsd/imsqtiasi_v3p0"}

        # Find choice interaction
        choice_interaction = root.find(
            ".//qti:choiceInteraction", ns
        ) or root.find(".//choiceInteraction")

        if choice_interaction is not None:
            for choice in choice_interaction.findall(".//*"):
                if "simpleChoice" in choice.tag or choice.tag.endswith(
                    "simpleChoice"
                ):
                    choice_id = choice.get("identifier", "")
                    choice_text = "".join(choice.itertext()).strip()
                    if choice_id:
                        choices.append({"id": choice_id, "text": choice_text})

    except ET.ParseError:
        pass

    return choices
