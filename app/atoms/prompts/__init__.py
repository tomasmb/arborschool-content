"""Prompt builders for atom generation.

This package contains prompts and guidelines for generating learning atoms.
The prompts follow Gemini best practices from
`docs/gemini-3-pro-prompt-engineering-best-practices.md`.
"""

from __future__ import annotations

from app.atoms.prompts.atom_generation import build_atom_generation_prompt
from app.atoms.prompts.atom_guidelines import ATOM_GRANULARITY_GUIDELINES
from app.atoms.prompts.atom_schema import format_atom_schema_example

__all__ = [
    "ATOM_GRANULARITY_GUIDELINES",
    "build_atom_generation_prompt",
    "format_atom_schema_example",
]
