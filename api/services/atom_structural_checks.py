"""Structural checks service for atoms.

Aggregates deterministic validation checks into a single synchronous result.
Reuses existing domain functions -- never reimplements validation logic.

Checks performed:
- Pydantic schema validation (via Atom.model_validate)
- ID-eje cross-check (via validate_atom_id_matches_eje)
- Circular dependency detection (via find_cycles)
- Prerequisite reference validation (all referenced IDs exist)
- Standard reference validation (all standard_ids exist)
- Granularity heuristics (via _validate_atom_granularity)
"""

from __future__ import annotations

import json
import logging
from typing import Any

from api.schemas.atom_models import (
    StructuralCheckItem,
    StructuralChecksResult,
)
from app.atoms.generation import _validate_atom_granularity
from app.atoms.models import Atom, validate_atom_id_matches_eje
from app.atoms.scripts.check_circular_dependencies import find_cycles
from app.utils.paths import get_atoms_file, get_standards_file

logger = logging.getLogger(__name__)


def _load_data(
) -> tuple[list[dict[str, Any]], set[str]] | None:
    """Load atoms list and known standard IDs.

    Returns:
        Tuple of (atoms_list, known_standard_ids) or None if
        the atoms file doesn't exist.
    """
    atoms_path = get_atoms_file("paes_m1_2026")
    if not atoms_path.exists():
        return None

    with open(atoms_path, encoding="utf-8") as f:
        atoms_data = json.load(f)
    atoms_list: list[dict[str, Any]] = atoms_data.get("atoms", [])

    standards_path = get_standards_file("paes_m1_2026")
    known_ids: set[str] = set()
    if standards_path.exists():
        with open(standards_path, encoding="utf-8") as f:
            std_data = json.load(f)
        std_list = (
            std_data if isinstance(std_data, list)
            else std_data.get("standards", [])
        )
        known_ids = {s.get("id", "") for s in std_list}

    return atoms_list, known_ids


def _check_schemas(
    atoms_list: list[dict[str, Any]],
) -> tuple[list[Atom], int, list[StructuralCheckItem]]:
    """Check 1 & 2: Pydantic schema + ID-eje cross-check.

    Returns:
        (validated_atoms, schema_errors, id_eje_errors, issues)
    """
    issues: list[StructuralCheckItem] = []
    validated: list[Atom] = []
    schema_errors = 0

    for idx, atom_dict in enumerate(atoms_list):
        try:
            atom = Atom.model_validate(atom_dict)
            validated.append(atom)
        except Exception as e:
            schema_errors += 1
            atom_id = atom_dict.get("id", f"atom[{idx}]")
            issues.append(StructuralCheckItem(
                atom_id=atom_id, check="schema",
                severity="error", message=str(e)[:200],
            ))

    id_eje_errors = 0
    for atom in validated:
        try:
            validate_atom_id_matches_eje(atom)
        except ValueError as e:
            id_eje_errors += 1
            issues.append(StructuralCheckItem(
                atom_id=atom.id, check="id_eje_mismatch",
                severity="error", message=str(e),
            ))

    return validated, schema_errors, id_eje_errors, issues


def _check_references(
    validated_atoms: list[Atom],
    known_standard_ids: set[str],
) -> tuple[int, int, list[StructuralCheckItem]]:
    """Check 4 & 5: Prerequisite + standard references.

    Returns:
        (missing_prereqs, missing_std_refs, issues)
    """
    issues: list[StructuralCheckItem] = []
    atom_ids = {a.id for a in validated_atoms}
    missing_prereqs = 0
    missing_std_refs = 0

    for atom in validated_atoms:
        for prereq_id in atom.prerrequisitos:
            if prereq_id not in atom_ids:
                missing_prereqs += 1
                issues.append(StructuralCheckItem(
                    atom_id=atom.id,
                    check="missing_prerequisite",
                    severity="error",
                    message=f"Prerequisite '{prereq_id}' "
                    f"does not exist",
                ))

    if known_standard_ids:
        for atom in validated_atoms:
            for std_id in atom.standard_ids:
                if std_id not in known_standard_ids:
                    missing_std_refs += 1
                    issues.append(StructuralCheckItem(
                        atom_id=atom.id,
                        check="missing_standard_ref",
                        severity="error",
                        message=f"Standard '{std_id}' not found"
                        f" in standards file",
                    ))

    return missing_prereqs, missing_std_refs, issues


def _check_granularity(
    validated_atoms: list[Atom],
) -> list[StructuralCheckItem]:
    """Check 6: Granularity heuristics."""
    issues: list[StructuralCheckItem] = []
    warnings = _validate_atom_granularity(validated_atoms)
    for msg in warnings:
        atom_id = None
        if msg.startswith("Atom "):
            parts = msg.split(":", 1)
            atom_id = parts[0].replace("Atom ", "").strip()
        issues.append(StructuralCheckItem(
            atom_id=atom_id, check="granularity",
            severity="warning", message=msg,
        ))
    return issues


def _build_graph_stats(
    validated_atoms: list[Atom],
) -> dict[str, int]:
    """Build prerequisite graph statistics."""
    with_prereqs = sum(
        1 for a in validated_atoms if a.prerrequisitos
    )
    total_edges = sum(
        len(a.prerrequisitos) for a in validated_atoms
    )
    return {
        "atoms_with_prerequisites": with_prereqs,
        "atoms_without_prerequisites": (
            len(validated_atoms) - with_prereqs
        ),
        "total_prerequisite_edges": total_edges,
    }


def run_structural_checks(
    subject_id: str,
) -> StructuralChecksResult:
    """Run all deterministic structural checks on atoms.

    Args:
        subject_id: Subject identifier (e.g. "paes-m1-2026").

    Returns:
        Aggregated result with all issues found.
    """
    loaded = _load_data()
    if loaded is None:
        return StructuralChecksResult(
            passed=False, total_atoms=0,
            issues=[StructuralCheckItem(
                atom_id=None, check="file_exists",
                severity="error",
                message="Atoms file not found",
            )],
        )

    atoms_list, known_standard_ids = loaded
    all_issues: list[StructuralCheckItem] = []

    # Checks 1-2: Schema + ID-eje
    validated, schema_errs, id_eje_errs, schema_issues = (
        _check_schemas(atoms_list)
    )
    all_issues.extend(schema_issues)

    # Check 3: Circular dependencies
    cycles = find_cycles(validated)
    for cycle in cycles:
        all_issues.append(StructuralCheckItem(
            atom_id=cycle[0], check="circular_dependency",
            severity="error",
            message=f"Cycle: {' -> '.join(cycle)}",
        ))

    # Checks 4-5: References
    missing_pre, missing_std, ref_issues = _check_references(
        validated, known_standard_ids,
    )
    all_issues.extend(ref_issues)

    # Check 6: Granularity
    gran_issues = _check_granularity(validated)
    all_issues.extend(gran_issues)

    error_count = sum(
        1 for i in all_issues if i.severity == "error"
    )

    return StructuralChecksResult(
        passed=error_count == 0,
        total_atoms=len(atoms_list),
        schema_errors=schema_errs,
        id_eje_errors=id_eje_errs,
        circular_dependencies=len(cycles),
        missing_prerequisites=missing_pre,
        missing_standard_refs=missing_std,
        granularity_warnings=len(gran_issues),
        issues=all_issues,
        cycles=cycles,
        graph_stats=_build_graph_stats(validated),
    )
