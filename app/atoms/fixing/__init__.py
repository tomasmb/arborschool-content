"""Atom fix pipeline — LLM-powered correction of validation issues.

Orchestrates the full flow:
  1. Parse validation result JSONs into ``FixAction`` objects.
  2. Sort actions by dependency-safe execution order.
  3. Execute each fix (LLM call or deterministic).
  4. Apply results to the atoms file and cascade side effects.

Usage::

    from app.atoms.fixing import fix_all_validation_issues
    from app.llm_clients import load_default_openai_client

    client = load_default_openai_client()
    results, report = fix_all_validation_issues(client, dry_run=True)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.atoms.fixing.applier import ChangeReport, apply_results
from app.atoms.fixing.executor import execute_fix
from app.atoms.fixing.issue_parser import parse_all_validation_results
from app.atoms.fixing.models import FIX_ORDER, FixAction, FixResult, FixType
from app.llm_clients import OpenAIClient
from app.utils.paths import (
    PRUEBAS_FINALIZADAS_DIR,
    get_atoms_file,
    get_standards_file,
)

logger = logging.getLogger(__name__)

__all__ = [
    "fix_all_validation_issues",
    "ChangeReport",
    "FixAction",
    "FixResult",
    "FixType",
]


# -----------------------------------------------------------------------------
# Public orchestrator
# -----------------------------------------------------------------------------


def fix_all_validation_issues(
    client: OpenAIClient,
    *,
    dry_run: bool = True,
    fix_types: list[FixType] | None = None,
    standard_ids: list[str] | None = None,
) -> tuple[list[FixResult], ChangeReport]:
    """Run the full fix pipeline.

    Args:
        client: Configured OpenAI client (GPT-5.1).
        dry_run: If True, report proposed changes without writing files.
        fix_types: Optional filter — only apply these fix types.
        standard_ids: Optional filter — only fix these standards.

    Returns:
        Tuple of (all FixResults, aggregated ChangeReport).
    """
    # 1. Parse validation results.
    actions = parse_all_validation_results(
        fix_types=fix_types,
        standard_ids=standard_ids,
    )
    if not actions:
        logger.info("No fix actions found — nothing to do.")
        return [], ChangeReport()

    # 2. Sort by execution order.
    actions = _sort_actions(actions)
    logger.info("Executing %d fix actions…", len(actions))

    # 3. Load shared data.
    standards = _load_standards()
    all_atoms = _load_all_atoms()
    question_refs = _build_question_refs()

    # 4. Execute each fix.
    results: list[FixResult] = []
    for i, action in enumerate(actions, 1):
        std = standards.get(action.standard_id)
        if std is None:
            logger.warning("Standard %s not found — skipping.", action.standard_id)
            continue

        logger.info(
            "[%d/%d] %s — %s (%s)",
            i,
            len(actions),
            action.fix_type.value,
            ", ".join(action.atom_ids) or action.standard_id,
            action.reasoning_effort,
        )

        result = execute_fix(
            client=client,
            action=action,
            standard=std,
            all_atoms=all_atoms,
            question_refs=question_refs,
        )
        results.append(result)

        if result.success:
            logger.info("  ✓ Success")
        else:
            logger.warning("  ✗ Failed: %s", result.error)

    # 5. Apply results.
    successful = [r for r in results if r.success]
    report = apply_results(successful, dry_run=dry_run)

    logger.info("Pipeline complete.\n%s", report.summary())
    return results, report


# -----------------------------------------------------------------------------
# Sorting
# -----------------------------------------------------------------------------

_TYPE_ORDER = {ft: idx for idx, ft in enumerate(FIX_ORDER)}


def _sort_actions(actions: list[FixAction]) -> list[FixAction]:
    """Sort actions by the dependency-safe execution order."""
    return sorted(actions, key=lambda a: _TYPE_ORDER.get(a.fix_type, 99))


# -----------------------------------------------------------------------------
# Data loaders
# -----------------------------------------------------------------------------


def _load_standards() -> dict[str, dict[str, Any]]:
    """Load standard definitions keyed by standard_id."""
    path = get_standards_file()
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    standards_list = data if isinstance(data, list) else data.get("standards", [])
    return {s["id"]: s for s in standards_list if "id" in s}


def _load_all_atoms() -> list[dict[str, Any]]:
    """Load every atom from the canonical atoms file."""
    path = get_atoms_file()
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return data.get("atoms", [])


def _build_question_refs() -> dict[str, list[dict[str, Any]]]:
    """Build atom_id → list of question ref dicts.

    Each ref dict has ``question_id``, ``relevance``, ``file``.
    """
    refs: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(PRUEBAS_FINALIZADAS_DIR.rglob("metadata_tags.json")):
        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        question_id = path.parent.name  # e.g. "Q1"
        for entry in data.get("selected_atoms", []):
            atom_id = entry.get("atom_id", "")
            if not atom_id:
                continue
            refs.setdefault(atom_id, []).append({
                "question_id": question_id,
                "relevance": entry.get("relevance", ""),
                "file": str(path),
            })
    return refs
