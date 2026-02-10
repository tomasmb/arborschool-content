"""Data models for the atom fix pipeline.

Defines fix types, actions parsed from validation results, and
results returned after applying LLM-powered fixes.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

# -----------------------------------------------------------------------------
# Fix type taxonomy
# -----------------------------------------------------------------------------


class FixType(str, Enum):
    """Categories of fixes derived from validation issues."""

    SPLIT = "split"
    MERGE = "merge"
    FIX_CONTENT = "fix_content"
    FIX_FIDELITY = "fix_fidelity"
    FIX_COMPLETENESS = "fix_completeness"
    FIX_PREREQUISITES = "fix_prerequisites"
    ADD_MISSING = "add_missing"


# Map fix types to GPT-5.1 reasoning effort levels.
REASONING_EFFORT: dict[FixType, str] = {
    FixType.SPLIT: "high",
    FixType.MERGE: "high",
    FixType.FIX_CONTENT: "medium",
    FixType.FIX_FIDELITY: "medium",
    FixType.FIX_COMPLETENESS: "medium",
    FixType.FIX_PREREQUISITES: "low",
    FixType.ADD_MISSING: "high",
}

# Execution order — deterministic, dependency-safe sequence.
FIX_ORDER: list[FixType] = [
    FixType.FIX_PREREQUISITES,
    FixType.FIX_CONTENT,
    FixType.FIX_FIDELITY,
    FixType.FIX_COMPLETENESS,
    FixType.MERGE,
    FixType.SPLIT,
    FixType.ADD_MISSING,
]


# -----------------------------------------------------------------------------
# Action (input) and Result (output) of a single fix
# -----------------------------------------------------------------------------


@dataclass
class FixAction:
    """A single fix to apply, parsed from a validation result."""

    fix_type: FixType
    standard_id: str
    atom_ids: list[str]
    issues: list[str]
    recommendations: list[str]
    # Extra context for ADD_MISSING: free-text areas to cover.
    missing_areas: list[str] = field(default_factory=list)

    @property
    def reasoning_effort(self) -> str:
        """GPT-5.1 reasoning effort for this fix type."""
        return REASONING_EFFORT[self.fix_type]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict."""
        d = asdict(self)
        d["fix_type"] = self.fix_type.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> FixAction:
        """Deserialize from a dict."""
        return cls(
            fix_type=FixType(d["fix_type"]),
            standard_id=d["standard_id"],
            atom_ids=d["atom_ids"],
            issues=d["issues"],
            recommendations=d["recommendations"],
            missing_areas=d.get("missing_areas", []),
        )


@dataclass
class FixResult:
    """Outcome of executing a single FixAction via LLM."""

    action: FixAction
    success: bool
    # Replacement / new atoms (full dicts matching Atom schema).
    new_atoms: list[dict] = field(default_factory=list)
    # Atom IDs that should be removed from the canonical file.
    removed_atom_ids: list[str] = field(default_factory=list)
    # old_id → [new_id, …] for SPLIT; old_id → [kept_id] for MERGE.
    id_mapping: dict[str, list[str]] = field(default_factory=dict)
    # atom_id → updated prerrequisitos list (cascading changes).
    prerequisite_updates: dict[str, list[str]] = field(
        default_factory=dict,
    )
    # question_id → suggested new atom_id (for SPLIT/MERGE).
    question_mapping_suggestions: dict[str, str] = field(
        default_factory=dict,
    )
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict."""
        return {
            "action": self.action.to_dict(),
            "success": self.success,
            "new_atoms": self.new_atoms,
            "removed_atom_ids": self.removed_atom_ids,
            "id_mapping": self.id_mapping,
            "prerequisite_updates": self.prerequisite_updates,
            "question_mapping_suggestions": self.question_mapping_suggestions,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> FixResult:
        """Deserialize from a dict."""
        return cls(
            action=FixAction.from_dict(d["action"]),
            success=d["success"],
            new_atoms=d.get("new_atoms", []),
            removed_atom_ids=d.get("removed_atom_ids", []),
            id_mapping=d.get("id_mapping", {}),
            prerequisite_updates=d.get("prerequisite_updates", {}),
            question_mapping_suggestions=d.get(
                "question_mapping_suggestions", {},
            ),
            error=d.get("error"),
        )
