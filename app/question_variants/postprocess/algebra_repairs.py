"""Deterministic repairs for algebra-family variants."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from app.question_variants.postprocess.repair_utils import serialize_xml


def repair_symbolic_formula_presentation(qti_xml: str) -> str:
    try:
        root = ET.fromstring(qti_xml)
    except ET.ParseError:
        return qti_xml

    item_body = root.find(".//qti-item-body") or root.find(".//{*}qti-item-body")
    if item_body is None:
        return qti_xml

    equation_block = next(
        (
            child
            for child in list(item_body)
            if child.tag.endswith("div") and "equation" in (child.attrib.get("class") or "").lower()
        ),
        None,
    )
    if equation_block is None:
        return qti_xml

    verbal_rule = _build_formula_rule(re.sub(r"\s+", "", "".join(equation_block.itertext())))
    if not verbal_rule:
        return qti_xml

    paragraphs = [child for child in list(item_body) if child.tag.endswith("p")]
    if paragraphs:
        first_text = (paragraphs[0].text or "").replace("la siguiente ecuación", "la siguiente regla de cálculo")
        first_text = first_text.replace("la siguiente expresion", "la siguiente regla de cálculo")
        paragraphs[0].text = first_text

    replacement = ET.Element("qti-p")
    replacement.text = verbal_rule
    index = list(item_body).index(equation_block)
    item_body.remove(equation_block)
    item_body.insert(index, replacement)
    return serialize_xml(root)


def repair_property_justification_choice(qti_xml: str, result_property_type: str) -> str:
    try:
        root = ET.fromstring(qti_xml)
    except ET.ParseError:
        return qti_xml

    correct_identifier = None
    for value in root.findall(".//{*}qti-correct-response/{*}qti-value"):
        correct_identifier = (value.text or "").strip()
        if correct_identifier:
            break
    if not correct_identifier:
        return qti_xml

    base, exponent_gap = _extract_power_division_case(root)
    if base is None or exponent_gap is None:
        return qti_xml
    justification = _build_property_justification(base, exponent_gap, result_property_type)
    if not justification:
        return qti_xml

    for choice in root.findall(".//{*}qti-simple-choice"):
        if choice.attrib.get("identifier") == correct_identifier:
            choice.text = justification
            break
    return serialize_xml(root)


def _build_formula_rule(math_text: str) -> str:
    match = re.search(r"([A-Za-z])=([\d.,]+)[·*]([A-Za-z])", math_text)
    if not match:
        return ""
    _, coefficient, input_var = match.groups()
    return f"La regla de cálculo consiste en multiplicar el valor de {input_var} por {coefficient}."


def _extract_power_division_case(root: ET.Element) -> tuple[int | None, int | None]:
    text = re.sub(r"\s+", " ", "".join(root.itertext()))
    match = re.search(
        r"(\d+)\s*\^\s*(\d+)\s*[:/÷]\s*(\d+)\s*\^\s*(\d+)",
        text,
    )
    if not match:
        return None, None
    base_left, exp_left, base_right, exp_right = map(int, match.groups())
    if base_left != base_right:
        return None, None
    return base_left, exp_left - exp_right


def _build_property_justification(base: int, exponent_gap: int, result_property_type: str) -> str:
    if result_property_type == "even_exponent_square_form" and exponent_gap > 0 and exponent_gap % 2 == 0:
        half = exponent_gap // 2
        return f"Al dividir se obtiene {base}^{exponent_gap} y, como {exponent_gap} es par, puede escribirse como ({base}^{half})^2."
    if result_property_type == "negative_exponent_reciprocal" and exponent_gap < 0:
        return f"Al dividir se obtiene {base}^{exponent_gap}; un exponente negativo representa el recíproco de {base}^{abs(exponent_gap)}."
    if exponent_gap > 0:
        return f"Al dividir potencias de igual base se restan exponentes, por lo que queda {base}^{exponent_gap}."
    return ""
