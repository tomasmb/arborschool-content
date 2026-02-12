"""Atom coverage analysis service.

Computes coverage dynamically from:
- Standards JSON (expected coverage map)
- Atoms JSON (which standards each atom maps to)
- metadata_tags.json files across tests (question-to-atom links)

Logic derived from docs/analysis/analisis_cobertura_atomos.md but
computed on the fly rather than hardcoded.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import Any

from api.schemas.atom_models import (
    AtomQuestionCoverage,
    CoverageAnalysisResult,
    OverlapCandidate,
    StandardCoverageItem,
)
from app.utils.paths import (
    PRUEBAS_FINALIZADAS_DIR,
    get_atoms_file,
    get_standards_file,
)

logger = logging.getLogger(__name__)


def load_question_to_atom_map() -> dict[str, set[str]]:
    """Scan metadata_tags.json files to build atom -> questions map.

    Returns:
        Dict mapping atom_id -> set of question identifiers.
    """
    atom_questions: dict[str, set[str]] = defaultdict(set)
    if not PRUEBAS_FINALIZADAS_DIR.exists():
        return atom_questions

    for test_dir in sorted(PRUEBAS_FINALIZADAS_DIR.iterdir()):
        if not test_dir.is_dir():
            continue
        qti_dir = test_dir / "qti"
        if not qti_dir.exists():
            continue
        for q_dir in sorted(qti_dir.iterdir()):
            if not q_dir.is_dir():
                continue
            meta_path = q_dir / "metadata_tags.json"
            if not meta_path.exists():
                continue
            try:
                with open(meta_path, encoding="utf-8") as f:
                    meta = json.load(f)
                for entry in meta.get("selected_atoms", []):
                    atom_id = (
                        entry.get("atom_id")
                        if isinstance(entry, dict)
                        else entry
                    )
                    if atom_id:
                        q_label = f"{test_dir.name}/{q_dir.name}"
                        atom_questions[atom_id].add(q_label)
            except (json.JSONDecodeError, OSError):
                continue
    return atom_questions


def build_prereq_dependents(
    atoms_list: list[dict[str, Any]],
) -> dict[str, set[str]]:
    """Build reverse map: atom_id -> atoms that depend on it."""
    dependents: dict[str, set[str]] = defaultdict(set)
    for atom in atoms_list:
        atom_id = atom.get("id", "")
        for prereq_id in atom.get("prerrequisitos", []):
            dependents[prereq_id].add(atom_id)
    return dependents


# ---------------------------------------------------------------------------
# Public helpers for per-atom coverage (used by subjects router)
# ---------------------------------------------------------------------------


def load_atom_coverage_maps(
    atoms_data: list[dict[str, Any]],
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Load question-to-atom map and prerequisite dependents.

    Convenience wrapper for callers that need both maps.

    Returns:
        Tuple of (atom_questions_map, dependents_map).
    """
    atom_qs = load_question_to_atom_map()
    deps = build_prereq_dependents(atoms_data)
    return atom_qs, deps


def compute_atom_coverage_status(
    atom_id: str,
    direct_count: int,
    deps: dict[str, set[str]],
    atom_qs: dict[str, set[str]],
) -> str:
    """Compute coverage status for a single atom.

    Args:
        atom_id: Atom identifier.
        direct_count: Number of direct PAES questions.
        deps: Dependents map from build_prereq_dependents.
        atom_qs: Questions map from load_question_to_atom_map.

    Returns:
        "direct", "transitive", or "none".
    """
    if direct_count > 0:
        return "direct"
    for dep_id in deps.get(atom_id, set()):
        if dep_id in atom_qs and atom_qs[dep_id]:
            return "transitive"
    return "none"


def _compute_standards_coverage(
    standards_list: list[dict[str, Any]],
    atoms_list: list[dict[str, Any]],
) -> tuple[list[StandardCoverageItem], int, int, int]:
    """Compute per-standard coverage.

    Returns:
        (items, fully, partially, not_covered)
    """
    std_to_atoms: dict[str, list[str]] = defaultdict(list)
    for atom in atoms_list:
        for sid in atom.get("standard_ids", []):
            std_to_atoms[sid].append(atom.get("id", ""))

    items: list[StandardCoverageItem] = []
    fully = partially = none = 0

    for std in standards_list:
        sid = std.get("id", "")
        count = len(std_to_atoms.get(sid, []))
        if count == 0:
            status, none = "none", none + 1
        elif count >= 3:
            status, fully = "full", fully + 1
        else:
            status, partially = "partial", partially + 1
        items.append(StandardCoverageItem(
            standard_id=sid, title=std.get("titulo", ""),
            atom_count=count, coverage_status=status,
        ))

    return items, fully, partially, none


