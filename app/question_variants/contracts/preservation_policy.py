"""Contract-preservation policy for structural validation."""

from __future__ import annotations


def must_preserve_cognitive_action(contract: dict[str, object]) -> bool:
    """Return whether the validator should enforce identical cognitive action."""
    return str(contract.get("cognitive_action")) in {
        "identify_error",
        "interpret_representation",
        "evaluate_claims",
        "substitute_and_compute",
        "interpret_model",
        "apply_probability_model",
        "identify_transformation",
    }


def must_preserve_solution_structure(contract: dict[str, object]) -> bool:
    """Return whether the validator should enforce identical solution structure."""
    return str(contract.get("solution_structure")) in {
        "direct_single_step",
        "representation_reading",
        "data_to_claim_check",
        "error_localization",
        "equation_resolution",
        "model_interpretation",
        "parameter_meaning_interpretation",
        "proportional_setup",
        "probability_counting",
        "isometry_identification",
        "geometry_formula_application",
    }


def must_preserve_main_skill(contract: dict[str, object]) -> bool:
    """Return whether the validator should preserve the source main skill tag."""
    return str(contract.get("main_skill")) in {"ARG", "REP"}
