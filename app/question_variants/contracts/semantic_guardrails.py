"""Reusable semantic guardrails for hard-variant validation."""

from __future__ import annotations

import re
from typing import Any

from app.question_variants.qti_validation_utils import surface_similarity


def failed_generator_self_check(metadata: dict[str, Any]) -> str:
    """Return a rejection reason when the generator self-check already flags drift."""
    self_check = metadata.get("generator_self_check", {}) or {}
    guarded_flags = {
        "task_form_preserved": "La variante reconoce que no preservó la forma de tarea.",
        "evidence_mode_preserved": "La variante reconoce que no preservó el modo de evidencia.",
        "cognitive_action_preserved": "La variante reconoce que no preservó la acción cognitiva.",
        "solution_structure_preserved": "La variante reconoce que no preservó la estructura de solución.",
        "auxiliary_transformations_preserved": "La variante reconoce que agregó transformaciones auxiliares.",
        "distractor_logic_preserved": "La variante reconoce que no preservó la lógica de distractores.",
    }
    for field, reason in guarded_flags.items():
        if self_check.get(field) is False:
            return reason
    axes = self_check.get("realized_non_mechanizable_axes", []) or []
    if axes and len([str(axis).strip() for axis in axes if str(axis).strip()]) < 2:
        return "La variante reconoce menos de dos ejes no mecanizables materializados."
    return ""


def is_insufficiently_different(
    source_text: str,
    source_choices: list[str],
    variant_text: str,
    variant_choices: list[str],
    contract: dict[str, Any],
) -> bool:
    """Flag variants that stay too close to the source despite hard-variant goals."""
    text_similarity = surface_similarity(source_text, variant_text)
    choice_similarity = surface_similarity(" | ".join(source_choices), " | ".join(variant_choices))
    task_form = str(contract.get("task_form"))
    operation_signature = str(contract.get("operation_signature"))

    if task_form == "claim_evaluation":
        return text_similarity >= 0.72 and choice_similarity >= 0.58
    if operation_signature == "property_justification":
        return text_similarity >= 0.78 and choice_similarity >= 0.72
    if str(contract.get("solution_structure")) == "direct_single_step":
        return text_similarity >= 0.88 and choice_similarity >= 0.75
    return False


def adds_auxiliary_transformations(source_contract: dict[str, Any], variant_contract: dict[str, Any]) -> bool:
    source_steps = int(source_contract.get("auxiliary_transformations", 0) or 0)
    variant_steps = int(variant_contract.get("auxiliary_transformations", 0) or 0)
    if variant_steps <= source_steps:
        return False
    guarded_structures = {
        "direct_single_step",
        "formula_substitution",
        "representation_reading",
        "property_justification",
        "equation_resolution",
        "data_to_claim_check",
    }
    return str(source_contract.get("solution_structure")) in guarded_structures or source_steps == 0


def breaks_expected_distractor_logic(source_contract: dict[str, Any], variant_contract: dict[str, Any]) -> bool:
    if not source_contract.get("must_preserve_distractor_logic"):
        return False
    source_archetypes = {str(item).strip() for item in source_contract.get("distractor_archetypes", []) if str(item).strip()}
    variant_archetypes = {str(item).strip() for item in variant_contract.get("distractor_archetypes", []) if str(item).strip()}
    return bool(source_archetypes) and not source_archetypes.issubset(variant_archetypes)


def adds_reference_load(source_contract: dict[str, Any], variant_contract: dict[str, Any]) -> bool:
    source_count = int(source_contract.get("reference_relation_count", 0) or 0)
    variant_count = int(variant_contract.get("reference_relation_count", 0) or 0)
    guarded_structures = {"formula_substitution", "equation_resolution", "direct_single_step"}
    return variant_count > source_count and str(source_contract.get("solution_structure")) in guarded_structures


def inflates_data_burden(source_contract: dict[str, Any], variant_contract: dict[str, Any]) -> bool:
    if str(source_contract.get("operation_signature")) != "descriptive_statistics":
        return False
    source_burden = int(source_contract.get("data_burden_score", 0) or 0)
    variant_burden = int(variant_contract.get("data_burden_score", 0) or 0)
    return source_burden > 0 and variant_burden > source_burden + 2


def repeats_claim_archetype(source_contract: dict[str, Any], variant_contract: dict[str, Any]) -> bool:
    if str(source_contract.get("task_form")) == "claim_evaluation":
        source_archetype = str(source_contract.get("correct_claim_archetype") or "")
        variant_archetype = str(variant_contract.get("correct_claim_archetype") or "")
        return bool(source_archetype) and source_archetype == variant_archetype and source_archetype != "other_claim"
    if str(source_contract.get("operation_signature")) == "property_justification":
        source_archetype = str(source_contract.get("correct_justification_archetype") or "")
        variant_archetype = str(variant_contract.get("correct_justification_archetype") or "")
        return bool(source_archetype) and source_archetype == variant_archetype and source_archetype != "other_justification"
    return False


