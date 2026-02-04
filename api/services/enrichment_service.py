"""Enrichment service for test-level feedback generation.

Manages async enrichment jobs that run the QuestionPipeline to add feedback
to questions. Uses in-memory storage for job state (Redis recommended for production).
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from api.config import PRUEBAS_FINALIZADAS_DIR
from app.question_feedback.pipeline import QuestionPipeline
from app.question_feedback.utils.image_utils import extract_image_urls

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentJob:
    """State for an enrichment job."""

    job_id: str
    status: str  # started, in_progress, completed, failed
    total: int
    completed: int
    successful: int
    failed: int
    results: list[dict] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    current_question: str | None = None


# In-memory job storage (use Redis in production)
_jobs: dict[str, EnrichmentJob] = {}


def _get_questions_to_enrich(
    test_id: str,
    question_ids: list[str] | None = None,
    all_tagged: bool = False,
    skip_already_enriched: bool = True,
) -> list[dict]:
    """Get list of questions to enrich from the test folder.

    Returns list of dicts with: id, qti_xml, image_urls, output_dir
    """
    base_path = PRUEBAS_FINALIZADAS_DIR / test_id / "qti"
    questions: list[dict] = []

    if not base_path.exists():
        logger.warning(f"Test QTI folder not found: {base_path}")
        return questions

    # Get all Q* folders, sorted by question number
    q_folders = sorted(
        [f for f in base_path.iterdir() if f.is_dir() and f.name.startswith("Q")],
        key=lambda p: int(p.name[1:]) if p.name[1:].isdigit() else 0,
    )

    for q_folder in q_folders:
        question_num = q_folder.name  # e.g., "Q6"
        question_id = f"{test_id}-{question_num}"

        # Filter by specific question_ids if provided
        if question_ids and question_num not in question_ids:
            continue

        # Check if tagged (metadata_tags.json exists with selected_atoms)
        metadata_path = q_folder / "metadata_tags.json"
        if not metadata_path.exists():
            continue

        try:
            with open(metadata_path, encoding="utf-8") as f:
                metadata = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read metadata for {question_id}: {e}")
            continue

        # Skip if not tagged (no atoms selected) when all_tagged is True
        if all_tagged and not metadata.get("selected_atoms"):
            continue

        # Check if already enriched
        validated_xml_path = q_folder / "question_validated.xml"
        if skip_already_enriched and validated_xml_path.exists():
            continue

        # Read original QTI XML
        qti_path = q_folder / "question.xml"
        if not qti_path.exists():
            continue

        try:
            qti_xml = qti_path.read_text(encoding="utf-8")
        except OSError as e:
            logger.warning(f"Failed to read QTI for {question_id}: {e}")
            continue

        # Extract image URLs from QTI
        image_urls = extract_image_urls(qti_xml)

        questions.append({
            "id": question_id,
            "question_num": question_num,
            "qti_xml": qti_xml,
            "image_urls": image_urls if image_urls else None,
            "output_dir": str(q_folder),
        })

    return questions


async def start_enrichment_job(
    test_id: str,
    question_ids: list[str] | None = None,
    all_tagged: bool = False,
    skip_already_enriched: bool = True,
) -> tuple[str, int, float]:
    """Start async enrichment job.

    Returns:
        Tuple of (job_id, questions_to_process, estimated_cost_usd)
    """
    job_id = f"enrich-{uuid.uuid4().hex[:8]}"

    # Get questions to process
    questions = _get_questions_to_enrich(
        test_id, question_ids, all_tagged, skip_already_enriched
    )

    job = EnrichmentJob(
        job_id=job_id,
        status="started",
        total=len(questions),
        completed=0,
        successful=0,
        failed=0,
        results=[],
    )
    _jobs[job_id] = job

    estimated_cost = get_enrichment_cost_estimate(len(questions))

    # Start background task
    asyncio.create_task(_run_enrichment(job_id, questions))

    return job_id, len(questions), estimated_cost


async def _run_enrichment(job_id: str, questions: list[dict]) -> None:
    """Run enrichment in background.

    Uses asyncio.to_thread() to run sync pipeline.process()
    without blocking the event loop.
    """
    job = _jobs.get(job_id)
    if not job:
        logger.error(f"Job {job_id} not found")
        return

    job.status = "in_progress"

    # Create pipeline instance
    pipeline = QuestionPipeline()

    for q in questions:
        job.current_question = q["id"]

        try:
            # Run sync pipeline in thread pool to avoid blocking
            result = await asyncio.to_thread(
                pipeline.process,
                question_id=q["id"],
                qti_xml=q["qti_xml"],
                image_urls=q.get("image_urls"),
                output_dir=Path(q["output_dir"]),
            )

            job.completed += 1

            if result.success:
                job.successful += 1
                job.results.append({"question_id": q["id"], "status": "success"})
                logger.info(f"Enrichment succeeded for {q['id']}")
            else:
                job.failed += 1
                error_msg = result.error or "Unknown error"
                if result.xsd_errors:
                    error_msg = f"XSD validation failed: {result.xsd_errors}"
                job.results.append({
                    "question_id": q["id"],
                    "status": "failed",
                    "error": error_msg,
                })
                logger.warning(f"Enrichment failed for {q['id']}: {error_msg}")

        except Exception as e:
            job.completed += 1
            job.failed += 1
            job.results.append({
                "question_id": q["id"],
                "status": "failed",
                "error": str(e),
            })
            logger.exception(f"Exception during enrichment for {q['id']}")

    job.status = "completed"
    job.current_question = None
    job.completed_at = datetime.now(timezone.utc)
    logger.info(
        f"Enrichment job {job_id} completed: "
        f"{job.successful} succeeded, {job.failed} failed"
    )


def get_job_status(job_id: str) -> EnrichmentJob | None:
    """Get job status by ID."""
    return _jobs.get(job_id)


def get_enrichment_cost_estimate(question_count: int) -> float:
    """Calculate estimated cost for enrichment.

    Based on GPT 5.1 pricing:
    - ~3,000 input tokens @ $1.25/1M = $0.00375
    - ~2,000 output tokens @ $10.00/1M = $0.02
    - Total per question: ~$0.024
    """
    cost_per_question = 0.024
    return round(question_count * cost_per_question, 2)
