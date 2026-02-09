"""Atom validation service for LLM-based quality checks.

Manages async validation jobs that run validate_atoms_with_llm()
per standard, with bounded parallelism. Uses in-memory storage for
job state (same pattern as enrichment_service.py).

Reuses existing domain functions -- never reimplements validation logic.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.utils.paths import (
    ATOM_VALIDATION_RESULTS_DIR,
    get_atoms_file,
    get_standards_file,
)

logger = logging.getLogger(__name__)


# Cost estimate per standard (GPT-5.1, medium reasoning, no output cap)
# Input  ~13K tokens @ $1.25/1M  = $0.016
# Output  ~8K tokens @ $10.00/1M = $0.08
# Reasoning ~15K tokens (billed as output) @ $10.00/1M = $0.15
# Total ~$0.25 -- rounded up as safety buffer
COST_PER_STANDARD_USD = 0.25

# Max concurrent LLM calls.  Keeps us within OpenAI rate limits
# while still being ~4x faster than sequential execution.
_MAX_CONCURRENT_VALIDATIONS = 4


@dataclass
class AtomValidationJob:
    """State for an atom validation job."""

    job_id: str
    status: str  # started | in_progress | completed | failed
    total: int
    completed: int
    passed: int
    with_issues: int
    results: list[dict[str, Any]] = field(default_factory=list)
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    completed_at: datetime | None = None
    current_standard: str | None = None


# In-memory job storage (same pattern as enrichment_service)
_jobs: dict[str, AtomValidationJob] = {}


def _load_atoms_and_standards() -> (
    tuple[list[dict[str, Any]], list[dict[str, Any]]]
):
    """Load atoms and standards from canonical JSON files.

    Returns:
        Tuple of (atoms_list, standards_list) as raw dicts.
    """
    atoms_path = get_atoms_file("paes_m1_2026")
    standards_path = get_standards_file("paes_m1_2026")

    with open(atoms_path, encoding="utf-8") as f:
        atoms_data = json.load(f)
    atoms_list = atoms_data.get("atoms", [])

    with open(standards_path, encoding="utf-8") as f:
        std_data = json.load(f)
    standards_list = (
        std_data if isinstance(std_data, list)
        else std_data.get("standards", [])
    )

    return atoms_list, standards_list


def _get_validated_standard_ids() -> set[str]:
    """Get standard IDs that already have saved validation results."""
    if not ATOM_VALIDATION_RESULTS_DIR.exists():
        return set()
    validated = set()
    for f in ATOM_VALIDATION_RESULTS_DIR.iterdir():
        if f.name.startswith("validation_") and f.suffix == ".json":
            # Format: validation_M1-NUM-01.json
            std_id = f.stem.replace("validation_", "")
            validated.add(std_id)
    return validated


def get_saved_validation_results() -> list[dict[str, Any]]:
    """Load all saved validation results from disk.

    Returns:
        List of per-standard validation result summaries.
    """
    results: list[dict[str, Any]] = []
    if not ATOM_VALIDATION_RESULTS_DIR.exists():
        return results

    for f in sorted(ATOM_VALIDATION_RESULTS_DIR.iterdir()):
        if not (f.name.startswith("validation_") and f.suffix == ".json"):
            continue
        std_id = f.stem.replace("validation_", "")
        try:
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
            summary = data.get("evaluation_summary", {})
            results.append({
                "standard_id": std_id,
                "overall_quality": summary.get("overall_quality"),
                "coverage_assessment": summary.get("coverage_assessment"),
                "granularity_assessment": summary.get(
                    "granularity_assessment"
                ),
                "total_atoms": summary.get("total_atoms", 0),
                "atoms_passing": summary.get(
                    "atoms_passing_all_checks", 0
                ),
                "atoms_with_issues": summary.get("atoms_with_issues", 0),
            })
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load validation %s: %s", f, e)
            results.append({
                "standard_id": std_id,
                "overall_quality": "error",
                "error": str(e),
            })

    return results


def get_validation_cost_estimate(standard_count: int) -> float:
    """Estimate cost for LLM validation.

    Args:
        standard_count: Number of standards to validate.

    Returns:
        Estimated cost in USD.
    """
    return round(standard_count * COST_PER_STANDARD_USD, 2)


async def start_validation_job(
    selection_mode: str = "unvalidated",
    standard_ids: list[str] | None = None,
) -> tuple[str, int, float]:
    """Start async LLM validation job.

    Args:
        selection_mode: "unvalidated" | "all" | "specific"
        standard_ids: IDs for selection_mode="specific"

    Returns:
        Tuple of (job_id, standards_to_validate, estimated_cost_usd)
    """
    atoms_list, standards_list = _load_atoms_and_standards()

    # Build set of standards that have atoms
    standard_ids_in_atoms: set[str] = set()
    for atom in atoms_list:
        standard_ids_in_atoms.update(atom.get("standard_ids", []))

    # Filter standards based on selection mode
    candidates = [
        s for s in standards_list
        if s.get("id") in standard_ids_in_atoms
    ]

    if selection_mode == "specific" and standard_ids:
        target_set = set(standard_ids)
        candidates = [
            s for s in candidates if s.get("id") in target_set
        ]
    elif selection_mode == "unvalidated":
        already_validated = _get_validated_standard_ids()
        candidates = [
            s for s in candidates
            if s.get("id") not in already_validated
        ]

    job_id = f"atom-val-{uuid.uuid4().hex[:8]}"
    job = AtomValidationJob(
        job_id=job_id,
        status="started",
        total=len(candidates),
        completed=0,
        passed=0,
        with_issues=0,
    )
    _jobs[job_id] = job

    estimated_cost = get_validation_cost_estimate(len(candidates))

    # Start background task
    asyncio.create_task(
        _run_validation(job_id, candidates, atoms_list)
    )

    return job_id, len(candidates), estimated_cost


async def _validate_single_standard(
    client: Any,
    validate_fn: Any,
    standard: dict[str, Any],
    all_atoms: list[dict[str, Any]],
    job: AtomValidationJob,
    semaphore: asyncio.Semaphore,
) -> None:
    """Validate atoms for one standard and update job state.

    Acquires ``semaphore`` before making the LLM call so that at
    most ``_MAX_CONCURRENT_VALIDATIONS`` requests run in parallel.
    """
    std_id = standard.get("id", "unknown")

    std_atoms = [
        a for a in all_atoms
        if std_id in a.get("standard_ids", [])
    ]
    if not std_atoms:
        job.completed += 1
        job.results.append({
            "standard_id": std_id, "status": "pass",
            "evaluation_summary": {
                "total_atoms": 0, "overall_quality": "n/a",
            },
        })
        return

    async with semaphore:
        logger.info("Starting validation for %s", std_id)
        try:
            result = await asyncio.to_thread(
                validate_fn, client, standard, std_atoms,
            )
        except Exception as e:
            job.completed += 1
            job.with_issues += 1
            job.results.append({
                "standard_id": std_id,
                "status": "error", "error": str(e),
            })
            logger.exception(
                "Validation failed for %s: %s", std_id, e,
            )
            return

    # Persist result to disk
    output_path = (
        ATOM_VALIDATION_RESULTS_DIR
        / f"validation_{std_id}.json"
    )
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    _record_standard_result(job, std_id, result)


def _record_standard_result(
    job: AtomValidationJob,
    std_id: str,
    result: dict[str, Any],
) -> None:
    """Parse LLM result and update job counters."""
    summary = result.get("evaluation_summary", {})
    quality = summary.get("overall_quality", "")
    has_issues = (
        quality == "needs_improvement"
        or summary.get("atoms_with_issues", 0) > 0
    )
    if has_issues:
        job.with_issues += 1
        status = "issues"
    else:
        job.passed += 1
        status = "pass"

    job.completed += 1
    job.results.append({
        "standard_id": std_id,
        "status": status,
        "evaluation_summary": summary,
        "coverage_analysis": result.get("coverage_analysis"),
        "global_recommendations": result.get(
            "global_recommendations", []
        ),
    })


async def _run_validation(
    job_id: str,
    standards: list[dict[str, Any]],
    all_atoms: list[dict[str, Any]],
) -> None:
    """Run LLM validation in background with bounded parallelism.

    Up to ``_MAX_CONCURRENT_VALIDATIONS`` standards are validated
    concurrently.  Each task handles its own errors so one failure
    does not cancel the rest.
    """
    job = _jobs.get(job_id)
    if not job:
        logger.error("Job %s not found", job_id)
        return

    job.status = "in_progress"

    # Invalidate stale fix results — they were based on the
    # previous validation run and are no longer applicable.
    from app.atoms.fixing.results_store import clear_results
    clear_results()

    # Import OpenAI client lazily to avoid import at module load
    try:
        from app.atoms.validation.validation import (
            validate_atoms_with_llm,
        )
        from app.llm_clients import load_default_openai_client
        client = load_default_openai_client()
    except Exception as e:
        job.status = "failed"
        job.completed_at = datetime.now(timezone.utc)
        logger.exception("Failed to initialize OpenAI: %s", e)
        return

    ATOM_VALIDATION_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    semaphore = asyncio.Semaphore(_MAX_CONCURRENT_VALIDATIONS)

    tasks = [
        _validate_single_standard(
            client, validate_atoms_with_llm,
            standard, all_atoms, job, semaphore,
        )
        for standard in standards
    ]
    await asyncio.gather(*tasks)

    job.status = "completed"
    job.current_standard = None
    job.completed_at = datetime.now(timezone.utc)
    logger.info(
        "Atom validation job %s completed: %d passed, "
        "%d with issues",
        job_id, job.passed, job.with_issues,
    )


def get_job_status(job_id: str) -> AtomValidationJob | None:
    """Get job status by ID."""
    return _jobs.get(job_id)
