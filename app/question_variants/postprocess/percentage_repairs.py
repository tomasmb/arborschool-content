"""Deterministic repairs for percentage-family variants."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from app.question_variants.postprocess.repair_utils import NS, format_number, parse_number
from app.question_variants.qti_validation_utils import extract_question_text


def repair_percentage_choices(
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

    parsed = _extract_percentage_case(extract_question_text(qti_xml), operation_signature)
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

    replacements: dict[str, str] = {}
    next_distractor = iter(distractors)
    correct_text = format_number(correct_value)
    for choice in choice_nodes:
        identifier = choice.attrib.get("identifier", "")
        replacements[identifier] = correct_text if identifier == correct_id else next(next_distractor)
    for choice in choice_nodes:
        choice.text = replacements.get(choice.attrib.get("identifier", ""), choice.text or "")
    return ET.tostring(root, encoding="unicode")


def _find_correct_identifier(root: ET.Element) -> str:
    value = root.find(".//qti:qti-correct-response/qti:qti-value", NS)
    if value is None:
        value = root.find(".//{*}qti-correct-response/{*}qti-value")
    return (value.text or "").strip() if value is not None else ""


def _find_numeric_choice(choice_nodes: list[ET.Element], correct_id: str) -> float | None:
    for choice in choice_nodes:
        if choice.attrib.get("identifier") == correct_id:
            return parse_number(choice.text or "")
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
    return base_candidates[0], percent_value


def _build_percentage_distractors(
    base_value: float,
    percent_value: float,
    correct_value: float,
    operation_signature: str,
    distractor_archetypes: list[str],
    percentage_band: str,
) -> list[str]:
    increment = round(base_value * percent_value / 100)
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
        candidates = [base_value, base_value + increment, increment * 2, correct_value + increment]

    cleaned: list[str] = []
    seen: set[str] = {format_number(correct_value)}
    for value in candidates:
        formatted = format_number(value)
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
        candidates.extend([base_value, base_value + rounded_percent, correct_value + scaled_jump])

    candidates.extend([base_value, base_value - increment, correct_value + max(1, increment)])
    return candidates