def _compute_question_coverage(
    atoms_list: list[dict[str, Any]],
    atom_questions: dict[str, set[str]],
    dependents_map: dict[str, set[str]],
) -> tuple[list[AtomQuestionCoverage], int, int, int]:
    """Compute per-atom question coverage.

    Returns:
        (items, direct_count, transitive_count, uncovered_count)
    """
    items: list[AtomQuestionCoverage] = []
    direct_count = transitive_count = uncovered_count = 0

    def has_transitive(aid: str) -> bool:
        for dep_id in dependents_map.get(aid, set()):
            if dep_id in atom_questions and atom_questions[dep_id]:
                return True
        return False

    for atom in atoms_list:
        aid = atom.get("id", "")
        direct = len(atom_questions.get(aid, set()))
        transitive = has_transitive(aid)

        if direct > 0:
            status = "direct"
            direct_count += 1
        elif transitive:
            status = "transitive"
            transitive_count += 1
        else:
            status = "none"
            uncovered_count += 1

        items.append(AtomQuestionCoverage(
            atom_id=aid, titulo=atom.get("titulo", ""),
            eje=atom.get("eje", ""),
            direct_questions=direct,
            transitive_coverage=transitive,
            coverage_status=status,
        ))

    return items, direct_count, transitive_count, uncovered_count


def _detect_overlaps(
    atoms_list: list[dict[str, Any]],
) -> list[OverlapCandidate]:
    """Find atom pairs sharing standards with same type."""
    std_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for atom in atoms_list:
        for sid in atom.get("standard_ids", []):
            std_groups[sid].append(atom)

    seen: set[tuple[str, str]] = set()
    candidates: list[OverlapCandidate] = []

    for group in std_groups.values():
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                if a.get("tipo_atomico") != b.get("tipo_atomico"):
                    continue
                pair = tuple(sorted([
                    a.get("id", ""), b.get("id", ""),
                ]))
                if pair in seen:
                    continue
                seen.add(pair)
                shared = list(
                    set(a.get("standard_ids", []))
                    & set(b.get("standard_ids", []))
                )
                candidates.append(OverlapCandidate(
                    atom_a=pair[0], atom_b=pair[1],
                    shared_standards=shared,
                    reason=(
                        f"Same tipo_atomico "
                        f"'{a.get('tipo_atomico')}' "
                        f"under shared standard(s)"
                    ),
                ))

    return candidates


def compute_coverage(subject_id: str) -> CoverageAnalysisResult:
    """Compute full coverage analysis.

    Args:
        subject_id: Subject identifier (e.g. "paes-m1-2026").

    Returns:
        Complete coverage analysis result.
    """
    atoms_path = get_atoms_file("paes_m1_2026")
    standards_path = get_standards_file("paes_m1_2026")

    atoms_list: list[dict[str, Any]] = []
    standards_list: list[dict[str, Any]] = []

    if atoms_path.exists():
        with open(atoms_path, encoding="utf-8") as f:
            atoms_list = json.load(f).get("atoms", [])
    if standards_path.exists():
        with open(standards_path, encoding="utf-8") as f:
            sd = json.load(f)
        standards_list = (
            sd if isinstance(sd, list)
            else sd.get("standards", [])
        )

    atom_qs = load_question_to_atom_map()
    deps = build_prereq_dependents(atoms_list)

    std_items, fully, partial, none_c = (
        _compute_standards_coverage(standards_list, atoms_list)
    )
    q_items, q_direct, q_trans, q_none = (
        _compute_question_coverage(atoms_list, atom_qs, deps)
    )
    overlaps = _detect_overlaps(atoms_list)

    # Distribution stats
    eje_dist: dict[str, int] = defaultdict(int)
    type_dist: dict[str, int] = defaultdict(int)
    for atom in atoms_list:
        eje_dist[atom.get("eje", "unknown")] += 1
        type_dist[atom.get("tipo_atomico", "unknown")] += 1

    return CoverageAnalysisResult(
        total_standards=len(standards_list),
        standards_fully_covered=fully,
        standards_partially_covered=partial,
        standards_not_covered=none_c,
        standards_coverage=std_items,
        total_atoms=len(atoms_list),
        atoms_with_direct_questions=q_direct,
        atoms_with_transitive_coverage=q_trans,
        atoms_without_coverage=q_none,
        atom_question_coverage=q_items,
        overlap_candidates=overlaps,
        eje_distribution=dict(eje_dist),
        type_distribution=dict(type_dist),
    )
