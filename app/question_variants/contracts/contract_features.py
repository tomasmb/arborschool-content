"""Auxiliary construct-contract feature inference helpers."""

from __future__ import annotations

import re
from typing import Any


def infer_claim_archetype(statement: str) -> str:
    lowered = statement.lower().strip()
    if not lowered:
        return ""
    if "la mayor" in lowered or "la principal" in lowered:
        return "largest_subgroup_identification"
    if "se debe realizar la operación" in lowered or "se debe realizar la operacion" in lowered:
        return "operation_setup_claim"
    if "en conjunto" in lowered:
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
    analysis = str(metadata.get("general_analysis", "")).lower()
    markers = (
        "equivale",
        "equivalente",
        "convert",
        "transform",
        "promedio",
        "media aritmética",
        "media aritmetica",
        "desviación",
        "desviacion",
        "cambio de unidad",
        "conversión",
        "conversion",
    )
    hits = sum(1 for marker in markers if marker in text or marker in analysis)
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
    xml_lower = qti_xml.lower()
    math_text = re.sub(r"\s+", "", qti_xml)
    if "<mo>+</mo>" in xml_lower or "+" in math_text:
        return "affine_substitution"
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
        if any(marker in lowered for marker in ("por cada", "por 1", "cada", "directamente proporcional")):
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
        if any(marker in lowered for marker in ("pendiente", "por cada", "tasa")):
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
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*%", question_text.lower())
    if not match:
        return "unknown"
    value = float(match.group(1).replace(",", "."))
    if value <= 20:
        return "small"
    if value <= 80:
        return "medium"
    return "large"


def infer_base_domain(question_text: str, profile: dict[str, bool | str]) -> str:
    if profile["operation_signature"] != "property_justification":
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
