"""Reusable semantic guardrails for hard-variant validation."""

from __future__ import annotations

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
    if str(source_contract.get("task_form")) != "claim_evaluation":
        return False
    source_archetype = str(source_contract.get("correct_claim_archetype") or "")
    variant_archetype = str(variant_contract.get("correct_claim_archetype") or "")
    return bool(source_archetype) and source_archetype == variant_archetype and source_archetype != "other_claim"


def has_numeric_option_scale_outlier(choices: list[str], correct_answer: str) -> bool:
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
