"""Course-scoped sync router.

Provides endpoints to preview and execute syncs for a specific course.
These endpoints are mounted at /api/subjects/{subject_id}/sync/*.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from api.config import SUBJECTS_CONFIG
from api.schemas.api_models import (
    SyncExecuteRequest,
    SyncExecuteResponse,
    SyncPreviewRequest,
    SyncPreviewResponse,
    SyncTableSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_table_summaries(summary: dict, extracted: dict) -> list[SyncTableSummary]:
    """Build table summaries from sync payload summary."""
    tables = []

    if summary.get("subjects", 0) > 0:
        tables.append(SyncTableSummary(table="subjects", total=summary["subjects"]))

    if summary.get("standards", 0) > 0:
        tables.append(SyncTableSummary(table="standards", total=summary["standards"]))

    if summary.get("atoms", 0) > 0:
        tables.append(SyncTableSummary(table="atoms", total=summary["atoms"]))

    if summary.get("tests", 0) > 0:
        tables.append(SyncTableSummary(table="tests", total=summary["tests"]))

    if summary.get("questions", 0) > 0:
        official_count = len(extracted["questions"])
        variant_count = len(extracted["variants"])
        tables.append(SyncTableSummary(
            table="questions",
            total=summary["questions"],
            breakdown={"official": official_count, "variants": variant_count},
        ))

    if summary.get("question_atoms", 0) > 0:
        tables.append(SyncTableSummary(
            table="question_atoms",
            total=summary["question_atoms"],
        ))

    if summary.get("test_questions", 0) > 0:
        tables.append(SyncTableSummary(
            table="test_questions",
            total=summary["test_questions"],
        ))

    return tables


@router.post("/{subject_id}/sync/preview", response_model=SyncPreviewResponse)
async def preview_course_sync(
    subject_id: str,
    request: SyncPreviewRequest,
) -> SyncPreviewResponse:
    """Preview what would be synced for this course (dry run)."""
    if subject_id not in SUBJECTS_CONFIG:
        raise HTTPException(status_code=404, detail=f"Subject '{subject_id}' not found")

    # Import sync helpers from sync.py
    from api.routers.sync import _build_payload, _check_db_config, _extract_data

    try:
        extracted = _extract_data(
            request.entities,
            request.include_variants,
            subject_id=subject_id,
        )

        payload = _build_payload(extracted, subject_id=subject_id)
        summary = payload.summary()
        tables = _build_table_summaries(summary, extracted)

        warnings = []
        if not _check_db_config():
            warnings.append(
                "Database configuration not found. "
                "Set HOST, DB_NAME, DB_USER, DB_PASSWORD environment variables."
            )

        return SyncPreviewResponse(
            tables=tables,
            summary={
                "subject_id": subject_id,
                "entities_requested": request.entities,
                "include_variants": request.include_variants,
                "upload_images": request.upload_images,
                "total_tables": len(tables),
            },
            warnings=warnings,
        )

    except Exception as e:
        logger.exception("Error during course sync preview")
        raise HTTPException(status_code=500, detail=f"Preview failed: {e!s}") from e


@router.post("/{subject_id}/sync/execute", response_model=SyncExecuteResponse)
async def execute_course_sync(
    subject_id: str,
    request: SyncExecuteRequest,
) -> SyncExecuteResponse:
    """Execute sync to the production database for this course."""
    if subject_id not in SUBJECTS_CONFIG:
        raise HTTPException(status_code=404, detail=f"Subject '{subject_id}' not found")

    from api.routers.sync import (
        _build_payload,
        _check_db_config,
        _check_s3_config,
        _extract_data,
    )

    if not request.confirm:
        return SyncExecuteResponse(
            success=False,
            results={},
            message="Sync not executed. Set confirm=True to execute.",
            errors=["Confirmation required"],
        )

    if not _check_db_config():
        return SyncExecuteResponse(
            success=False,
            results={},
            message="Database configuration not found.",
            errors=["Set HOST, DB_NAME, DB_USER, DB_PASSWORD environment variables."],
        )

    if request.upload_images and not _check_s3_config():
        return SyncExecuteResponse(
            success=False,
            results={},
            message="S3 credentials not found but image upload requested.",
            errors=["Set AWS_S3_KEY and AWS_S3_SECRET environment variables."],
        )

    try:
        from app.sync.db_client import DBClient, DBConfig
        from app.utils.paths import PRUEBAS_FINALIZADAS_DIR

        extracted = _extract_data(
            request.entities,
            request.include_variants,
            subject_id=subject_id,
        )

        images_uploaded = 0
        if request.upload_images and extracted["questions"]:
            from app.sync.s3_client import (
                ImageUploader,
                S3Config,
                process_all_questions_images,
            )

            s3_config = S3Config.from_env()
            uploader = ImageUploader(s3_config)

            updated_qti = process_all_questions_images(
                extracted["questions"],
                PRUEBAS_FINALIZADAS_DIR,
                uploader,
            )

            for q in extracted["questions"]:
                if q.id in updated_qti:
                    q.qti_xml = updated_qti[q.id]
                    images_uploaded += 1

        payload = _build_payload(extracted, subject_id=subject_id)

        db_config = DBConfig.from_env()
        db_client = DBClient(db_config)
        results = db_client.sync_all(payload, dry_run=False)

        total_affected = sum(results.values())
        msg = f"Sync completed for {subject_id}. {total_affected} total rows affected."
        if request.upload_images:
            msg += f" {images_uploaded} questions processed for S3 images."

        return SyncExecuteResponse(
            success=True,
            results=results,
            message=msg,
            errors=[],
        )

    except ValueError as e:
        logger.exception("Configuration error during course sync")
        return SyncExecuteResponse(
            success=False,
            results={},
            message=f"Configuration error: {e!s}",
            errors=[str(e)],
        )
    except Exception as e:
        logger.exception("Error during course sync execution")
        return SyncExecuteResponse(
            success=False,
            results={},
            message=f"Sync failed: {e!s}",
            errors=[str(e)],
        )
