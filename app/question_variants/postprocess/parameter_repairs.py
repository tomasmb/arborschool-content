"""Deterministic repairs for parameter interpretation variants."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from app.question_variants.postprocess.repair_utils import NS, format_number, parse_number, serialize_xml


def repair_parameter_interpretation_prompt(qti_xml: str) -> str:
    try:
        root = ET.fromstring(qti_xml)
    except ET.ParseError:
        return qti_xml

    prompt = root.find(".//qti:qti-prompt", NS) or root.find(".//{*}qti-prompt")
    replacement = "¿Cuál afirmación interpreta correctamente el significado del parámetro o coeficiente presentado en el modelo?"
    if prompt is not None:
        prompt_text = "".join(prompt.itertext()).strip().lower()
        if "cuál afirmación" not in prompt_text and "cual afirmación" not in prompt_text and "cual afirmacion" not in prompt_text:
            prompt.clear()
            prompt.text = replacement
    else:
        paragraphs = root.findall(".//qti:p", NS) or root.findall(".//{*}p")
        for paragraph in reversed(paragraphs):
            paragraph_text = "".join(paragraph.itertext()).strip()
            lowered = paragraph_text.lower()
            if "?" not in paragraph_text:
                continue
            if "cuál afirmación" in lowered or "cual afirmación" in lowered or "cual afirmacion" in lowered:
                break
            paragraph.clear()
            paragraph.text = replacement
            break

    _rescale_rate_reference_choices(root)
    _rewrite_parameter_choices_as_variation(root)
    _rewrite_parameter_choices_as_records(root)
    _ensure_choice_interaction_declarations(root)
    return serialize_xml(root)


def _rescale_rate_reference_choices(root: ET.Element) -> None:
    choice_nodes = root.findall(".//qti:qti-simple-choice", NS) or root.findall(".//{*}qti-simple-choice")
    for choice in choice_nodes:
        if choice.text:
            rescaled = _contextualize_rate_reference_text(choice.text)
            rescaled = _rewrite_comparative_rate_statement(rescaled)
            rescaled = _rewrite_fixed_case_rate_statement(rescaled)
            if rescaled != choice.text:
                choice.text = rescaled


def _contextualize_rate_reference_text(text: str) -> str:
    quantity_first_pattern = re.compile(
        r"^(?P<prefix>.+?)(?P<quantity>\d+(?:[.,]\d+)?)\s+"
        r"(?P<unit>kilómetros|kilometros|kilómetro|kilometro|km|metros|metro|m|kilogramos|kilogramo|kg|mililitros|mililitro|ml|gramos|gramo|g|litros|litro|l)"
        r"(?P<object>(?:\s+de\s+[a-záéíóúñ]+)?(?:\s+[a-záéíóúñ]+){0,4}?)\s+por cada\s+"
        r"(?:(\d+(?:[.,]\d+)?)\s+)?"
        r"(?P<ref_unit>hora|horas|h|metro cuadrado|metros cuadrados|m2|m²|metro|metros|m|kilómetro|kilometro|kilómetros|kilometros|km|kilogramo|kilogramos|kg|litro|litros|l|watt|watts)\b"
        r"(?P<ref_object>(?:\s+de\s+[a-záéíóúñ]+){0,2})",
        flags=re.IGNORECASE,
    )
    grouped_reference_pattern = re.compile(
        r"^Que\s+por cada\s+(?P<ref_amount>\d+(?:[.,]\d+)?)\s+"
        r"(?P<ref_unit>hora|horas|h|metro cuadrado|metros cuadrados|m2|m²|metro|metros|m|kilómetro|kilometro|kilómetros|kilometros|km|kilogramo|kilogramos|kg|litro|litros|l|watt|watts)\b"
        r"(?P<ref_object>(?:\s+de\s+[a-záéíóúñ]+)?(?:\s+[a-záéíóúñ]+){0,4}?),\s+"
        r"(?P<predicate>.+?)\s+(?P<quantity>\d+(?:[.,]\d+)?)\s+"
        r"(?P<unit>kilómetros|kilometros|kilómetro|kilometro|km|metros|metro|m|kilogramos|kilogramo|kg|mililitros|mililitro|ml|gramos|gramo|g|litros|litro|l)"
        r"(?P<object>(?:\s+de\s+[a-záéíóúñ]+)?(?:\s+[a-záéíóúñ]+){0,4}?)\.$",
        flags=re.IGNORECASE,
    )

    match = quantity_first_pattern.search(text)
    if match:
        prefix = (match.group("prefix") or "").strip()
        quantity = match.group("quantity")
        unit = match.group("unit")
        object_phrase = (match.group("object") or "").strip()
        reference_amount = format_number(parse_number(match.group(5) or "1") or 1)
        ref_unit = match.group("ref_unit")
        ref_object = (match.group("ref_object") or "").strip()
        normalized_ref_unit = _normalize_grouped_denominator(ref_unit, int(float(str(reference_amount).replace(",", "."))))
        if prefix.lower().startswith("que "):
            prefix = prefix[4:].strip()
        quantity_phrase = f"{quantity} {unit}"
        if object_phrase:
            quantity_phrase = f"{quantity_phrase} {object_phrase}"
        reference_phrase = f"{reference_amount} {normalized_ref_unit}"
        if ref_object:
            reference_phrase = f"{reference_phrase} {ref_object}"
        rebuilt = f"Que para {reference_phrase}, {prefix} {quantity_phrase}."
        return re.sub(r"\s+", " ", rebuilt).strip().replace(" ,", ",")

    match = grouped_reference_pattern.search(re.sub(r"\s+", " ", text).strip())
    if not match:
        return text

    reference_amount = format_number(parse_number(match.group("ref_amount")) or 1)
    normalized_ref_unit = _normalize_grouped_denominator(
        match.group("ref_unit"),
        int(float(str(reference_amount).replace(",", "."))),
    )
    ref_object = (match.group("ref_object") or "").strip()
    quantity = match.group("quantity")
    unit = match.group("unit")
    object_phrase = (match.group("object") or "").strip()
    quantity_phrase = f"{quantity} {unit}"
    if object_phrase:
        quantity_phrase = f"{quantity_phrase} {object_phrase}"
    reference_phrase = f"{reference_amount} {normalized_ref_unit}"
    if ref_object:
        reference_phrase = f"{reference_phrase} {ref_object}"
    rebuilt = f"Que para {reference_phrase}, {(match.group('predicate') or '').strip()} {quantity_phrase}."
    return re.sub(r"\s+", " ", rebuilt).strip().replace(" ,", ",")


def _rewrite_comparative_rate_statement(text: str) -> str:
    compact_text = re.sub(r"\s+", " ", text).strip()
    pattern = re.compile(
        r"^(?:Que\s+)?Una diferencia de\s+(?P<ref_amount>\d+(?:[.,]\d+)?)\s+"
        r"(?P<ref_unit>kilogramos|kilogramo|kg|metros|metro|m|kilómetros|kilometros|kilómetro|kilometro|km|horas|hora|h)\s+"
        r"en\s+(?P<subject>.+?)\s+implica una diferencia de\s+"
        r"(?P<quantity>\d+(?:[.,]\d+)?)\s+"
        r"(?P<unit>miligramos|miligramo|mg|mililitros|mililitro|ml|gramos|gramo|g|litros|litro|l)\s+"
        r"en\s+(?P<object>sus\s+.+?|las\s+.+?|los\s+.+?)\.$",
        flags=re.IGNORECASE,
    )
    match = pattern.search(compact_text)
    if not match:
        return text

    reference_phrase = _build_single_case_reference(
        match.group("ref_amount"),
        match.group("ref_unit"),
        match.group("subject").strip(),
    )
    quantity_phrase = f"{match.group('quantity')} {match.group('unit')}"
    object_phrase = _normalize_single_case_object(match.group("object").strip())
    rebuilt = f"Que para {reference_phrase}, {object_phrase} es {quantity_phrase}."
    return re.sub(r"\s+", " ", rebuilt).strip()


def _rewrite_parameter_choices_as_records(root: ET.Element) -> None:
    prompt = root.find(".//qti:qti-prompt", NS) or root.find(".//{*}qti-prompt")
    if prompt is not None:
        prompt.clear()
        prompt.text = "¿Cuál registro operativo es coherente con el significado del coeficiente del modelo?"

    choice_nodes = root.findall(".//qti:qti-simple-choice", NS) or root.findall(".//{*}qti-simple-choice")
    for choice in choice_nodes:
        text = (choice.text or "").strip()
        if not text:
            continue
        rewritten = text
        if rewritten.lower().startswith("registro operativo:"):
            rewritten = rewritten.split(":", 1)[1].strip()
        if rewritten.lower().startswith("que "):
            rewritten = rewritten[4:].strip()
        rewritten = _rewrite_fixed_case_rate_statement(rewritten)
        rewritten = rewritten[4:].strip() if rewritten.lower().startswith("que ") else rewritten
        if rewritten.lower().startswith("registro operativo:"):
            choice.text = rewritten
            continue
        rewritten = re.sub(r"^asumir que\s+", "", rewritten, flags=re.IGNORECASE)
        rewritten = rewritten[0].lower() + rewritten[1:] if rewritten else rewritten
        choice.text = f"Registro operativo: {rewritten}"


def _rewrite_fixed_case_rate_statement(text: str) -> str:
    compact_text = re.sub(r"\s+", " ", text).strip()
    pattern = re.compile(
        r"^(?:Que\s+)?para\s+(?P<base>\d+(?:[.,]\d+)?)\s+"
        r"(?P<base_unit>metros cuadrados|metro cuadrado|m2|m²|kilómetros|kilometros|kilómetro|kilometro|km|horas|hora|h|kilogramos|kilogramo|kg|litros|litro|l)"
        r"(?:\s+de)?\s+(?P<subject>.+?),\s+"
        r"(?P<predicate>.+?)\s+"
        r"(?P<quantity>\d+(?:[.,]\d+)?)\s+"
        r"(?P<quantity_unit>mililitros|mililitro|ml|litros|litro|l|gramos|gramo|g|kilogramos|kilogramo|kg|metros|metro|m)"
        r"(?:\s+de\s+[a-záéíóúñ]+(?:\s+[a-záéíóúñ]+){0,3})?\b",
        flags=re.IGNORECASE,
    )
    match = pattern.search(compact_text)
    if not match:
        return text

    base_value = parse_number(match.group("base"))
    quantity_value = parse_number(match.group("quantity"))
    if not base_value or not quantity_value or base_value <= 0:
        return text

    per_unit_value = quantity_value / base_value
    subject = match.group("subject").strip()
    predicate = (match.group("predicate") or "").strip().lower()
    quantity_unit = match.group("quantity_unit")
    if "suministrar" in predicate:
        return (
            f"Que por cada metro cuadrado de {subject}, se deben suministrar "
            f"{format_number(per_unit_value)} {quantity_unit}."
        )
    if "aplicar" in predicate:
        return (
            f"Que por cada metro cuadrado de {subject}, se deben aplicar "
            f"{format_number(per_unit_value)} {quantity_unit}."
        )
    return (
        f"Que por cada metro cuadrado de {subject}, corresponden "
        f"{format_number(per_unit_value)} {quantity_unit}."
    )


def _rewrite_parameter_choices_as_variation(root: ET.Element) -> None:
    context = _extract_parameter_context(root)
    if context is None:
        return
    indep_label, indep_unit, dep_label, dep_unit, coefficient = context
    if coefficient <= 0:
        return

    base_step = _choose_variation_step(coefficient)
    delta_value = coefficient * base_step
    if abs(delta_value - round(delta_value, 2)) > 1e-9:
        return
    delta_text = format_number(round(delta_value, 2))
    step_text = format_number(base_step)
    wrong_scale = format_number(round(delta_value * 10, 2))
    inverse_value = 0.0 if coefficient == 0 else round(base_step / coefficient, 2)
    inverse_text = format_number(inverse_value) if inverse_value > 0 else delta_text

    correct_id = None
    for value in root.findall(".//{*}qti-correct-response/{*}qti-value"):
        candidate = (value.text or "").strip()
        if candidate:
            correct_id = candidate
            break
    if not correct_id:
        return

    prompt = root.find(".//qti:qti-prompt", NS) or root.find(".//{*}qti-prompt")
    if prompt is not None:
        prompt.clear()
        prompt.text = "¿Qué registro operativo es coherente con la variación que representa el coeficiente del modelo?"

    choice_nodes = root.findall(".//qti:qti-simple-choice", NS) or root.findall(".//{*}qti-simple-choice")
    if len(choice_nodes) != 4:
        return

    replacements = {
        correct_id: (
            f"Registro operativo: si {_with_article(indep_label, capitalized=False)} aumenta en {step_text} {indep_unit}, "
            f"{_with_article(dep_label, capitalized=False)} debe aumentar en {delta_text} {dep_unit}."
        )
    }
    distractor_texts = [
        f"Registro operativo: si {_with_article(indep_label, capitalized=False)} aumenta en {step_text} {indep_unit}, {_with_article(dep_label, capitalized=False)} debe aumentar en {wrong_scale} {dep_unit}.",
        f"Registro operativo: si {_with_article(indep_label, capitalized=False)} aumenta en {step_text} {indep_unit}, entonces {_with_article(indep_label, capitalized=False)} equivale a {delta_text} veces {_with_article(dep_label, capitalized=False)}.",
        f"Registro operativo: si {_with_article(dep_label, capitalized=False)} aumenta en {step_text} {dep_unit}, entonces {_with_article(indep_label, capitalized=False)} debe aumentar en {inverse_text} {indep_unit}.",
    ]
    distractor_iter = iter(distractor_texts)
    for choice in choice_nodes:
        identifier = choice.attrib.get("identifier", "")
        if identifier == correct_id:
            choice.text = replacements[identifier]
        else:
            choice.text = next(distractor_iter)


def _extract_parameter_context(root: ET.Element) -> tuple[str, str, str, str, float] | None:
    paragraphs = root.findall(".//qti:p", NS) or root.findall(".//{*}p")
    if not paragraphs:
        return None
    text = re.sub(r"\s+", " ", "".join(paragraphs[0].itertext())).strip()
    normalized = text.lower()
    coefficient_match = re.search(r"([0-9]+(?:[.,][0-9]+)?)\s*$", normalized)
    if not coefficient_match:
        coefficient_match = re.search(r"([0-9]+(?:[.,][0-9]+)?)", normalized)
    coefficient = parse_number(coefficient_match.group(1)) if coefficient_match else None
    if coefficient is None:
        return None

    match = re.search(
        r"determina\s+(?P<dep_label>.+?),\s+en\s+(?P<dep_unit>[^,]+?),.+?seg[uú]n\s+(?P<indep_label>.+?),\s+en\s+(?P<indep_unit>[^,\.]+)",
        normalized,
    )
    if match:
        return (
            _clean_parameter_label(match.group("indep_label")),
            match.group("indep_unit").strip(),
            _clean_parameter_label(match.group("dep_label")),
            match.group("dep_unit").strip(),
            coefficient,
        )

    match = re.search(
        r"para calcular\s+(?P<dep_label>.+?)\s+seg[uú]n\s+(?P<indep_label>.+?)\s+en\s+(?P<indep_unit>[^()]+)",
        normalized,
    )
    if match:
        dep_label = _clean_parameter_label(match.group("dep_label").replace("los ", "").replace("las ", ""))
        dep_unit_match = re.search(r"([a-záéíóúñ]+)\s+de\s+" + re.escape(dep_label), normalized)
        dep_unit = dep_unit_match.group(1) if dep_unit_match else "unidades"
        return (
            _clean_parameter_label(match.group("indep_label")),
            match.group("indep_unit").strip(),
            dep_label,
            dep_unit.strip(),
            coefficient,
        )

    match = re.search(
        r"programa\s+(?P<dep_label>.+?)\s+\(en\s+(?P<dep_unit>[^)]+)\)\s+.+?en funci[oó]n del?\s+(?P<indep_label>.+?)\s+\(en\s+(?P<indep_unit>[^)]+)\)",
        normalized,
    )
    if match:
        return (
            _clean_parameter_label(match.group("indep_label")),
            match.group("indep_unit").strip(),
            _clean_parameter_label(match.group("dep_label")),
            match.group("dep_unit").strip(),
            coefficient,
        )

    match = re.search(
        r"la cantidad\s+[a-z]\s+de\s+(?P<dep_unit>[^,]+?)\s+de\s+(?P<dep_label>.+?)\s+.*?tal que\s+[a-z]\s+es\s+la\s+(?P<indep_label>.+?),\s+en\s+(?P<indep_unit>[^,\.]+)",
        normalized,
    )
    if match:
        return (
            _clean_parameter_label(match.group("indep_label")),
            match.group("indep_unit").strip(),
            _clean_parameter_label(match.group("dep_label")),
            match.group("dep_unit").strip(),
            coefficient,
        )
    return None


def _choose_variation_step(coefficient: float) -> int:
    preferred_steps = (20, 10, 4, 8, 25, 50, 100)
    for step in preferred_steps:
        delta = coefficient * step
        if abs(delta - round(delta, 2)) > 1e-9:
            continue
        rounded = round(delta, 2)
        if rounded >= 1 and abs(rounded - round(rounded)) <= 1e-9:
            return step
    return 10


def _clean_parameter_label(label: str) -> str:
    cleaned = re.sub(r"\b[a-z]\b$", "", label.strip()).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _with_article(label: str, capitalized: bool = True) -> str:
    cleaned = _clean_parameter_label(label)
    lowered = cleaned.lower()
    if lowered.startswith(("el ", "la ", "los ", "las ")):
        return cleaned.capitalize() if capitalized else cleaned
    feminine_markers = ("área", "area", "cantidad", "masa", "dosis", "distancia")
    article = "la" if lowered.startswith(feminine_markers) else "el"
    phrase = f"{article} {cleaned}"
    return phrase.capitalize() if capitalized else phrase


def _ensure_choice_interaction_declarations(root: ET.Element) -> None:
    declaration = root.find(".//qti:qti-response-declaration", NS) or root.find(".//{*}qti-response-declaration")
    interaction = root.find(".//qti:qti-choice-interaction", NS) or root.find(".//{*}qti-choice-interaction")
    if interaction is None:
        return

    response_identifier = (
        interaction.attrib.get("response-identifier")
        or interaction.attrib.get("responseIdentifier")
        or "RESPONSE"
    )
    interaction.attrib["response-identifier" if "response-identifier" in interaction.attrib else "responseIdentifier"] = response_identifier

    if declaration is None:
        return

    declaration.attrib["identifier"] = response_identifier
    declaration.attrib.setdefault("cardinality", "single")
    declaration.attrib.setdefault("baseType", "identifier")


def _build_single_case_reference(ref_amount: str, ref_unit: str, subject: str) -> str:
    lowered = subject.lower()
    if "peso de dos pacientes" in lowered:
        return f"un paciente con {ref_amount} {ref_unit} de peso"
    if lowered.startswith("el peso de "):
        return f"{ref_amount} {ref_unit} de peso de {subject[11:].strip()}"
    return f"{ref_amount} {ref_unit} de {subject}"


def _normalize_single_case_object(object_phrase: str) -> str:
    mapping = {
        "sus dosis": "la dosis correspondiente",
        "las dosis": "la dosis correspondiente",
        "sus consumos": "el consumo correspondiente",
        "sus costos": "el costo correspondiente",
    }
    return mapping.get(object_phrase.lower(), object_phrase)


def _normalize_grouped_denominator(unit: str, scale: int) -> str:
    plural_map = {
        "metro cuadrado": "metros cuadrados",
        "metros cuadrados": "metros cuadrados",
        "m2": "m2",
        "m²": "m²",
        "metro": "metros",
        "metros": "metros",
        "m": "m",
        "kilómetro": "kilómetros",
        "kilometro": "kilometros",
        "kilómetros": "kilómetros",
        "kilometros": "kilometros",
        "km": "km",
        "hora": "horas",
        "horas": "horas",
        "h": "h",
        "kilogramo": "kilogramos",
        "kilogramos": "kilogramos",
        "kg": "kg",
        "litro": "litros",
        "litros": "litros",
        "l": "l",
        "watt": "watts",
        "watts": "watts",
    }
    if scale == 1:
        return unit
    return plural_map.get(unit.lower(), unit)
