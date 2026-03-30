"""Dispatcher for deterministic family-specific QTI repairs."""

from __future__ import annotations

import re

from app.question_variants.postprocess.algebra_repairs import (
    repair_algebraic_model_translation_prompt,
    repair_property_justification_choice,
    repair_symbolic_formula_presentation,
    repair_verbal_formula_distractors,
)
from app.question_variants.postprocess.graph_repairs import repair_graph_representation_mentions
from app.question_variants.postprocess.linear_repairs import repair_linear_equation_variant
from app.question_variants.postprocess.parameter_repairs import repair_parameter_interpretation_prompt
from app.question_variants.postprocess.percentage_repairs import repair_percentage_choices
from app.question_variants.postprocess.proportion_repairs import (
    repair_direct_proportion_value_variant,
    repair_divisibility_condition_variant,
)


def repair_family_specific_qti(
    qti_xml: str,
    contract: dict[str, object],
    metadata: dict[str, object] | None = None,
) -> str:
    """Apply deterministic family-specific repairs before semantic validation."""
    qti_xml = _normalize_math_tag_names(qti_xml)
    operation = str(contract.get("operation_signature") or "")
    task_form = str(contract.get("task_form") or "")
    presentation_style = str(contract.get("presentation_style") or "")
    model_family = str(contract.get("model_family") or "")
    blueprint = ((metadata or {}).get("planning_blueprint", {}) or {}) if metadata else {}
    selected_shape_id = str(blueprint.get("selected_shape_id") or "standard_variant")

    if operation == "graph_interpretation":
        if (
            str(contract.get("graph_rate_frame") or "") == "direct_slope_rate"
            and str(contract.get("response_mode") or "") == "label_selection"
        ):
            selected_shape_id = "single_series_visual_claim"
        return repair_graph_representation_mentions(qti_xml, contract, selected_shape_id)
    if operation == "algebraic_model_translation" and task_form == "representation_interpretation":
        return repair_algebraic_model_translation_prompt(qti_xml, selected_shape_id)
    if operation == "parameter_interpretation" and presentation_style == "direct_parameter_prompt":
        return repair_parameter_interpretation_prompt(qti_xml)
    if operation == "direct_proportion_reasoning" and str(contract.get("proportional_reasoning_mode") or "") == "divisibility_condition":
        return repair_divisibility_condition_variant(qti_xml)
    if operation == "direct_proportion_reasoning":
        return repair_direct_proportion_value_variant(qti_xml)
    if operation == "linear_equation_resolution" and model_family == "quotient_relation":
        return repair_linear_equation_variant(qti_xml)
    if operation in {"direct_percentage_calculation", "percentage_increase_application"}:
        return repair_percentage_choices(
            qti_xml,
            operation,
            [str(item).strip() for item in contract.get("distractor_archetypes", []) if str(item).strip()],
            str(contract.get("percentage_band") or "unknown"),
            selected_shape_id,
        )
    if operation == "algebraic_expression_evaluation" and task_form == "substitute_expression":
        if presentation_style == "symbolic_formula_plus_reference":
            qti_xml = repair_symbolic_formula_presentation(qti_xml)
        if selected_shape_id == "verbal_formula_rule":
            qti_xml = repair_verbal_formula_distractors(qti_xml)
        return qti_xml
    if operation == "property_justification" and str(contract.get("correct_justification_archetype") or "") == "same_base_exponent_difference":
        return repair_property_justification_choice(
            qti_xml,
            str(contract.get("result_property_type") or ""),
            str(contract.get("power_base_family") or ""),
            str(contract.get("argument_polarity") or ""),
        )
    return qti_xml


def _normalize_math_tag_names(qti_xml: str) -> str:
    normalized = re.sub(r"<(/?)qti-math\b", r"<\1math", qti_xml)
    return normalized