def has_numeric_option_scale_outlier(
    choices: list[str],
    correct_answer: str,
    contract: dict[str, Any],
) -> bool:
    if str(contract.get("operation_signature")) not in {
        "direct_percentage_calculation",
        "percentage_increase_application",
    }:
        return False
    parsed = [_parse_numeric_text(choice) for choice in choices]
    correct = _parse_numeric_text(correct_answer)
    if correct is None or any(value is None for value in parsed):
        return False
    base = abs(correct)
    if base < 1e-9:
        return False
    for value in parsed:
        if abs(value - correct) < 1e-9:
            continue
        ratio = abs(value) / base
        if ratio < 0.2 or ratio > 5.0:
            return True
    return False


def has_equivalent_correct_choice(
    choices: list[str],
    correct_answer: str,
    contract: dict[str, Any],
) -> bool:
    """Detect multiple equivalent correct interpretations expressed with different units."""
    if str(contract.get("operation_signature")) != "parameter_interpretation":
        return False
    normalized_correct = re.sub(r"\s+", "", correct_answer)
    correct_rate = _parse_rate_statement(correct_answer)
    if correct_rate is None:
        return False
    for choice in choices:
        if choice == correct_answer or re.sub(r"\s+", "", choice) == normalized_correct:
            continue
        parsed = _parse_rate_statement(choice)
        if parsed is None:
            continue
        if abs(parsed - correct_rate) <= 1e-12:
            return True
    return False


def has_semantic_contract_drift(source_contract: dict[str, Any], variant_contract: dict[str, Any]) -> str:
    comparisons = {
        "argument_polarity": (
            "La variante cambió la polaridad argumentativa del ítem.",
            {"justify_valid_application", "refute_invalid_argument"},
        ),
        "formula_shape": (
            "La variante cambió la forma algebraica de sustitución del ítem.",
            {"pure_multiplicative_substitution", "affine_substitution"},
        ),
        "model_family": (
            "La variante cambió la familia de modelo matemático del ítem.",
            {
                "quotient_relation",
                "affine_relation",
                "ratio_table_or_unit_rate",
                "direct_proportion_setup",
                "classical_probability",
                "dependent_probability",
                "area_formula",
                "volume_formula",
                "perimeter_formula",
                "pythagorean_relation",
                "rate_parameter_interpretation",
                "intercept_parameter_interpretation",
            },
        ),
        "statistic_target_domain": (
            "La variante cambió el dominio estadístico objetivo del ítem.",
            {"statistic_over_transformed_values", "original_data_from_transformation", "statistic_over_raw_values"},
        ),
    }
    for key, (reason, guarded_values) in comparisons.items():
        source_value = str(source_contract.get(key) or "not_applicable")
        variant_value = str(variant_contract.get(key) or "not_applicable")
        if source_value in guarded_values and source_value != variant_value:
            return reason
    percentage_source = str(source_contract.get("percentage_band") or "not_applicable")
    percentage_variant = str(variant_contract.get("percentage_band") or "not_applicable")
    if percentage_source not in {"not_applicable", "unknown"} and percentage_source != percentage_variant:
        return "La variante cambió la banda de magnitud porcentual del ítem."
    selection_source = str(source_contract.get("selection_load") or "not_applicable")
    selection_variant = str(variant_contract.get("selection_load") or "not_applicable")
    if selection_source != "not_applicable" and selection_source != selection_variant:
        return "La variante cambió la carga de selección de datos del ítem."
    measure_transition_source = str(source_contract.get("measure_transition") or "not_applicable")
    measure_transition_variant = str(variant_contract.get("measure_transition") or "not_applicable")
    if (
        str(source_contract.get("operation_signature")) == "geometry_measurement_application"
        and str(source_contract.get("solution_structure")) in {"direct_single_step", "geometry_formula_application"}
        and measure_transition_source not in {"not_applicable", "generic_measure_to_generic_measure"}
        and measure_transition_source == measure_transition_variant
    ):
        return "La variante repitió intacta la misma transición de medida geométrica de la fuente."
    if (
        str(source_contract.get("operation_signature")) == "parameter_interpretation"
        and str(source_contract.get("presentation_style") or "not_applicable")
        == str(variant_contract.get("presentation_style") or "not_applicable")
        == "direct_parameter_prompt"
    ):
        return "La variante conservó el mismo marco interrogativo directo para interpretar el parámetro."
    if (
        str(source_contract.get("operation_signature")) == "parameter_interpretation"
        and str(variant_contract.get("parameter_statement_form") or "not_applicable") == "comparative_difference_statement"
    ):
        return (
            "La variante reemplazó la interpretación directa del parámetro por una lectura comparativa "
            "de diferencias entre dos casos."
        )
    extremum_source = str(source_contract.get("extremum_polarity") or "not_applicable")
    extremum_variant = str(variant_contract.get("extremum_polarity") or "not_applicable")
    if extremum_source != "not_applicable" and extremum_source != extremum_variant:
        return "La variante cambió la polaridad del objetivo que se debe identificar en la representación."
    family_source = str(source_contract.get("family_id") or "")
    family_variant = str(variant_contract.get("family_id") or "")
    if family_source and family_variant and family_source != family_variant:
        return "La variante cambió la familia estructural del ítem."
    presentation_source = str(source_contract.get("presentation_style") or "not_applicable")
    presentation_variant = str(variant_contract.get("presentation_style") or "not_applicable")
    if (
        (
            str(source_contract.get("task_form")) == "substitute_expression"
            or str(source_contract.get("operation_signature")) in {"direct_percentage_calculation", "percentage_increase_application"}
        )
        and presentation_source not in {"not_applicable", "verbal_formula"}
        and presentation_source == presentation_variant
    ):
        return "La variante conservó el mismo estilo de presentación del problema."
    response_source = str(source_contract.get("response_mode") or "unknown")
    response_variant = str(variant_contract.get("response_mode") or "unknown")
    if (
        str(source_contract.get("operation_signature")) == "graph_interpretation"
        and response_source in {"label_selection", "statement_selection"}
        and response_source != response_variant
    ):
        return "La variante cambió el modo de respuesta del ítem."
    series_source = str(source_contract.get("representation_series_count") or "not_applicable")
    series_variant = str(variant_contract.get("representation_series_count") or "not_applicable")
    if (
        str(source_contract.get("operation_signature")) == "graph_interpretation"
        and series_source == "single_series"
        and series_variant == "multiple_series"
    ):
        return "La variante agregó una segunda serie de datos y convirtió el ítem en una comparación más cargada que la fuente."
    return ""


