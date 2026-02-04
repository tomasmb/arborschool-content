"""Sync router for database synchronization.

Provides global endpoints to preview and execute syncs to the production database.
Course-scoped sync endpoints are in api/routers/course_sync.py.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
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
from app.utils.paths import ATOMS_DIR, STANDARDS_DIR

# Load environment variables for database config
REPO_ROOT = Path(__file__).parent.parent.parent
load_dotenv(REPO_ROOT / ".env")

logger = logging.getLogger(__name__)

router = APIRouter()

# Type alias for environment
SyncEnvironment = Literal["local", "staging", "prod"]


def _check_db_config(environment: SyncEnvironment = "local") -> bool:
    """Check if database configuration is available for the given environment."""
    from app.sync.db_client import DBConfig
    return DBConfig.check_environment_configured(environment)


def _get_subject_files(subject_id: str) -> tuple[Path | None, Path | None]:
    """Get the standards and atoms file paths for a subject.

    Args:
        subject_id: Subject identifier (e.g., "paes-m1-2026")

    Returns:
        Tuple of (standards_file, atoms_file) paths, or None if not configured
    """
    config = SUBJECTS_CONFIG.get(subject_id)
    if not config:
        return None, None

    standards_file = STANDARDS_DIR / config.get("standards_file", "")
    atoms_file = ATOMS_DIR / config.get("atoms_file", "")

    return standards_file, atoms_file


def _extract_data(
    entities: list[str],
    subject_id: str | None = None,
) -> dict:
    """Extract data from content repo based on requested entities.

    Args:
        entities: List of entity types to extract (standards, atoms, tests,
            questions, variants)
        subject_id: Optional subject ID to scope extraction. If provided, only
            data for that subject is extracted.

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

    # Get subject-specific file paths if subject_id provided
    standards_file, atoms_file = None, None
    if subject_id:
        standards_file, atoms_file = _get_subject_files(subject_id)

    # Determine what to extract based on entities list
    sync_standards = "standards" in entities
    sync_atoms = "atoms" in entities
    sync_tests = "tests" in entities
    sync_questions = "questions" in entities
    sync_variants = "variants" in entities

    if sync_standards:
        result["standards"] = extract_standards(standards_file)

    if sync_atoms:
        result["atoms"] = extract_atoms(atoms_file)

    if sync_tests or sync_questions:
        tests, questions = extract_all_tests()
        if sync_tests:
            result["tests"] = tests
        if sync_questions:
            result["questions"] = questions

    if sync_variants:
        result["variants"] = extract_all_variants()

    return result


def _api_to_db_subject_id(api_subject_id: str) -> str:
    """Convert API subject ID to database subject ID.

    API uses "paes-m1-2026" format, DB uses "paes_m1" format.
    """
    # Map API IDs to DB IDs
    mapping = {
        "paes-m1-2026": "paes_m1",
    }
    return mapping.get(api_subject_id, api_subject_id.replace("-", "_").rsplit("_", 1)[0])


def _build_payload(extracted_data: dict, subject_id: str | None = None):
    """Build sync payload from extracted data.

    Args:
        extracted_data: Dict with extracted data
        subject_id: Optional API subject ID (e.g., "paes-m1-2026")
    """
    from app.sync.transformers import build_sync_payload

    # Convert API subject_id to DB format
    db_subject_id = _api_to_db_subject_id(subject_id) if subject_id else "paes_m1"

    return build_sync_payload(
        standards=extracted_data["standards"],
        atoms=extracted_data["atoms"],
        tests=extracted_data["tests"],
        questions=extracted_data["questions"],
        variants=extracted_data["variants"] if extracted_data["variants"] else None,
        subject_id=db_subject_id,
    )


@router.post("/preview", response_model=SyncPreviewResponse)
async def preview_sync(request: SyncPreviewRequest) -> SyncPreviewResponse:
    """Preview what would be synced (dry run).

    This endpoint extracts data from the content repo and shows what would
    be synced to the database without making any changes.
    """
    # Validate environment
    if request.environment not in VALID_SYNC_ENVIRONMENTS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid environment: {request.environment}"
        )

    try:
        # Extract data based on requested entities
        extracted = _extract_data(request.entities)

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
                "entities_requested": request.entities,
                "total_tables": len(tables),
            },
            warnings=warnings,
            environment=request.environment,
        )

    except Exception as e:
        logger.exception("Error during sync preview")
        raise HTTPException(status_code=500, detail=f"Preview failed: {e!s}") from e


def _check_s3_config() -> bool:
    """Check if S3 configuration is available (AWS credentials present)."""
    access_key = os.getenv("AWS_S3_KEY") or os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_S3_SECRET") or os.getenv("AWS_SECRET_ACCESS_KEY")
    return bool(access_key and secret_key)


@router.post("/execute", response_model=SyncExecuteResponse)
async def execute_sync(request: SyncExecuteRequest) -> SyncExecuteResponse:
    """Execute sync to the database.

    This endpoint actually syncs data to the database. Requires confirm=True.
    Automatically uploads images to S3 if S3 is configured and questions are synced.
    """
    # Validate environment
    if request.environment not in VALID_SYNC_ENVIRONMENTS:
        return SyncExecuteResponse(
            success=False,
            results={},
            message=f"Invalid environment: {request.environment}",
            errors=[f"Environment must be one of: {', '.join(VALID_SYNC_ENVIRONMENTS)}"],
            environment=request.environment,
        )

    # Safety check: require explicit confirmation
    if not request.confirm:
        return SyncExecuteResponse(
            success=False,
            results={},
            message="Sync not executed. Set confirm=True to execute.",
            errors=["Confirmation required"],
            environment=request.environment,
        )

    # Check database configuration for the target environment
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
        # Lazy imports
        from app.sync.db_client import DBClient, DBConfig
        from app.utils.paths import PRUEBAS_FINALIZADAS_DIR

        # Extract and transform data
        extracted = _extract_data(request.entities)

        # Auto-upload images to S3 if configured and questions are being synced
        images_uploaded = 0
        if _check_s3_config() and extracted["questions"]:
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

        # Connect to the appropriate database based on environment
        db_config = DBConfig.for_environment(request.environment)
        db_client = DBClient(db_config)

        results = db_client.sync_all(payload, dry_run=False)

        # Format results message
        total_affected = sum(results.values())
        msg = f"Sync to {request.environment} completed. {total_affected} total rows affected."
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
        logger.exception("Configuration error during sync")
        return SyncExecuteResponse(
            success=False,
            results={},
            message=f"Configuration error: {e!s}",
            errors=[str(e)],
            environment=request.environment,
        )
    except Exception as e:
        logger.exception("Error during sync execution")
        return SyncExecuteResponse(
            success=False,
            results={},
            message=f"Sync failed: {e!s}",
            errors=[str(e)],
            environment=request.environment,
        )


@router.get("/status")
async def sync_status() -> dict:
    """Get current sync status and configuration availability for all environments."""
    has_s3_config = _check_s3_config()

    # Check each environment's database configuration
    environments = {
        env: _check_db_config(env)
        for env in VALID_SYNC_ENVIRONMENTS
    }

    return {
        "environments": environments,
        "s3_configured": has_s3_config,
        "available_entities": ["standards", "atoms", "tests", "questions", "variants"],
    }
