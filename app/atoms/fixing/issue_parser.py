"""Parse validation result JSONs into categorised FixActions.

Reads every ``validation_*.json`` in the validation-results directory,
inspects which dimensions failed for each atom, and produces a flat list
of :class:`FixAction` objects ready for the executor.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from app.atoms.fixing.models import FixAction, FixType
from app.utils.paths import ATOM_VALIDATION_RESULTS_DIR

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------


def parse_all_validation_results(
    results_dir: Path = ATOM_VALIDATION_RESULTS_DIR,
    *,
    fix_types: list[FixType] | None = None,
    standard_ids: list[str] | None = None,
) -> list[FixAction]:
    """Parse every validation JSON and return a list of FixActions.

    Args:
        results_dir: Directory containing ``validation_*.json`` files.
        fix_types: Optional filter — keep only these fix types.
        standard_ids: Optional filter — keep only these standards.

    Returns:
        Flat, de-duplicated list of FixActions.
    """
    actions: list[FixAction] = []

    json_files = sorted(results_dir.glob("validation_*.json"))
    if not json_files:
        logger.warning("No validation result files found in %s", results_dir)
        return actions

    for path in json_files:
        standard_id = _extract_standard_id(path)
        if standard_ids and standard_id not in standard_ids:
            continue

        data = _load_json(path)
        if data is None:
            continue

        file_actions = _parse_single_result(standard_id, data)
        actions.extend(file_actions)

    # Filter by fix type if requested.
    if fix_types:
        allowed = set(fix_types)
        actions = [a for a in actions if a.fix_type in allowed]

    actions = _deduplicate_actions(actions)
    logger.info(
        "Parsed %d fix actions from %d validation files",
        len(actions),
        len(json_files),
    )
    return actions


# -----------------------------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------------------------


def _extract_standard_id(path: Path) -> str:
    """Derive the standard ID from the filename.

    ``validation_M1-ALG-01.json`` → ``M1-ALG-01``
    """
    stem = path.stem  # "validation_M1-ALG-01"
    return stem.replace("validation_", "")


def _load_json(path: Path) -> dict[str, Any] | None:
    """Load a JSON file, returning None on failure."""
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to load %s: %s", path, exc)
        return None


def _parse_single_result(
    standard_id: str,
    data: dict[str, Any],
) -> list[FixAction]:
    """Extract FixActions from one validation result dict."""
    actions: list[FixAction] = []

    # --- Per-atom evaluations ---
    for atom_eval in data.get("atoms_evaluation", []):
        atom_id: str = atom_eval.get("atom_id", "")
        recs: list[str] = atom_eval.get("recommendations", [])
        actions.extend(
            _classify_atom_issues(standard_id, atom_id, atom_eval, recs),
        )

    # --- Coverage analysis (standard-level) ---
    coverage = data.get("coverage_analysis", {})
    actions.extend(
        _parse_coverage(standard_id, coverage),
    )

    return actions


# -----------------------------------------------------------------------------
# Issue → FixType classification
# -----------------------------------------------------------------------------

_DIMENSION_TO_FIX: dict[str, FixType] = {
    "content_quality": FixType.FIX_CONTENT,
    "fidelity": FixType.FIX_FIDELITY,
    "completeness": FixType.FIX_COMPLETENESS,
    "prerequisites": FixType.FIX_PREREQUISITES,
}


def _classify_atom_issues(
    standard_id: str,
    atom_id: str,
    atom_eval: dict[str, Any],
    recommendations: list[str],
) -> list[FixAction]:
    """Map per-dimension warnings to FixActions for a single atom."""
    actions: list[FixAction] = []

    # 1. Granularity — SPLIT when single_cognitive_intention is False.
    granularity = atom_eval.get("granularity", {})
    checks = granularity.get("checks", {})
    if checks.get("single_cognitive_intention") is False:
        actions.append(
            FixAction(
                fix_type=FixType.SPLIT,
                standard_id=standard_id,
                atom_ids=[atom_id],
                issues=granularity.get("issues", []),
                recommendations=recommendations,
            ),
        )
        # If the atom needs splitting, skip other in-place fixes for it
        # — the split will produce entirely new atoms.
        return actions

    # 2. Simple dimension warnings (content, fidelity, completeness, prereqs).
    for dimension, fix_type in _DIMENSION_TO_FIX.items():
        dim_data = atom_eval.get(dimension, {})
        if dim_data.get("score") == "warning":
            actions.append(
                FixAction(
                    fix_type=fix_type,
                    standard_id=standard_id,
                    atom_ids=[atom_id],
                    issues=dim_data.get("issues", []),
                    recommendations=recommendations,
                ),
            )

    return actions


def _parse_coverage(
    standard_id: str,
    coverage: dict[str, Any],
) -> list[FixAction]:
    """Extract ADD_MISSING and MERGE actions from coverage_analysis."""
    actions: list[FixAction] = []

    # Missing areas → ADD_MISSING
    missing: list[str] = coverage.get("missing_areas", [])
    if missing:
        actions.append(
            FixAction(
                fix_type=FixType.ADD_MISSING,
                standard_id=standard_id,
                atom_ids=[],
                issues=[
                    f"Coverage incomplete for: {area}" for area in missing
                ],
                recommendations=[],
                missing_areas=missing,
            ),
        )

    # Duplication issues → MERGE
    duplications: list[str] = coverage.get("duplication_issues", [])
    if duplications:
        # Try to extract atom IDs mentioned in the duplication text.
        atom_ids = _extract_atom_ids_from_text(duplications)
        actions.append(
            FixAction(
                fix_type=FixType.MERGE,
                standard_id=standard_id,
                atom_ids=atom_ids,
                issues=duplications,
                recommendations=[],
            ),
        )

    return actions


# -----------------------------------------------------------------------------
# De-duplication
# -----------------------------------------------------------------------------


def _deduplicate_actions(actions: list[FixAction]) -> list[FixAction]:
    """Remove exact-duplicate actions (same type + same atom set)."""
    seen: set[str] = set()
    unique: list[FixAction] = []
    for action in actions:
        key = f"{action.fix_type.value}|{action.standard_id}|{','.join(sorted(action.atom_ids))}"
        if key not in seen:
            seen.add(key)
            unique.append(action)
    return unique


# -----------------------------------------------------------------------------
# Atom-ID extraction from free text
# -----------------------------------------------------------------------------

_ATOM_ID_RE = re.compile(r"A-M1-[A-Z]+-\d+-\d+")


def _extract_atom_ids_from_text(texts: list[str]) -> list[str]:
    """Pull atom IDs (``A-M1-…-NN``) from free-text descriptions."""
    ids: list[str] = []
    for text in texts:
        ids.extend(_ATOM_ID_RE.findall(text))
    # Preserve order, remove duplicates.
    return list(dict.fromkeys(ids))
