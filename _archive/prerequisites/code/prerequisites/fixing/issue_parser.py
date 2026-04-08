"""Parse prerequisite validation results into FixActions.

Reads the single ``validation_result.json`` produced by Phase 4
and converts LLM validation issues into categorised FixActions.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.atoms.fixing.models import FixAction, FixType
from app.prerequisites.constants import PREREQ_ATOM_ID_PATTERN
from app.utils.paths import PREREQ_VALIDATION_FILE

logger = logging.getLogger(__name__)

_ATOM_ID_RE = re.compile(PREREQ_ATOM_ID_PATTERN)


def parse_prereq_validation_results(
    *,
    fix_types: list[FixType] | None = None,
    standard_ids: list[str] | None = None,
) -> list[FixAction]:
    """Parse prereq validation JSON and return a list of FixActions.

    Args:
        fix_types: Optional filter -- keep only these fix types.
        standard_ids: Optional filter -- keep only these standards.

    Returns:
        Flat, de-duplicated list of FixActions.
    """
    if not PREREQ_VALIDATION_FILE.exists():
        logger.warning("No validation file at %s", PREREQ_VALIDATION_FILE)
        return []

    with PREREQ_VALIDATION_FILE.open(encoding="utf-8") as f:
        data = json.load(f)

    actions: list[FixAction] = []

    for llm_result in data.get("llm_validation_results", []):
        std_id: str = llm_result.get("_standard_id", "")
        if standard_ids and std_id not in standard_ids:
            continue
        actions.extend(_parse_single_result(std_id, llm_result))

    if fix_types:
        allowed = set(fix_types)
        actions = [a for a in actions if a.fix_type in allowed]

    actions = _deduplicate(actions)
    logger.info("Parsed %d fix actions from prereq validation", len(actions))
    return actions


_DIMENSION_TO_FIX: dict[str, FixType] = {
    "content_quality": FixType.FIX_CONTENT,
    "fidelity": FixType.FIX_FIDELITY,
    "completeness": FixType.FIX_COMPLETENESS,
    "prerequisites": FixType.FIX_PREREQUISITES,
}


def _parse_single_result(
    standard_id: str,
    data: dict[str, Any],
) -> list[FixAction]:
    """Extract FixActions from one per-standard LLM validation result."""
    actions: list[FixAction] = []

    for atom_eval in data.get("atoms_evaluation", []):
        atom_id: str = atom_eval.get("atom_id", "")
        recs: list[str] = atom_eval.get("recommendations", [])
        actions.extend(
            _classify_atom_issues(standard_id, atom_id, atom_eval, recs),
        )

    coverage = data.get("coverage_analysis", {})
    actions.extend(_parse_coverage(standard_id, coverage))
    return actions


def _classify_atom_issues(
    standard_id: str,
    atom_id: str,
    atom_eval: dict[str, Any],
    recommendations: list[str],
) -> list[FixAction]:
    """Map per-dimension warnings to FixActions for a single atom."""
    actions: list[FixAction] = []

    granularity = atom_eval.get("granularity", {})
    checks = granularity.get("checks", {})
    if checks.get("single_cognitive_intention") is False:
        actions.append(FixAction(
            fix_type=FixType.SPLIT,
            standard_id=standard_id,
            atom_ids=[atom_id],
            issues=granularity.get("issues", []),
            recommendations=recommendations,
        ))
        return actions

    for dimension, fix_type in _DIMENSION_TO_FIX.items():
        dim_data = atom_eval.get(dimension, {})
        if dim_data.get("score") == "warning":
            actions.append(FixAction(
                fix_type=fix_type,
                standard_id=standard_id,
                atom_ids=[atom_id],
                issues=dim_data.get("issues", []),
                recommendations=recommendations,
            ))
    return actions


def _parse_coverage(
    standard_id: str,
    coverage: dict[str, Any],
) -> list[FixAction]:
    """Extract ADD_MISSING and MERGE actions from coverage_analysis."""
    actions: list[FixAction] = []

    missing: list[str] = coverage.get("missing_areas", [])
    if missing:
        actions.append(FixAction(
            fix_type=FixType.ADD_MISSING,
            standard_id=standard_id,
            atom_ids=[],
            issues=[f"Coverage incomplete for: {a}" for a in missing],
            recommendations=[],
            missing_areas=missing,
        ))

    raw_dups: list[Any] = coverage.get("duplication_issues", [])
    if raw_dups:
        texts, explicit_ids = _normalise_dup_issues(raw_dups)
        atom_ids = explicit_ids or _extract_atom_ids(texts)
        actions.append(FixAction(
            fix_type=FixType.MERGE,
            standard_id=standard_id,
            atom_ids=atom_ids,
            issues=texts,
            recommendations=[],
        ))
    return actions


def _normalise_dup_issues(
    raw: list[Any],
) -> tuple[list[str], list[str]]:
    """Convert duplication entries to (text_list, atom_ids)."""
    texts: list[str] = []
    atom_ids: list[str] = []
    for entry in raw:
        if isinstance(entry, str):
            texts.append(entry)
        elif isinstance(entry, dict):
            desc = entry.get("description", "")
            atoms = entry.get("atoms", [])
            if desc:
                texts.append(desc)
            atom_ids.extend(atoms)
    atom_ids = list(dict.fromkeys(atom_ids))
    return texts, atom_ids


def _extract_atom_ids(texts: list[str]) -> list[str]:
    """Pull prereq atom IDs from free-text descriptions."""
    ids: list[str] = []
    for text in texts:
        ids.extend(_ATOM_ID_RE.findall(text))
    return list(dict.fromkeys(ids))


def _deduplicate(actions: list[FixAction]) -> list[FixAction]:
    """Remove exact-duplicate actions (same type + same atom set)."""
    seen: set[str] = set()
    unique: list[FixAction] = []
    for action in actions:
        key = (
            f"{action.fix_type.value}|{action.standard_id}"
            f"|{','.join(sorted(action.atom_ids))}"
        )
        if key not in seen:
            seen.add(key)
            unique.append(action)
    return unique
