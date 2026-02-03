"""Overview router - dashboard home data.

GET /api/overview - Returns stats for all subjects.
GET /api/config-status - Returns configuration status for all services.
"""

from __future__ import annotations

import os

from fastapi import APIRouter

from api.config import SUBJECTS_CONFIG
from api.schemas.api_models import OverviewResponse, SubjectBrief, SubjectStats
from api.services.status_tracker import StatusTracker

router = APIRouter()


@router.get("/overview", response_model=OverviewResponse)
async def get_overview() -> OverviewResponse:
    """Get overview data for all subjects.

    Returns quick stats for each subject to display on dashboard cards.
    """
    subjects: list[SubjectBrief] = []

    for subject_id, config in SUBJECTS_CONFIG.items():
        tracker = StatusTracker(subject_id)
        stats_data = tracker.get_subject_stats()

        subjects.append(
            SubjectBrief(
                id=subject_id,
                name=config["name"],
                full_name=config["full_name"],
                year=config["year"],
                stats=SubjectStats(**stats_data),
            )
        )

    return OverviewResponse(subjects=subjects)


@router.get("/config-status")
async def get_config_status() -> dict:
    """Get configuration status for all external services.

    Returns which services are properly configured based on environment variables.
    This helps users understand what features will work.
    """
    # Database configuration (for sync)
    db_configured = bool(os.getenv("HOST"))

    # S3 configuration (for image upload)
    s3_key = os.getenv("AWS_S3_KEY") or os.getenv("AWS_ACCESS_KEY_ID")
    s3_secret = os.getenv("AWS_S3_SECRET") or os.getenv("AWS_SECRET_ACCESS_KEY")
    s3_configured = bool(s3_key and s3_secret)

    # AI configuration (for pipelines)
    gemini_configured = bool(os.getenv("GEMINI_API_KEY"))
    openai_configured = bool(os.getenv("OPENAI_API_KEY"))

    return {
        "database": {
            "configured": db_configured,
            "required_vars": ["HOST", "PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"],
            "description": "Required for database sync",
        },
        "s3": {
            "configured": s3_configured,
            "required_vars": ["AWS_S3_KEY", "AWS_S3_SECRET"],
            "optional_vars": ["S3_BUCKET", "S3_REGION"],
            "description": "Required for S3 image upload (uses default bucket: paes-question-images)",
        },
        "ai": {
            "gemini_configured": gemini_configured,
            "openai_configured": openai_configured,
            "any_configured": gemini_configured or openai_configured,
            "required_vars": ["GEMINI_API_KEY"],
            "optional_vars": ["OPENAI_API_KEY"],
            "description": "GEMINI_API_KEY required for AI pipelines. OPENAI_API_KEY optional as fallback.",
        },
        "summary": {
            "can_sync": db_configured,
            "can_upload_images": s3_configured,
            "can_run_ai_pipelines": gemini_configured or openai_configured,
        },
    }
