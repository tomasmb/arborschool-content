"""QTI XML extraction utilities.

This module provides centralized functions for extracting text content,
choices, images, and correct answers from QTI (Question and Test
Interoperability) XML files.

These functions are used across multiple modules (tagging, question_variants)
to avoid code duplication.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from app.utils.mathml_parser import extract_math_tokens, process_mathml


@dataclass
class QTIParsedContent:
    """Structured content extracted from QTI XML.

    Attributes:
        text: The question text with MathML converted to readable format.
        choices: List of choice texts.
        image_urls: List of image URLs found in the question.
        correct_answer_id: The identifier of the correct answer choice.
        correct_answer_text: The text of the correct answer choice.
        choice_id_map: Mapping from choice identifiers to choice texts.
    """

    text: str = ""
    choices: list[str] = field(default_factory=list)
    image_urls: list[str] = field(default_factory=list)
    correct_answer_id: str | None = None
    correct_answer_text: str | None = None
    choice_id_map: dict[str, str] = field(default_factory=dict)


def parse_qti_xml(xml_content: str) -> QTIParsedContent:
    """Parse QTI XML and extract all relevant content.

    This is the main entry point that extracts text, choices, images,
    and correct answer from a QTI XML string.

    Args:
        xml_content: The QTI XML content as a string.

    Returns:
        QTIParsedContent with all extracted data.
    """
    result = QTIParsedContent()

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return result

    # Extract correct answer ID
    result.correct_answer_id = _extract_correct_answer_id(root)

    # Extract question text
    result.text = extract_text_from_qti(root)

    # Extract choices
    choices, choice_id_map = extract_choices_from_qti(root)
    result.choices = choices
    result.choice_id_map = choice_id_map

    # Resolve correct answer text
    if result.correct_answer_id and result.correct_answer_id in choice_id_map:
        result.correct_answer_text = choice_id_map[result.correct_answer_id]

    # Extract image URLs
    result.image_urls = _extract_image_urls(root, xml_content)

    return result


def extract_text_from_qti(root_or_xml: ET.Element | str) -> str:
    """Extract question text from QTI XML.

    This function handles MathML, tables, and images specially.

    Args:
        root_or_xml: Either an ElementTree root or XML string.

    Returns:
        The extracted and cleaned question text.
    """
    if isinstance(root_or_xml, str):
        try:
            root = ET.fromstring(root_or_xml)
        except ET.ParseError:
            return ""
    else:
        root = root_or_xml

    # Find item body (support both v2 and v3)
    item_body = root.find(".//{*}itemBody") or root.find(".//{*}qti-item-body")
    if item_body is None:
        return ""

    raw_text = _extract_full_text(item_body)
    return _clean_text(raw_text)


def extract_choices_from_qti(root_or_xml: ET.Element | str) -> tuple[list[str], dict[str, str]]:
    """Extract choice texts and their identifiers from QTI XML.

    Args:
        root_or_xml: Either an ElementTree root or XML string.

    Returns:
        Tuple of (list of choice texts, mapping of choice ID to text).
    """
    if isinstance(root_or_xml, str):
        try:
            root = ET.fromstring(root_or_xml)
        except ET.ParseError:
            return [], {}
    else:
        root = root_or_xml

    choices = []
    choice_id_map = {}

    # Find all simpleChoice or qti-simple-choice
    choice_nodes = root.findall(".//{*}simpleChoice") + root.findall(".//{*}qti-simple-choice")

    for choice in choice_nodes:
        cid = choice.get("identifier")
        raw_choice = _extract_full_text(choice)
        cleaned_choice = _clean_text(raw_choice)
        choices.append(cleaned_choice)
        if cid:
            choice_id_map[cid] = cleaned_choice

    return choices, choice_id_map


def extract_correct_answer_from_qti(root_or_xml: ET.Element | str) -> str | None:
    """Extract the correct answer ID from QTI XML.

    Args:
        root_or_xml: Either an ElementTree root or XML string.

    Returns:
        The correct answer identifier, or None if not found.
    """
    if isinstance(root_or_xml, str):
        try:
            root = ET.fromstring(root_or_xml)
        except ET.ParseError:
            return None
    else:
        root = root_or_xml

    return _extract_correct_answer_id(root)


def get_correct_answer_text(xml_content: str) -> str:
    """Get the text of the correct answer from QTI XML.

    This is a convenience function that finds the correct answer and
    returns its text content.

    Args:
        xml_content: The QTI XML content as a string.

    Returns:
        The text of the correct answer, or empty string if not found.
    """
    parsed = parse_qti_xml(xml_content)
    return parsed.correct_answer_text or ""


# -----------------------------------------------------------------------------
# Internal helper functions
# -----------------------------------------------------------------------------


def _extract_correct_answer_id(root: ET.Element) -> str | None:
    """Extract the correct answer identifier from QTI XML root."""
    # QTI 3.0: responseDeclaration -> correctResponse -> value
    # Use {*} wildcard to handle namespaces robustly
    resp_decl = root.find(".//{*}responseDeclaration") or root.find(".//{*}qti-response-declaration")
    if resp_decl is not None:
        corr_resp = resp_decl.find(".//{*}correctResponse") or resp_decl.find(".//{*}qti-correct-response")
        if corr_resp is not None:
            val_node = corr_resp.find(".//{*}value") or corr_resp.find(".//{*}qti-value")
            if val_node is not None and val_node.text:
                return val_node.text.strip()

    # Fallback: literal search for value inside any correct response tag
    any_corr = root.find(".//{*}qti-correct-response") or root.find(".//{*}correctResponse")
    if any_corr is not None:
        val_node = any_corr.find(".//{*}qti-value") or any_corr.find(".//{*}value")
        if val_node is not None and val_node.text:
            return val_node.text.strip()

    return None


def _extract_image_urls(root: ET.Element, xml_content: str) -> list[str]:
    """Extract image URLs from QTI XML."""
    image_urls = []

    # Support img in any namespace/prefix
    for img in root.findall(".//{*}img") + root.findall(".//{*}qti-img"):
        src = img.get("src")
        if src:
            image_urls.append(src)

    # Fallback regex for edge cases
    if not image_urls:
        image_urls = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', xml_content)

    return sorted(list(set(image_urls)))


def _extract_full_text(element: ET.Element) -> str:
    """Extract text from an element, processing MathML, Tables, and Images specially."""
    parts = []
    if element.text:
        parts.append(element.text)

    for child in element:
        tag = child.tag.split("}")[-1].lower()
        if tag == "math":
            parts.append(process_mathml(child))
        elif tag == "table":
            parts.append(_process_html_table(child))
        elif tag in ["p", "div", "li", "br"]:
            # Add spacing for block elements
            content = _extract_full_text(child)
            parts.append(f"\n{content}\n" if tag != "br" else "\n")
        elif tag in ["img", "qti-img"]:
            alt = child.get("alt")
            if alt:
                parts.append(f" [Imagen: {alt}] ")
        elif tag in ("qti-simple-choice", "simplechoice"):
            # Skip individual choices when extracting question text
            # (we extract them separately)
            pass
        else:
            parts.append(_extract_full_text(child))

        if child.tail:
            parts.append(child.tail)

    return "".join(parts)


def _process_html_table(element: ET.Element) -> str:
    """Convert an HTML table to a readable text representation."""
    rows = []
    # Support both standard tr and namespaced qti-tr
    tr_nodes = element.findall(".//{*}tr")
    for tr in tr_nodes:
        cols = []
        for cell in tr.findall(".//{*}th") + tr.findall(".//{*}td"):
            cell_text = _extract_full_text(cell).strip()
            cols.append(cell_text)
        if cols:
            rows.append(" | ".join(cols))

    if rows:
        return "\n[ " + " | ".join(rows) if len(rows) == 1 else "\n" + "\n".join(rows) + "\n"
    return ""


def _clean_text(text: str) -> str:
    """Clean extracted text, preserving structural newlines."""
    if not text:
        return ""
    # Collapse multiple spaces but preserve single ones
    text = re.sub(r"[ \t]+", " ", text)
    # Collapse excessive newlines (more than 2) to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove space at start/end of lines
    text = re.sub(r"^ +| +$", "", text, flags=re.MULTILINE)
    return text.strip()


# -----------------------------------------------------------------------------
# Simple extraction (without MathML processing)
# -----------------------------------------------------------------------------


def extract_text_recursive_simple(element: ET.Element, include_math_tokens: bool = True) -> str:
    """Recursively extract text from XML element with simple approach.

    This is a simpler extraction that doesn't do full MathML processing,
    just gets raw text content.

    Args:
        element: The XML element to extract text from.
        include_math_tokens: If True, extract tokens from MathML elements.

    Returns:
        The extracted text as a string.
    """
    parts = []

    if element.text:
        parts.append(element.text.strip())

    for child in element:
        tag = child.tag.split("}")[-1].lower()

        if tag == "math":
            if include_math_tokens:
                tokens = extract_math_tokens(child)
                parts.extend(tokens)
        else:
            child_text = extract_text_recursive_simple(child, include_math_tokens)
            if child_text:
                parts.append(child_text)

        if child.tail:
            parts.append(child.tail.strip())

    return " ".join(filter(None, parts))
