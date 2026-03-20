"""Deterministic repairs for proportional-reasoning variants."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from app.question_variants.postprocess.repair_utils import NS, serialize_xml


def repair_divisibility_condition_variant(qti_xml: str) -> str:
    """Strengthen divisibility-condition variants and shift presentation slightly."""
    try:
        root = ET.fromstring(qti_xml)
    except ET.ParseError:
        return qti_xml

    item_body = root.find(".//qti:qti-item-body", NS) or root.find(".//{*}qti-item-body")
    if item_body is None:
        return qti_xml

    context = _extract_divisibility_context(item_body)
    _restructure_divisibility_presentation(item_body)

    choice_nodes = root.findall(".//qti:qti-simple-choice", NS) or root.findall(".//{*}qti-simple-choice")
    if len(choice_nodes) != 4:
        return serialize_xml(root)

    correct_id = _find_correct_identifier(root)
    if not correct_id:
        return serialize_xml(root)

    correct_choice = next((choice for choice in choice_nodes if choice.attrib.get("identifier") == correct_id), None)
    if correct_choice is None:
        return serialize_xml(root)

    parsed = _parse_divisibility_choice("".join(correct_choice.itertext()))
    if parsed is None:
        return serialize_xml(root)
    multiplier, variable, target = parsed

    distractors = _build_divisibility_distractors(multiplier, variable, target)
    if len(distractors) != 3:
        return serialize_xml(root)

    for choice in choice_nodes:
        if choice is correct_choice:
            continue
        _replace_choice_text(choice, distractors.pop(0))
    _annotate_divisibility_choices(choice_nodes, correct_id, multiplier, variable, target, context)

    return serialize_xml(root)


def repair_direct_proportion_value_variant(qti_xml: str) -> str:
    """Make direct-proportion value items less template-like and improve distractors."""
    try:
        root = ET.fromstring(qti_xml)
    except ET.ParseError:
        return qti_xml

    item_body = root.find(".//qti:qti-item-body", NS) or root.find(".//{*}qti-item-body")
    if item_body is None:
        return qti_xml

    _restructure_direct_proportion_presentation(item_body)
    _annotate_numeric_choices(root)
    return serialize_xml(root)


def _restructure_divisibility_presentation(item_body: ET.Element) -> None:
    paragraphs = item_body.findall("./qti:p", NS) or item_body.findall("./{*}p")
    if not paragraphs:
        return

    first_text = _normalize_text("".join(paragraphs[0].itertext()))
    if not first_text.lower().startswith("registro del problema"):
        label = ET.Element("p")
        label.text = "Registro del problema:"
        item_body.insert(0, label)

    question_paragraph = None
    for paragraph in paragraphs:
        text = _normalize_text("".join(paragraph.itertext()))
        if "garantiza" in text.lower() and "?" in text:
            question_paragraph = paragraph
            break
    if question_paragraph is not None:
        question_paragraph.clear()
        question_paragraph.text = "Según el registro, ¿qué control operativo garantiza que se completó una cantidad exacta de bloques?"


def _restructure_direct_proportion_presentation(item_body: ET.Element) -> None:
    paragraphs = item_body.findall("./qti:p", NS) or item_body.findall("./{*}p")
    if not paragraphs:
        return
    choice_interaction = item_body.find(".//qti:qti-choice-interaction", NS) or item_body.find(".//{*}qti-choice-interaction")
    if choice_interaction is None:
        return

    for paragraph in paragraphs:
        text = _normalize_text("".join(paragraph.itertext()))
        if "registro del caso" in text.lower():
            return

    label = ET.Element("p")
    label.text = "Registro del caso:"
    insert_index = list(item_body).index(choice_interaction)
    item_body.insert(0, label)

    prompt = choice_interaction.find("./qti:qti-prompt", NS) or choice_interaction.find("./{*}qti-prompt")
    if prompt is not None:
        prompt.clear()
        prompt.text = "Según el registro, ¿qué cantidad mantiene correctamente la razón indicada?"


def _find_correct_identifier(root: ET.Element) -> str:
    value = root.find(".//qti:qti-correct-response/qti:qti-value", NS)
    if value is None:
        value = root.find(".//{*}qti-correct-response/{*}qti-value")
    return (value.text or "").strip() if value is not None else ""


def _parse_divisibility_choice(choice_text: str) -> tuple[int, str, int] | None:
    compact = _normalize_text(choice_text)
    divisible_pattern = re.compile(
        r"Que\s+(?P<expr>(?:(?P<mult>\d+)\s*[·*]\s*)?(?P<var>[a-z]))\s+es\s+divisible\s+por\s+(?P<target>\d+)\.?",
        flags=re.IGNORECASE,
    )
    division_pattern = re.compile(
        r"Que\s+al\s+dividir\s+(?:(?P<div_mult>\d+)\s*[·*]\s*)?(?P<div_var>[a-z])\s+por\s+(?P<div_target>\d+),\s+el\s+resto\s+sea\s+cero\.?",
        flags=re.IGNORECASE,
    )
    match = divisible_pattern.search(compact)
    if not match:
        match = division_pattern.search(compact)
        if match:
            multiplier = int(match.group("div_mult") or "1")
            variable = match.group("div_var")
            target = int(match.group("div_target"))
            if multiplier <= 0 or target <= 0:
                return None
            return multiplier, variable, target
    if not match:
        return None
    multiplier = int(match.group("mult") or "1")
    variable = match.group("var")
    target = int(match.group("target"))
    if multiplier <= 0 or target <= 0:
        return None
    return multiplier, variable, target


def _build_divisibility_distractors(multiplier: int, variable: str, target: int) -> list[str]:
    candidates: list[str] = []
    quotient = target // multiplier if target % multiplier == 0 else None
    raw_candidates = [
        f"Que {variable} es divisible por {target}.",
        f"Que {multiplier}·{variable} es divisible por {quotient}." if quotient and quotient > 1 else "",
        f"Que {quotient}·{variable} es divisible por {target}." if quotient and quotient > 1 else "",
        f"Que {multiplier}·{variable} es divisible por {target // 2}." if target % 2 == 0 else "",
    ]
    correct_text = f"Que {multiplier}·{variable} es divisible por {target}."
    for candidate in raw_candidates:
        cleaned = candidate.strip()
        if not cleaned or cleaned == correct_text or cleaned in candidates:
            continue
        candidates.append(cleaned)
        if len(candidates) == 3:
            break
    return candidates


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _replace_choice_text(choice: ET.Element, text: str) -> None:
    identifier = choice.attrib.get("identifier")
    for child in list(choice):
        choice.remove(child)
    choice.text = text
    choice.attrib.clear()
    if identifier:
        choice.set("identifier", identifier)


def _annotate_divisibility_choices(
    choice_nodes: list[ET.Element],
    correct_id: str,
    multiplier: int,
    variable: str,
    target: int,
    context: tuple[str, str] | None,
) -> None:
    count_label, derived_unit = context or ("registro", "medida acumulada")
    quotient = target // multiplier if target % multiplier == 0 else target
    for choice in choice_nodes:
        choice_text = _normalize_text("".join(choice.itertext()))
        parsed = _parse_divisibility_choice(choice_text)
        if choice.attrib.get("identifier") == correct_id:
            _replace_choice_text(
                choice,
                (
                    f"La {derived_unit}, {multiplier}·{variable}, "
                    f"debe ser múltiplo de {target}."
                ),
            )
        elif parsed and parsed[0] == 1:
            _replace_choice_text(
                choice,
                f"La cantidad de {count_label}, {variable}, debe ser múltiplo de {target}.",
            )
        elif parsed and parsed[0] == multiplier and parsed[2] == quotient:
            _replace_choice_text(
                choice,
                (
                    f"La {derived_unit}, {multiplier}·{variable}, "
                    f"debe ser múltiplo de {quotient}."
                ),
            )
        else:
            distractor_multiplier = parsed[0] if parsed else quotient
            distractor_target = parsed[2] if parsed else target
            _replace_choice_text(
                choice,
                f"{distractor_multiplier}·{variable} debe ser múltiplo de {distractor_target}.",
            )


def _extract_divisibility_context(item_body: ET.Element) -> tuple[str, str] | None:
    text = _normalize_text(" ".join("".join(paragraph.itertext()) for paragraph in item_body.findall("./{*}p")))
    count_match = re.search(r"cantidad de ([a-záéíóúñ]+)", text, flags=re.IGNORECASE)
    count_label = count_match.group(1) if count_match else "registros"
    derived_match = re.search(r"de \d+(?:[.,]\d+)?\s+([a-záéíóúñ]+)", text, flags=re.IGNORECASE)
    derived_unit = _build_measure_phrase(derived_match.group(1) if derived_match else "")
    return count_label, derived_unit


def _build_measure_phrase(unit: str) -> str:
    normalized = unit.lower()
    if normalized in {"minuto", "minutos", "hora", "horas"}:
        return f"tiempo total en {normalized}"
    if normalized in {"cm", "m", "metros", "metro"}:
        return f"medida total en {normalized}"
    if normalized:
        return f"magnitud acumulada en {normalized}"
    return "magnitud acumulada"


def _annotate_numeric_choices(root: ET.Element) -> None:
    choice_nodes = root.findall(".//qti:qti-simple-choice", NS) or root.findall(".//{*}qti-simple-choice")
    if len(choice_nodes) != 4:
        return
    correct_id = _find_correct_identifier(root)
    if not correct_id:
        return
    values: list[tuple[ET.Element, int | None]] = []
    for choice in choice_nodes:
        parsed = _parse_plain_int("".join(choice.itertext()))
        values.append((choice, parsed))
    correct_value = next((value for choice, value in values if choice.attrib.get("identifier") == correct_id), None)
    if correct_value is None:
        return
    for choice, value in values:
        if value is None:
            continue
        _replace_choice_text(choice, str(value))


def _parse_plain_int(text: str) -> int | None:
    compact = _normalize_text(text).replace("\xa0", "").replace(" ", "")
    if not compact.isdigit():
        return None
    return int(compact)
