"""Prompt builders for atom generation.

This module re-exports from the prompts package for backward compatibility.
The actual implementation is now split across multiple files in app/atoms/prompts/.

Follows Gemini best practices from
`docs/gemini-3-pro-prompt-engineering-best-practices.md` for `gemini-3-pro-preview`:
- Context first, then instructions
- Explicit output format with JSON schema
- Clear task description
- Negative constraints (what NOT to do)
- Anchor phrases like "Based on the information above..."
"""

from __future__ import annotations

# Re-export everything for backward compatibility
from app.atoms.prompts import (
    ATOM_GRANULARITY_GUIDELINES,
    build_atom_generation_prompt,
    format_atom_schema_example,
)

__all__ = [
    "ATOM_GRANULARITY_GUIDELINES",
    "build_atom_generation_prompt",
    "format_atom_schema_example",
]
