"""Shared helpers for deterministic family repairs."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

NS = {"qti": "http://www.imsglobal.org/xsd/imsqtiasi_v3p0"}
QTI_NS = "http://www.imsglobal.org/xsd/imsqtiasi_v3p0"
MATHML_NS = "http://www.w3.org/1998/Math/MathML"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

ET.register_namespace("", QTI_NS)
ET.register_namespace("m", MATHML_NS)
ET.register_namespace("xsi", XSI_NS)

QTI_SCHEMA_LOCATION = (
    "http://www.imsglobal.org/xsd/imsqtiasi_v3p0 "
    "https://purl.imsglobal.org/spec/qti/v3p0/schema/xsd/imsqti_asiv3p0_v1p0.xsd"
)

CANONICAL_QTI_LOCAL_NAMES = {
    "assessmentitem": "qti-assessment-item",
    "responsedeclaration": "qti-response-declaration",
    "correctresponse": "qti-correct-response",
    "outcomedeclaration": "qti-outcome-declaration",
    "defaultvalue": "qti-default-value",
    "value": "qti-value",
    "itembody": "qti-item-body",
    "choiceinteraction": "qti-choice-interaction",
    "simplechoice": "qti-simple-choice",
    "responseprocessing": "qti-response-processing",
    "prompt": "qti-prompt",
    "feedbackinline": "qti-feedback-inline",
    "feedbackblock": "qti-feedback-block",
}

QTI_RENDER_TAGS = {
    "p",
    "div",
    "span",
    "strong",
    "em",
    "sub",
    "sup",
    "img",
    "object",
    "table",
    "tr",
    "td",
    "th",
    "thead",
    "tbody",
    "ul",
    "ol",
    "li",
    "br",
}

QTI_ATTR_RENAMES = {
    "baseType": "base-type",
    "timeDependent": "time-dependent",
    "responseIdentifier": "response-identifier",
    "maxChoices": "max-choices",
    "minChoices": "min-choices",
}

HTML_NAMED_ENTITY_REPLACEMENTS = {
    "&aacute;": "á",
    "&eacute;": "é",
    "&iacute;": "í",
    "&oacute;": "ó",
    "&uacute;": "ú",
    "&Aacute;": "Á",
    "&Eacute;": "É",
    "&Iacute;": "Í",
    "&Oacute;": "Ó",
    "&Uacute;": "Ú",
    "&ntilde;": "ñ",
    "&Ntilde;": "Ñ",
    "&iquest;": "¿",
    "&iexcl;": "¡",
    "&nbsp;": " ",
}


def normalized_tag_name(tag: str) -> str:
    """Normalize XML tag names across namespaced, camelCase and qti-* variants."""
    raw = tag.split("}", 1)[-1]
    raw = raw.split(":", 1)[-1]
    if raw.startswith("qti-"):
        raw = raw[4:]
    return re.sub(r"[-_]", "", raw).lower()


def find_first_by_tag_name(root: ET.Element, *tag_names: str) -> ET.Element | None:
    """Find the first descendant whose normalized tag matches any candidate."""
    expected = {normalized_tag_name(tag) for tag in tag_names if tag}
    for node in root.iter():
        if normalized_tag_name(node.tag) in expected:
            return node
    return None


def find_all_by_tag_name(root: ET.Element, *tag_names: str) -> list[ET.Element]:
    """Find all descendants whose normalized tag matches any candidate."""
    expected = {normalized_tag_name(tag) for tag in tag_names if tag}
    return [node for node in root.iter() if normalized_tag_name(node.tag) in expected]


def parse_number(text: str) -> float | None:
    cleaned = re.sub(r"[^0-9,.-]", "", text.replace("\xa0", ""))
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def format_number(value: float) -> str:
    rounded = int(value) if float(value).is_integer() else round(value, 2)
    if isinstance(rounded, int):
        return str(rounded)
    return str(rounded).replace(".", ",")


def clone_element(element: ET.Element) -> ET.Element:
    return ET.fromstring(serialize_xml(element))


def serialize_xml(element: ET.Element) -> str:
    return ET.tostring(element, encoding="unicode")


def canonicalize_qti_markup(qti_xml: str) -> str:
    """Normalize generated QTI XML to the same structural style as the source bank."""
    try:
        root = ET.fromstring(qti_xml)
    except ET.ParseError:
        return qti_xml

    _canonicalize_qti_tree(root)
    _ensure_standard_qti_scaffolding(root)
    return serialize_xml(root)


def strip_xml_comments(qti_xml: str) -> str:
    """Remove XML comments from a QTI artifact before validation/persistence."""
    return re.sub(r"<!--.*?-->", "", qti_xml, flags=re.DOTALL)


def normalize_named_entities(qti_xml: str) -> str:
    """Replace HTML named entities that break XML parsing in generated artifacts."""
    normalized = qti_xml
    for entity, replacement in HTML_NAMED_ENTITY_REPLACEMENTS.items():
        normalized = normalized.replace(entity, replacement)
    return normalized


def ensure_choice_interaction_declarations(qti_xml: str) -> str:
    """Normalize choice-interaction wiring without inventing a correct answer.

    This helper is intentionally conservative: it can align response identifiers
    and fill missing declaration attributes when a declaration already exists,
    but it must not guess the correct option when the source XML omitted it.
    """
    try:
        root = ET.fromstring(qti_xml)
    except ET.ParseError:
        return qti_xml

    declaration = find_first_by_tag_name(root, "qti-response-declaration", "responseDeclaration")
    interaction = find_first_by_tag_name(root, "qti-choice-interaction", "choiceInteraction")
    if interaction is None:
        return qti_xml

    response_identifier = (
        interaction.attrib.get("response-identifier")
        or interaction.attrib.get("responseIdentifier")
        or "RESPONSE"
    )
    interaction.attrib["response-identifier" if "response-identifier" in interaction.attrib else "responseIdentifier"] = response_identifier

    if declaration is None:
        return qti_xml

    declaration.attrib["identifier"] = response_identifier
    declaration.attrib.setdefault("cardinality", "single")
    declaration.attrib.setdefault("baseType", "identifier")

    return serialize_xml(root)


def apply_declared_correct_choice(qti_xml: str, correct_identifier: str) -> str:
    """Create or normalize response wiring using an explicit declared choice id.

    This is safe because it never guesses: it only writes the correct-response
    when the generator already declared an identifier that exists in the item.
    """
    declared = (correct_identifier or "").strip()
    if not declared:
        return qti_xml

    try:
        root = ET.fromstring(qti_xml)
    except ET.ParseError:
        return qti_xml

    interaction = find_first_by_tag_name(root, "qti-choice-interaction", "choiceInteraction")
    if interaction is None:
        return qti_xml

    choice_nodes = find_all_by_tag_name(interaction, "qti-simple-choice", "simpleChoice")
    choice_ids = {
        (choice.attrib.get("identifier") or "").strip()
        for choice in choice_nodes
        if (choice.attrib.get("identifier") or "").strip()
    }
    normalized_declared = _normalize_choice_identifier(declared, choice_ids)
    if not normalized_declared:
        return qti_xml

    response_identifier = (
        interaction.attrib.get("response-identifier")
        or interaction.attrib.get("responseIdentifier")
        or "RESPONSE"
    )
    interaction.attrib["response-identifier" if "response-identifier" in interaction.attrib else "responseIdentifier"] = response_identifier

    declaration = find_first_by_tag_name(root, "qti-response-declaration", "responseDeclaration")
    if declaration is None:
        declaration = ET.Element(
            "{http://www.imsglobal.org/xsd/imsqtiasi_v3p0}qti-response-declaration",
            {
                "identifier": response_identifier,
                "cardinality": "single",
                "baseType": "identifier",
            },
        )
        root.insert(0, declaration)
    else:
        declaration.attrib["identifier"] = response_identifier
        declaration.attrib.setdefault("cardinality", "single")
        declaration.attrib.setdefault("baseType", "identifier")

    correct_response = find_first_by_tag_name(declaration, "qti-correct-response", "correctResponse")
    if correct_response is None:
        correct_response = ET.SubElement(
            declaration,
            "{http://www.imsglobal.org/xsd/imsqtiasi_v3p0}qti-correct-response",
        )

    value_node = find_first_by_tag_name(correct_response, "qti-value", "value")
    if value_node is None:
        value_node = ET.SubElement(correct_response, "{http://www.imsglobal.org/xsd/imsqtiasi_v3p0}qti-value")
    value_node.text = normalized_declared

    return serialize_xml(root)


def _canonicalize_qti_tree(node: ET.Element) -> None:
    if not isinstance(node.tag, str):
        return

    namespace, local_name = _split_namespace(node.tag)
    normalized = normalized_tag_name(node.tag)
    if namespace in {"", QTI_NS}:
        if normalized in CANONICAL_QTI_LOCAL_NAMES:
            node.tag = f"{{{QTI_NS}}}{CANONICAL_QTI_LOCAL_NAMES[normalized]}"
        elif local_name in QTI_RENDER_TAGS or normalized in QTI_RENDER_TAGS:
            node.tag = f"{{{QTI_NS}}}{local_name if local_name in QTI_RENDER_TAGS else normalized}"

    _canonicalize_qti_attributes(node)
    for child in list(node):
        _canonicalize_qti_tree(child)


def _canonicalize_qti_attributes(node: ET.Element) -> None:
    updated: dict[str, str] = {}
    for key, value in list(node.attrib.items()):
        new_key = QTI_ATTR_RENAMES.get(key, key)
        updated[new_key] = value
    node.attrib.clear()
    node.attrib.update(updated)


def _ensure_standard_qti_scaffolding(root: ET.Element) -> None:
    local_name = _split_namespace(root.tag)[1]
    if normalized_tag_name(local_name) != "assessmentitem":
        return

    root.attrib.setdefault("adaptive", "false")
    root.attrib.setdefault("time-dependent", "false")
    root.attrib.setdefault(f"{{{XSI_NS}}}schemaLocation", QTI_SCHEMA_LOCATION)

    interaction = find_first_by_tag_name(root, "qti-choice-interaction", "choiceInteraction")
    declaration = find_first_by_tag_name(root, "qti-response-declaration", "responseDeclaration")
    if interaction is None or declaration is None:
        return

    outcome = find_first_by_tag_name(root, "qti-outcome-declaration", "outcomeDeclaration")
    if outcome is None:
        outcome = ET.Element(
            f"{{{QTI_NS}}}qti-outcome-declaration",
            {
                "identifier": "SCORE",
                "cardinality": "single",
                "base-type": "float",
            },
        )
        insert_index = 1 if len(root) >= 1 else len(root)
        root.insert(insert_index, outcome)
    outcome.attrib.setdefault("identifier", "SCORE")
    outcome.attrib.setdefault("cardinality", "single")
    outcome.attrib.setdefault("base-type", "float")
    default_value = find_first_by_tag_name(outcome, "qti-default-value", "defaultValue")
    if default_value is None:
        default_value = ET.SubElement(outcome, f"{{{QTI_NS}}}qti-default-value")
    value = find_first_by_tag_name(default_value, "qti-value", "value")
    if value is None:
        value = ET.SubElement(default_value, f"{{{QTI_NS}}}qti-value")
    if not (value.text or "").strip():
        value.text = "0"

    response_processing = find_first_by_tag_name(root, "qti-response-processing", "responseProcessing")
    if response_processing is None:
        response_processing = ET.Element(
            f"{{{QTI_NS}}}qti-response-processing",
            {
                "template": "https://purl.imsglobal.org/spec/qti/v3p0/rptemplates/match_correct.xml",
            },
        )
        root.append(response_processing)


def _split_namespace(tag: str) -> tuple[str, str]:
    if tag.startswith("{") and "}" in tag:
        namespace, local = tag[1:].split("}", 1)
        return namespace, local
    return "", tag


def _normalize_choice_identifier(declared: str, choice_ids: set[str]) -> str:
    if declared in choice_ids:
        return declared
    lowered_map = {choice_id.lower(): choice_id for choice_id in choice_ids}
    direct = lowered_map.get(declared.lower())
    if direct:
        return direct

    suffix = declared.lower().replace("choice", "").strip()
    if not suffix:
        return ""
    for choice_id in choice_ids:
        normalized_choice = choice_id.lower().replace("choice", "").strip()
        if normalized_choice == suffix:
            return choice_id
    return ""
