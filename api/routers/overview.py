"""Overview router - dashboard home data.

GET /api/overview - Returns stats for all subjects.
"""

from __future__ import annotations

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
