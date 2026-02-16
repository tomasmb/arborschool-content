"""Pipelines router - pipeline execution and job management.

Endpoints:
    GET  /api/pipelines - List available pipelines
    GET  /api/pipelines/{pipeline_id} - Get pipeline details and params
    POST /api/pipelines/estimate - Estimate cost for a pipeline run
    POST /api/pipelines/run - Start a pipeline job
    GET  /api/pipelines/jobs - List recent jobs
    GET  /api/pipelines/jobs/{job_id} - Get job status
    POST /api/pipelines/jobs/{job_id}/cancel - Cancel a running job
    DELETE /api/pipelines/jobs/{job_id} - Delete a job record
    GET  /api/pipelines/question_gen/{atom_id}/checkpoints - Read checkpoint data
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from api.schemas.api_models import (
    CostEstimate,
    JobListResponse,
    JobResumeRequest,
    JobStatus,
    PipelineDefinition,
    RunPipelineRequest,
    RunPipelineResponse,
)
from api.services.cost_estimator import (
    CostEstimatorService,
    generate_confirmation_token,
    verify_confirmation_token,
)
from api.services.pipeline_runner import get_runner

router = APIRouter()


# -----------------------------------------------------------------------------
# Pipeline definitions
# -----------------------------------------------------------------------------


@router.get("", response_model=list[PipelineDefinition])
async def list_pipelines() -> list[PipelineDefinition]:
    """List all available pipelines."""
    runner = get_runner()
    return runner.get_pipelines()


@router.get("/{pipeline_id}")
async def get_pipeline(pipeline_id: str) -> dict[str, Any]:
    """Get a pipeline definition with its parameters."""
    runner = get_runner()
    pipeline = runner.get_pipeline(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_id}' not found")

    params = runner.get_pipeline_params(pipeline_id)

    return {
        "pipeline": pipeline.model_dump(),
        "params": [p.model_dump() for p in params],
    }


# -----------------------------------------------------------------------------
# Cost estimation
# -----------------------------------------------------------------------------


@router.post("/estimate", response_model=CostEstimate)
async def estimate_pipeline_cost(
    pipeline_id: str,
    params: dict[str, Any] | None = None,
) -> CostEstimate:
    """Estimate cost for running a pipeline.

    Returns estimated token usage and cost range.
    Also returns a confirmation_token to use when starting the job.
    """
    runner = get_runner()
    if not runner.get_pipeline(pipeline_id):
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_id}' not found")

    estimator = CostEstimatorService()
    safe_params = params or {}
    estimate = estimator.estimate_pipeline_cost(pipeline_id, safe_params)

    # Stale artifact warning only when force_all (full rerun).
    # In resume mode (default), downstream checkpoints are preserved.
    if pipeline_id == "question_gen" and safe_params.get("force_all"):
        atom_id = safe_params.get("atom_id", "")
        phase = safe_params.get("phase", "all")
        if atom_id:
            from app.question_generation.artifacts import (
                get_stale_artifacts,
            )
            estimate.stale_artifacts = get_stale_artifacts(
                atom_id, phase,
            )

    return estimate


# -----------------------------------------------------------------------------
# Job execution
# -----------------------------------------------------------------------------


@router.post("/run", response_model=RunPipelineResponse)
async def run_pipeline(request: RunPipelineRequest) -> RunPipelineResponse:
    """Start a pipeline job.

    If the pipeline has AI costs, a confirmation_token must be provided
    to confirm the user has seen the cost estimate.
    """
    runner = get_runner()
    pipeline = runner.get_pipeline(request.pipeline_id)

    if not pipeline:
        raise HTTPException(
            status_code=404,
            detail=f"Pipeline '{request.pipeline_id}' not found",
        )

    # For AI-cost pipelines, verify confirmation token
    if pipeline.has_ai_cost:
        if not request.confirmation_token:
            raise HTTPException(
                status_code=400,
                detail="Pipeline has AI costs. Get cost estimate first and include confirmation_token.",
            )
        if not verify_confirmation_token(
            request.confirmation_token,
            request.pipeline_id,
            request.params,
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired confirmation token. Re-run cost estimate.",
            )

    # Create and start the job
    job = runner.create_job(request.pipeline_id, request.params)
    job = runner.start_job(job.job_id)

    return RunPipelineResponse(
        job_id=job.job_id,
        status=job.status,
        message=f"Pipeline {request.pipeline_id} started",
    )


# -----------------------------------------------------------------------------
# Job management
# -----------------------------------------------------------------------------


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(limit: int = 20) -> JobListResponse:
    """List recent pipeline jobs."""
    runner = get_runner()
    jobs = runner.list_jobs(limit=limit)
    return JobListResponse(jobs=jobs)


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job(job_id: str) -> JobStatus:
    """Get status of a specific job."""
    runner = get_runner()
    job = runner.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return job


@router.post("/jobs/{job_id}/cancel", response_model=JobStatus)
async def cancel_job(job_id: str) -> JobStatus:
    """Cancel a running job."""
    runner = get_runner()
    job = runner.cancel_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return job


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str) -> dict[str, str]:
    """Delete a completed/failed/cancelled job record."""
    runner = get_runner()
    job = runner.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    if job.status == "running":
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a running job. Cancel it first.",
        )

    success = runner.delete_job(job_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete job")

    return {"message": f"Job '{job_id}' deleted"}


@router.post("/jobs/{job_id}/resume", response_model=RunPipelineResponse)
async def resume_job(job_id: str, request: JobResumeRequest) -> RunPipelineResponse:
    """Resume a failed or cancelled job.

    Args:
        job_id: The job to resume
        request: Resume options - mode can be 'remaining' or 'failed_only'

    Returns:
        New job info for the resumed job
    """
    runner = get_runner()
    job = runner.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    if job.status not in ("failed", "cancelled"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot resume job with status '{job.status}'. Only failed or cancelled jobs can be resumed.",
        )

    if not job.can_resume:
        raise HTTPException(
            status_code=400,
            detail="This job cannot be resumed. It may lack the required tracking data.",
        )

    # Create new job with remaining/failed items
    new_job = runner.resume_job(job_id, mode=request.mode)
    if not new_job:
        raise HTTPException(
            status_code=500,
            detail="Failed to create resume job",
        )

    return RunPipelineResponse(
        job_id=new_job.job_id,
        status=new_job.status,
        message=f"Resumed job {job_id} with mode '{request.mode}'",
    )


@router.get("/jobs/{job_id}/logs")
async def get_job_logs(
    job_id: str,
    offset: int = 0,
    limit: int = 100
) -> dict[str, Any]:
    """Get logs for a specific job.

    Args:
        job_id: The job ID
        offset: Start from this log line (0-indexed)
        limit: Maximum number of log lines to return

    Returns:
        Dict with logs array and metadata
    """
    runner = get_runner()
    job = runner.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    logs = job.logs[offset:offset + limit]
    total = len(job.logs)

    return {
        "job_id": job_id,
        "logs": logs,
        "offset": offset,
        "limit": limit,
        "total": total,
        "has_more": offset + limit < total,
    }


# -----------------------------------------------------------------------------
# Confirmation tokens
# -----------------------------------------------------------------------------


@router.post("/confirm")
async def get_confirmation_token(
    pipeline_id: str,
    params: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Get a confirmation token after reviewing the cost estimate.

    This token proves the user has seen the estimated cost.
    """
    runner = get_runner()
    if not runner.get_pipeline(pipeline_id):
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_id}' not found")

    token = generate_confirmation_token(pipeline_id, params or {})
    return {"confirmation_token": token}


