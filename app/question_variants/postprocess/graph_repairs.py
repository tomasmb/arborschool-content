"""Deterministic repairs for graph/data representation items."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from app.question_variants.postprocess.repair_utils import (
    find_all_by_tag_name,
    find_first_by_tag_name,
    serialize_xml,
)


def repair_graph_representation_mentions(
    qti_xml: str,
    contract: dict[str, object] | None = None,
    selected_shape_id: str = "standard_variant",
) -> str:
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
    if selected_shape_id == "single_series_visual_claim":
        changed = _rewrite_single_series_claim_choices(root, contract) or changed
    changed = _align_graph_extremum_prompt(root, contract) or changed
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


def _rewrite_single_series_claim_choices(root: ET.Element, contract: dict[str, object] | None) -> bool:
    contract = contract or {}
    if str(contract.get("graph_rate_frame") or "") != "direct_slope_rate":
        return False

    choice_nodes = find_all_by_tag_name(root, "qti-simple-choice", "simpleChoice")
    if len(choice_nodes) != 4:
        return False
    correct_response = find_first_by_tag_name(root, "qti-correct-response", "correctResponse")
    value_node = find_first_by_tag_name(correct_response, "qti-value", "value") if correct_response is not None else None
    correct_identifier = (value_node.text or "").strip() if value_node is not None else ""
    if not correct_identifier:
        return False

    raw_labels = {choice.attrib.get("identifier", ""): _extract_choice_label(choice) for choice in choice_nodes}
    label_candidates = _extract_label_candidates(root)
    if not label_candidates:
        label_candidates = _canonical_label_sequence()
    if _labels_need_canonicalization(label_candidates):
        label_candidates = _canonical_label_sequence()
    steepest_label = _extract_steepest_label(root)
    if not steepest_label:
        steepest_label = raw_labels.get(correct_identifier, "")
    if steepest_label not in label_candidates:
        correct_index = _identifier_to_index(correct_identifier)
        if correct_index is not None:
            steepest_label = label_candidates[correct_index]
    if not steepest_label:
        return False
    _rewrite_direct_slope_graph_description(root, label_candidates, steepest_label)

    extremum = str(contract.get("extremum_polarity") or "maximum_target")
    interaction = find_first_by_tag_name(root, "qti-choice-interaction", "choiceInteraction")
    if interaction is None:
        return False
    prompt = find_first_by_tag_name(interaction, "qti-prompt", "prompt")
    if prompt is None:
        prompt = ET.Element("qti-prompt")
        interaction.insert(0, prompt)
    prompt.text = (
        "¿Cuál de las siguientes afirmaciones describe correctamente al vehículo de mayor rendimiento?"
        if extremum != "minimum_target"
        else "¿Cuál de las siguientes afirmaciones describe correctamente al vehículo de menor rendimiento?"
    )

    ordered_labels = [label for label in label_candidates if label != steepest_label]
    wrong_claims = _build_graph_distractor_claims(root, ordered_labels, steepest_label, extremum)
    wrong_iter = iter(wrong_claims)
    changed = False
    for choice in choice_nodes:
        identifier = choice.attrib.get("identifier", "")
        if identifier == correct_identifier:
            claim = _build_graph_claim(steepest_label, True, extremum)
        else:
            claim = next(wrong_iter, "Todos los vehículos tienen el mismo rendimiento, porque todas las rectas pasan por el origen del plano cartesiano.")
        if "".join(choice.itertext()).strip() != claim:
            for child in list(choice):
                choice.remove(child)
            choice.text = claim
            changed = True
    return changed


def _extract_choice_label(choice: ET.Element) -> str:
    text = re.sub(r"\s+", " ", "".join(choice.itertext())).strip()
    text = re.sub(
        r"^(?P<label>.+?)\s+es\s+el\s+que\s+presenta\s+(?:mayor|menor)\s+rendimiento.*$",
        r"\g<label>",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"^(?P<label>.+?)\s+tiene\s+(?:mayor|menor)\s+rendimiento.*$",
        r"\g<label>",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"^(?P<label>.+?)\s+es\s+el\s+que\s+tiene\s+(?:mayor|menor)\s+rendimiento.*$",
        r"\g<label>",
        text,
        flags=re.IGNORECASE,
    )
    text = text.replace("Vehículo", "Vehículo ").replace("Vehiculo", "Vehículo ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _build_graph_claim(label: str, is_correct: bool, extremum: str) -> str:
    target = "mayor" if extremum != "minimum_target" else "menor"
    slope = "más inclinada" if extremum != "minimum_target" else "menos inclinada"
    if is_correct:
        return (
            f"{label} es el que presenta {target} rendimiento, porque su recta es la {slope} "
            "y eso representa la razón buscada en el gráfico."
        )
    return (
        f"{label} es el que presenta {target} rendimiento, porque su recta sería la que mejor "
        "representa la razón buscada en el gráfico."
    )


def _build_graph_distractor_claims(
    root: ET.Element,
    labels: list[str],
    correct_label: str,
    extremum: str,
) -> list[str]:
    target = "mayor" if extremum != "minimum_target" else "menor"
    claims: list[str] = []
    remaining_labels = [label for label in labels if label and label != correct_label]
    highest_endpoint_label = _extract_highest_endpoint_label(root)
    lowest_slope_label = _extract_lowest_slope_label(root)
    if highest_endpoint_label and highest_endpoint_label in remaining_labels:
        claims.append(
            f"{highest_endpoint_label} es el que presenta {target} rendimiento, porque alcanza el punto más alto "
            "de kilómetros al final del tramo dibujado."
        )
        remaining_labels.remove(highest_endpoint_label)
    if lowest_slope_label and lowest_slope_label in remaining_labels:
        claims.append(
            f"{lowest_slope_label} es el que presenta {target} rendimiento, porque su recta es la menos inclinada en el gráfico."
        )
        remaining_labels.remove(lowest_slope_label)
    if remaining_labels:
        claims.append(
            f"{remaining_labels[0]} es el que presenta {target} rendimiento, porque para la misma cantidad de litros "
            "recorre más kilómetros que los demás."
        )
    claims.append(
        "Todos los vehículos tienen el mismo rendimiento, porque todas las rectas pasan por el origen del plano cartesiano."
    )
    return claims[:3]


def _extract_highest_endpoint_label(root: ET.Element) -> str:
    image_node = root.find(".//{*}img")
    if image_node is None:
        return ""
    alt_text = (image_node.attrib.get("alt") or "").strip()
    if not alt_text:
        return ""
    patterns = (
        r"punto m[aá]s alto[^.]*?pertenece a la recta\s+([A-Za-z][A-Za-z0-9_-]*)",
        r"mayor valor vertical[^.]*?([A-Za-z][A-Za-z0-9_-]*)",
    )
    for pattern in patterns:
        match = re.search(pattern, alt_text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def _extract_lowest_slope_label(root: ET.Element) -> str:
    image_node = root.find(".//{*}img")
    if image_node is None:
        return ""
    alt_text = (image_node.attrib.get("alt") or "").strip()
    if not alt_text:
        return ""
    patterns = (
        r"la menos inclinada es\s+(?:la recta\s+)?([A-Za-z][A-Za-z0-9_-]*)",
        r"([A-Za-z][A-Za-z0-9_-]*)\s+es la de menor pendiente",
    )
    for pattern in patterns:
        match = re.search(pattern, alt_text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def _extract_label_candidates(root: ET.Element) -> list[str]:
    labels: list[str] = []
    image_node = root.find(".//{*}img")
    alt_text = (image_node.attrib.get("alt") or "").strip() if image_node is not None else ""
    if alt_text:
        labels.extend(re.findall(r"\b(?:V|M)\s*_?\d+\b|\b[A-D]\b", alt_text))
    for choice in find_all_by_tag_name(root, "qti-simple-choice", "simpleChoice"):
        label = _extract_choice_label(choice)
        if label:
            labels.append(label)
    unique: list[str] = []
    for label in labels:
        normalized = re.sub(r"\s+", " ", label.replace("_", "")).strip()
        if normalized not in unique:
            unique.append(normalized)
    return unique


def _labels_need_canonicalization(labels: list[str]) -> bool:
    if len(labels) != 4:
        return True
    return any("_" in label or len(label.split()) > 2 for label in labels)


def _canonical_label_sequence() -> list[str]:
    return ["V1", "V2", "V3", "V4"]


def _identifier_to_index(identifier: str) -> int | None:
    suffix_map = {
        "ChoiceA": 0,
        "ChoiceB": 1,
        "ChoiceC": 2,
        "ChoiceD": 3,
    }
    return suffix_map.get(identifier)


def _extract_steepest_label(root: ET.Element) -> str:
    image_node = root.find(".//{*}img")
    if image_node is None:
        return ""
    alt_text = (image_node.attrib.get("alt") or "").strip()
    if not alt_text:
        return ""
    patterns = (
        r"(?:la recta\s+)?([A-Za-z][A-Za-z0-9_-]*)\s+es la m[aá]s inclinada",
        r"(?:la recta\s+)?([A-Za-z][A-Za-z0-9_-]*)\s+tiene la mayor pendiente",
        r"([A-Za-z][A-Za-z0-9_-]*)\s+es la de mayor pendiente",
    )
    for pattern in patterns:
        match = re.search(pattern, alt_text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def _rewrite_direct_slope_graph_description(root: ET.Element, labels: list[str], steepest_label: str) -> None:
    item_body = find_first_by_tag_name(root, "qti-item-body", "itemBody")
    if item_body is None:
        return
    labels = [label for label in labels if label]
    if steepest_label not in labels:
        labels = [steepest_label] + labels
    ordered_labels = [steepest_label] + [label for label in labels if label != steepest_label]
    if len(ordered_labels) < 4:
        return

    vehicle_sentence = ", ".join(ordered_labels[:-1]) + f" y {ordered_labels[-1]}"
    paragraphs = [child for child in list(item_body) if child.tag.split("}")[-1] == "p"]
    if len(paragraphs) >= 2:
        paragraphs[1].text = (
            "En el siguiente gráfico se representa la cantidad de kilómetros recorridos por cuatro vehículos "
            f"{vehicle_sentence} en función de la cantidad de litros de bencina que consumen para recorrerlos."
        )

    image_node = root.find(".//{*}img")
    if image_node is None:
        return
    second_label, third_label, lowest_label = ordered_labels[1], ordered_labels[2], ordered_labels[3]
    image_node.attrib["alt"] = (
        "Plano cartesiano con el eje horizontal etiquetado 'Litros de bencina (L)' y el eje vertical "
        "'Kilómetros recorridos (km)'. Desde el origen parten cuatro rectas crecientes que representan a los "
        f"vehículos {vehicle_sentence}. La recta {steepest_label} es la más inclinada de todas. "
        f"La recta {second_label} tiene una pendiente menor que {steepest_label}, la recta {third_label} "
        f"tiene una pendiente menor que {second_label}, y la recta {lowest_label} es la de menor pendiente. "
        "Todas las rectas cruzan una misma vertical para una cantidad fija de litros, de modo que la recta más "
        "inclinada también alcanza más kilómetros para la misma cantidad de litros consumidos."
    )


def _align_graph_extremum_prompt(root: ET.Element, contract: dict[str, object] | None) -> bool:
    contract = contract or {}
    target = str(contract.get("extremum_polarity") or "not_applicable")
    if target == "not_applicable":
        return False

    changed = False
    replacements = (
        (r"\bmenor\b", "mayor"),
        (r"\bm[ií]nimo\b", "máximo"),
        (r"m[aá]s bajo", "más alto"),
    ) if target == "maximum_target" else (
        (r"\bmayor\b", "menor"),
        (r"\bm[aá]ximo\b", "mínimo"),
        (r"m[aá]s alto", "más bajo"),
    )

    for element in root.iter():
        if element.tag.split("}")[-1] not in {"p", "prompt", "qti-prompt", "simpleChoice", "qti-simple-choice"}:
            continue
        if element.text:
            updated = element.text
            for pattern, replacement in replacements:
                updated = re.sub(pattern, replacement, updated, flags=re.IGNORECASE)
            if updated != element.text:
                element.text = updated
                changed = True
    return changed


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
