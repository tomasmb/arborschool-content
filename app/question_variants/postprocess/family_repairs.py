"""Family-specific deterministic repairs for variant QTI."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from app.question_variants.qti_validation_utils import extract_question_text

NS = {"qti": "http://www.imsglobal.org/xsd/imsqtiasi_v3p0"}


def repair_family_specific_qti(qti_xml: str, contract: dict[str, object]) -> str:
    """Apply deterministic family-specific repairs before semantic validation."""
    op = str(contract.get("operation_signature") or "")
    if op in {"direct_percentage_calculation", "percentage_increase_application"}:
        return _repair_percentage_choices(
            qti_xml,
            op,
            [str(item).strip() for item in contract.get("distractor_archetypes", []) if str(item).strip()],
            str(contract.get("percentage_band") or "unknown"),
        )
    if (
        op == "algebraic_expression_evaluation"
        and str(contract.get("task_form") or "") == "substitute_expression"
        and str(contract.get("presentation_style") or "") == "symbolic_formula_plus_reference"
    ):
        return _repair_symbolic_formula_presentation(qti_xml)
    if (
        op == "property_justification"
        and str(contract.get("correct_justification_archetype") or "") == "same_base_exponent_difference"
    ):
        return _repair_property_justification_choice(qti_xml, str(contract.get("result_property_type") or ""))
    return qti_xml


def _repair_percentage_choices(
    qti_xml: str,
    operation_signature: str,
    distractor_archetypes: list[str],
    percentage_band: str,
) -> str:
    try:
        root = ET.fromstring(qti_xml)
    except ET.ParseError:
        return qti_xml

    choice_nodes = root.findall(".//qti:qti-simple-choice", NS) or root.findall(".//{*}qti-simple-choice")
    if len(choice_nodes) != 4:
        return qti_xml

    correct_id = _find_correct_identifier(root)
    if not correct_id:
        return qti_xml

    question_text = extract_question_text(qti_xml)
    parsed = _extract_percentage_case(question_text, operation_signature)
    if parsed is None:
        return qti_xml
    base_value, percent_value = parsed

    correct_value = _find_numeric_choice(choice_nodes, correct_id)
    if correct_value is None:
        return qti_xml

    distractors = _build_percentage_distractors(
        base_value,
        percent_value,
        correct_value,
        operation_signature,
        distractor_archetypes,
        percentage_band,
    )
    if len(distractors) != 3:
        return qti_xml

    correct_text = _format_number(correct_value)
    replacement_values: dict[str, str] = {}
    next_distractor = iter(distractors)
    for choice in choice_nodes:
        identifier = choice.attrib.get("identifier", "")
        replacement_values[identifier] = correct_text if identifier == correct_id else next(next_distractor)

    for choice in choice_nodes:
        choice.text = replacement_values.get(choice.attrib.get("identifier", ""), choice.text or "")

    return ET.tostring(root, encoding="unicode")


def _find_correct_identifier(root: ET.Element) -> str:
    value = root.find(".//qti:qti-correct-response/qti:qti-value", NS)
    if value is None:
        value = root.find(".//{*}qti-correct-response/{*}qti-value")
    return (value.text or "").strip() if value is not None else ""


def _find_numeric_choice(choice_nodes: list[ET.Element], correct_id: str) -> float | None:
    for choice in choice_nodes:
        if choice.attrib.get("identifier") != correct_id:
            continue
        return _parse_number(choice.text or "")
    return None


def _extract_percentage_case(question_text: str, operation_signature: str) -> tuple[float, float] | None:
    normalized = question_text.replace("\xa0", " ")
    percent_match = re.search(r"(\d+(?:[.,]\d+)?)\s*%", normalized)
    if not percent_match:
        return None
    percent_value = float(percent_match.group(1).replace(",", "."))
    number_tokens = [float(match.group(0).replace(",", ".")) for match in re.finditer(r"\d+(?:[.,]\d+)?", normalized)]
    base_candidates = [value for value in number_tokens if value != percent_value]
    if not base_candidates:
        return None
    base_value = base_candidates[0]
    return base_value, percent_value


def _build_percentage_distractors(
    base_value: float,
    percent_value: float,
    correct_value: float,
    operation_signature: str,
    distractor_archetypes: list[str],
    percentage_band: str,
) -> list[str]:
    increment = round(base_value * percent_value / 100)
    candidates: list[float] = []
    if operation_signature == "percentage_increase_application":
        candidates.extend(
            _build_increase_candidates(
                base_value,
                percent_value,
                increment,
                correct_value,
                distractor_archetypes,
                percentage_band,
            )
        )
    else:
        candidates.extend([
            base_value,
            base_value + increment,
            increment * 2,
            correct_value + increment,
        ])

    cleaned: list[str] = []
    seen: set[str] = {_format_number(correct_value)}
    for value in candidates:
        formatted = _format_number(value)
        if formatted in seen:
            continue
        seen.add(formatted)
        cleaned.append(formatted)
        if len(cleaned) == 3:
            break
    return cleaned


def _build_increase_candidates(
    base_value: float,
    percent_value: float,
    increment: float,
    correct_value: float,
    distractor_archetypes: list[str],
    percentage_band: str,
) -> list[float]:
    candidates: list[float] = []
    rounded_percent = max(1, round(percent_value))
    scaled_jump = max(2, round(base_value * 0.2)) if percentage_band == "small" else max(2, 2 * round(percent_value))

    for archetype in distractor_archetypes:
        if archetype == "increment_only":
            candidates.append(base_value + rounded_percent)
        elif archetype == "base_plus_increment":
            candidates.append(base_value + increment + rounded_percent)
        elif archetype == "gross_overestimate":
            candidates.append(correct_value + scaled_jump)

    if not candidates:
        candidates.extend([
            base_value,
            base_value + rounded_percent,
            correct_value + scaled_jump,
        ])

    candidates.extend([
        base_value,
        base_value - increment,
        correct_value + max(1, increment),
    ])
    return candidates


def _parse_number(text: str) -> float | None:
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


def _format_number(value: float) -> str:
    rounded = int(value) if float(value).is_integer() else round(value, 2)
    if isinstance(rounded, int):
        return str(rounded)
    return str(rounded).replace(".", ",")


def _repair_symbolic_formula_presentation(qti_xml: str) -> str:
    try:
        root = ET.fromstring(qti_xml)
    except ET.ParseError:
        return qti_xml

    item_body = root.find(".//qti:qti-item-body", NS) or root.find(".//{*}qti-item-body")
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

    math_text = re.sub(r"\s+", "", "".join(equation_block.itertext()))
    verbal_rule = _build_formula_rule(math_text)
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
    return ET.tostring(root, encoding="unicode")


def _build_formula_rule(math_text: str) -> str:
    match = re.search(r"([A-Za-z])=([\d.,]+)[·*]([A-Za-z])", math_text)
    if not match:
        return ""
    result_var, coefficient, input_var = match.groups()
    return (
        f"La regla de cálculo indica que {result_var} se obtiene multiplicando "
        f"{coefficient} por {input_var}."
    )


def _repair_property_justification_choice(qti_xml: str, result_property_type: str) -> str:
    try:
        root = ET.fromstring(qti_xml)
    except ET.ParseError:
        return qti_xml

    correct_id = _find_correct_identifier(root)
    if not correct_id:
        return qti_xml

    base, exponent_gap = _extract_power_division_case(root)
    if base is None or exponent_gap is None:
        return qti_xml

    inferred_property_type = _infer_result_property_type_from_text(extract_question_text(qti_xml))
    resolved_property_type = inferred_property_type or result_property_type
    rewritten = _build_property_justification(base, exponent_gap, resolved_property_type)
    if not rewritten:
        return qti_xml

    choice_nodes = root.findall(".//qti:qti-simple-choice", NS) or root.findall(".//{*}qti-simple-choice")
    for choice in choice_nodes:
        if choice.attrib.get("identifier") == correct_id:
            choice.text = rewritten
            return ET.tostring(root, encoding="unicode")
    return qti_xml


def _extract_power_division_case(root: ET.Element) -> tuple[int | None, int | None]:
    powers: list[tuple[int, int]] = []
    for msup in root.findall(".//{*}msup"):
        values = [text.strip() for text in msup.itertext() if text.strip()]
        if len(values) < 2:
            continue
        try:
            base = int(values[0].replace(",", "."))
            exponent = int(values[1].replace(",", "."))
        except ValueError:
            continue
        powers.append((base, exponent))
        if len(powers) == 2:
            break
    if len(powers) < 2 or powers[0][0] != powers[1][0]:
        return None, None
    return powers[0][0], powers[0][1] - powers[1][1]


def _build_property_justification(base: int, exponent_gap: int, result_property_type: str) -> str:
    if exponent_gap < 0:
        positive_gap = abs(exponent_gap)
        return (
            f"Que al dividir potencias de igual base se obtiene {base}^{exponent_gap} = 1/{base}^{positive_gap} y, "
            f"como {base}^{positive_gap} es mayor que 1, su recíproco es un número positivo menor que 1."
        )
    if exponent_gap == 0:
        return ""
    if result_property_type == "perfect_square":
        return (
            f"Que al dividir potencias de igual base se obtiene {base}^{exponent_gap} y, como {exponent_gap} es par, "
            f"ese resultado puede escribirse como ({base}^{exponent_gap // 2})^2."
        )
    if result_property_type == "even_integer" and base % 2 == 0:
        return (
            f"Que al dividir potencias de igual base se obtiene {base}^{exponent_gap} y toda potencia positiva "
            f"de una base par sigue siendo un número par."
        )
    if result_property_type == "positive_fraction_less_than_one":
        return (
            f"Que al dividir potencias de igual base se obtiene {base}^{exponent_gap} y una potencia positiva "
            "de una base entre 0 y 1 sigue siendo positiva y menor que 1."
        )
    return ""


def _infer_result_property_type_from_text(question_text: str) -> str:
    lowered = question_text.lower()
    if "cuadrado perfecto" in lowered:
        return "perfect_square"
    if "número par" in lowered or "numero par" in lowered:
        return "even_integer"
    if "número positivo menor que 1" in lowered or "numero positivo menor que 1" in lowered:
        return "positive_fraction_less_than_one"
    if "múltiplo de" in lowered or "multiplo de" in lowered:
        return "multiple_of_base"
    return ""