# -----------------------------------------------------------------------------
# Pipeline output clearing
# -----------------------------------------------------------------------------


@router.delete("/{pipeline_id}/clear")
async def clear_pipeline_outputs(
    pipeline_id: str,
    subject_id: str | None = None,
    test_id: str | None = None,
) -> dict[str, Any]:
    """Clear/delete outputs for a specific pipeline.

    Args:
        pipeline_id: The pipeline whose outputs to clear
        subject_id: Optional subject ID to scope the clearing
        test_id: Optional test ID for test-specific pipelines

    Returns:
        Dict with deleted counts and paths
    """
    import shutil

    from app.utils.paths import (
        ATOMS_DIR,
        PRUEBAS_ALTERNATIVAS_DIR,
        PRUEBAS_FINALIZADAS_DIR,
        PRUEBAS_PROCESADAS_DIR,
        STANDARDS_DIR,
    )

    runner = get_runner()
    if not runner.get_pipeline(pipeline_id):
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_id}' not found")

    deleted_count = 0
    deleted_paths: list[str] = []

    if pipeline_id == "standards_gen":
        # Delete standards JSON file for the subject
        if subject_id:
            pattern = f"*{subject_id.replace('-', '_')}*.json"
        else:
            pattern = "*.json"
        for f in STANDARDS_DIR.glob(pattern):
            f.unlink()
            deleted_paths.append(str(f))
            deleted_count += 1

    elif pipeline_id == "atoms_gen":
        # Delete atoms JSON file for the subject
        if subject_id:
            pattern = f"*{subject_id.replace('-', '_')}*_atoms.json"
        else:
            pattern = "*_atoms.json"
        for f in ATOMS_DIR.glob(pattern):
            f.unlink()
            deleted_paths.append(str(f))
            deleted_count += 1

    elif pipeline_id == "variant_gen":
        # Delete variant folders
        if test_id:
            variant_dir = PRUEBAS_ALTERNATIVAS_DIR / test_id
            if variant_dir.exists():
                shutil.rmtree(variant_dir)
                deleted_paths.append(str(variant_dir))
                deleted_count = 1
        else:
            for test_dir in PRUEBAS_ALTERNATIVAS_DIR.iterdir():
                if test_dir.is_dir():
                    shutil.rmtree(test_dir)
                    deleted_paths.append(str(test_dir))
                    deleted_count += 1

    elif pipeline_id == "tagging":
        # Delete metadata_tags.json files
        if test_id:
            qti_dir = PRUEBAS_FINALIZADAS_DIR / test_id / "qti"
        else:
            qti_dir = PRUEBAS_FINALIZADAS_DIR
        for f in qti_dir.rglob("metadata_tags.json"):
            f.unlink()
            deleted_paths.append(str(f))
            deleted_count += 1

    elif pipeline_id == "pdf_to_qti":
        # Delete QTI folders (but not the PDFs)
        if test_id:
            qti_dir = PRUEBAS_FINALIZADAS_DIR / test_id / "qti"
            if qti_dir.exists():
                shutil.rmtree(qti_dir)
                deleted_paths.append(str(qti_dir))
                deleted_count = 1
        else:
            for test_dir in PRUEBAS_FINALIZADAS_DIR.iterdir():
                qti_dir = test_dir / "qti"
                if qti_dir.exists():
                    shutil.rmtree(qti_dir)
                    deleted_paths.append(str(qti_dir))
                    deleted_count += 1

    elif pipeline_id == "pdf_split":
        # Delete processed PDF folders
        if test_id:
            pdf_dir = PRUEBAS_PROCESADAS_DIR / test_id
            if pdf_dir.exists():
                shutil.rmtree(pdf_dir)
                deleted_paths.append(str(pdf_dir))
                deleted_count = 1
        else:
            for test_dir in PRUEBAS_PROCESADAS_DIR.iterdir():
                if test_dir.is_dir():
                    shutil.rmtree(test_dir)
                    deleted_paths.append(str(test_dir))
                    deleted_count += 1

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Clear not supported for pipeline '{pipeline_id}'",
        )

    return {
        "pipeline_id": pipeline_id,
        "deleted_count": deleted_count,
        "deleted_paths": deleted_paths[:10],  # Limit paths in response
        "message": f"Cleared {deleted_count} items for {pipeline_id}",
    }


# -----------------------------------------------------------------------------
# Question generation checkpoint inspection
# -----------------------------------------------------------------------------


@router.get("/question_gen/{atom_id}/checkpoints")
async def get_atom_checkpoints(atom_id: str) -> dict[str, Any]:
    """Read all available checkpoint data for a question generation atom.

    Returns structured data from each completed pipeline phase,
    plus the pipeline report if available. Used by the frontend
    results inspector to render plan slots and QTI previews.
    """
    from app.question_generation.checkpoint_reader import (
        read_atom_checkpoints,
    )
    from app.utils.paths import QUESTION_GENERATION_DIR

    output_dir = QUESTION_GENERATION_DIR / atom_id
    if not output_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No generation data for atom '{atom_id}'",
        )

    return read_atom_checkpoints(output_dir, atom_id)
