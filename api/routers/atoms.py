"""Atoms pipeline router.

Endpoints:
    GET  /{subject_id}/atoms/pipeline-summary
    GET  /{subject_id}/atoms/structural-checks
    GET  /{subject_id}/atoms/structural-checks/saved
    POST /{subject_id}/atoms/validate
    GET  /{subject_id}/atoms/validate/status/{job_id}
    GET  /{subject_id}/atoms/validation-results
    POST /{subject_id}/atoms/fix
    GET  /{subject_id}/atoms/fix/status/{job_id}
    GET  /{subject_id}/atoms/coverage
    POST /{subject_id}/atoms/batch-enrich
    GET  /{subject_id}/atoms/batch-enrich/{job_id}
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from api.config import SUBJECTS_CONFIG
from api.schemas.atom_fix_models import (
    AtomFixActionResult,
    AtomFixChangeReport,
    AtomFixJobResponse,
    AtomFixProgress,
    AtomFixRequest,
    AtomFixStatusResponse,
)
from api.schemas.atom_models import (
    AtomPipelineSummary,
    AtomValidationJobResponse,
    AtomValidationProgress,
    AtomValidationRequest,
    AtomValidationStatusResponse,
    CoverageAnalysisResult,
    SavedValidationSummary,
    StandardValidationResult,
    StructuralChecksResult,
)
from api.services import (
    atom_coverage_service,
    atom_fix_service,
    atom_validation_service,
    batch_atom_enrichment_service,
)
from api.services.atom_structural_checks import (
    load_saved_results as load_saved_structural,
)
from api.services.atom_structural_checks import (
    run_structural_checks,
)
from app.utils.paths import get_atoms_file, get_standards_file

logger = logging.getLogger(__name__)

router = APIRouter()


def _validate_subject(subject_id: str) -> None:
    """Validate that subject exists."""
    if subject_id not in SUBJECTS_CONFIG:
        raise HTTPException(
            status_code=404,
            detail=f"Subject '{subject_id}' not found",
        )


# -----------------------------------------------------------------
# Pipeline summary
# -----------------------------------------------------------------

@router.get(
    "/{subject_id}/atoms/pipeline-summary",
    response_model=AtomPipelineSummary,
)
def get_pipeline_summary(subject_id: str) -> AtomPipelineSummary:
    """Get summary counts for atom pipeline tab status."""
    _validate_subject(subject_id)

    import json

    has_standards = get_standards_file("paes_m1_2026").exists()
    atoms_path = get_atoms_file("paes_m1_2026")

    atom_count = 0
    last_gen_date: str | None = None
    if atoms_path.exists():
        with open(atoms_path, encoding="utf-8") as f:
            data = json.load(f)
        atom_count = len(data.get("atoms", []))
        last_gen_date = data.get("metadata", {}).get("version")

    standards_count = 0
    if has_standards:
        with open(get_standards_file("paes_m1_2026"), encoding="utf-8") as f:
            std_data = json.load(f)
        std_list = std_data if isinstance(std_data, list) else std_data.get("standards", [])
        standards_count = len(std_list)

    saved = atom_validation_service.get_saved_validation_results()
    standards_validated = len(saved)
    standards_with_issues = sum(
        1 for r in saved
        if r.get("overall_quality") == "needs_improvement" or r.get("atoms_with_issues", 0) > 0
    )
    saved_structural = load_saved_structural()
    structural_passed: bool | None = saved_structural.passed if saved_structural else None

    from app.atoms.fixing.results_store import load_latest_results
    has_saved_fix = load_latest_results() is not None

    return AtomPipelineSummary(
        has_standards=has_standards,
        atom_count=atom_count,
        standards_count=standards_count,
        last_generation_date=last_gen_date,
        structural_checks_passed=structural_passed,
        standards_validated=standards_validated,
        standards_with_issues=standards_with_issues,
        has_saved_fix_results=has_saved_fix,
    )


# -----------------------------------------------------------------
# Structural checks
# -----------------------------------------------------------------

@router.get(
    "/{subject_id}/atoms/structural-checks",
    response_model=StructuralChecksResult,
)
def get_structural_checks(
    subject_id: str,
) -> StructuralChecksResult:
    """Run structural checks, persist, and return results."""
    _validate_subject(subject_id)
    return run_structural_checks(subject_id)


@router.get(
    "/{subject_id}/atoms/structural-checks/saved",
    response_model=StructuralChecksResult | None,
)
def get_saved_structural_checks(
    subject_id: str,
) -> StructuralChecksResult | None:
    """Return previously saved structural check results."""
    _validate_subject(subject_id)
    return load_saved_structural()


# -----------------------------------------------------------------
# LLM validation
# -----------------------------------------------------------------

@router.post(
    "/{subject_id}/atoms/validate",
    response_model=AtomValidationJobResponse,
)
async def start_validation(
    subject_id: str,
    request: AtomValidationRequest,
) -> AtomValidationJobResponse:
    """Start LLM validation (requires structural checks passed)."""
    _validate_subject(subject_id)

    # Gate: structural checks must have passed
    saved_structural = load_saved_structural()
    if saved_structural is None:
        raise HTTPException(
            status_code=400,
            detail="Run structural checks before LLM validation.",
        )
    if not saved_structural.passed:
        raise HTTPException(
            status_code=400,
            detail="Structural checks have errors. "
            "Fix them before running LLM validation.",
        )

    atoms_path = get_atoms_file("paes_m1_2026")
    if not atoms_path.exists():
        raise HTTPException(
            status_code=400,
            detail="No atoms file found. Generate atoms first.",
        )

    job_id, count, cost = await atom_validation_service.start_validation_job(
        selection_mode=request.selection_mode,
        standard_ids=request.standard_ids,
    )

    return AtomValidationJobResponse(
        job_id=job_id,
        status="started",
        standards_to_validate=count,
        estimated_cost_usd=cost,
    )


@router.get(
    "/{subject_id}/atoms/validate/status/{job_id}",
    response_model=AtomValidationStatusResponse,
)
def get_validation_status(
    subject_id: str,
    job_id: str,
) -> AtomValidationStatusResponse:
    """Get status of an atom validation job."""
    _validate_subject(subject_id)

    job = atom_validation_service.get_job_status(job_id)
    if job is None:
        raise HTTPException(
            status_code=404, detail=f"Job '{job_id}' not found"
        )

    return AtomValidationStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress=AtomValidationProgress(
            total=job.total,
            completed=job.completed,
            passed=job.passed,
            with_issues=job.with_issues,
        ),
        results=[
            StandardValidationResult(
                standard_id=r["standard_id"],
                status=r["status"],
                evaluation_summary=r.get("evaluation_summary"),
                coverage_analysis=r.get("coverage_analysis"),
                global_recommendations=r.get(
                    "global_recommendations", []
                ),
                error=r.get("error"),
            )
            for r in job.results
        ],
        started_at=job.started_at.isoformat(),
        completed_at=(
            job.completed_at.isoformat() if job.completed_at else None
        ),
    )


# -----------------------------------------------------------------
# Saved validation results
# -----------------------------------------------------------------

@router.get(
    "/{subject_id}/atoms/validation-results",
    response_model=list[SavedValidationSummary],
)
def get_validation_results(
    subject_id: str,
) -> list[SavedValidationSummary]:
    """Get saved LLM validation results from disk."""
    _validate_subject(subject_id)

    saved = atom_validation_service.get_saved_validation_results()
    return [
        SavedValidationSummary(
            standard_id=r["standard_id"],
            overall_quality=r.get("overall_quality"),
            coverage_assessment=r.get("coverage_assessment"),
            granularity_assessment=r.get("granularity_assessment"),
            total_atoms=r.get("total_atoms", 0),
            atoms_passing=r.get("atoms_passing", 0),
            atoms_with_issues=r.get("atoms_with_issues", 0),
        )
        for r in saved
    ]


# -----------------------------------------------------------------
# LLM fix
# -----------------------------------------------------------------

@router.post(
    "/{subject_id}/atoms/fix",
    response_model=AtomFixJobResponse,
)
async def start_fix(
    subject_id: str,
    request: AtomFixRequest,
) -> AtomFixJobResponse:
    """Start LLM fix job for atoms with validation issues."""
    _validate_subject(subject_id)

    # Gate: validation must have found issues
    saved = atom_validation_service.get_saved_validation_results()
    issues_count = sum(
        1 for r in saved
        if r.get("atoms_with_issues", 0) > 0
    )
    if issues_count == 0:
        raise HTTPException(
            status_code=400,
            detail="No validation issues found. Run validation first.",
        )

    job_id, count, cost = await atom_fix_service.start_fix_job(
        dry_run=request.dry_run,
        fix_types=request.fix_types,
        standard_ids=request.standard_ids,
    )

    return AtomFixJobResponse(
        job_id=job_id,
        status="started",
        actions_to_fix=count,
        estimated_cost_usd=cost,
        dry_run=request.dry_run,
    )


@router.post(
    "/{subject_id}/atoms/fix/apply-saved",
    response_model=AtomFixJobResponse,
)
async def apply_saved_fix(
    subject_id: str,
) -> AtomFixJobResponse:
    """Apply saved dry-run fix results (no LLM calls)."""
    _validate_subject(subject_id)
    try:
        job_id, count = await atom_fix_service.start_apply_saved_job()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return AtomFixJobResponse(
        job_id=job_id,
        status="started",
        actions_to_fix=count,
        estimated_cost_usd=0.0,
        dry_run=False,
    )


@router.post(
    "/{subject_id}/atoms/fix/retry-failed",
    response_model=AtomFixJobResponse,
)
async def retry_failed_fix(
    subject_id: str,
    request: AtomFixRequest,
) -> AtomFixJobResponse:
    """Retry only the actions that failed in the most recent run."""
    _validate_subject(subject_id)
    try:
        job_id, count, cost = await atom_fix_service.start_retry_failed_job(
            dry_run=request.dry_run,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if count == 0:
        raise HTTPException(status_code=400, detail="No failed actions to retry.")
    return AtomFixJobResponse(
        job_id=job_id, status="started", actions_to_fix=count,
        estimated_cost_usd=cost, dry_run=request.dry_run,
    )


@router.get(
    "/{subject_id}/atoms/fix/status/{job_id}",
    response_model=AtomFixStatusResponse,
)
def get_fix_status(
    subject_id: str,
    job_id: str,
) -> AtomFixStatusResponse:
    """Get status of an atom fix job."""
    _validate_subject(subject_id)

    job = atom_fix_service.get_job_status(job_id)
    if job is None:
        raise HTTPException(
            status_code=404, detail=f"Job '{job_id}' not found",
        )

    change_report = None
    if job.change_report:
        change_report = AtomFixChangeReport(**job.change_report)

    return AtomFixStatusResponse(
        job_id=job.job_id,
        status=job.status,
        dry_run=job.dry_run,
        progress=AtomFixProgress(
            total=job.total,
            completed=job.completed,
            succeeded=job.succeeded,
            failed=job.failed,
        ),
        results=[
            AtomFixActionResult(**r) for r in job.results
        ],
        change_report=change_report,
        has_saved_results=job.has_saved_results,
        started_at=job.started_at.isoformat(),
        completed_at=(
            job.completed_at.isoformat()
            if job.completed_at else None
        ),
    )


# -----------------------------------------------------------------
# Coverage analysis
# -----------------------------------------------------------------

@router.get(
    "/{subject_id}/atoms/coverage",
    response_model=CoverageAnalysisResult,
)
def get_coverage(subject_id: str) -> CoverageAnalysisResult:
    """Compute coverage analysis for atoms."""
    _validate_subject(subject_id)
    return atom_coverage_service.compute_coverage(subject_id)


# -----------------------------------------------------------------
# Batch atom enrichment
# -----------------------------------------------------------------

@router.get("/{subject_id}/atoms/batch-enrich/estimate")
def get_batch_enrich_estimate(
    subject_id: str,
    mode: str = Query("unenriched_only"),
) -> dict:
    """Preview atom counts and cost before starting enrichment."""
    _validate_subject(subject_id)
    return batch_atom_enrichment_service.get_batch_enrich_estimate(mode)


@router.post("/{subject_id}/atoms/batch-enrich")
async def start_batch_enrich(
    subject_id: str,
    body: dict | None = None,
) -> dict:
    """Start batch enrichment for covered atoms."""
    _validate_subject(subject_id)
    mode = (body or {}).get("mode", "unenriched_only")
    if mode not in ("unenriched_only", "all"):
        raise HTTPException(
            status_code=400,
            detail="mode must be 'unenriched_only' or 'all'",
        )

    job_id, count, skipped = (
        await batch_atom_enrichment_service
        .start_batch_enrichment(mode=mode)
    )
    est = batch_atom_enrichment_service.get_batch_enrich_estimate(mode)
    return {
        "job_id": job_id,
        "status": "started",
        "atoms_to_process": count,
        "skipped": skipped,
        "estimated_cost_usd": est["estimated_cost_usd"],
    }


@router.get("/{subject_id}/atoms/batch-enrich/{job_id}")
def get_batch_enrich_status(
    subject_id: str,
    job_id: str,
) -> dict:
    """Get status of a batch enrichment job."""
    _validate_subject(subject_id)
    job = batch_atom_enrichment_service.get_job_status(job_id)
    if job is None:
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' not found",
        )
    return {
        "job_id": job.job_id,
        "status": job.status,
        "total": job.total,
        "completed": job.completed,
        "succeeded": job.succeeded,
        "failed": job.failed,
        "skipped": job.skipped,
        "current_atom": job.current_atom,
        "results": job.results,
        "started_at": job.started_at.isoformat(),
        "completed_at": (
            job.completed_at.isoformat()
            if job.completed_at else None
        ),
    }
