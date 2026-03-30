"""Contract-related helpers for the hard-variants pipeline.

Contracts drive the generation prompts (family rules, structural profile,
construct contract). They are NOT used for validation blocking.
"""

from app.question_variants.contracts.family_catalog import (
    get_family_spec_by_id,
    resolve_family_spec,
)
from app.question_variants.contracts.family_specs import build_family_prompt_rules
from app.question_variants.contracts.structural_profile import (
    build_construct_contract,
    build_structural_profile,
)

__all__ = [
    "build_construct_contract",
    "build_structural_profile",
    "resolve_family_spec",
    "get_family_spec_by_id",
    "build_family_prompt_rules",
]
