"""Dispatcher for deterministic family-specific QTI repairs."""

from __future__ import annotations

from app.question_variants.postprocess.algebra_repairs import (
    repair_property_justification_choice,
    repair_symbolic_formula_presentation,
)
from app.question_variants.postprocess.graph_repairs import repair_graph_representation_mentions
from app.question_variants.postprocess.linear_repairs import repair_linear_equation_variant
from app.question_variants.postprocess.parameter_repairs import repair_parameter_interpretation_prompt
from app.question_variants.postprocess.percentage_repairs import repair_percentage_choices


def repair_family_specific_qti(qti_xml: str, contract: dict[str, object]) -> str:
    """Apply deterministic family-specific repairs before semantic validation."""
    operation = str(contract.get("operation_signature") or "")
    task_form = str(contract.get("task_form") or "")
    presentation_style = str(contract.get("presentation_style") or "")
    model_family = str(contract.get("model_family") or "")

    if operation == "graph_interpretation":
        return repair_graph_representation_mentions(qti_xml, contract)
    if operation == "parameter_interpretation" and presentation_style == "direct_parameter_prompt":
        return repair_parameter_interpretation_prompt(qti_xml)
    if operation == "linear_equation_resolution" and model_family == "quotient_relation":
        return repair_linear_equation_variant(qti_xml)
    if operation in {"direct_percentage_calculation", "percentage_increase_application"}:
        return repair_percentage_choices(
            qti_xml,
            operation,
            [str(item).strip() for item in contract.get("distractor_archetypes", []) if str(item).strip()],
            str(contract.get("percentage_band") or "unknown"),
        )
    if operation == "algebraic_expression_evaluation" and task_form == "substitute_expression" and presentation_style == "symbolic_formula_plus_reference":
        return repair_symbolic_formula_presentation(qti_xml)
    if operation == "property_justification" and str(contract.get("correct_justification_archetype") or "") == "same_base_exponent_difference":
        return repair_property_justification_choice(qti_xml, str(contract.get("result_property_type") or ""))
    return qti_xml
