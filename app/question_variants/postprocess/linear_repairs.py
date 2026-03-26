"""Deterministic repairs for linear-equation family variants."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from app.question_variants.postprocess.repair_utils import NS, clone_element, format_number, parse_number, serialize_xml
from app.question_variants.qti_validation_utils import extract_question_text


def repair_linear_equation_variant(qti_xml: str) -> str:
    try:
        root = ET.fromstring(qti_xml)
    except ET.ParseError:
        return qti_xml

    parsed = _extract_linear_equation_case(extract_question_text(qti_xml), qti_xml)
    if parsed is None:
        return qti_xml

    _clarify_linear_equation_formula(root, parsed)
    _restructure_linear_equation_context(root)

    bundle_count, bundle_total, fixed_amount, target_amount = parsed
    if bundle_count == 0:
        return serialize_xml(root)
    rate = bundle_total / bundle_count
    if abs(rate) < 1e-9:
        return serialize_xml(root)

    correct_value = (target_amount - fixed_amount) / rate
    candidate_values = [fixed_amount / rate, target_amount / rate, (target_amount + fixed_amount) / rate]
    values = [correct_value] + candidate_values
    rounded_values: list[int] = []
    for value in values:
        if value <= 0 or abs(value - round(value)) > 1e-9:
            return serialize_xml(root)
        rounded_values.append(int(round(value)))
    if len(set(rounded_values)) != 4:
        return serialize_xml(root)

    choice_nodes = root.findall(".//qti:qti-simple-choice", NS) or root.findall(".//{*}qti-simple-choice")
    if len(choice_nodes) != 4:
        return serialize_xml(root)
    correct_id = _find_correct_identifier(root)
    if not correct_id:
        return serialize_xml(root)

    distractors = [str(value) for value in rounded_values[1:]]
    next_distractor = iter(distractors)
    for choice in choice_nodes:
        if choice.attrib.get("identifier", "") == correct_id:
            choice.text = str(rounded_values[0])
        else:
            choice.text = next(next_distractor)

    return serialize_xml(root)


def _find_correct_identifier(root: ET.Element) -> str:
    value = root.find(".//qti:qti-correct-response/qti:qti-value", NS)
    if value is None:
        value = root.find(".//{*}qti-correct-response/{*}qti-value")
    return (value.text or "").strip() if value is not None else ""


def _extract_linear_equation_case(question_text: str, qti_xml: str) -> tuple[float, float, float, float] | None:
    try:
        root = ET.fromstring(qti_xml)
    except ET.ParseError:
        return None

    paragraphs = root.findall(".//qti:p", NS) or root.findall(".//{*}p")
    if len(paragraphs) < 2:
        return None

    support_paragraph = None
    for paragraph in paragraphs:
        paragraph_text = re.sub(r"\s+", " ", "".join(paragraph.itertext())).lower()
        if "meta" in paragraph_text and ("ahorr" in paragraph_text or "inicial" in paragraph_text):
            support_paragraph = paragraph
            break
    if support_paragraph is None and len(paragraphs) >= 3:
        support_paragraph = paragraphs[2]
    if support_paragraph is None:
        return None

    fraction = root.find(".//{*}mfrac")
    if fraction is None or len(list(fraction)) < 2:
        return None
    numerator_text = re.sub(r"\s+", " ", "".join(list(fraction)[0].itertext())).replace("\u2009", "").replace("\xa0", " ")
    denominator_text = re.sub(r"\s+", " ", "".join(list(fraction)[1].itertext())).replace("\u2009", "").replace("\xa0", " ")
    numerator_text = re.sub(r"(?<=\d)\.(?=\d{3}\b)", "", numerator_text)
    denominator_text = re.sub(r"(?<=\d)\.(?=\d{3}\b)", "", denominator_text)
    numerator_text = re.sub(r"(?<=\d)\s+(?=\d)", "", numerator_text)
    denominator_text = re.sub(r"(?<=\d)\s+(?=\d)", "", denominator_text)
    numerator_values = [value for value in (parse_number(v) for v in re.findall(r"\d+(?:[.,]\d+)?", numerator_text)) if value is not None]
    denominator_values = [value for value in (parse_number(v) for v in re.findall(r"\d+(?:[.,]\d+)?", denominator_text)) if value is not None]
    if not numerator_values or not denominator_values:
        return None

    bundle_count, bundle_total = denominator_values[0], numerator_values[0]

    support_text = _normalize_numeric_text("".join(support_paragraph.itertext()))
    support_values = [value for value in (parse_number(v) for v in re.findall(r"\d+(?:[.,]\d+)?", support_text)) if value is not None]
    if len(support_values) >= 2:
        return bundle_count, bundle_total, support_values[1], support_values[0]

    first_text = _normalize_numeric_text("".join(paragraphs[0].itertext()))
    trailing_support = None
    for paragraph in reversed(paragraphs):
        lowered = re.sub(r"\s+", " ", "".join(paragraph.itertext())).lower()
        if any(token in lowered for token in ("quedan", "queda", "restan", "resta", "meta", "ahorr", "inicial")):
            trailing_support = paragraph
            break
    if trailing_support is None and len(paragraphs) >= 2:
        trailing_support = paragraphs[-2]
    if trailing_support is None:
        return None
    last_text = _normalize_numeric_text("".join(trailing_support.itertext()))
    first_values = [value for value in (parse_number(v) for v in re.findall(r"\d+(?:[.,]\d+)?", first_text)) if value is not None]
    last_values = [value for value in (parse_number(v) for v in re.findall(r"\d+(?:[.,]\d+)?", last_text)) if value is not None]
    intro_lower = re.sub(r"\s+", " ", "".join(paragraphs[0].itertext())).lower()
    last_lower = re.sub(r"\s+", " ", "".join(trailing_support.itertext())).lower()
    if first_values and last_values and "inicial" in intro_lower and any(token in last_lower for token in ("quedan", "queda", "restan", "resta")):
        initial_amount = first_values[0]
        remaining_amount = last_values[0]
        return bundle_count, bundle_total, remaining_amount, initial_amount

    return None


def _normalize_numeric_text(text: str) -> str:
    normalized = text.replace("\u2009", "").replace("\xa0", " ").replace("$", "")
    normalized = re.sub(r"(?<=\d)\.(?=\d{3}\b)", "", normalized)
    normalized = re.sub(r"(?<=\d)\s+(?=\d)", "", normalized)
    return re.sub(r"\s+", " ", normalized)


def _restructure_linear_equation_context(root: ET.Element) -> None:
    item_body = root.find(".//qti:qti-item-body", NS) or root.find(".//{*}qti-item-body")
    if item_body is None:
        return
    choice_interaction = item_body.find(".//qti:qti-choice-interaction", NS) or item_body.find(".//{*}qti-choice-interaction")
    paragraphs = item_body.findall("./qti:p", NS) or item_body.findall("./{*}p")
    if choice_interaction is None or len(paragraphs) < 3:
        return
    if any(not re.sub(r"\s+", " ", "".join(paragraph.itertext())).strip() for paragraph in paragraphs[:3]):
        return

    intro_label = ET.Element("p")
    intro_label.text = "Registro del caso:"
    details = [clone_element(paragraph) for paragraph in paragraphs[:3]]
    details[1].text = f"Modelo de cálculo: {details[1].text or ''}"

    prompt = choice_interaction.find("./qti:qti-prompt", NS) or choice_interaction.find("./{*}qti-prompt")
    if prompt is not None:
        prompt_text = re.sub(r"\s+", " ", "".join(prompt.itertext())).strip()
        prompt.clear()
        prompt.text = (
            f"Según el registro, {prompt_text[:1].lower() + prompt_text[1:]}"
            if prompt_text
            else "Según el registro, ¿cuál es el valor buscado?"
        )

    for paragraph in paragraphs[:3]:
        item_body.remove(paragraph)
    children = list(item_body)
    insert_index = children.index(choice_interaction) if choice_interaction in children else len(children)
    for offset, paragraph in enumerate((intro_label, *details)):
        item_body.insert(insert_index + offset, paragraph)


def _clarify_linear_equation_formula(root: ET.Element, parsed: tuple[float, float, float, float]) -> None:
    bundle_count, bundle_total, fixed_amount, target_amount = parsed
    if bundle_count <= 0 or not any(abs(bundle_total - value) < 1e-9 for value in (fixed_amount, target_amount)):
        return

    item_body = root.find(".//qti:qti-item-body", NS) or root.find(".//{*}qti-item-body")
    if item_body is None:
        return
    paragraphs = item_body.findall("./qti:p", NS) or item_body.findall("./{*}p")
    if len(paragraphs) < 2:
        return

    rate_value = bundle_total / bundle_count
    if abs(rate_value) < 1e-9:
        return

    paragraph = paragraphs[1]
    paragraph.clear()
    paragraph.text = "Para calcular cuánto dinero adicional "

    math_d = ET.SubElement(paragraph, "{http://www.w3.org/1998/Math/MathML}math")
    ET.SubElement(math_d, "{http://www.w3.org/1998/Math/MathML}mi").text = "D"
    math_d.tail = (
        f" se recauda al vender entradas para el evento, conviene interpretar primero que cada entrada aporta "
        f"${format_number(rate_value)}. Por eso se puede usar la fórmula "
    )

    math_formula = ET.SubElement(paragraph, "{http://www.w3.org/1998/Math/MathML}math")
    ET.SubElement(math_formula, "{http://www.w3.org/1998/Math/MathML}mi").text = "D"
    ET.SubElement(math_formula, "{http://www.w3.org/1998/Math/MathML}mo").text = "="
    mrow = ET.SubElement(math_formula, "{http://www.w3.org/1998/Math/MathML}mrow")
    ET.SubElement(mrow, "{http://www.w3.org/1998/Math/MathML}mo").text = "("
    frac = ET.SubElement(mrow, "{http://www.w3.org/1998/Math/MathML}mfrac")
    ET.SubElement(frac, "{http://www.w3.org/1998/Math/MathML}mn").text = format_number(bundle_total)
    ET.SubElement(frac, "{http://www.w3.org/1998/Math/MathML}mn").text = format_number(bundle_count)
    ET.SubElement(mrow, "{http://www.w3.org/1998/Math/MathML}mo").text = ")"
    ET.SubElement(mrow, "{http://www.w3.org/1998/Math/MathML}mi").text = "e"
    math_formula.tail = ", tal que "

    math_e = ET.SubElement(paragraph, "{http://www.w3.org/1998/Math/MathML}math")
    ET.SubElement(math_e, "{http://www.w3.org/1998/Math/MathML}mi").text = "e"
    math_e.tail = " es la cantidad de entradas vendidas."
