"""Sync router for database synchronization.

Provides endpoints to preview and execute syncs to the production database.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException

from api.schemas.api_models import (
    SyncExecuteRequest,
    SyncExecuteResponse,
    SyncPreviewRequest,
    SyncPreviewResponse,
    SyncTableSummary,
)

# Load environment variables for database config
REPO_ROOT = Path(__file__).parent.parent.parent
load_dotenv(REPO_ROOT / ".env")

logger = logging.getLogger(__name__)

router = APIRouter()


def _check_db_config() -> bool:
    """Check if database configuration is available."""
    return bool(os.getenv("HOST"))


def _extract_data(
    entities: list[str],
    include_variants: bool,
    include_diagnostic_variants: bool = True,
) -> dict:
    """Extract data from content repo based on requested entities.

    Args:
        entities: List of entity types to extract
        include_variants: Whether to include variants
        include_diagnostic_variants: Whether to include diagnostic test variants

    Returns:
        Dict with extracted data for each entity type
    """
    # Lazy import to avoid loading sync modules at startup
    from app.sync.extractors import (
        extract_all_tests,
        extract_atoms,
        extract_standards,
    )
    from app.sync.variant_extractors import extract_all_variants

    result = {
        "standards": [],
        "atoms": [],
        "tests": [],
        "questions": [],
        "variants": [],
    }

    # Determine what to extract based on entities list
    sync_standards = "standards" in entities
    sync_atoms = "atoms" in entities
    sync_tests = "tests" in entities
    sync_questions = "questions" in entities
    sync_variants = include_variants or "variants" in entities

    if sync_standards:
        result["standards"] = extract_standards()

    if sync_atoms:
        result["atoms"] = extract_atoms()

    if sync_tests or sync_questions:
        tests, questions = extract_all_tests()
        if sync_tests:
            result["tests"] = tests
        if sync_questions:
            result["questions"] = questions

    if sync_variants:
        # Extract both regular and diagnostic variants
        result["variants"] = extract_all_variants(
            include_diagnostic=include_diagnostic_variants
        )

    return result


def _build_payload(extracted_data: dict):
    """Build sync payload from extracted data."""
    from app.sync.transformers import build_sync_payload

    return build_sync_payload(
        standards=extracted_data["standards"],
        atoms=extracted_data["atoms"],
        tests=extracted_data["tests"],
        questions=extracted_data["questions"],
        variants=extracted_data["variants"] if extracted_data["variants"] else None,
    )


@router.post("/preview", response_model=SyncPreviewResponse)
async def preview_sync(request: SyncPreviewRequest) -> SyncPreviewResponse:
    """Preview what would be synced (dry run).

    This endpoint extracts data from the content repo and shows what would
    be synced to the database without making any changes.
    """
    try:
        # Extract data based on requested entities
        extracted = _extract_data(request.entities, request.include_variants)

        # Build the payload to get accurate counts
        payload = _build_payload(extracted)
        summary = payload.summary()

        # Build table summaries
        tables = []

        if "subjects" in summary and summary["subjects"] > 0:
            tables.append(SyncTableSummary(
                table="subjects",
                total=summary["subjects"],
            ))

        if "standards" in summary and summary["standards"] > 0:
            tables.append(SyncTableSummary(
                table="standards",
                total=summary["standards"],
            ))

        if "atoms" in summary and summary["atoms"] > 0:
            tables.append(SyncTableSummary(
                table="atoms",
                total=summary["atoms"],
            ))

        if "tests" in summary and summary["tests"] > 0:
            tables.append(SyncTableSummary(
                table="tests",
                total=summary["tests"],
            ))

        if "questions" in summary and summary["questions"] > 0:
            # Count official vs variants
            official_count = len(extracted["questions"])
            variant_count = len(extracted["variants"])
            tables.append(SyncTableSummary(
                table="questions",
                total=summary["questions"],
                breakdown={
                    "official": official_count,
                    "variants": variant_count,
                },
            ))

        if "question_atoms" in summary and summary["question_atoms"] > 0:
            tables.append(SyncTableSummary(
                table="question_atoms",
                total=summary["question_atoms"],
            ))

        if "test_questions" in summary and summary["test_questions"] > 0:
            tables.append(SyncTableSummary(
                table="test_questions",
                total=summary["test_questions"],
            ))

        # Check for warnings
        warnings = []
        if not _check_db_config():
            warnings.append(
                "Database configuration not found. "
                "Set HOST, DB_NAME, DB_USER, DB_PASSWORD environment variables."
            )

        return SyncPreviewResponse(
            tables=tables,
            summary={
                "entities_requested": request.entities,
                "include_variants": request.include_variants,
                "upload_images": request.upload_images,
                "total_tables": len(tables),
            },
            warnings=warnings,
        )

    except Exception as e:
        logger.exception("Error during sync preview")
        raise HTTPException(status_code=500, detail=f"Preview failed: {e!s}") from e


def _check_s3_config() -> bool:
    """Check if S3 configuration is available."""
    return bool(os.getenv("S3_BUCKET"))


@router.post("/execute", response_model=SyncExecuteResponse)
async def execute_sync(request: SyncExecuteRequest) -> SyncExecuteResponse:
    """Execute sync to the production database.

    This endpoint actually syncs data to the database. Requires confirm=True.
    If upload_images is True, uploads local images to S3 and updates QTI XML.
    """
    # Safety check: require explicit confirmation
    if not request.confirm:
        return SyncExecuteResponse(
            success=False,
            results={},
            message="Sync not executed. Set confirm=True to execute.",
            errors=["Confirmation required"],
        )

    # Check database configuration
    if not _check_db_config():
        return SyncExecuteResponse(
            success=False,
            results={},
            message="Database configuration not found.",
            errors=[
                "Set HOST, DB_NAME, DB_USER, DB_PASSWORD environment variables."
            ],
        )

    # Check S3 configuration if image upload requested
    if request.upload_images and not _check_s3_config():
        return SyncExecuteResponse(
            success=False,
            results={},
            message="S3 configuration not found but image upload requested.",
            errors=[
                "Set S3_BUCKET, AWS_S3_KEY, AWS_S3_SECRET environment variables."
            ],
        )

    try:
        # Lazy imports
        from app.sync.db_client import DBClient, DBConfig
        from app.utils.paths import PRUEBAS_FINALIZADAS_DIR

        # Extract and transform data
        extracted = _extract_data(request.entities, request.include_variants)

        # Process S3 image uploads if requested
        images_uploaded = 0
        if request.upload_images and extracted["questions"]:
            from app.sync.s3_client import (
                ImageUploader,
                S3Config,
                process_all_questions_images,
            )

            s3_config = S3Config.from_env()
            uploader = ImageUploader(s3_config)

            # Process images and get updated QTI XML
            updated_qti = process_all_questions_images(
                extracted["questions"],
                PRUEBAS_FINALIZADAS_DIR,
                uploader,
            )

            # Update the extracted questions with S3 URLs in their QTI
            for q in extracted["questions"]:
                if q.id in updated_qti:
                    q.qti_xml = updated_qti[q.id]
                    images_uploaded += 1

            logger.info(f"Processed {images_uploaded} questions for S3 images")

        payload = _build_payload(extracted)

        # Connect and sync
        db_config = DBConfig.from_env()
        db_client = DBClient(db_config)

        results = db_client.sync_all(payload, dry_run=False)

        # Format results message
        total_affected = sum(results.values())
        msg = f"Sync completed. {total_affected} total rows affected."
        if request.upload_images:
            msg += f" {images_uploaded} questions processed for S3 images."

        return SyncExecuteResponse(
            success=True,
            results=results,
            message=msg,
            errors=[],
        )

    except ValueError as e:
        logger.exception("Configuration error during sync")
        return SyncExecuteResponse(
            success=False,
            results={},
            message=f"Configuration error: {e!s}",
            errors=[str(e)],
        )
    except Exception as e:
        logger.exception("Error during sync execution")
        return SyncExecuteResponse(
            success=False,
            results={},
            message=f"Sync failed: {e!s}",
            errors=[str(e)],
        )


@router.get("/status")
async def sync_status() -> dict:
    """Get current sync status and configuration availability."""
    has_db_config = _check_db_config()
    has_s3_config = bool(os.getenv("S3_BUCKET"))

    return {
        "database_configured": has_db_config,
        "s3_configured": has_s3_config,
        "available_entities": ["standards", "atoms", "tests", "questions", "variants"],
    }
