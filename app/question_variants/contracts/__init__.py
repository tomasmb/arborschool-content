"""Contract-related helpers for the hard-variants pipeline."""

from app.question_variants.contracts.family_catalog import get_family_spec_by_id, resolve_family_spec
from app.question_variants.contracts.family_specs import build_family_prompt_rules
from app.question_variants.contracts.preservation_policy import (
    must_preserve_cognitive_action,
    must_preserve_main_skill,
    must_preserve_solution_structure,
)
from app.question_variants.contracts.semantic_guardrails import (
    adds_auxiliary_transformations,
    adds_reference_load,
    breaks_expected_distractor_logic,
    failed_generator_self_check,
    has_numeric_option_scale_outlier,
    has_semantic_contract_drift,
    inflates_data_burden,
    is_insufficiently_different,
    repeats_claim_archetype,
)
from app.question_variants.contracts.structural_profile import build_construct_contract, build_structural_profile

__all__ = [
    "build_construct_contract",
    "build_structural_profile",
    "resolve_family_spec",
    "get_family_spec_by_id",
    "build_family_prompt_rules",
    "must_preserve_cognitive_action",
    "must_preserve_solution_structure",
    "must_preserve_main_skill",
    "failed_generator_self_check",
    "is_insufficiently_different",
    "adds_auxiliary_transformations",
    "breaks_expected_distractor_logic",
    "adds_reference_load",
    "inflates_data_burden",
    "repeats_claim_archetype",
    "has_numeric_option_scale_outlier",
    "has_semantic_contract_drift",
]
