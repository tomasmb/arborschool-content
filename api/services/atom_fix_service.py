"""Atom fix service for LLM-powered correction of validation issues.

Manages async fix jobs that execute FixActions from the fixing pipeline,
with bounded parallelism. Uses in-memory storage for job state
(same pattern as atom_validation_service.py).

Persists full FixResults to disk so dry-run results can be applied
later and failed actions can be retried without re-running all LLM calls.

Reuses existing domain functions from app.atoms.fixing -- never
reimplements fix logic.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Cost per action by reasoning effort (GPT-5.1).
# high  = ~30K in + ~8K out + ~20K reasoning ≈ $0.32
# medium = ~10K in + ~3K out + ~10K reasoning ≈ $0.15
# low   = ~10K in + ~3K out + ~2K reasoning  ≈ $0.06
_COST_BY_EFFORT: dict[str, float] = {
    "high": 0.32,
    "medium": 0.15,
    "low": 0.06,
}

# Max concurrent LLM calls (keep within rate limits).
_MAX_CONCURRENT_FIXES = 3


@dataclass
class AtomFixJob:
    """State for an atom fix job."""

    job_id: str
    status: str  # started | in_progress | completed | failed
    dry_run: bool
    total: int
    completed: int
    succeeded: int
    failed: int
    results: list[dict[str, Any]] = field(default_factory=list)
    change_report: dict[str, Any] | None = None
    has_saved_results: bool = False
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    completed_at: datetime | None = None


# In-memory job storage (same pattern as atom_validation_service)
_jobs: dict[str, AtomFixJob] = {}


def estimate_fix_cost(actions: list[Any]) -> float:
    """Estimate total USD cost for a list of FixActions."""
    total = 0.0
    for action in actions:
        total += _COST_BY_EFFORT.get(action.reasoning_effort, 0.15)
    return round(total, 2)


# -----------------------------------------------------------------------------
# Start a full fix job (dry-run or apply)
# -----------------------------------------------------------------------------


async def start_fix_job(
    *,
    dry_run: bool = True,
    fix_types: list[str] | None = None,
    standard_ids: list[str] | None = None,
) -> tuple[str, int, float]:
    """Start an async atom fix job.

    Returns:
        Tuple of (job_id, actions_count, estimated_cost_usd).
    """
    from app.atoms.fixing.issue_parser import (
        parse_all_validation_results,
    )
    from app.atoms.fixing.models import FixType

    ft_filter = (
        [FixType(ft) for ft in fix_types] if fix_types else None
    )
    actions = parse_all_validation_results(
        fix_types=ft_filter,
        standard_ids=standard_ids,
    )

    cost = estimate_fix_cost(actions)
    job = _create_job(dry_run=dry_run, total=len(actions))
    asyncio.create_task(_run_fix(job.job_id, actions, dry_run))
    return job.job_id, len(actions), cost


# -----------------------------------------------------------------------------
# Apply previously saved dry-run results (no LLM)
# -----------------------------------------------------------------------------


async def start_apply_saved_job() -> tuple[str, int]:
    """Apply the most recently saved dry-run results.

    Returns:
        Tuple of (job_id, actions_count).

    Raises:
        FileNotFoundError: If no saved results exist.
    """
    from app.atoms.fixing.results_store import load_latest_results

    loaded = load_latest_results()
    if loaded is None:
        raise FileNotFoundError(
            "No saved fix results found. Run the pipeline first.",
        )
    results, path = loaded
    successful = [r for r in results if r.success]

    job = _create_job(dry_run=False, total=len(successful))
    asyncio.create_task(
        _run_apply_saved(job.job_id, successful),
    )
    return job.job_id, len(successful)


# -----------------------------------------------------------------------------
# Retry only failed actions from the last run
# -----------------------------------------------------------------------------


async def start_retry_failed_job(
    *,
    dry_run: bool = True,
) -> tuple[str, int, float]:
    """Retry only the failed actions from the most recent run.

    Returns:
        Tuple of (job_id, actions_count, estimated_cost_usd).

    Raises:
        FileNotFoundError: If no saved results exist.
    """
    from app.atoms.fixing.results_store import (
        get_failed_actions_from_latest,
    )

    loaded = get_failed_actions_from_latest()
    if loaded is None:
        raise FileNotFoundError(
            "No saved fix results found. Run the pipeline first.",
        )
    failed_results, _path = loaded
    actions = [r.action for r in failed_results]
    cost = estimate_fix_cost(actions)

    job = _create_job(dry_run=dry_run, total=len(actions))
    asyncio.create_task(_run_fix(job.job_id, actions, dry_run))
    return job.job_id, len(actions), cost


# -----------------------------------------------------------------------------
# Background job runners
# -----------------------------------------------------------------------------


async def _run_fix(
    job_id: str,
    actions: list[Any],
    dry_run: bool,
) -> None:
    """Run fix actions in background with bounded parallelism."""
    job = _jobs.get(job_id)
    if not job:
        logger.error("Job %s not found", job_id)
        return

    job.status = "in_progress"

    try:
        from app.atoms.fixing import _build_question_refs, _load_all_atoms, _load_standards, _sort_actions
        from app.atoms.fixing.applier import apply_results
        from app.atoms.fixing.executor import execute_fix
        from app.atoms.fixing.results_store import save_results
        from app.llm_clients import load_default_openai_client

        client = load_default_openai_client()
    except Exception as exc:
        job.status = "failed"
        job.completed_at = datetime.now(timezone.utc)
        logger.exception("Failed to initialise: %s", exc)
        return

    standards = _load_standards()
    all_atoms = _load_all_atoms()
    question_refs = _build_question_refs()
    sorted_actions = _sort_actions(actions)

    semaphore = asyncio.Semaphore(_MAX_CONCURRENT_FIXES)
    fix_results: list[Any] = []

    async def _process_one(action: Any) -> None:
        """Execute one fix action with bounded concurrency."""
        std = standards.get(action.standard_id)
        if std is None:
            job.completed += 1
            job.failed += 1
            job.results.append(
                _action_dict(action, False, "Standard not found"),
            )
            return

        async with semaphore:
            result = await asyncio.to_thread(
                execute_fix,
                client=client,
                action=action,
                standard=std,
                all_atoms=all_atoms,
                question_refs=question_refs,
            )

        fix_results.append(result)
        job.completed += 1
        if result.success:
            job.succeeded += 1
        else:
            job.failed += 1
        job.results.append(
            _action_dict(action, result.success, result.error),
        )

    await asyncio.gather(
        *[_process_one(a) for a in sorted_actions],
    )

    # Save full results to disk (for apply-saved / retry-failed).
    await asyncio.to_thread(save_results, fix_results)
    job.has_saved_results = True

    # Apply all successful results in one batch.
    successful = [r for r in fix_results if r.success]
    report = apply_results(successful, dry_run=dry_run)
    job.change_report = _report_to_dict(report)

    job.status = "completed"
    job.completed_at = datetime.now(timezone.utc)
    logger.info(
        "Fix job %s completed: %d succeeded, %d failed",
        job_id, job.succeeded, job.failed,
    )


async def _run_apply_saved(
    job_id: str,
    successful_results: list[Any],
) -> None:
    """Apply previously saved successful results (no LLM calls)."""
    job = _jobs.get(job_id)
    if not job:
        logger.error("Job %s not found", job_id)
        return

    job.status = "in_progress"

    try:
        from app.atoms.fixing.applier import apply_results

        report = await asyncio.to_thread(
            apply_results,
            successful_results,
            dry_run=False,
        )
    except Exception as exc:
        job.status = "failed"
        job.completed_at = datetime.now(timezone.utc)
        logger.exception("Failed to apply saved results: %s", exc)
        return

    job.completed = job.total
    job.succeeded = job.total
    job.change_report = _report_to_dict(report)

    for r in successful_results:
        job.results.append(
            _action_dict(r.action, True, None),
        )

    job.status = "completed"
    job.completed_at = datetime.now(timezone.utc)
    logger.info(
        "Apply-saved job %s completed: %d applied",
        job_id, job.total,
    )


# -----------------------------------------------------------------------------
# Job management
# -----------------------------------------------------------------------------


def get_job_status(job_id: str) -> AtomFixJob | None:
    """Get job status by ID."""
    return _jobs.get(job_id)


def _create_job(*, dry_run: bool, total: int) -> AtomFixJob:
    """Create and register a new job."""
    job_id = f"atom-fix-{uuid.uuid4().hex[:8]}"
    job = AtomFixJob(
        job_id=job_id,
        status="started",
        dry_run=dry_run,
        total=total,
        completed=0,
        succeeded=0,
        failed=0,
    )
    _jobs[job_id] = job
    return job


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _action_dict(
    action: Any,
    success: bool,
    error: str | None,
) -> dict[str, Any]:
    """Serialise a fix action result for the job results list."""
    return {
        "fix_type": action.fix_type.value,
        "atom_ids": action.atom_ids,
        "standard_id": action.standard_id,
        "success": success,
        "error": error,
    }


def _report_to_dict(report: Any) -> dict[str, Any]:
    """Convert a ChangeReport dataclass to a plain dict."""
    return {
        "atoms_added": report.atoms_added,
        "atoms_removed": report.atoms_removed,
        "atoms_modified": report.atoms_modified,
        "prerequisite_cascades": len(report.prerequisite_cascades),
        "question_mapping_updates": len(
            report.question_mapping_updates,
        ),
        "manual_review_needed": report.manual_review_needed,
    }
