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


def repair_algebraic_model_translation_prompt(
    qti_xml: str,
    selected_shape_id: str = "context_to_model_match",
) -> str:
    try:
        root = ET.fromstring(qti_xml)
    except ET.ParseError:
        return qti_xml

    lowered = qti_xml.lower()
    has_visual_support = any(token in lowered for token in ("<img", "<object", "<table", "<qti-object", "<qti-table"))

    interaction = find_first_by_tag_name(root, "qti-choice-interaction", "choiceInteraction")
    if interaction is None:
        return qti_xml

    effective_shape = selected_shape_id
    if _choices_look_symbolic(interaction):
        effective_shape = "context_to_model_match"

    prompt = find_first_by_tag_name(interaction, "qti-prompt", "prompt")
    if prompt is None:
        prompt = ET.Element("qti-prompt")
        interaction.insert(0, prompt)

    if effective_shape == "model_to_context_match":
        prompt.text = "¿Cuál de las siguientes descripciones interpreta correctamente el modelo algebraico presentado?"
        noun_replacement = "modelo"
        phrase_replacement = "modelo presentado"
        if _looks_like_place_value_model(root):
            _rewrite_numeric_choices_as_place_value_descriptions(interaction)
            _align_place_value_stem(root, interaction)
    else:
        prompt.text = "¿Cuál de las siguientes expresiones representa correctamente la situación descrita?"
        noun_replacement = "registro"
        phrase_replacement = "registro descrito"

    if has_visual_support:
        return serialize_xml(root)

    replacements = [
        (r"\bla\s+figura adjunta\b", f"el {phrase_replacement}"),
        (r"\bla\s+tabla adjunta\b", f"el {phrase_replacement}"),
        (r"\bla\s+imagen adjunta\b", f"el {phrase_replacement}"),
        (r"\bel\s+gráfico adjunto\b", f"el {phrase_replacement}"),
        (r"\bel\s+grafico adjunto\b", f"el {phrase_replacement}"),
        (r"\bla\s+figura\b", f"el {noun_replacement}"),
        (r"\bla\s+tabla\b", f"el {noun_replacement}"),
        (r"\bla\s+imagen\b", f"el {noun_replacement}"),
        (r"\bel\s+gráfico\b", f"el {noun_replacement}"),
        (r"\bel\s+grafico\b", f"el {noun_replacement}"),
        (r"\bel\s+diagrama\b", f"el {noun_replacement}"),
        (r"\bla\s+infografía\b", "la representación del modelo" if noun_replacement == "modelo" else f"el {noun_replacement}"),
        (r"\bla\s+infografia\b", "la representación del modelo" if noun_replacement == "modelo" else f"el {noun_replacement}"),
        (r"\bfigura adjunta\b", phrase_replacement),
        (r"\btabla adjunta\b", phrase_replacement),
        (r"\bimagen adjunta\b", phrase_replacement),
        (r"\bgráfico adjunto\b", phrase_replacement),
        (r"\bgrafico adjunto\b", phrase_replacement),
        (r"\bgráfico\b", noun_replacement),
        (r"\bgrafico\b", noun_replacement),
        (r"\bdiagrama\b", noun_replacement),
        (r"\bfigura\b", noun_replacement),
        (r"\bimagen\b", noun_replacement),
        (r"\binfografía\b", noun_replacement),
        (r"\binfografia\b", noun_replacement),
        (r"\btabla\b", noun_replacement),
    ]

    changed = False
    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        local = element.tag.split("}")[-1]
        if local not in {"p", "qti-prompt", "prompt", "div", "span"}:
            continue
        if element.text:
            updated = element.text
            for pattern, replacement in replacements:
                updated = re.sub(pattern, replacement, updated, flags=re.IGNORECASE)
            if updated != element.text:
                element.text = updated
                changed = True
        if element.tail:
            updated_tail = element.tail
            for pattern, replacement in replacements:
                updated_tail = re.sub(pattern, replacement, updated_tail, flags=re.IGNORECASE)
            if updated_tail != element.tail:
                element.tail = updated_tail
                changed = True

    return serialize_xml(root) if changed else serialize_xml(root)


