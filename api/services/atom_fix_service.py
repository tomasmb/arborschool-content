"""Atom fix service for LLM-powered correction of validation issues.

Manages async fix jobs that execute FixActions from the fixing pipeline,
with bounded parallelism. Uses in-memory storage for job state
(same pattern as atom_validation_service.py).

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


async def start_fix_job(
    *,
    dry_run: bool = True,
    fix_types: list[str] | None = None,
    standard_ids: list[str] | None = None,
) -> tuple[str, int, float]:
    """Start an async atom fix job.

    Args:
        dry_run: If True, report changes without writing files.
        fix_types: Optional filter for fix types.
        standard_ids: Optional filter for standards.

    Returns:
        Tuple of (job_id, actions_count, estimated_cost_usd).
    """
    from app.atoms.fixing.issue_parser import (
        parse_all_validation_results,
    )
    from app.atoms.fixing.models import FixType

    # Parse fix types filter.
    ft_filter = (
        [FixType(ft) for ft in fix_types] if fix_types else None
    )

    actions = parse_all_validation_results(
        fix_types=ft_filter,
        standard_ids=standard_ids,
    )

    cost = estimate_fix_cost(actions)

    job_id = f"atom-fix-{uuid.uuid4().hex[:8]}"
    job = AtomFixJob(
        job_id=job_id,
        status="started",
        dry_run=dry_run,
        total=len(actions),
        completed=0,
        succeeded=0,
        failed=0,
    )
    _jobs[job_id] = job

    asyncio.create_task(
        _run_fix(job_id, actions, dry_run),
    )

    return job_id, len(actions), cost


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

    # Lazy imports to avoid module-load side effects.
    try:
        from app.atoms.fixing import _build_question_refs
        from app.atoms.fixing import _load_all_atoms
        from app.atoms.fixing import _load_standards
        from app.atoms.fixing import _sort_actions
        from app.atoms.fixing.applier import apply_results
        from app.atoms.fixing.executor import execute_fix
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

    for action in sorted_actions:
        std = standards.get(action.standard_id)
        if std is None:
            job.completed += 1
            job.failed += 1
            job.results.append(_action_dict(action, False, "Standard not found"))
            continue

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


def get_job_status(job_id: str) -> AtomFixJob | None:
    """Get job status by ID."""
    return _jobs.get(job_id)


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
        "question_mapping_updates": len(report.question_mapping_updates),
        "manual_review_needed": report.manual_review_needed,
    }
