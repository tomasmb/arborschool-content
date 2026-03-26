"""Deterministic repairs for percentage-family variants."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from app.question_variants.postprocess.repair_utils import (
    NS,
    find_all_by_tag_name,
    find_first_by_tag_name,
    format_number,
    parse_number,
    serialize_xml,
)
from app.question_variants.qti_validation_utils import extract_question_text

NUMBER_PATTERN = r"\d{1,3}(?:[\s\u00a0]\d{3})*(?:[.,]\d+)?|\d+(?:[.,]\d+)?"


def repair_percentage_choices(
    qti_xml: str,
    operation_signature: str,
    distractor_archetypes: list[str],
    percentage_band: str,
    selected_shape_id: str = "standard_variant",
) -> str:
    try:
        root = ET.fromstring(qti_xml)
    except ET.ParseError:
        return qti_xml

    choice_nodes = find_all_by_tag_name(root, "qti-simple-choice", "simpleChoice")
    if len(choice_nodes) != 4:
        return qti_xml

    correct_id = _find_correct_identifier(root)
    if not correct_id:
        return qti_xml

    detected_correct_value = _find_numeric_choice(choice_nodes, correct_id)
    parsed = _extract_percentage_case(extract_question_text(qti_xml), operation_signature)
    if parsed is None:
        inferred = _infer_percentage_case_from_base_and_correct(extract_question_text(qti_xml), detected_correct_value)
        if inferred is None:
            return qti_xml
        base_value, percent_value = inferred
    else:
        base_value, percent_value = parsed

    if detected_correct_value is None and operation_signature != "percentage_increase_application":
        if operation_signature == "percentage_increase_application" and _has_successive_percentage_changes(extract_question_text(qti_xml)):
            _rewrite_successive_change_context(root)
            _rewrite_successive_change_prompt(root)
            _annotate_successive_formula_choices(choice_nodes, correct_id)
            return serialize_xml(root)
        return qti_xml

    correct_value = (
        _calculate_percentage_increase_total(base_value, percent_value)
        if operation_signature == "percentage_increase_application"
        else _calculate_direct_percentage_total(base_value, percent_value)
    )
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

    replacements: dict[str, str] = {}
    distractor_iter = iter(distractors)
    correct_text = format_number(correct_value)
    for choice in choice_nodes:
        identifier = choice.attrib.get("identifier", "")
        if identifier == correct_id:
            replacements[identifier] = correct_text
        else:
            pair = next(distractor_iter, None)
            if pair is None:
                return qti_xml
            replacements[identifier] = pair[1]
    for choice in choice_nodes:
        _replace_choice_text(choice, replacements.get(choice.attrib.get("identifier", ""), "".join(choice.itertext())))

    if operation_signature == "percentage_increase_application" and _has_successive_percentage_changes(extract_question_text(qti_xml)):
        _rewrite_successive_change_context(root)
        _rewrite_successive_change_prompt(root)
        _annotate_successive_change_choices(choice_nodes, correct_id)
    if selected_shape_id == "decision_statement":
        _rewrite_decision_statement_variant(
            root,
            choice_nodes,
            correct_id,
            operation_signature,
            base_value,
            percent_value,
            correct_value,
            distractors,
        )
    return serialize_xml(root)


def _find_correct_identifier(root: ET.Element) -> str:
    correct_response = find_first_by_tag_name(root, "qti-correct-response", "correctResponse")
    value = find_first_by_tag_name(correct_response, "qti-value", "value") if correct_response is not None else None
    return (value.text or "").strip() if value is not None else ""


def _find_numeric_choice(choice_nodes: list[ET.Element], correct_id: str) -> float | None:
    for choice in choice_nodes:
        if choice.attrib.get("identifier") == correct_id:
            return parse_number("".join(choice.itertext()))
    return None


def _extract_percentage_case(question_text: str, operation_signature: str) -> tuple[float, float] | None:
    normalized = question_text.replace("\xa0", " ")
    percent_match = re.search(r"(\d+(?:[.,]\d+)?)\s*%", normalized)
    if not percent_match:
        return None
    percent_value = float(percent_match.group(1).replace(",", "."))
    base_value = _extract_base_value_from_context(normalized, percent_value)
    if base_value is None:
        return None
    return base_value, percent_value


def _infer_percentage_case_from_base_and_correct(question_text: str, correct_value: float | None) -> tuple[float, float] | None:
    if correct_value is None:
        return None
    number_tokens = _extract_numeric_values(question_text)
    if not number_tokens:
        return None
    base_value = max(number_tokens)
    if base_value <= 0 or correct_value <= base_value:
        return None
    percent_value = ((correct_value - base_value) / base_value) * 100
    if percent_value <= 0:
        return None
    return base_value, round(percent_value, 2)


def _build_percentage_distractors(
    base_value: float,
    percent_value: float,
    correct_value: float,
    operation_signature: str,
    distractor_archetypes: list[str],
    percentage_band: str,
) -> list[tuple[str, str]]:
    increment = _calculate_increment(base_value, percent_value)
    if operation_signature == "percentage_increase_application":
        candidates = _build_increase_candidates(
            base_value,
            percent_value,
            increment,
            correct_value,
            distractor_archetypes,
            percentage_band,
        )
    else:
        candidates = _build_direct_percentage_candidates(base_value, percent_value, correct_value)

    cleaned: list[tuple[str, str]] = []
    seen: set[str] = {format_number(correct_value)}
    for archetype, value in candidates:
        formatted = format_number(value)
        if formatted in seen:
            continue
        seen.add(formatted)
        cleaned.append((archetype, formatted))
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
) -> list[tuple[str, float]]:
    candidates: list[tuple[str, float]] = []
    rounded_percent = max(1, round(percent_value))
    scaled_jump = max(2, round(base_value * 0.2)) if percentage_band == "small" else max(2, 2 * round(percent_value))

    for archetype in distractor_archetypes:
        if archetype == "increment_only":
            candidates.append((archetype, increment))
        elif archetype == "base_plus_increment":
            candidates.append((archetype, base_value + rounded_percent))
        elif archetype == "gross_overestimate":
            candidates.append((archetype, correct_value + increment))

    if not candidates:
        candidates.extend(
            [
                ("increment_only", increment),
                ("base_plus_increment", base_value + rounded_percent),
                ("gross_overestimate", correct_value + scaled_jump),
            ]
        )

    candidates.extend(
        [
            ("base_only", base_value),
            ("decrease_instead", max(0, base_value - increment)),
            ("gross_overestimate", correct_value + max(1, increment)),
        ]
    )
    return candidates


def _build_direct_percentage_candidates(
    base_value: float,
    percent_value: float,
    correct_value: float,
) -> list[tuple[str, float]]:
    anchor_percent = 10.0
    anchor_value = round(base_value * (anchor_percent / 100), 2)
    if abs(anchor_value - correct_value) < 1e-9:
        anchor_value = round(base_value * (1 / 100), 2)
    candidates = [
        ("decimal_shift_low", max(1, correct_value / 10)),
        ("ten_percent_anchor", max(1, anchor_value)),
        ("divide_by_percent_number", max(1, base_value / max(percent_value, 1))),
        ("base_only", base_value),
    ]
    return candidates


def _has_successive_percentage_changes(question_text: str) -> bool:
    matches = [match.group(1).replace(",", ".") for match in re.finditer(r"(\d+(?:[.,]\d+)?)\s*%", question_text)]
    return len(set(matches)) >= 2


def _rewrite_successive_change_prompt(root: ET.Element) -> None:
    prompt = find_first_by_tag_name(root, "qti-prompt", "prompt")
    if prompt is not None:
        prompt.clear()
        prompt.text = "¿Cuál de las siguientes expresiones representa correctamente el valor final luego de los cambios porcentuales sucesivos?"


def _rewrite_successive_change_context(root: ET.Element) -> None:
    item_body = find_first_by_tag_name(root, "qti-item-body", "itemBody")
    if item_body is None:
        return
    question_text = extract_question_text(serialize_xml(root))
    narrative = _build_successive_change_narrative(question_text)
    if not narrative:
        return

    choice_interaction = find_first_by_tag_name(item_body, "qti-choice-interaction", "choiceInteraction")
    if choice_interaction is None:
        return

    for child in list(item_body):
        if child is choice_interaction:
            continue
        if child.tag.endswith("p") or child.tag.endswith("qti-p"):
            item_body.remove(child)

    narrative_el = ET.Element("qti-p")
    narrative_el.text = narrative
    insert_index = list(item_body).index(choice_interaction)
    item_body.insert(insert_index, narrative_el)


def _annotate_successive_change_choices(choice_nodes: list[ET.Element], correct_id: str) -> None:
    return


def _annotate_successive_formula_choices(choice_nodes: list[ET.Element], correct_id: str) -> None:
    return


def _infer_successive_change_label(choice_text: str, is_correct: bool) -> str:
    compact = re.sub(r"\s+", "", choice_text)
    if is_correct:
        return "Registro correcto"
    if compact.startswith("(") and "+" in compact:
        return "Suma lineal de cambios"
    if compact.count("·") >= 2 and compact.startswith("0,"):
        return "Producto solo de porcentajes"
    if compact.count("·") >= 2 and compact.startswith("1,"):
        return "Aplicación multiplicativa directa"
    return "Registro alternativo"


def _rewrite_decision_statement_variant(
    root: ET.Element,
    choice_nodes: list[ET.Element],
    correct_id: str,
    operation_signature: str,
    base_value: float,
    percent_value: float,
    correct_value: float,
    distractors: list[tuple[str, str]],
) -> None:
    question_text = extract_question_text(serialize_xml(root))
    unit_label = _extract_context_unit(question_text)
    percent_label = _extract_percentage_label(question_text, choice_nodes, correct_id)
    interaction = find_first_by_tag_name(root, "qti-choice-interaction", "choiceInteraction")
    if interaction is None:
        return

    prompt = find_first_by_tag_name(interaction, "qti-prompt", "prompt")
    if prompt is None:
        prompt = ET.Element("qti-prompt")
        interaction.insert(0, prompt)
    prompt.text = (
        "¿Cuál de las siguientes afirmaciones describe correctamente el nuevo total?"
        if operation_signature == "percentage_increase_application"
        else "¿Cuál de las siguientes afirmaciones describe correctamente la parte porcentual calculada?"
    )

    item_body = find_first_by_tag_name(root, "qti-item-body", "itemBody")
    if item_body is not None:
        for child in list(item_body):
            if child is interaction:
                continue
            if child.tag.endswith("p"):
                item_body.remove(child)

        narrative = ET.Element("qti-p")
        narrative.text = _build_decision_statement_context(
            operation_signature,
            base_value,
            unit_label,
            percent_label,
        )
        instruction = ET.Element("qti-p")
        instruction.text = _build_decision_statement_instruction(operation_signature)
        children = list(item_body)
        insert_index = children.index(interaction) if interaction in children else len(children)
        item_body.insert(insert_index, narrative)
        item_body.insert(insert_index + 1, instruction)

    distractor_by_identifier: dict[str, tuple[str, str]] = {}
    distractor_iter = iter(distractors)
    for choice in choice_nodes:
        identifier = choice.attrib.get("identifier", "")
        if identifier == correct_id:
            continue
        distractor_by_identifier[identifier] = next(distractor_iter, ("other", choice.text or ""))

    increment_value = _calculate_increment(base_value, percent_value)
    for choice in choice_nodes:
        identifier = choice.attrib.get("identifier", "")
        value = (choice.text or "").strip()
        if not value:
            continue
        if identifier == correct_id:
            if operation_signature == "percentage_increase_application":
                _replace_choice_text(
                    choice,
                    f"Se vendieron {format_number(increment_value)} {unit_label} más que antes, "
                    f"por lo que el total actualizado fue {format_number(correct_value)} {unit_label}.",
                )
            else:
                _replace_choice_text(
                    choice,
                    f"Se afirma que el {percent_label or 'porcentaje solicitado'} de "
                    f"{format_number(base_value)} {unit_label} equivale a "
                    f"{format_number(correct_value)} {unit_label}, que es la parte porcentual pedida.",
                )
            continue
        archetype, distractor_value = distractor_by_identifier.get(identifier, ("other", value))
        _replace_choice_text(
            choice,
            _build_percentage_statement_distractor(
                archetype,
                distractor_value,
                unit_label,
                percent_label,
                increment_value,
                base_value,
                operation_signature,
            ),
        )


def _extract_context_unit(question_text: str) -> str:
    text = re.sub(r"\s+", " ", question_text)
    lowered = text.lower()
    if "$" in text or any(marker in lowered for marker in ("monto", "pesos", "dinero", "presupuesto", "costo", "precio")):
        return "pesos"
    match = re.search(
        r"\d+(?:[.,]\d+)?\s+([a-záéíóúñ]+(?:\s+de\s+[a-záéíóúñ]+){0,3})",
        text.lower(),
    )
    if not match:
        return "unidades"
    candidate = match.group(1).strip()
    candidate = re.sub(r"\b(este|esta|estos|estas|ese|esa|esos|esas|un|una|el|la|los|las)\b\s*", "", candidate).strip()
    candidate = candidate.rstrip(".,;:")
    return candidate or "unidades"


def _extract_percentage_label(question_text: str, choice_nodes: list[ET.Element], correct_id: str) -> str:
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*%", question_text)
    if not match:
        base_value = _extract_base_value(question_text)
        correct_value = _find_numeric_choice(choice_nodes, correct_id)
        if base_value is None or correct_value is None or base_value <= 0:
            return ""
        inferred_percent = ((correct_value - base_value) / base_value) * 100
        if inferred_percent <= 0:
            return ""
        return f"{format_number(round(inferred_percent, 2))} %"
    return f"{match.group(1)} %"


def _extract_base_value(question_text: str) -> float | None:
    candidates = _extract_numeric_values(question_text)
    if not candidates:
        return None
    return max(candidates)


def _extract_base_value_from_context(question_text: str, percent_value: float) -> float | None:
    scored_candidates: list[tuple[int, float]] = []
    for match in re.finditer(NUMBER_PATTERN, question_text):
        value = parse_number(match.group(0))
        if value is None or value == percent_value:
            continue
        start, end = match.span()
        before = question_text[max(0, start - 24) : start].lower()
        after = question_text[end : min(len(question_text), end + 36)].lower()
        if re.match(r"\s*%", after):
            continue

        score = 0
        if re.search(r"^\s*[:\-]?\s*[a-záéíóúñ]+", after):
            score += 4
        if any(
            marker in before
            for marker in (
                "vendieron",
                "venden",
                "despach",
                "registr",
                "report",
                "produj",
                "fabric",
                "almacen",
                "inventario",
                "inicial",
                "base",
                "cantidad de",
            )
        ):
            score += 3
        if any(marker in before for marker in ("día ", "dia ", "paso ", "etapa ", "caso ", "opción ", "opcion ")):
            score -= 6
        if value > percent_value:
            score += 1
        scored_candidates.append((score, value))

    if not scored_candidates:
        return None
    scored_candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return scored_candidates[0][1]


def _calculate_percentage_increase_total(base_value: float, percent_value: float) -> float:
    return round(base_value * (1 + percent_value / 100), 2)


def _calculate_direct_percentage_total(base_value: float, percent_value: float) -> float:
    return round(base_value * (percent_value / 100), 2)


def _calculate_increment(base_value: float, percent_value: float) -> float:
    return round(base_value * percent_value / 100, 2)


def _build_percentage_statement_distractor(
    archetype: str,
    distractor_value: str,
    unit_label: str,
    percent_label: str,
    increment_value: float,
    base_value: float,
    operation_signature: str,
) -> str:
    if operation_signature == "direct_percentage_calculation":
        if archetype == "decimal_shift_low":
            return (
                f"Se afirma que el {percent_label or 'porcentaje solicitado'} de "
                f"{format_number(base_value)} {unit_label} es {distractor_value} {unit_label}, "
                "como si el porcentaje se hubiera interpretado como un decimal diez veces menor de lo debido."
            )
        if archetype == "ten_percent_anchor":
            return (
                f"Se afirma que el {percent_label or 'porcentaje solicitado'} de "
                f"{format_number(base_value)} {unit_label} es {distractor_value} {unit_label}, "
                "pero ese valor corresponde a quedarse solo con un 10 % de la base."
            )
        if archetype == "divide_by_percent_number":
            return (
                f"Se afirma que el {percent_label or 'porcentaje solicitado'} de "
                f"{format_number(base_value)} {unit_label} es {distractor_value} {unit_label}, "
                "como si bastara dividir la cantidad base por el número del porcentaje."
            )
        if archetype == "base_only":
            return (
                f"Se afirma que el {percent_label or 'porcentaje solicitado'} de "
                f"{format_number(base_value)} {unit_label} es {distractor_value} {unit_label}, "
                "pero en realidad solo se repitió la cantidad base sin calcular la parte porcentual."
            )
        return f"La parte porcentual se estimó como {distractor_value} {unit_label}."

    if archetype == "increment_only":
        return (
            f"Se calculó que el aumento equivalía a {format_number(increment_value)} {unit_label} "
            f"y ese valor se tomó como total final: {distractor_value} {unit_label}."
        )
    if archetype == "base_plus_increment":
        return (
            f"Se agregaron {percent_label or 'esos puntos porcentuales'} directamente a "
            f"{format_number(base_value)} {unit_label} y se reportó un total de {distractor_value} {unit_label}."
        )
    if archetype == "gross_overestimate":
        return (
            f"Se volvió a sumar el aumento calculado y por eso el total registrado fue {distractor_value} {unit_label}."
        )
    if archetype == "base_only":
        return f"No hubo cambio relevante y el total actualizado siguió siendo {distractor_value} {unit_label}."
    if archetype == "decrease_instead":
        return f"El total actualizado bajó hasta {distractor_value} {unit_label}."
    return f"El total actualizado sería {distractor_value} {unit_label}."


def _build_decision_statement_context(
    operation_signature: str,
    base_value: float,
    unit_label: str,
    percent_label: str,
) -> str:
    if operation_signature == "direct_percentage_calculation":
        if percent_label:
            return (
                f"En un registro breve se reportaron {format_number(base_value)} {unit_label}. "
                f"Se pidió calcular el {percent_label} de esa cantidad."
            )
        return (
            f"En un registro breve se reportaron {format_number(base_value)} {unit_label}. "
            "Se pidió calcular el porcentaje solicitado de esa cantidad."
        )
    if percent_label:
        return (
            f"En un registro breve se reportaron {format_number(base_value)} {unit_label}. "
            f"Luego se estimó un aumento de {percent_label} respecto de esa cantidad."
        )
    return (
        f"En un registro breve se reportaron {format_number(base_value)} {unit_label}. "
        "Luego se estimó un aumento porcentual respecto de esa cantidad."
    )


def _build_decision_statement_instruction(operation_signature: str) -> str:
    if operation_signature == "direct_percentage_calculation":
        return "Selecciona la afirmación que interpreta correctamente el porcentaje calculado sobre esa cantidad."
    return "Selecciona la afirmación que interpreta correctamente el aumento porcentual aplicado a esa cantidad."


def _replace_choice_text(choice: ET.Element, text: str) -> None:
    for child in list(choice):
        choice.remove(child)
    choice.text = text


def _extract_numeric_values(text: str) -> list[float]:
    values: list[float] = []
    for match in re.finditer(NUMBER_PATTERN, text.replace("\xa0", " ")):
        value = parse_number(match.group(0))
        if value is not None:
            values.append(value)
    return values


def _build_successive_change_summary(question_text: str) -> str:
    text = re.sub(r"\s+", " ", question_text)
    percent_matches = list(re.finditer(r"(\d+(?:[.,]\d+)?)\s*%", text))
    if len(percent_matches) < 2:
        return ""
    percents = [match.group(1) for match in percent_matches[:2]]
    numbers = [
        match.group(0).replace(" ", "")
        for match in re.finditer(r"\d{1,3}(?:[\s\u00a0]\d{3})*(?:[.,]\d+)?|\d+(?:[.,]\d+)?", text)
    ]
    base_candidates = [value for value in numbers if value not in percents]
    base = max(base_candidates, key=lambda value: len(value.replace(".", "").replace(",", "")), default="")
    if not base:
        return ""
    first_sign = _infer_percentage_sign(text, percent_matches[0].start())
    second_sign = _infer_percentage_sign(text, percent_matches[1].start())
    return f"Registro de cambios: valor inicial = {base}; cambio 1 = {first_sign}{percents[0]}%; cambio 2 = {second_sign}{percents[1]}%."


def _build_successive_change_narrative(question_text: str) -> str:
    text = re.sub(r"\s+", " ", question_text)
    percent_matches = list(re.finditer(r"(\d+(?:[.,]\d+)?)\s*%", text))
    if len(percent_matches) < 2:
        return ""
    percents = [match.group(1) for match in percent_matches[:2]]
    numbers = [
        match.group(0).replace(" ", "")
        for match in re.finditer(r"\d{1,3}(?:[\s\u00a0]\d{3})*(?:[.,]\d+)?|\d+(?:[.,]\d+)?", text)
    ]
    base_candidates = [value for value in numbers if value not in percents]
    base = max(base_candidates, key=lambda value: len(value.replace(".", "").replace(",", "")), default="")
    if not base:
        return ""

    first_sign = _infer_percentage_sign(text, percent_matches[0].start())
    second_sign = _infer_percentage_sign(text, percent_matches[1].start())
    first_action = "aumentó" if first_sign == "+" else "disminuyó"
    second_action = "aumentó" if second_sign == "+" else "disminuyó"
    currency = "pesos" if any(token in text.lower() for token in ("$", "precio", "pesos")) else "unidades"
    return (
        f"Un valor inicial de {base} {currency} {first_action} un {percents[0]} % "
        f"y luego {second_action} un {percents[1]} % sobre el resultado anterior."
    )


def _infer_percentage_sign(text: str, position: int) -> str:
    window = text[max(0, position - 80) : min(len(text), position + 40)].lower()
    negative_markers = ("dismin", "rebaj", "descuent", "caída", "caida", "pérdida", "perdida")
    positive_markers = ("aument", "increment", "sub", "gan", "recargo")
    if any(marker in window for marker in negative_markers):
        return "-"
    if any(marker in window for marker in positive_markers):
        return "+"
    return "+"
