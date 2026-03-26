"""Auxiliary construct-contract feature inference helpers."""

from __future__ import annotations

import re
from typing import Any


def infer_response_mode(choices: list[str], correct_answer: str) -> str:
    """Infer whether the item expects label selection or statement evaluation."""
    normalized_choices = [choice.strip() for choice in choices if choice.strip()]
    if not normalized_choices:
        return "unknown"
    sentence_like = sum(1 for choice in normalized_choices if len(choice.split()) >= 5 or choice.endswith("."))
    if sentence_like >= max(2, len(normalized_choices) // 2):
        return "statement_selection"
    if all(len(choice.split()) <= 3 for choice in normalized_choices):
        return "label_selection"
    return "mixed_selection"


def infer_claim_archetype(statement: str) -> str:
    lowered = statement.lower().strip()
    if not lowered:
        return ""
    if "la mayor" in lowered or "la principal" in lowered:
        return "largest_subgroup_identification"
    if any(
        marker in lowered
        for marker in (
            "se debe realizar la operación",
            "se debe realizar la operacion",
            "se debe multiplicar",
            "se debe dividir",
            "se debe calcular multiplicando",
        )
    ):
        return "operation_setup_claim"
    if any(marker in lowered for marker in ("en conjunto", "conjunta", "juntas", "sumadas", "al sumar")):
        return "combined_group_comparison"
    if "%" in lowered and ("del total" in lowered or "del agua" in lowered or "del país" in lowered or "del pais" in lowered):
        return "subgroup_percentage_as_total"
    return "other_claim"


def infer_justification_archetype(statement: str, profile: dict[str, bool | str]) -> str:
    if profile["operation_signature"] != "property_justification":
        return "not_applicable"
    lowered = statement.lower()
    if (
        "puede escribirse como" in lowered
        or "se puede escribir como" in lowered
        or "cuadrado de" in lowered
        or "cuadrado perfecto" in lowered and "exponente par" in lowered
    ):
        return "even_exponent_square_form"
    if "potencia positiva de base par" in lowered or "base par" in lowered and "sigue siendo par" in lowered:
        return "even_base_parity_propagation"
    if (
        "exponente negativo" in lowered
        or "recíproco" in lowered
        or "reciproco" in lowered
        or "1/" in lowered
        or "inverso" in lowered
    ):
        return "negative_exponent_reciprocal_range"
    if "entre 0 y 1" in lowered and "sigue" in lowered:
        return "fractional_base_range_preservation"
    if "bases" in lowered and "iguales" in lowered and "resta" in lowered and "exponente" in lowered:
        return "same_base_exponent_difference"
    if "producto" in lowered and "potencias" in lowered:
        return "same_base_exponent_addition"
    return "other_justification"


def infer_auxiliary_transformations(question_text: str, metadata: dict[str, Any]) -> int:
    text = question_text.lower()
    marker_groups = (
        ("unit_equivalence", ("equivale", "equivalente")),
        ("unit_or_representation_change", ("convert", "transform", "cambio de unidad", "conversión", "conversion")),
        ("average_statistic", ("promedio", "media aritmética", "media aritmetica")),
        ("deviation_statistic", ("desviación", "desviacion")),
    )
    hits = 0
    for _, markers in marker_groups:
        if any(marker in text for marker in markers):
            hits += 1
    if hits == 0:
        return 0
    if hits <= 2:
        return 1
    if hits <= 4:
        return 2
    return 3


def infer_reference_relation_count(question_text: str) -> int:
    text = question_text.lower()
    explicit_equalities = len(re.findall(r"\b1\s+[^\s]+\s*=\s*[\d.,]+", text))
    generic_equalities = len(re.findall(r"\b[a-z]\s*=", text))
    equivalence_markers = len(re.findall(r"\bequivale\b|\bequivalente\b", text))
    return explicit_equalities + generic_equalities + equivalence_markers


def infer_data_burden_score(question_text: str, profile: dict[str, bool | str]) -> int:
    if profile["operation_signature"] != "descriptive_statistics":
        return 0
    text = question_text.lower()
    numeric_tokens = len(re.findall(r"\d+(?:[.,]\d+)?", text))
    word_counts = sum(text.count(word) for word in ("dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez"))
    return numeric_tokens + word_counts


def infer_formula_shape(question_text: str, qti_xml: str, profile: dict[str, bool | str]) -> str:
    if profile["task_form"] != "substitute_expression":
        return "not_applicable"
    lowered = f"{question_text} {qti_xml}".lower()
    xml_lower = qti_xml.lower()
    math_text = re.sub(r"\s+", "", qti_xml)
    if "<mo>+</mo>" in xml_lower or "+" in math_text:
        return "affine_substitution"
    verbal_multiplicative_patterns = (
        "se obtiene multiplicando",
        "se obtiene al multiplicar",
        "se calcula multiplicando",
        "se calcula al multiplicar",
        "resulta de multiplicar",
        "es igual a multiplicar",
        "se debe multiplicar",
        "debe multiplicar",
        "se multiplica la cantidad",
        "multiplica la cantidad",
        "la regla establece que se debe multiplicar",
        "se utiliza la siguiente regla de cálculo",
        "se utiliza la siguiente regla de calculo",
        "regla de cálculo",
        "regla de calculo",
        "multiplicando la cantidad",
        "multiplicando el número",
        "multiplicando el numero",
    )
    if any(pattern in lowered for pattern in verbal_multiplicative_patterns):
        return "pure_multiplicative_substitution"
    if (
        any(marker in lowered for marker in ("multiplicar", "se multiplica", "producto", "por "))
        and any(marker in lowered for marker in ("cantidad", "valor inicial", "medida en", "resultado en"))
        and re.search(r"\d+(?:[.,]\d+)?", lowered)
    ):
        return "pure_multiplicative_substitution"
    if "<mo>&#183;</mo>" in xml_lower or "<mo>*</mo>" in xml_lower or "·" in qti_xml:
        return "pure_multiplicative_substitution"
    return "generic_substitution"


def infer_selection_load(question_text: str, qti_xml: str, profile: dict[str, bool | str]) -> str:
    if profile["operation_signature"] not in {"direct_percentage_calculation", "percentage_increase_application"}:
        return "not_applicable"
    lowered = f"{question_text} {qti_xml}".lower()
    has_table = "<table" in lowered or "<qti-table" in lowered
    listed_days = len(re.findall(r"d[ií]a\s*\d+", lowered))
    labeled_entries = len(re.findall(r":\s*\d+(?:[.,]\d+)?", question_text.lower()))
    if has_table or listed_days >= 2 or labeled_entries >= 3:
        return "requires_base_selection"
    return "single_given_base"


def infer_argument_polarity(question_text: str, profile: dict[str, bool | str]) -> str:
    if profile["operation_signature"] != "property_justification":
        return "not_applicable"
    text = question_text.lower()
    if any(marker in text for marker in ("incorrecto", "incorrecta", "error", "razonamiento es incorrecto")):
        return "refute_invalid_argument"
    return "justify_valid_application"


def infer_model_family(question_text: str, qti_xml: str, profile: dict[str, bool | str]) -> str:
    op = str(profile.get("operation_signature") or "")
    if profile["task_form"] != "solve_for_unknown" and op not in {
        "direct_proportion_reasoning",
        "simple_probability",
        "conditional_probability",
        "geometry_measurement_application",
        "parameter_interpretation",
    }:
        return "not_applicable"
    lowered = f"{question_text} {qti_xml}".lower()
    if op == "direct_proportion_reasoning":
        if ":" in lowered or "razón" in lowered or "razon" in lowered or "respectivamente" in lowered:
            return "direct_proportion_setup"
        if any(marker in lowered for marker in ("por cada", "por 1", "directamente proporcional")):
            return "ratio_table_or_unit_rate"
        return "direct_proportion_setup"
    if op in {"simple_probability", "conditional_probability"}:
        if any(marker in lowered for marker in ("sin reemplazo", "sin reposición", "sin reposicion", "dado que", "condicional")):
            return "dependent_probability"
        return "classical_probability"
    if op == "geometry_measurement_application":
        if any(marker in lowered for marker in ("área", "area")):
            return "area_formula"
        if any(marker in lowered for marker in ("volumen", "capacidad")):
            return "volume_formula"
        if any(marker in lowered for marker in ("perímetro", "perimetro")):
            return "perimeter_formula"
        if any(marker in lowered for marker in ("pitágoras", "pitagoras", "hipotenusa", "cateto")):
            return "pythagorean_relation"
        return "geometry_measurement"
    if op == "parameter_interpretation":
        rate_markers = (
            "pendiente",
            "por cada",
            "tasa",
            "aumenta",
            "incrementa",
            "incremento",
            "consume",
            "consumo",
            "se necesitan",
            "se necesita",
            "se deben aplicar",
            "se debe aplicar",
            "costo total",
            "costo",
            "adicional",
            "recorre",
            "distancia",
            "tiempo",
            "horas",
            "kilómetros",
            "kilometros",
            "km",
            "metros cuadrados",
            "m2",
            "m²",
            "kilogramos",
            "kg",
            "litros",
        )
        if any(marker in lowered for marker in rate_markers):
            return "rate_parameter_interpretation"
        if any(marker in lowered for marker in ("intercepto", "valor inicial", "cuando x = 0", "cuando x=0")):
            return "intercept_parameter_interpretation"
        return "generic_parameter_interpretation"
    if "<mfrac" in lowered or "/" in lowered:
        return "quotient_relation"
    if any(marker in lowered for marker in ("-kt", "- k", "+kt", "+ k")):
        return "affine_relation"
    return "generic_linear_relation"


def infer_statistic_target_domain(question_text: str, profile: dict[str, bool | str]) -> str:
    if profile["operation_signature"] != "descriptive_statistics":
        return "not_applicable"
    text = question_text.lower()
    if "datos originales" in text:
        return "original_data_from_transformation"
    if "desviación" in text or "desviacion" in text:
        return "statistic_over_transformed_values"
    return "statistic_over_raw_values"


def infer_percentage_band(question_text: str, profile: dict[str, bool | str]) -> str:
    if profile["operation_signature"] not in {"direct_percentage_calculation", "percentage_increase_application"}:
        return "not_applicable"
    matches = re.findall(r"(\d+(?:[.,]\d+)?)\s*%", question_text.lower())
    if not matches:
        return "unknown"
    value = max(float(match.replace(",", ".")) for match in matches)
    if value <= 30:
        return "small"
    if value <= 80:
        return "medium"
    return "large"


def infer_percentage_change_pattern(question_text: str, profile: dict[str, bool | str]) -> str:
    if profile["operation_signature"] != "percentage_increase_application":
        return "not_applicable"
    text = re.sub(r"\s+", " ", question_text.lower())
    percent_matches = list(re.finditer(r"(\d+(?:[.,]\d+)?)\s*%", text))
    if len(percent_matches) < 2:
        if any(token in text for token in ("rebaj", "descuent", "dismin", "caída", "caida", "pérdida", "perdida")):
            return "single_decrease"
        if any(token in text for token in ("aument", "increment", "alza", "recargo", "sub")):
            return "single_increase"
        return "not_applicable"

    signs: list[str] = []
    for match in percent_matches[:2]:
        window = text[max(0, match.start() - 80) : min(len(text), match.start() + 40)]
        if any(token in window for token in ("rebaj", "descuent", "dismin", "caída", "caida", "pérdida", "perdida")):
            signs.append("decrease")
        elif any(token in window for token in ("aument", "increment", "alza", "recargo", "sub")):
            signs.append("increase")
        else:
            signs.append("unknown")
    percent_values = [match.group(1).replace(",", ".") for match in percent_matches]
    if len(set(percent_values)) == 1 and len(set(signs)) <= 1:
        if signs[0] == "decrease":
            return "single_decrease"
        if signs[0] in {"increase", "unknown"}:
            return "single_increase"
    return "_then_".join(signs)


def infer_base_domain(question_text: str, profile: dict[str, bool | str]) -> str:
    if profile["operation_signature"] not in {"property_justification", "ten_power_zero_composition"}:
        return "not_applicable"
    text = question_text.lower().replace(" ", "")
    fraction_match = re.search(r"\((\d+)\/(\d+)\)\^\(", text)
    if fraction_match:
        numerator = int(fraction_match.group(1))
        denominator = int(fraction_match.group(2))
        if numerator < denominator:
            return "proper_fraction_between_0_and_1"
        return "fraction_greater_than_1"
    decimal_match = re.search(r"(\d+[.,]\d+)\^\(", text)
    if decimal_match:
        value = float(decimal_match.group(1).replace(",", "."))
        if 0 < value < 1:
            return "decimal_between_0_and_1"
        return "decimal_greater_than_1"
    int_match = re.search(r"(\d+)\^\(", text)
    if int_match:
        value = int(int_match.group(1))
        if value > 1:
            return "integer_greater_than_1"
        if value == 1:
            return "one"
    return "generic_base"


def infer_power_base_family(question_text: str, profile: dict[str, bool | str]) -> str:
    if profile["operation_signature"] not in {"property_justification", "ten_power_zero_composition"}:
        return "not_applicable"
    lowered = question_text.lower()
    if any(
        marker in lowered
        for marker in ("[00]", "[000]", "botón", "boton", "botones", "tecla 00", "tecla 000", "grupo de ceros", "grupos de ceros")
    ) and any(marker in lowered for marker in ("[00]", "[000]", "doble cero", "triple cero", "grupo de ceros", "grupos de ceros")) and any(
        marker in lowered for marker in ("10^", "10 ", "10)", "número 1000", "numero 1000")
    ):
        return "ten_power_zero_composition"
    if re.search(r"<msup><mn>(?:2|4|8|16)</mn>", question_text) or re.search(r"\b(?:2|4|8|16)\^", lowered):
        return "binary_power_composition"
    return "generic_power_family"


def infer_result_property_type(question_text: str, profile: dict[str, bool | str]) -> str:
    if profile["operation_signature"] != "property_justification":
        return "not_applicable"
    text = question_text.lower()
    if "número par" in text or "numero par" in text:
        return "even_integer"
    if "número positivo menor que 1" in text or "numero positivo menor que 1" in text:
        return "positive_fraction_less_than_one"
    if "cuadrado perfecto" in text:
        return "perfect_square"
    if "múltiplo de" in text or "multiplo de" in text:
        return "multiple_of_base"
    return "other_result_property"


def infer_measure_transition(question_text: str, profile: dict[str, bool | str]) -> str:
    if profile["operation_signature"] != "geometry_measurement_application":
        return "not_applicable"
    text = question_text.lower()
    target_text = text.split("¿")[-1] if "¿" in text else text
    source_text = text[: len(text) - len(target_text)] if len(target_text) < len(text) else text

    def detect_measure(segment: str) -> str:
        if any(marker in segment for marker in ("perímetro", "perimetro", "circunferencia", "borde")):
            return "perimeter"
        if any(marker in segment for marker in ("área", "area", "superficie")):
            return "area"
        if any(marker in segment for marker in ("volumen", "capacidad")):
            return "volume"
        if any(marker in segment for marker in ("radio", "diámetro", "diametro", "lado", "cateto", "hipotenusa")):
            return "length"
        return "generic_measure"

    source_measure = detect_measure(source_text)
    target_measure = detect_measure(target_text)
    return f"{source_measure}_to_{target_measure}"


def infer_rate_reference_frame(correct_answer: str, profile: dict[str, bool | str]) -> str:
    if profile["operation_signature"] != "parameter_interpretation":
        return "not_applicable"
    lowered = correct_answer.lower()
    if re.search(r"por cada\s+(10|100)\s+", lowered):
        return "grouped_reference"
    if re.search(
        r"por cada\s+(1\s+)?(hora|horas|h|metro cuadrado|metros cuadrados|m2|m²|metro|metros|m|kilómetro|kilometro|kilómetros|kilometros|km|kilogramo|kilogramos|kg|litro|litros|l|watt|watts)\b",
        lowered,
    ):
        return "unit_reference"
    return "other_reference"


def infer_parameter_statement_form(correct_answer: str, profile: dict[str, bool | str]) -> str:
    if profile["operation_signature"] != "parameter_interpretation":
        return "not_applicable"
    lowered = correct_answer.lower()
    if "diferencia de" in lowered and "implica una diferencia" in lowered:
        return "comparative_difference_statement"
    if "por cada" in lowered:
        return "literal_rate_statement"
    if any(marker in lowered for marker in ("para ", "si ", "requiere", "se necesitan", "se necesita", "consume")):
        return "contextual_case_statement"
    if "veces" in lowered:
        return "inverse_relation_statement"
    return "other_statement"


def infer_graph_rate_frame(question_text: str, qti_xml: str, profile: dict[str, bool | str]) -> str:
    if str(profile.get("operation_signature") or "") != "graph_interpretation":
        return "not_applicable"
    lowered_question = question_text.lower().replace("\xa0", " ")
    lowered_xml = qti_xml.lower().replace("\xa0", " ")
    requested = _extract_fraction_units(lowered_xml)
    if requested is None:
        return "not_applicable"
    numerator_unit, denominator_unit = requested
    axes = _extract_graph_axes(lowered_question)
    if axes is None:
        axes = _extract_graph_axes(lowered_xml)
    if axes is None:
        return "not_applicable"
    vertical_unit, horizontal_unit = axes
    if numerator_unit == vertical_unit and denominator_unit == horizontal_unit:
        return "direct_slope_rate"
    if numerator_unit == horizontal_unit and denominator_unit == vertical_unit:
        return "inverse_slope_rate"
    return "not_applicable"


def infer_extremum_polarity(question_text: str, profile: dict[str, bool | str]) -> str:
    op = str(profile.get("operation_signature") or "")
    task_form = str(profile.get("task_form") or "")
    if op != "graph_interpretation" and task_form != "claim_evaluation":
        return "not_applicable"
    lowered = question_text.lower()
    focus_text = lowered.split("¿")[-1] if "¿" in lowered else lowered
    if any(marker in focus_text for marker in ("más débil", "mas debil", "menor", "mínimo", "minimo", "más bajo", "mas bajo")):
        return "minimum_target"
    if any(marker in focus_text for marker in ("más fuerte", "mas fuerte", "mayor", "máximo", "maximo", "más alto", "mas alto")):
        return "maximum_target"
    if op == "graph_interpretation":
        if any(
            marker in lowered
            for marker in (
                "mayor rendimiento",
                "más rendimiento",
                "mas rendimiento",
                "mayor rapidez",
                "más kilómetros por cada",
                "mas kilometros por cada",
            )
        ):
            return "maximum_target"
        if any(
            marker in lowered
            for marker in (
                "menor rendimiento",
                "menos rendimiento",
                "mínimo rendimiento",
                "minimo rendimiento",
                "menos kilómetros por cada",
                "menos kilometros por cada",
            )
        ):
            return "minimum_target"
    return "not_applicable"


def infer_presentation_style(question_text: str, qti_xml: str, profile: dict[str, bool | str]) -> str:
    question_lower = question_text.lower()
    xml_lower = qti_xml.lower()
    lowered = f"{question_lower} {xml_lower}"
    has_table = "<table" in lowered or "<qti-table" in lowered
    has_list = "<ul" in lowered or "<ol" in lowered or "<li" in lowered

    if profile["operation_signature"] == "parameter_interpretation":
        direct_markers = (
            "¿cómo se puede interpretar",
            "¿como se puede interpretar",
            "cuál es la interpretación",
            "cual es la interpretacion",
            "interpretar el número",
            "interpretar el numero",
        )
        if any(marker in lowered for marker in direct_markers):
            return "direct_parameter_prompt"
        if any(marker in lowered for marker in ("cuál afirmación", "cual afirmacion", "qué afirmación", "que afirmacion")):
            return "claim_selection_prompt"
        return "embedded_parameter_prompt"

    if profile["operation_signature"] in {"direct_percentage_calculation", "percentage_increase_application"}:
        if has_table:
            return "tabular_context"
        if has_list or any(
            marker in lowered
            for marker in (
                "registro del caso",
                "desglose",
                "detalle",
                "resumen",
                "composición",
                "composicion",
                "siguientes datos",
                "registro de datos",
                "información sobre",
            )
        ):
            return "structured_text_context"
        return "plain_narrative"

    if profile["task_form"] != "substitute_expression":
        return "not_applicable"

    has_equation = (
        "<mo>=</mo>" in xml_lower
        or "ecuación" in question_lower
        or "ecuacion" in question_lower
        or bool(re.search(r"\b[a-z]\s*=\s*[\d(]", question_lower))
    )
    has_reference = "equivale" in question_lower or "equivalente" in question_lower
    if has_table:
        return "tabular_formula_context"
    if has_equation and has_reference:
        return "symbolic_formula_plus_reference"
    if has_equation:
        return "symbolic_formula_only"
    return "verbal_formula"


def infer_representation_series_count(question_text: str, qti_xml: str, profile: dict[str, bool | str]) -> str:
    if str(profile.get("operation_signature") or "") != "graph_interpretation":
        return "not_applicable"
    lowered = f"{question_text} {qti_xml}".lower()
    dual_series_markers = (
        "matutino",
        "vespertino",
        "serie 1",
        "serie 2",
        "grupo a",
        "grupo b",
        "hombres y mujeres",
        "dos conjuntos",
    )
    if any(marker in lowered for marker in dual_series_markers):
        return "multiple_series"
    return "single_series"


def infer_proportional_reasoning_mode(
    question_text: str,
    correct_answer: str,
    profile: dict[str, bool | str],
) -> str:
    if str(profile.get("operation_signature") or "") != "direct_proportion_reasoning":
        return "not_applicable"
    lowered_question = question_text.lower()
    lowered_answer = correct_answer.lower()
    if any(marker in lowered_question for marker in ("garantiza", "condición", "condicion")) or "divisible" in lowered_answer:
        return "divisibility_condition"
    if any(token in correct_answer for token in ("<mfrac", "/", "÷")):
        return "direct_quotient_expression"
    return "generic_proportional_rule"


def _extract_fraction_units(text: str) -> tuple[str, str] | None:
    compact = re.sub(r"\s+", " ", text)
    math_match = re.search(
        r"<mfrac>.*?(?:<mtext>|<mi>)([^<]+)(?:</mtext>|</mi>).*?(?:<mtext>|<mi>)([^<]+)(?:</mtext>|</mi>).*?</mfrac>",
        compact,
        re.DOTALL,
    )
    if math_match:
        numerator = _normalize_unit_token(math_match.group(1))
        denominator = _normalize_unit_token(math_match.group(2))
        if numerator and denominator:
            return numerator, denominator

    text_match = re.search(
        r"se expresa en [^(]*\(([^()/]+)\s*/\s*([^()]+)\)",
        compact,
    )
    if text_match:
        numerator = _normalize_unit_token(text_match.group(1))
        denominator = _normalize_unit_token(text_match.group(2))
        if numerator and denominator:
            return numerator, denominator

    verbal_match = re.search(
        r"(kil[oó]metros?|km|litros?|horas?|minutos?|p[aá]ginas?)\s+por\s+(litros?|horas?|minutos?|l|h|min)",
        compact,
    )
    if verbal_match:
        numerator = _normalize_unit_token(verbal_match.group(1))
        denominator = _normalize_unit_token(verbal_match.group(2))
        if numerator and denominator:
            return numerator, denominator
    return None


def _extract_graph_axes(text: str) -> tuple[str, str] | None:
    compact = re.sub(r"\s+", " ", text)
    vertical_windows = re.findall(r"([^.]{0,80})\(\s*eje vertical\s*\)", compact)
    horizontal_windows = re.findall(r"([^.]{0,80})\(\s*eje horizontal\s*\)", compact)
    if vertical_windows and horizontal_windows:
        vertical = _normalize_unit_token(vertical_windows[-1])
        horizontal = _normalize_unit_token(horizontal_windows[-1])
        if vertical and horizontal and vertical != horizontal:
            return vertical, horizontal

    vertical_match = re.search(
        r"eje vertical[^.:\n]*?\b(kil[oó]metros?|km|litros?|horas?|minutos?|l|h|min)\b",
        compact,
    )
    horizontal_match = re.search(
        r"eje horizontal[^.:\n]*?\b(kil[oó]metros?|km|litros?|horas?|minutos?|l|h|min)\b",
        compact,
    )
    if vertical_match and horizontal_match:
        vertical = _normalize_unit_token(vertical_match.group(1))
        horizontal = _normalize_unit_token(horizontal_match.group(1))
        if vertical and horizontal and vertical != horizontal:
            return vertical, horizontal

    function_match = re.search(
        r"(?:se representa|se muestra|muestra)\s+(.{0,120}?)\s+en función de(?: la cantidad de)?\s+([^.;]+)",
        compact,
    )
    if function_match:
        vertical = _normalize_unit_token(function_match.group(1))
        horizontal = _normalize_unit_token(function_match.group(2))
        if vertical and horizontal:
            return vertical, horizontal
    return None


def _normalize_unit_token(token: str) -> str:
    normalized = token.strip().lower()
    normalized = re.sub(r"[^a-záéíóúñ/]+", " ", normalized)
    if any(marker in normalized for marker in ("kilómetro", "kilometro", "kilometros", "kilómetros")) or re.search(r"\bkm\b", normalized):
        return "km"
    if any(marker in normalized for marker in ("litro", "litros", "bencina", "gasolina")) or re.search(r"\bl\b", normalized):
        return "l"
    if any(marker in normalized for marker in ("hora", "horas")) or re.search(r"\b(?:h|hr)\b", normalized):
        return "h"
    if any(marker in normalized for marker in ("minuto", "minutos")) or re.search(r"\bmin\b", normalized):
        return "min"
    if any(marker in normalized for marker in ("página", "pagina", "páginas", "paginas")):
        return "pages"
    return ""