def _parse_numeric_text(text: str) -> float | None:
    cleaned = (
        text.strip()
        .replace("\xa0", "")
        .replace("%", "")
        .replace("kilómetros", "")
        .replace("kilometros", "")
        .replace("personas", "")
        .replace("pesos", "")
        .replace("minutos", "")
        .replace("segundos", "")
        .replace("ml/h", "")
        .replace("mb/s", "")
        .strip()
    )
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


def _parse_rate_statement(text: str) -> float | None:
    lowered = text.lower().replace("\xa0", " ")
    match = re.search(
        r"(\d+(?:[.,]\d+)?)\s*(kilogramos|kilogramos|kg|gramos|gramo|g|litros|litro|l|mililitros|mililitro|ml)"
        r".*?por cada\s+(\d+(?:[.,]\d+)?)?\s*"
        r"(metro cuadrado|metros cuadrados|m2|m²|hectárea|hectareas|hectáreas|ha|kilogramo|kilogramos|kg|gramo|gramos|g|litro|litros|l|mililitro|mililitros|ml)",
        lowered,
    )
    if not match:
        return None
    numerator_value = float(match.group(1).replace(",", "."))
    numerator_unit = match.group(2)
    denominator_value = float((match.group(3) or "1").replace(",", "."))
    denominator_unit = match.group(4)

    numerator_factor = _unit_factor(numerator_unit)
    denominator_factor = _unit_factor(denominator_unit)
    if numerator_factor is None or denominator_factor is None or denominator_value == 0:
        return None
    normalized_numerator = numerator_value * numerator_factor
    normalized_denominator = denominator_value * denominator_factor
    return normalized_numerator / normalized_denominator


def _unit_factor(unit: str) -> float | None:
    normalized = unit.strip().lower()
    mapping = {
        "kilogramos": 1000.0,
        "kilogramos": 1000.0,
        "kg": 1000.0,
        "gramos": 1.0,
        "gramo": 1.0,
        "g": 1.0,
        "litros": 1000.0,
        "litro": 1000.0,
        "l": 1000.0,
        "mililitros": 1.0,
        "mililitro": 1.0,
        "ml": 1.0,
        "metro cuadrado": 1.0,
        "metros cuadrados": 1.0,
        "m2": 1.0,
        "m²": 1.0,
        "hectárea": 10000.0,
        "hectareas": 10000.0,
        "hectáreas": 10000.0,
        "ha": 10000.0,
    }
    return mapping.get(normalized)
