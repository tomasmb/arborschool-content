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
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from api.schemas.api_models import (
    CostEstimate,
    JobListResponse,
    JobStatus,
    PipelineDefinition,
    PipelineParam,
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
    estimate = estimator.estimate_pipeline_cost(pipeline_id, params or {})

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
