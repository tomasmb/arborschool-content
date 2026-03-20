"""Deterministic repairs for graph/data representation items."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from app.question_variants.postprocess.repair_utils import serialize_xml


def repair_graph_representation_mentions(qti_xml: str, contract: dict[str, object] | None = None) -> str:
    try:
        root = ET.fromstring(qti_xml)
    except ET.ParseError:
        return qti_xml

    lowered = qti_xml.lower()
    has_table = "<table" in lowered or "<qti-table" in lowered
    has_image = any(token in lowered for token in ("<img", "<object", "<qti-object"))
    changed = False
    contract = contract or {}
    if not has_table and not has_image:
        changed = materialize_grouped_series_table(root) or changed
        changed = _materialize_bullet_series_table(root) or changed
        lowered = serialize_xml(root).lower()
        has_table = "<table" in lowered or "<qti-table" in lowered
        has_image = any(token in lowered for token in ("<img", "<object", "<qti-object"))
    if str(contract.get("representation_series_count") or "") == "single_series":
        changed = _collapse_to_single_series_table(root) or changed
    if not has_table or has_image:
        return serialize_xml(root) if changed else qti_xml

    replacements = {
        "gráfico de dispersión": "registro de datos",
        "grafico de dispersion": "registro de datos",
        "gráfico": "registro",
        "grafico": "registro",
        "diagrama": "registro",
        "infografía": "tabla",
        "infografia": "tabla",
        "tabla adjunta": "tabla incluida",
    }
    for element in root.iter():
        if element.text:
            new_text = element.text
            for old, new in replacements.items():
                new_text = re.sub(old, new, new_text, flags=re.IGNORECASE)
            if new_text != element.text:
                element.text = new_text
                changed = True
        if element.tail:
            new_tail = element.tail
            for old, new in replacements.items():
                new_tail = re.sub(old, new, new_tail, flags=re.IGNORECASE)
            if new_tail != element.tail:
                element.tail = new_tail
                changed = True

    return serialize_xml(root) if changed else qti_xml


def materialize_grouped_series_table(root: ET.Element) -> bool:
    item_body = root.find(".//{*}qti-item-body")
    if item_body is None:
        item_body = root.find(".//{*}itemBody")
    if item_body is None:
        return False

    paragraphs = item_body.findall(".//{*}p")
    if not paragraphs:
        return False

    dataset_paragraph = None
    series_headers: tuple[str, str] | None = None
    entries: list[tuple[str, str, str]] = []
    for paragraph in paragraphs:
        text = re.sub(r"\s+", " ", "".join(paragraph.itertext())).strip()
        if not text:
            continue
        header_match = re.search(r"\(([^()]+?)\s*/\s*([^()]+?)\)\s*:\s*", text)
        entry_matches = re.findall(
            r"([A-Za-zÁÉÍÓÚáéíóúñÑ][A-Za-zÁÉÍÓÚáéíóúñÑ ]+?)\s*\(\s*(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)\s*\)",
            text,
        )
        if not header_match or len(entry_matches) < 3:
            continue
        dataset_paragraph = paragraph
        series_headers = (header_match.group(1).strip(), header_match.group(2).strip())
        entries = [
            (re.sub(r"^(?:y|e)\s+", "", label.strip(), flags=re.IGNORECASE), first.strip(), second.strip())
            for label, first, second in entry_matches
        ]
        break

    if dataset_paragraph is None or series_headers is None or not entries:
        return False

    table = ET.Element("table", {"border": "1"})
    header_row = ET.SubElement(table, "tr")
    for heading in ("Categoría", series_headers[0], series_headers[1]):
        cell = ET.SubElement(header_row, "th")
        cell.text = heading
    for label, first, second in entries:
        row = ET.SubElement(table, "tr")
        for value in (label, first, second):
            cell = ET.SubElement(row, "td")
            cell.text = value

    children = list(item_body)
    try:
        index = children.index(dataset_paragraph) + 1
    except ValueError:
        index = len(children)
    item_body.insert(index, table)
    return True


def _materialize_bullet_series_table(root: ET.Element) -> bool:
    item_body = root.find(".//{*}qti-item-body")
    if item_body is None:
        item_body = root.find(".//{*}itemBody")
    if item_body is None:
        return False

    bullet_items = item_body.findall(".//{*}li")
    if len(bullet_items) < 3:
        return False

    entries: list[tuple[str, str, str]] = []
    for item in bullet_items:
        text = re.sub(r"\s+", " ", "".join(item.itertext())).strip()
        match = re.search(
            r"^(?P<label>[^:]+):\s*(?:Matutino|Entrenamiento matutino)\s*(?P<first>\d+(?:[.,]\d+)?)\s*,\s*"
            r"(?:Vespertino|Entrenamiento vespertino)\s*(?P<second>\d+(?:[.,]\d+)?)$",
            text,
            flags=re.IGNORECASE,
        )
        if not match:
            return False
        entries.append((match.group("label").strip(), match.group("first").strip(), match.group("second").strip()))

    table = ET.Element("table", {"border": "1"})
    header_row = ET.SubElement(table, "tr")
    for heading in ("Categoría", "Entrenamiento matutino", "Entrenamiento vespertino"):
        cell = ET.SubElement(header_row, "th")
        cell.text = heading
    for label, first, second in entries:
        row = ET.SubElement(table, "tr")
        for value in (label, first, second):
            cell = ET.SubElement(row, "td")
            cell.text = value

    list_parent = None
    for child in list(item_body):
        if child.tag.endswith("ul"):
            list_parent = child
            break
    if list_parent is None:
        return False

    children = list(item_body)
    try:
        index = children.index(list_parent) + 1
    except ValueError:
        index = len(children)
    item_body.insert(index, table)
    return True


def _collapse_to_single_series_table(root: ET.Element) -> bool:
    table = root.find(".//{*}table")
    if table is None:
        return False

    rows = table.findall(".//{*}tr")
    if len(rows) < 2:
        return False
    header_cells = rows[0].findall("./{*}th")
    if len(header_cells) != 3:
        return False

    chosen_index = 1
    item_body = root.find(".//{*}qti-item-body")
    if item_body is None:
        return False
    full_text = " ".join(re.sub(r"\s+", " ", "".join(node.itertext())).lower() for node in item_body.findall(".//{*}p"))
    if "vespertino" in full_text:
        chosen_index = 2
    elif "matutino" in full_text:
        chosen_index = 1

    header_cells[0].text = "Categoría"
    header_cells[1].text = (header_cells[chosen_index].text or "Valor").strip()
    if len(header_cells) > 2:
        rows[0].remove(header_cells[2])

    for row in rows[1:]:
        cells = row.findall("./{*}td")
        if len(cells) != 3:
            return False
        cells[1].text = (cells[chosen_index].text or "").strip()
        row.remove(cells[2])

    for paragraph in item_body.findall("./{*}p"):
        if paragraph.text and "matutino y vespertino" in paragraph.text.lower():
            paragraph.text = re.sub(
                r"matutino y vespertino",
                "registrados",
                paragraph.text,
                flags=re.IGNORECASE,
            )
        if paragraph.text and "vespertino" in paragraph.text.lower():
            paragraph.text = re.sub(
                r"durante (?:su |el )?entrenamiento vespertino",
                "en el registro",
                paragraph.text,
                flags=re.IGNORECASE,
            )
            paragraph.text = re.sub(
                r"entrenamiento vespertino",
                "registro",
                paragraph.text,
                flags=re.IGNORECASE,
            )
        if paragraph.text and "matutino" in paragraph.text.lower():
            paragraph.text = re.sub(
                r"entrenamiento matutino",
                "registro",
                paragraph.text,
                flags=re.IGNORECASE,
            )
    return True
