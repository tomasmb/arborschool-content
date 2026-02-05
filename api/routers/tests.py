"""Tests router - test-level enrichment, validation, and sync endpoints.

Endpoints:
    POST /api/subjects/{subject_id}/tests/{test_id}/enrich
    GET  /api/subjects/{subject_id}/tests/{test_id}/enrich/status/{job_id}
    POST /api/subjects/{subject_id}/tests/{test_id}/validate
    GET  /api/subjects/{subject_id}/tests/{test_id}/validate/status/{job_id}
    POST /api/subjects/{subject_id}/tests/{test_id}/variants/enrich
    POST /api/subjects/{subject_id}/tests/{test_id}/variants/validate
    POST /api/subjects/{subject_id}/tests/{test_id}/sync/preview
    POST /api/subjects/{subject_id}/tests/{test_id}/sync/execute
    POST /api/subjects/{subject_id}/tests/{test_id}/upload-pdf
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

from api.config import PRUEBAS_FINALIZADAS_DIR, PRUEBAS_RAW_DIR, SUBJECTS_CONFIG
from api.schemas.pipeline_models import (
    EnrichmentJobResponse,
    EnrichmentProgress,
    EnrichmentQuestionResult,
    EnrichmentRequest,
    EnrichmentStatusResponse,
    TestSyncExecuteResponse,
    TestSyncPreviewRequest,
    TestSyncPreviewResponse,
    TestSyncSummary,
    ValidationJobResponse,
    ValidationProgress,
    ValidationQuestionResult,
    ValidationRequest,
    ValidationStatusResponse,
)
from api.services import enrichment_service, sync_service, validation_service

# -----------------------------------------------------------------------------
# Variant Request Models
# -----------------------------------------------------------------------------


class VariantEnrichmentRequest(BaseModel):
    """Request to enrich variants with feedback."""

    question_num: str | None = Field(
        None, description="Only enrich variants for this question (e.g., 'Q1')"
    )
    skip_already_enriched: bool = Field(
        True, description="Skip variants that already have feedback"
    )


class VariantValidationRequest(BaseModel):
    """Request to validate variants."""

    question_num: str | None = Field(
        None, description="Only validate variants for this question (e.g., 'Q1')"
    )
    revalidate_passed: bool = Field(
        False, description="Re-validate variants that already passed"
    )

router = APIRouter()


def _validate_subject_and_test(subject_id: str, test_id: str) -> None:
    """Validate that subject and test exist."""
    if subject_id not in SUBJECTS_CONFIG:
        raise HTTPException(status_code=404, detail=f"Subject '{subject_id}' not found")

    test_dir = PRUEBAS_FINALIZADAS_DIR / test_id
    if not test_dir.exists():
        raise HTTPException(status_code=404, detail=f"Test '{test_id}' not found")


# -----------------------------------------------------------------------------
# Enrichment Endpoints
# -----------------------------------------------------------------------------


@router.post(
    "/{subject_id}/tests/{test_id}/enrich",
    response_model=EnrichmentJobResponse,
)
async def start_enrichment(
    subject_id: str,
    test_id: str,
    request: EnrichmentRequest,
) -> EnrichmentJobResponse:
    """Start enrichment job for questions in a test.

    Adds feedback to QTI XML using the QuestionPipeline.
    """
    _validate_subject_and_test(subject_id, test_id)

    logger.warning(
        f"[ENRICH API] Starting enrichment: test_id={test_id}, "
        f"question_ids={request.question_ids}, all_tagged={request.all_tagged}, "
        f"skip_already_enriched={request.skip_already_enriched}, "
        f"only_failed_validation={request.only_failed_validation}"
    )

    job_id, questions_count, estimated_cost = await enrichment_service.start_enrichment_job(
        test_id=test_id,
        question_ids=request.question_ids,
        all_tagged=request.all_tagged,
        skip_already_enriched=request.skip_already_enriched,
        only_failed_validation=request.only_failed_validation,
    )

    logger.warning(
        f"[ENRICH API] Job created: job_id={job_id}, "
        f"questions_to_process={questions_count}, estimated_cost=${estimated_cost}"
    )

    return EnrichmentJobResponse(
        job_id=job_id,
        status="started",
        questions_to_process=questions_count,
        estimated_cost_usd=estimated_cost,
    )


@router.get(
    "/{subject_id}/tests/{test_id}/enrich/status/{job_id}",
    response_model=EnrichmentStatusResponse,
)
async def get_enrichment_status(
    subject_id: str,
    test_id: str,
    job_id: str,
) -> EnrichmentStatusResponse:
    """Get status of an enrichment job."""
    _validate_subject_and_test(subject_id, test_id)

    job = enrichment_service.get_job_status(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    return EnrichmentStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress=EnrichmentProgress(
            total=job.total,
            completed=job.completed,
            successful=job.successful,
            failed=job.failed,
        ),
        current_question=job.current_question,
        results=[
            EnrichmentQuestionResult(
                question_id=r["question_id"],
                status=r["status"],
                error=r.get("error"),
            )
            for r in job.results
        ],
        started_at=job.started_at.isoformat(),
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
    )


# -----------------------------------------------------------------------------
# Validation Endpoints
# -----------------------------------------------------------------------------


@router.post(
    "/{subject_id}/tests/{test_id}/validate",
    response_model=ValidationJobResponse,
)
async def start_validation(
    subject_id: str,
    test_id: str,
    request: ValidationRequest,
) -> ValidationJobResponse:
    """Start validation job for questions in a test.

    Runs LLM validation on enriched questions.
    """
    _validate_subject_and_test(subject_id, test_id)

    job_id, questions_count, estimated_cost = await validation_service.start_validation_job(
        test_id=test_id,
        question_ids=request.question_ids,
        all_enriched=request.all_enriched,
        revalidate_passed=request.revalidate_passed,
    )

    return ValidationJobResponse(
        job_id=job_id,
        status="started",
        questions_to_process=questions_count,
        estimated_cost_usd=estimated_cost,
    )


@router.get(
    "/{subject_id}/tests/{test_id}/validate/status/{job_id}",
    response_model=ValidationStatusResponse,
)
async def get_validation_status(
    subject_id: str,
    test_id: str,
    job_id: str,
) -> ValidationStatusResponse:
    """Get status of a validation job."""
    _validate_subject_and_test(subject_id, test_id)

    job = validation_service.get_validation_job_status(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    return ValidationStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress=ValidationProgress(
            total=job.total,
            completed=job.completed,
            passed=job.passed,
            failed=job.failed,
        ),
        results=[
            ValidationQuestionResult(
                question_id=r["question_id"],
                status=r["status"],
                failed_checks=r.get("failed_checks"),
                issues=r.get("issues"),
            )
            for r in job.results
        ],
        started_at=job.started_at.isoformat(),
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
    )


# -----------------------------------------------------------------------------
# Variant Enrichment & Validation Endpoints (DRY - reuses same logic as questions)
# -----------------------------------------------------------------------------


@router.post(
    "/{subject_id}/tests/{test_id}/variants/enrich",
    response_model=EnrichmentJobResponse,
)
async def start_variant_enrichment(
    subject_id: str,
    test_id: str,
    request: VariantEnrichmentRequest,
) -> EnrichmentJobResponse:
    """Start enrichment job for variants in a test.

    Uses the same enrichment logic as questions (DRY principle).
    This is for old variants that were generated without feedback.
    """
    _validate_subject_and_test(subject_id, test_id)

    job_id, variants_count, estimated_cost = await enrichment_service.start_variant_enrichment_job(
        test_id=test_id,
        question_num=request.question_num,
        skip_already_enriched=request.skip_already_enriched,
    )

    return EnrichmentJobResponse(
        job_id=job_id,
        status="started",
        questions_to_process=variants_count,  # Reusing field name for compatibility
        estimated_cost_usd=estimated_cost,
    )


@router.post(
    "/{subject_id}/tests/{test_id}/variants/validate",
    response_model=ValidationJobResponse,
)
async def start_variant_validation(
    subject_id: str,
    test_id: str,
    request: VariantValidationRequest,
) -> ValidationJobResponse:
    """Start validation job for variants in a test.

    Uses the same validation logic as questions (DRY principle).
    """
    _validate_subject_and_test(subject_id, test_id)

    job_id, variants_count, estimated_cost = await validation_service.start_variant_validation_job(
        test_id=test_id,
        question_num=request.question_num,
        revalidate_passed=request.revalidate_passed,
    )

    return ValidationJobResponse(
        job_id=job_id,
        status="started",
        questions_to_process=variants_count,  # Reusing field name for compatibility
        estimated_cost_usd=estimated_cost,
    )


# -----------------------------------------------------------------------------
# Sync Endpoints
# -----------------------------------------------------------------------------


@router.post(
    "/{subject_id}/tests/{test_id}/sync/preview",
    response_model=TestSyncPreviewResponse,
)
async def preview_sync(
    subject_id: str,
    test_id: str,
    request: TestSyncPreviewRequest,
) -> TestSyncPreviewResponse:
    """Preview what will be synced to database.

    Returns categorized questions: to_create, to_update, unchanged, skipped.
    """
    _validate_subject_and_test(subject_id, test_id)

    preview = sync_service.get_sync_preview(
        test_id=test_id,
        include_variants=request.include_variants,
    )

    return TestSyncPreviewResponse(
        questions=preview["questions"],
        summary=TestSyncSummary(**preview["summary"]),
    )


@router.post(
    "/{subject_id}/tests/{test_id}/sync/execute",
    response_model=TestSyncExecuteResponse,
)
async def execute_sync(
    subject_id: str,
    test_id: str,
    request: TestSyncPreviewRequest,
) -> TestSyncExecuteResponse:
    """Execute sync to database.

    Creates new questions and updates changed ones.
    """
    _validate_subject_and_test(subject_id, test_id)

    result = sync_service.execute_sync(
        test_id=test_id,
        include_variants=request.include_variants,
        upload_images=request.upload_images,
    )

    return TestSyncExecuteResponse(
        created=result["created"],
        updated=result["updated"],
        skipped=result["skipped"],
        details=result["details"],
    )


# -----------------------------------------------------------------------------
# PDF Upload Endpoint
# -----------------------------------------------------------------------------


@router.post("/{subject_id}/tests/{test_id}/upload-pdf")
async def upload_test_pdf(
    subject_id: str,
    test_id: str,
    file: UploadFile,
) -> dict:
    """Upload a raw PDF file for a test.

    The PDF is saved to the raw pruebas directory where it can be processed
    by the PDF splitting pipeline.

    Args:
        subject_id: The subject identifier
        test_id: The test identifier
        file: The PDF file to upload

    Returns:
        dict with success status and file path
    """
    if subject_id not in SUBJECTS_CONFIG:
        raise HTTPException(status_code=404, detail=f"Subject '{subject_id}' not found")

    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    # Create test directory if it doesn't exist
    test_dir = PRUEBAS_RAW_DIR / test_id
    test_dir.mkdir(parents=True, exist_ok=True)

    # Save the PDF file
    # Use the test_id as filename for consistency
    pdf_path = test_dir / f"{test_id}.pdf"

    try:
        content = await file.read()
        pdf_path.write_bytes(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    return {
        "success": True,
        "message": "PDF uploaded successfully",
        "path": str(pdf_path),
    }
