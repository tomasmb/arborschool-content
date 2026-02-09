"""Atom fix pipeline — LLM-powered correction of validation issues.

Orchestrates the full flow:
  1. Parse validation result JSONs into ``FixAction`` objects.
  2. Sort actions by dependency-safe execution order.
  3. Execute each fix (LLM call or deterministic).
  4. Apply results to the atoms file and cascade side effects.
  5. Persist results to disk for later review / apply / retry.

Usage::

    from app.atoms.fixing import fix_all_validation_issues
    from app.llm_clients import load_default_openai_client

    client = load_default_openai_client()
    results, report = fix_all_validation_issues(client, dry_run=True)

    # Later — apply saved dry-run results without re-running LLM:
    results, report = apply_saved_results()

    # Or retry only the failed actions:
    results, report = retry_failed_actions(client)
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from app.atoms.fixing.applier import ChangeReport, apply_results
from app.atoms.fixing.executor import execute_fix
from app.atoms.fixing.issue_parser import parse_all_validation_results
from app.atoms.fixing.models import FIX_ORDER, FixAction, FixResult, FixType
from app.atoms.fixing.results_store import (
    get_failed_actions_from_latest,
    load_latest_results,
    save_results,
)
from app.llm_clients import OpenAIClient
from app.utils.paths import (
    PRUEBAS_FINALIZADAS_DIR,
    get_atoms_file,
    get_standards_file,
)

logger = logging.getLogger(__name__)

__all__ = [
    "ChangeReport",
    "FixAction",
    "FixResult",
    "FixType",
    "apply_saved_results",
    "fix_all_validation_issues",
    "retry_failed_actions",
]


# -----------------------------------------------------------------------------
# Public orchestrator — full run
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

    # 2. Execute and apply.
    return _execute_and_apply(client, actions, dry_run=dry_run)


# -----------------------------------------------------------------------------
# Public — apply saved dry-run results
# -----------------------------------------------------------------------------


def apply_saved_results(
    *,
    results_file: Path | None = None,
) -> tuple[list[FixResult], ChangeReport]:
    """Apply previously saved results without re-running LLM calls.

    Args:
        results_file: Specific results file to load. If None, loads the
            most recent saved run.

    Returns:
        Tuple of (results, ChangeReport) after applying.

    Raises:
        FileNotFoundError: If no saved results exist.
    """
    if results_file:
        from app.atoms.fixing.results_store import load_results
        results = load_results(results_file)
        path = results_file
    else:
        loaded = load_latest_results()
        if loaded is None:
            raise FileNotFoundError(
                "No saved fix results found. Run the pipeline first.",
            )
        results, path = loaded

    succeeded = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    logger.info(
        "Loaded %d results from %s (%d ok, %d failed)",
        len(results), path, succeeded, failed,
    )

    successful = [r for r in results if r.success]
    if not successful:
        logger.warning("No successful results to apply.")
        return results, ChangeReport()

    report = apply_results(successful, dry_run=False)
    logger.info("Applied %d successful fixes.\n%s", len(successful), report.summary())
    return results, report


# -----------------------------------------------------------------------------
# Public — retry only failed actions from the last run
# -----------------------------------------------------------------------------


def retry_failed_actions(
    client: OpenAIClient,
    *,
    dry_run: bool = True,
) -> tuple[list[FixResult], ChangeReport]:
    """Re-run only the actions that failed in the most recent run.

    Args:
        client: Configured OpenAI client (GPT-5.1).
        dry_run: If True, save results but don't write atom files.

    Returns:
        Tuple of (all FixResults, aggregated ChangeReport).

    Raises:
        FileNotFoundError: If no saved results exist.
    """
    loaded = get_failed_actions_from_latest()
    if loaded is None:
        raise FileNotFoundError(
            "No saved fix results found. Run the pipeline first.",
        )

    failed_results, path = loaded
    if not failed_results:
        logger.info("No failed actions in the last run — nothing to retry.")
        return [], ChangeReport()

    # Extract the original FixActions from the failed results.
    actions = [r.action for r in failed_results]
    logger.info(
        "Retrying %d failed actions from %s",
        len(actions), path,
    )

    return _execute_and_apply(client, actions, dry_run=dry_run)


# -----------------------------------------------------------------------------
# Internal — shared execution + apply logic
# -----------------------------------------------------------------------------


# Max concurrent LLM calls (keep within rate limits).
_MAX_WORKERS = 3


def _execute_and_apply(
    client: OpenAIClient,
    actions: list[FixAction],
    *,
    dry_run: bool,
) -> tuple[list[FixResult], ChangeReport]:
    """Execute actions in parallel, apply results, persist to disk."""
    # 1. Sort by execution order.
    actions = _sort_actions(actions)
    logger.info("Executing %d fix actions…", len(actions))

    # 2. Load shared data (read-only snapshot for all workers).
    standards = _load_standards()
    all_atoms = _load_all_atoms()
    question_refs = _build_question_refs()

    # 3. Build executable tasks, skip missing standards.
    tasks: list[tuple[FixAction, dict[str, Any]]] = []
    for action in actions:
        std = standards.get(action.standard_id)
        if std is None:
            logger.warning(
                "Standard %s not found — skipping.",
                action.standard_id,
            )
            continue
        tasks.append((action, std))

    # 4. Execute in parallel with bounded concurrency.
    results = _execute_parallel(
        client, tasks, all_atoms, question_refs,
    )

    # 5. Persist results (always — both dry-run and apply modes).
    save_results(results)

    # 6. Apply results.
    successful = [r for r in results if r.success]
    report = apply_results(successful, dry_run=dry_run)

    logger.info("Pipeline complete.\n%s", report.summary())
    return results, report


def _execute_parallel(
    client: OpenAIClient,
    tasks: list[tuple[FixAction, dict[str, Any]]],
    all_atoms: list[dict[str, Any]],
    question_refs: dict[str, list[dict[str, Any]]],
) -> list[FixResult]:
    """Run fix actions concurrently via a thread pool.

    All workers share the same read-only ``all_atoms`` snapshot.
    Mutations only happen later in ``apply_results``.
    """
    if not tasks:
        return []

    total = len(tasks)
    results: list[FixResult] = []

    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        futures = {
            pool.submit(
                execute_fix,
                client=client,
                action=action,
                standard=std,
                all_atoms=all_atoms,
                question_refs=question_refs,
            ): action
            for action, std in tasks
        }

        for i, future in enumerate(as_completed(futures), 1):
            action = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                logger.error(
                    "Unexpected error for %s: %s", action, exc,
                )
                result = FixResult(
                    action=action, success=False, error=str(exc),
                )

            results.append(result)
            mark = "✓" if result.success else "✗"
            label = (
                ", ".join(action.atom_ids) or action.standard_id
            )
            logger.info(
                "[%d/%d] %s %s — %s",
                i, total, mark,
                action.fix_type.value, label,
            )

    return results


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
    standards_list = (
        data if isinstance(data, list) else data.get("standards", [])
    )
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
