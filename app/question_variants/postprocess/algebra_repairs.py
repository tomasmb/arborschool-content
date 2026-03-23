"""Deterministic repairs for algebra-family variants."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from app.question_variants.postprocess.repair_utils import (
    find_all_by_tag_name,
    find_first_by_tag_name,
    format_number,
    parse_number,
    serialize_xml,
)
from app.question_variants.qti_validation_utils import extract_question_text


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


def repair_verbal_formula_distractors(qti_xml: str) -> str:
    try:
        root = ET.fromstring(qti_xml)
    except ET.ParseError:
        return qti_xml

    choice_nodes = find_all_by_tag_name(root, "qti-simple-choice", "simpleChoice")
    if len(choice_nodes) != 4:
        return qti_xml

    correct_response = find_first_by_tag_name(root, "qti-correct-response", "correctResponse")
    value_node = find_first_by_tag_name(correct_response, "qti-value", "value") if correct_response is not None else None
    correct_id = (value_node.text or "").strip() if value_node is not None else ""
    if not correct_id:
        return qti_xml

    correct_choice = next((choice for choice in choice_nodes if choice.attrib.get("identifier") == correct_id), None)
    if correct_choice is None:
        return qti_xml

    correct_value = parse_number(correct_choice.text or "")
    case = _extract_verbal_conversion_case(extract_question_text(qti_xml), correct_value)
    if case is None:
        return qti_xml

    distractor_values = _build_verbal_formula_distractors(
        case["raw_result"],
        case["per_single_input"],
        case["partial_input_result"],
        case["correct_value"],
    )
    if len(distractor_values) != 3:
        return qti_xml

    distractor_iter = iter(distractor_values)
    for choice in choice_nodes:
        if choice.attrib.get("identifier") == correct_id:
            continue
        choice.text = f"{next(distractor_iter)} {case['final_unit']}"
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


def _extract_verbal_conversion_case(question_text: str, correct_value: float | None) -> dict[str, float | str] | None:
    if correct_value is None or correct_value <= 0:
        return None
    lowered = re.sub(r"\s+", " ", question_text).lower()

    coefficient_match = re.search(r"multiplicar(?:\s+la\s+cantidad\s+de\s+[a-záéíóúñ]+)?\s+por\s+(\d+(?:[.,]\d+)?)", lowered)
    divisor_match = re.search(r"equivalent[ea]\s+a\s+(\d+(?:[.,]\d+)?)\s+[a-záéíóúñ]+", lowered)
    question_match = re.search(
        r"¿cu[aá]nt[oa]s?\s+([a-záéíóúñ]+(?:\s+[a-záéíóúñ]+){0,2})\s+(?:son|corresponden a)\s+(\d+(?:[.,]\d+)?)",
        lowered,
    )
    if coefficient_match is None or divisor_match is None or question_match is None:
        return None

    coefficient = parse_number(coefficient_match.group(1))
    divisor = parse_number(divisor_match.group(1))
    input_value = parse_number(question_match.group(2))
    final_unit = question_match.group(1).strip()
    if coefficient is None or divisor is None or input_value is None or divisor <= 0 or input_value <= 0:
        return None

    raw_result = round(input_value * coefficient, 6)
    per_single_input = round(coefficient / divisor, 6)
    partial_input_result = round(correct_value / 2, 6) if input_value > 2 else round(correct_value / 4, 6)
    return {
        "raw_result": raw_result,
        "per_single_input": per_single_input,
        "partial_input_result": partial_input_result,
        "correct_value": correct_value,
        "final_unit": final_unit,
    }


def _build_verbal_formula_distractors(
    raw_result: float,
    per_single_input: float,
    partial_input_result: float,
    correct_value: float,
) -> list[str]:
    distractors: list[str] = []
    seen = {format_number(correct_value)}
    for value in (raw_result, per_single_input, partial_input_result):
        formatted = format_number(value)
        if formatted in seen:
            continue
        seen.add(formatted)
        distractors.append(formatted)
    return distractors[:3]


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
