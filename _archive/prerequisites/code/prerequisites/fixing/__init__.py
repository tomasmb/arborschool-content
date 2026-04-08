"""Prerequisite atom fix pipeline -- LLM-powered correction.

Orchestrates the fix flow for prerequisite atoms:
  1. Parse validation results into FixAction objects.
  2. Sort by dependency-safe execution order.
  3. Execute each fix (LLM call or deterministic).
  4. Apply results to the prereq atoms file.
  5. Persist results to disk.

Usage::

    from app.prerequisites.fixing import fix_prereq_validation_issues
    from app.llm_clients import load_default_openai_client

    client = load_default_openai_client()
    results, report = fix_prereq_validation_issues(client, dry_run=True)
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from app.atoms.fixing.models import FIX_ORDER, FixAction, FixResult, FixType
from app.atoms.fixing.results_store import save_results
from app.llm_clients import OpenAIClient
from app.prerequisites.fixing.applier import (
    PrereqChangeReport,
    apply_prereq_results,
)
from app.prerequisites.fixing.executor import execute_prereq_fix
from app.prerequisites.fixing.issue_parser import (
    parse_prereq_validation_results,
)
from app.utils.paths import PREREQUISITES_DIR, PREREQ_STANDARDS_FILE

logger = logging.getLogger(__name__)

_PREREQ_FIX_RESULTS_DIR = PREREQUISITES_DIR / "fix_results"
_MAX_WORKERS = 4

__all__ = [
    "PrereqChangeReport",
    "fix_prereq_validation_issues",
]


def fix_prereq_validation_issues(
    client: OpenAIClient,
    *,
    dry_run: bool = True,
    fix_types: list[FixType] | None = None,
    standard_ids: list[str] | None = None,
) -> tuple[list[FixResult], PrereqChangeReport]:
    """Run the full prereq fix pipeline.

    Args:
        client: Configured OpenAI client (GPT-5.1).
        dry_run: If True, report changes without writing files.
        fix_types: Optional filter.
        standard_ids: Optional filter.

    Returns:
        Tuple of (all FixResults, PrereqChangeReport).
    """
    actions = parse_prereq_validation_results(
        fix_types=fix_types,
        standard_ids=standard_ids,
    )
    if not actions:
        logger.info("No fix actions found -- nothing to do.")
        return [], PrereqChangeReport()

    return _execute_and_apply(client, actions, dry_run=dry_run)


def _execute_and_apply(
    client: OpenAIClient,
    actions: list[FixAction],
    *,
    dry_run: bool,
) -> tuple[list[FixResult], PrereqChangeReport]:
    """Execute actions in parallel, apply results, persist."""
    actions = _sort_actions(actions)
    logger.info("Executing %d prereq fix actions...", len(actions))

    standards = _load_standards()
    all_atoms = _load_all_atoms()

    tasks: list[tuple[FixAction, dict[str, Any]]] = []
    for action in actions:
        std = standards.get(action.standard_id)
        if std is None:
            logger.warning(
                "Standard %s not found -- skipping.", action.standard_id,
            )
            continue
        tasks.append((action, std))

    results = _execute_parallel(client, tasks, all_atoms)

    save_results(results, run_dir=_PREREQ_FIX_RESULTS_DIR)

    successful = [r for r in results if r.success]
    report = apply_prereq_results(successful, dry_run=dry_run)

    logger.info("Pipeline complete.\n%s", report.summary())
    return results, report


def _execute_parallel(
    client: OpenAIClient,
    tasks: list[tuple[FixAction, dict[str, Any]]],
    all_atoms: list[dict[str, Any]],
) -> list[FixResult]:
    """Run fix actions concurrently via a thread pool."""
    if not tasks:
        return []

    total = len(tasks)
    results: list[FixResult] = []

    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        futures = {
            pool.submit(
                execute_prereq_fix,
                client=client,
                action=action,
                standard=std,
                all_atoms=all_atoms,
            ): action
            for action, std in tasks
        }

        for i, future in enumerate(as_completed(futures), 1):
            action = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                logger.error("Unexpected error: %s", exc)
                result = FixResult(
                    action=action, success=False, error=str(exc),
                )
            results.append(result)
            mark = "ok" if result.success else "FAIL"
            label = ", ".join(action.atom_ids) or action.standard_id
            logger.info(
                "[%d/%d] %s %s -- %s",
                i, total, mark, action.fix_type.value, label,
            )

    return results


_TYPE_ORDER = {ft: idx for idx, ft in enumerate(FIX_ORDER)}


def _sort_actions(actions: list[FixAction]) -> list[FixAction]:
    """Sort actions by the dependency-safe execution order."""
    return sorted(
        actions, key=lambda a: _TYPE_ORDER.get(a.fix_type, 99),
    )


def _load_standards() -> dict[str, dict[str, Any]]:
    """Load prereq standard definitions keyed by standard_id."""
    with PREREQ_STANDARDS_FILE.open(encoding="utf-8") as f:
        data = json.load(f)
    standards_list = data.get("standards", [])
    return {s["id"]: s for s in standards_list if "id" in s}


def _load_all_atoms() -> list[dict[str, Any]]:
    """Load every prerequisite atom."""
    from app.utils.paths import PREREQ_ATOMS_FILE

    with PREREQ_ATOMS_FILE.open(encoding="utf-8") as f:
        data = json.load(f)
    return data.get("atoms", [])