def _choices_look_symbolic(interaction: ET.Element) -> bool:
    symbolic_choices = 0
    choice_nodes = find_all_by_tag_name(interaction, "qti-simple-choice", "simpleChoice")
    for choice in choice_nodes:
        plain_text = re.sub(r"\s+", " ", "".join(choice.itertext())).strip().lower()
        has_math = any(child.tag.split("}")[-1] == "math" for child in choice.iter())
        has_symbolic_tokens = bool(
            re.search(
                r"(10\s*\^|\b[xyz]\b|[+*=÷·])",
                plain_text,
            )
        )
        if has_math or has_symbolic_tokens:
            symbolic_choices += 1
            continue
        if re.search(r"\bexpresi[oó]n\b|\bmodelo\b|\bdescomposici[oó]n\b", plain_text):
            symbolic_choices += 1
    return symbolic_choices >= max(2, len(choice_nodes) // 2)


def _looks_like_place_value_model(root: ET.Element) -> bool:
    lowered = serialize_xml(root).lower()
    return bool(re.search(r"(10</m:mn>|10\^|potencias?\s+de\s+10|msup)", lowered))


def _rewrite_numeric_choices_as_place_value_descriptions(interaction: ET.Element) -> None:
    for choice in find_all_by_tag_name(interaction, "qti-simple-choice", "simpleChoice"):
        raw_text = re.sub(r"\s+", "", "".join(choice.itertext()))
        if not raw_text.isdigit():
            continue
        description = _build_place_value_description(raw_text)
        if not description:
            continue
        for child in list(choice):
            choice.remove(child)
        choice.text = description


def _build_place_value_description(digits_text: str) -> str:
    place_names_by_length = {
        4: ["unidades de millar", "centenas", "decenas", "unidades"],
        5: ["decenas de millar", "unidades de millar", "centenas", "decenas", "unidades"],
        6: ["centenas de millar", "decenas de millar", "unidades de millar", "centenas", "decenas", "unidades"],
    }
    place_names = place_names_by_length.get(len(digits_text))
    if not place_names:
        return ""

    pieces = [f"{digit} {place}" for digit, place in zip(digits_text, place_names, strict=False)]
    if len(pieces) == 1:
        joined = pieces[0]
    else:
        joined = ", ".join(pieces[:-1]) + f" y {pieces[-1]}"
    return f"Representa un número con {joined}."


def _align_place_value_stem(root: ET.Element, interaction: ET.Element) -> None:
    item_body = find_first_by_tag_name(root, "qti-item-body", "itemBody")
    if item_body is None:
        return

    for child in list(item_body):
        if child is interaction:
            continue
        if child.tag.split("}")[-1] != "p":
            continue
        text = re.sub(r"\s+", " ", "".join(child.itertext())).strip().lower()
        contains_math = any(grandchild.tag.split("}")[-1] == "math" for grandchild in child.iter())
        if contains_math:
            continue
        if "¿cuál" in text or "cual" in text or "número" in text or "numero" in text:
            item_body.remove(child)

    instruction = ET.Element("qti-p")
    instruction.text = "Selecciona la descripción de valor posicional que interpreta correctamente esa descomposición."
    children = list(item_body)
    insert_index = children.index(interaction) if interaction in children else len(children)
    item_body.insert(insert_index, instruction)


def repair_property_justification_choice(
    qti_xml: str,
    result_property_type: str,
    power_base_family: str = "",
    argument_polarity: str = "",
) -> str:
    try:
        root = ET.fromstring(qti_xml)
    except ET.ParseError:
        return qti_xml

    correct_response = find_first_by_tag_name(root, "qti-correct-response", "correctResponse")
    value_node = find_first_by_tag_name(correct_response, "qti-value", "value") if correct_response is not None else None
    correct_identifier = (value_node.text or "").strip() if value_node is not None else ""
    if not correct_identifier:
        return qti_xml

    case = _extract_power_division_case(root)
    if case is None:
        return qti_xml
    base, left_exp, right_exp = case
    if power_base_family == "binary_power_composition":
        if base not in {2, 4, 8, 16}:
            base = 4
        if result_property_type == "even_integer":
            base, left_exp, right_exp = _normalize_binary_even_integer_case(base, left_exp, right_exp)
    _rewrite_power_division_stem(root, base, left_exp, right_exp, result_property_type, argument_polarity)

    choices = find_all_by_tag_name(root, "qti-simple-choice", "simpleChoice")
    if len(choices) != 4:
        return qti_xml

    correct_text, distractors = _build_property_justification_options(
        base,
        left_exp,
        right_exp,
        result_property_type,
        power_base_family,
    )
    if not correct_text or len(distractors) != 3:
        return qti_xml

    distractor_iter = iter(distractors)
    for choice in choices:
        for child in list(choice):
            choice.remove(child)
        if choice.attrib.get("identifier") == correct_identifier:
            choice.text = correct_text
            continue
        choice.text = next(distractor_iter)
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


def _extract_power_division_case(root: ET.Element) -> tuple[int, int, int] | None:
    msup_nodes = [node for node in root.iter() if node.tag.split("}")[-1] == "msup"]
    if len(msup_nodes) >= 2:
        left = _parse_msup(msup_nodes[0])
        right = _parse_msup(msup_nodes[1])
        if left and right and left[0] == right[0]:
            return left[0], left[1], right[1]

    text = re.sub(r"\s+", " ", "".join(root.itertext()))
    match = re.search(
        r"(\d+)\s*\^\s*(\d+)\s*[:/÷]\s*(\d+)\s*\^\s*(\d+)",
        text,
    )
    if not match:
        match = re.search(
            r"divisi[oó]n\s+entre\s+(\d+)\s*\^\s*(\d+)\s+y\s+(\d+)\s*\^\s*(\d+)",
            text,
            flags=re.IGNORECASE,
        )
    if not match:
        match = re.search(
            r"dividir\s+(\d+)\s*\^\s*(\d+)\s+entre\s+(\d+)\s*\^\s*(\d+)",
            text,
            flags=re.IGNORECASE,
        )
    if not match:
        return None
    base_left, exp_left, base_right, exp_right = map(int, match.groups())
    if base_left != base_right:
        return None
    return base_left, exp_left, exp_right


def _parse_msup(node: ET.Element) -> tuple[int, int] | None:
    children = list(node)
    if len(children) < 2:
        return None
    base = parse_number("".join(children[0].itertext()))
    exponent = parse_number("".join(children[1].itertext()))
    if base is None or exponent is None:
        return None
    return int(base), int(exponent)


def _rewrite_power_division_stem(
    root: ET.Element,
    base: int,
    left_exp: int,
    right_exp: int,
    result_property_type: str,
    argument_polarity: str,
) -> None:
    item_body = find_first_by_tag_name(root, "qti-item-body", "itemBody")
    if item_body is None:
        return
    prompt_paragraph = next((child for child in list(item_body) if child.tag.split("}")[-1].lower() == "p"), None)
    if prompt_paragraph is None:
        return
    for child in list(prompt_paragraph):
        prompt_paragraph.remove(child)
    property_text = _target_property_text(result_property_type)
    if argument_polarity == "refute_invalid_argument":
        prompt_paragraph.text = (
            f"¿Cuál de los siguientes argumentos NO justifica correctamente que la división entre "
            f"{base}^{left_exp} y {base}^{right_exp} da como resultado {property_text}?"
        )
    else:
        prompt_paragraph.text = (
            f"¿Cuál de los siguientes argumentos justifica que la división entre "
            f"{base}^{left_exp} y {base}^{right_exp} da como resultado {property_text}?"
        )


def _normalize_binary_even_integer_case(base: int, left_exp: int, right_exp: int) -> tuple[int, int, int]:
    """Keep binary-power variants in-family while avoiding a literal clone of the source."""
    if base == 2:
        base = 4
    exponent_gap = left_exp - right_exp
    if exponent_gap <= 0:
        if right_exp < 2:
            right_exp = 2
        exponent_gap = 3
        left_exp = right_exp + exponent_gap
    return base, left_exp, right_exp


def _target_property_text(result_property_type: str) -> str:
    if result_property_type == "even_integer":
        return "un número par"
    if result_property_type == "perfect_square":
        return "un cuadrado perfecto"
    if result_property_type == "multiple_of_base":
        return "un múltiplo de la base"
    return "un resultado coherente con la propiedad pedida"


def _build_property_justification_options(
    base: int,
    left_exp: int,
    right_exp: int,
    result_property_type: str,
    power_base_family: str = "",
) -> tuple[str, list[str]]:
    exponent_gap = left_exp - right_exp
    if result_property_type == "even_integer" and power_base_family == "binary_power_composition" and exponent_gap > 0:
        justification = (
            f"Al dividir potencias de igual base se obtiene {base}^{exponent_gap}; como la base {base} es par "
            "y el exponente resultante sigue siendo entero positivo, esa potencia sigue siendo un número par."
        )
    else:
        justification = _build_property_justification(base, exponent_gap, result_property_type)
    if not justification:
        return "", []
    if result_property_type == "even_integer":
        distractors = [
            (
                f"Que las bases son iguales y múltiplos de 2, y que al dividir las potencias se conserva la base "
                f"pero se dividen los exponentes, obteniendo un exponente entero positivo."
            ),
            (
                f"Que al dividir las potencias se dividen las bases obteniendo 1, y que al restar los exponentes "
                f"se obtiene {exponent_gap}, el cual es un número par."
            ),
            (
                f"Que las bases son iguales y múltiplos de 2, y que al dividir las potencias se conserva la base "
                f"pero se suman los exponentes, obteniendo un exponente entero positivo."
            ),
        ]
        return justification, distractors
    distractors = [
        "Se conserva la base, pero el exponente resultante se obtiene dividiendo los exponentes.",
        "La propiedad se justifica sumando los exponentes de las potencias involucradas.",
        "La división entre potencias de igual base elimina la base y deja solo el exponente restante.",
    ]
    return justification, distractors


def _build_property_justification(base: int, exponent_gap: int, result_property_type: str) -> str:
    if result_property_type == "even_exponent_square_form" and exponent_gap > 0 and exponent_gap % 2 == 0:
        half = exponent_gap // 2
        return f"Al dividir se obtiene {base}^{exponent_gap} y, como {exponent_gap} es par, puede escribirse como ({base}^{half})^2."
    if result_property_type == "negative_exponent_reciprocal" and exponent_gap < 0:
        return f"Al dividir se obtiene {base}^{exponent_gap}; un exponente negativo representa el recíproco de {base}^{abs(exponent_gap)}."
    if exponent_gap > 0:
        if result_property_type == "even_integer" and base % 2 == 0:
            return (
                f"Al dividir potencias de igual base, las bases se mantienen iguales ({base}) y se restan los exponentes, "
                f"por lo que queda {base}^{exponent_gap}; como la base es par y el exponente sigue siendo "
                "entero positivo, el resultado continúa siendo un número par."
            )
        return f"Al dividir potencias de igual base se restan exponentes, por lo que queda {base}^{exponent_gap}."
    return ""
