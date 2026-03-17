"""Presentation normalization helpers for hard-variant families."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from app.question_variants.contracts.contract_features import infer_presentation_style
from app.question_variants.qti_validation_utils import extract_question_text


def normalize_variant_presentation(
    qti_xml: str,
    operation_signature: str,
    task_form: str,
    selection_load: str = "not_applicable",
) -> str:
    """Rewrite stubborn plain-narrative variants into structured presentation."""
    question_text = extract_question_text(qti_xml)
    profile = {"operation_signature": operation_signature, "task_form": task_form}
    style = infer_presentation_style(question_text, qti_xml, profile)
    if operation_signature not in {"direct_percentage_calculation", "percentage_increase_application"}:
        return qti_xml
    if task_form != "direct_resolution":
        return qti_xml
    if selection_load == "single_given_base":
        return qti_xml

    summary = _build_percentage_summary(qti_xml)
    if not summary and style == "plain_narrative":
        return qti_xml

    try:
        root = ET.fromstring(qti_xml)
    except ET.ParseError:
        return qti_xml

    item_body = root.find(".//{*}qti-item-body")
    if item_body is None:
        item_body = root.find(".//{*}itemBody")
    if item_body is None:
        return qti_xml

    if style == "tabular_context":
        structured_summary = _build_table_data_summary(item_body) or summary
        _replace_table_with_summary(item_body, structured_summary)
        _rewrite_table_mentions(item_body)
        return ET.tostring(root, encoding="unicode")

    if style != "plain_narrative":
        return qti_xml

    first_choice = item_body.find(".//{*}qti-choice-interaction")
    if first_choice is None:
        first_choice = item_body.find(".//{*}choiceInteraction")

    summary_el = ET.Element("qti-p")
    summary_el.text = summary
    if first_choice is not None:
        item_body.insert(list(item_body).index(first_choice), summary_el)
    else:
        item_body.insert(0, summary_el)

    return ET.tostring(root, encoding="unicode")


def _build_percentage_summary(qti_xml: str) -> str:
    text = re.sub(r"\s+", " ", qti_xml)
    percent_match = re.search(r"(\d+(?:[.,]\d+)?)\s*%", text)
    numbers = [match.group(0) for match in re.finditer(r"\d+(?:[.,]\d+)?", text)]
    if not percent_match or len(numbers) < 2:
        return ""
    percent = percent_match.group(1)
    base = next((value for value in numbers if value != percent), "")
    if not base:
        return ""
    return f"Resumen de datos: valor inicial = {base}; aumento porcentual = {percent}%."


def _replace_table_with_summary(item_body: ET.Element, summary: str) -> None:
    table = item_body.find(".//{*}table")
    if table is None:
        table = item_body.find(".//{*}qti-table")
    if table is None:
        return

    summary_el = ET.Element("qti-p")
    summary_el.text = summary or "Resumen de datos disponible en formato estructurado."
    children = list(item_body)
    try:
        index = children.index(table)
    except ValueError:
        index = 0
    item_body.remove(table)
    item_body.insert(index, summary_el)


def _rewrite_table_mentions(item_body: ET.Element) -> None:
    for element in item_body.iter():
        if element.text:
            element.text = element.text.replace(
                "La siguiente tabla muestra el registro de",
                "Se registró la siguiente información sobre",
            ).replace(
                "la siguiente tabla muestra el registro de",
                "se registró la siguiente información sobre",
            ).replace("La siguiente tabla muestra", "Se registró la siguiente información sobre").replace(
                "la siguiente tabla muestra",
                "se registró la siguiente información sobre",
            )


def _build_table_data_summary(item_body: ET.Element) -> str:
    table = item_body.find(".//{*}table")
    if table is None:
        table = item_body.find(".//{*}qti-table")
    if table is None:
        return ""

    headers = [
        re.sub(r"\s+", " ", "".join(cell.itertext())).strip()
        for cell in table.findall(".//{*}th")
        if re.sub(r"\s+", " ", "".join(cell.itertext())).strip()
    ]
    rows = table.findall(".//{*}tr")
    extracted_rows: list[str] = []
    for row in rows:
        cells = [re.sub(r"\s+", " ", "".join(cell.itertext())).strip() for cell in row.findall("./{*}td")]
        if len(cells) < 2:
            continue
        row_label = cells[0].rstrip(":")
        value = cells[1]
        if headers[:2] == ["Día", "Asistentes"]:
            extracted_rows.append(f"Día {row_label}: {value} asistentes")
        else:
            extracted_rows.append(f"{row_label}: {value}")
    if not extracted_rows:
        return ""
    return "Registro de datos: " + "; ".join(extracted_rows) + "."
