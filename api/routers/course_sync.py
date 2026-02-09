"""Course-scoped sync router.

Provides endpoints to preview and execute syncs for a specific course.
These endpoints are mounted at /api/subjects/{subject_id}/sync/*.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from api.config import SUBJECTS_CONFIG
from api.schemas.api_models import (
    VALID_SYNC_ENVIRONMENTS,
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
def preview_course_sync(
    subject_id: str,
    request: SyncPreviewRequest,
) -> SyncPreviewResponse:
    """Preview what would be synced for this course (dry run)."""
    if subject_id not in SUBJECTS_CONFIG:
        raise HTTPException(status_code=404, detail=f"Subject '{subject_id}' not found")

    # Validate environment
    if request.environment not in VALID_SYNC_ENVIRONMENTS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid environment: {request.environment}"
        )

    # Import sync helpers from sync.py
    from api.routers.sync import _build_payload, _check_db_config, _extract_data

    try:
        extracted = _extract_data(
            request.entities,
            subject_id=subject_id,
        )

        payload = _build_payload(
            extracted, subject_id=subject_id,
            entities=request.entities,
        )
        summary = payload.summary()
        tables = _build_table_summaries(summary, extracted)

        warnings = []
        if not _check_db_config(request.environment):
            env_help = {
                "local": "Set HOST, DB_NAME, DB_USER, DB_PASSWORD environment variables.",
                "staging": "Set DATABASE_URL_STAGING environment variable.",
                "prod": "Set DATABASE_URL_PROD environment variable.",
            }
            warnings.append(
                f"Database configuration not found for {request.environment}. "
                f"{env_help.get(request.environment, '')}"
            )

        return SyncPreviewResponse(
            tables=tables,
            summary={
                "subject_id": subject_id,
                "entities_requested": request.entities,
                "total_tables": len(tables),
            },
            warnings=warnings,
            environment=request.environment,
        )

    except Exception as e:
        logger.exception("Error during course sync preview")
        raise HTTPException(status_code=500, detail=f"Preview failed: {e!s}") from e


@router.post("/{subject_id}/sync/execute", response_model=SyncExecuteResponse)
def execute_course_sync(
    subject_id: str,
    request: SyncExecuteRequest,
) -> SyncExecuteResponse:
    """Execute sync to the database for this course."""
    if subject_id not in SUBJECTS_CONFIG:
        raise HTTPException(status_code=404, detail=f"Subject '{subject_id}' not found")

    from api.routers.sync import (
        _build_payload,
        _check_db_config,
        _check_s3_config,
        _extract_data,
    )

    # Validate environment
    if request.environment not in VALID_SYNC_ENVIRONMENTS:
        return SyncExecuteResponse(
            success=False,
            results={},
            message=f"Invalid environment: {request.environment}",
            errors=[f"Environment must be one of: {', '.join(VALID_SYNC_ENVIRONMENTS)}"],
            environment=request.environment,
        )

    if not request.confirm:
        return SyncExecuteResponse(
            success=False,
            results={},
            message="Sync not executed. Set confirm=True to execute.",
            errors=["Confirmation required"],
            environment=request.environment,
        )

    if not _check_db_config(request.environment):
        env_help = {
            "local": "Set HOST, DB_NAME, DB_USER, DB_PASSWORD environment variables.",
            "staging": "Set DATABASE_URL_STAGING environment variable.",
            "prod": "Set DATABASE_URL_PROD environment variable.",
        }
        return SyncExecuteResponse(
            success=False,
            results={},
            message=f"Database configuration not found for {request.environment}.",
            errors=[env_help.get(request.environment, "")],
            environment=request.environment,
        )

    try:
        from app.sync.db_client import DBClient, DBConfig
        from app.utils.paths import PRUEBAS_FINALIZADAS_DIR

        extracted = _extract_data(
            request.entities,
            subject_id=subject_id,
        )

        # Auto-upload images to S3 only when syncing question content
        images_uploaded = 0
        sync_question_content = "questions" in request.entities
        if sync_question_content and _check_s3_config() and extracted["questions"]:
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

        payload = _build_payload(
            extracted, subject_id=subject_id,
            entities=request.entities,
        )

        # Connect to the appropriate database based on environment
        db_config = DBConfig.for_environment(request.environment)
        db_client = DBClient(db_config)
        results = db_client.sync_all(payload, dry_run=False)

        total_affected = sum(results.values())
        msg = f"Sync to {request.environment} completed for {subject_id}. "
        msg += f"{total_affected} total rows affected."
        if images_uploaded > 0:
            msg += f" {images_uploaded} questions processed for S3 images."

        return SyncExecuteResponse(
            success=True,
            results=results,
            message=msg,
            errors=[],
            environment=request.environment,
        )

    except ValueError as e:
        logger.exception("Configuration error during course sync")
        return SyncExecuteResponse(
            success=False,
            results={},
            message=f"Configuration error: {e!s}",
            errors=[str(e)],
            environment=request.environment,
        )
    except Exception as e:
        logger.exception("Error during course sync execution")
        return SyncExecuteResponse(
            success=False,
            results={},
            message=f"Sync failed: {e!s}",
            errors=[str(e)],
            environment=request.environment,
        )


@router.get("/{subject_id}/sync/tests-status")
def get_tests_sync_status(
    subject_id: str,
    environment: str = "local",
) -> dict:
    """Get sync status for all tests in one batch call.

    Returns {tests: {test_id: TestSyncDiff, ...}, error: str | null}.
    Efficient: uses a single DB connection for all tests.
    """
    if subject_id not in SUBJECTS_CONFIG:
        raise HTTPException(status_code=404, detail=f"Subject '{subject_id}' not found")

    if environment not in VALID_SYNC_ENVIRONMENTS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid environment: {environment}"
        )

    from api.services.status_tracker import StatusTracker
    from api.services.sync_service import get_batch_sync_diff

    tracker = StatusTracker(subject_id)
    test_ids = [d.name for d in tracker.get_test_dirs()]

    try:
        diffs = get_batch_sync_diff(test_ids, environment)
        return {"tests": diffs, "error": None}
    except Exception as e:
        logger.exception("Error computing batch sync status")
        return {"tests": {}, "error": str(e)}


@router.get("/{subject_id}/sync/diff")
def get_course_sync_diff(
    subject_id: str,
    environment: str = "local",
) -> dict:
    """Get diff between local data and database for this course.

    Returns what would be new, modified, or deleted if a sync were performed.
    """
    if subject_id not in SUBJECTS_CONFIG:
        raise HTTPException(status_code=404, detail=f"Subject '{subject_id}' not found")

    if environment not in VALID_SYNC_ENVIRONMENTS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid environment: {environment}"
        )

    from api.routers.sync import _api_to_db_subject_id, _check_db_config, _extract_data
    from app.sync.diff import compute_sync_diff

    # Check if environment is configured
    if not _check_db_config(environment):
        return {
            "environment": environment,
            "has_changes": False,
            "entities": {},
            "error": f"Database not configured for {environment}",
        }

    try:
        # Extract all data for comparison
        extracted = _extract_data(
            ["standards", "atoms", "tests", "questions", "variants"],
            subject_id=subject_id,
        )

        # Convert API subject_id to DB format for querying
        db_subject_id = _api_to_db_subject_id(subject_id)

        # Compute diff using DB-format subject_id
        diff = compute_sync_diff(extracted, environment, db_subject_id)
        return diff.to_dict()

    except Exception as e:
        logger.exception("Error computing sync diff")
        return {
            "environment": environment,
            "has_changes": False,
            "entities": {},
            "error": str(e),
        }
