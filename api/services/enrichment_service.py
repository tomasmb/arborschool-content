"""Enrichment service for test-level feedback generation.

Manages async enrichment jobs that run the QuestionPipeline to add feedback
to questions AND variants. Uses in-memory storage for job state (Redis recommended
for production).

Follows DRY/SOLID - same logic handles both questions and variants, just different
source directories.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from api.config import PRUEBAS_ALTERNATIVAS_DIR, PRUEBAS_FINALIZADAS_DIR
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


def _get_items_to_enrich_from_path(
    base_path: Path,
    id_prefix: str,
    item_ids: list[str] | None = None,
    require_tagged: bool = False,
    skip_already_enriched: bool = True,
) -> list[dict]:
    """Get list of items to enrich from a folder containing question.xml files.

    This is the core function that handles both questions and variants.
    Returns list of dicts with: id, qti_xml, image_urls, output_dir
    """
    items: list[dict] = []

    logger.warning(
        f"[ENRICH DEBUG] _get_items_to_enrich_from_path called with: "
        f"base_path={base_path}, id_prefix={id_prefix}, item_ids={item_ids}, "
        f"require_tagged={require_tagged}, skip_already_enriched={skip_already_enriched}"
    )

    if not base_path.exists():
        logger.warning(f"Path not found: {base_path}")
        return items

    # Get all subfolders that might contain question.xml
    folders = sorted(
        [f for f in base_path.iterdir() if f.is_dir()],
        key=lambda p: p.name,
    )

    logger.warning(f"[ENRICH DEBUG] Found {len(folders)} folders: {[f.name for f in folders]}")

    for folder in folders:
        item_name = folder.name
        item_id = f"{id_prefix}-{item_name}"

        # Filter by specific ids if provided
        if item_ids and item_name not in item_ids:
            continue

        # Check if tagged (metadata_tags.json exists) - only if required
        metadata_path = folder / "metadata_tags.json"
        if require_tagged and not metadata_path.exists():
            continue

        if require_tagged and metadata_path.exists():
            try:
                with open(metadata_path, encoding="utf-8") as f:
                    metadata = json.load(f)
                if not metadata.get("selected_atoms"):
                    continue
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to read metadata for {item_id}: {e}")
                continue

        # Check if already enriched
        validated_xml_path = folder / "question_validated.xml"
        if skip_already_enriched and validated_xml_path.exists():
            logger.debug(f"[ENRICH DEBUG] Skipping {item_id}: already enriched")
            continue

        # Read original QTI XML
        qti_path = folder / "question.xml"
        if not qti_path.exists():
            logger.debug(f"[ENRICH DEBUG] Skipping {item_id}: no question.xml")
            continue

        logger.warning(f"[ENRICH DEBUG] Including {item_id} for enrichment")

        try:
            qti_xml = qti_path.read_text(encoding="utf-8")
        except OSError as e:
            logger.warning(f"Failed to read QTI for {item_id}: {e}")
            continue

        # Extract image URLs from QTI
        image_urls = extract_image_urls(qti_xml)

        items.append({
            "id": item_id,
            "item_name": item_name,
            "qti_xml": qti_xml,
            "image_urls": image_urls if image_urls else None,
            "output_dir": str(folder),
        })

    logger.warning(f"[ENRICH DEBUG] Returning {len(items)} items to enrich")
    return items


def _get_questions_to_enrich(
    test_id: str,
    question_ids: list[str] | None = None,
    all_tagged: bool = False,
    skip_already_enriched: bool = True,
) -> list[dict]:
    """Get list of questions to enrich from the test folder."""
    base_path = PRUEBAS_FINALIZADAS_DIR / test_id / "qti"
    logger.warning(
        f"[ENRICH DEBUG] _get_questions_to_enrich: test_id={test_id}, "
        f"question_ids={question_ids}, all_tagged={all_tagged}, "
        f"skip_already_enriched={skip_already_enriched}, base_path={base_path}"
    )
    return _get_items_to_enrich_from_path(
        base_path=base_path,
        id_prefix=test_id,
        item_ids=question_ids,
        require_tagged=all_tagged,
        skip_already_enriched=skip_already_enriched,
    )


def _get_variants_to_enrich(
    test_id: str,
    question_num: str | None = None,
    skip_already_enriched: bool = True,
) -> list[dict]:
    """Get list of variants to enrich from the alternativas folder.

    Variants are stored in: PRUEBAS_ALTERNATIVAS_DIR/{test_id}/Q{num}/approved/{variant}/
    """
    variants: list[dict] = []
    alternativas_base = PRUEBAS_ALTERNATIVAS_DIR / test_id

    if not alternativas_base.exists():
        logger.warning(f"Alternativas folder not found: {alternativas_base}")
        return variants

    # Get question folders to scan
    if question_num:
        q_folders = [alternativas_base / question_num]
    else:
        q_folders = sorted(
            [f for f in alternativas_base.iterdir() if f.is_dir() and f.name.startswith("Q")],
            key=lambda p: int(p.name[1:]) if p.name[1:].isdigit() else 0,
        )

    for q_folder in q_folders:
        approved_dir = q_folder / "approved"
        if not approved_dir.exists():
            continue

        q_name = q_folder.name
        items = _get_items_to_enrich_from_path(
            base_path=approved_dir,
            id_prefix=f"{test_id}-{q_name}",
            item_ids=None,
            require_tagged=False,  # Variants don't require tagging
            skip_already_enriched=skip_already_enriched,
        )
        variants.extend(items)

    return variants


async def start_enrichment_job(
    test_id: str,
    question_ids: list[str] | None = None,
    all_tagged: bool = False,
    skip_already_enriched: bool = True,
) -> tuple[str, int, float]:
    """Start async enrichment job for questions.

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


async def start_variant_enrichment_job(
    test_id: str,
    question_num: str | None = None,
    skip_already_enriched: bool = True,
) -> tuple[str, int, float]:
    """Start async enrichment job for variants.

    Uses the same enrichment logic as questions - DRY principle.

    Args:
        test_id: Test identifier
        question_num: Optional - only enrich variants for this question (e.g. "Q1")
        skip_already_enriched: Skip variants that already have feedback

    Returns:
        Tuple of (job_id, variants_to_process, estimated_cost_usd)
    """
    job_id = f"enrich-variant-{uuid.uuid4().hex[:8]}"

    # Get variants to process (same logic, different source)
    variants = _get_variants_to_enrich(test_id, question_num, skip_already_enriched)

    job = EnrichmentJob(
        job_id=job_id,
        status="started",
        total=len(variants),
        completed=0,
        successful=0,
        failed=0,
        results=[],
    )
    _jobs[job_id] = job

    estimated_cost = get_enrichment_cost_estimate(len(variants))

    # Uses the same _run_enrichment function - DRY!
    asyncio.create_task(_run_enrichment(job_id, variants))

    return job_id, len(variants), estimated_cost


# Concurrency limit for parallel processing
MAX_CONCURRENT_JOBS = 10


async def _run_enrichment(job_id: str, questions: list[dict]) -> None:
    """Run enrichment in background with parallel processing.

    Uses asyncio.Semaphore to limit concurrency to MAX_CONCURRENT_JOBS.
    Each question is processed in a separate thread via asyncio.to_thread().
    """
    job = _jobs.get(job_id)
    if not job:
        logger.error(f"Job {job_id} not found")
        return

    job.status = "in_progress"

    # Create pipeline instance - wrapped in try/except to catch initialization errors
    try:
        pipeline = QuestionPipeline()
    except Exception as e:
        job.status = "failed"
        job.completed_at = datetime.now(timezone.utc)
        error_msg = f"Pipeline initialization failed: {e}"
        job.results.append({"question_id": "init", "status": "failed", "error": error_msg})
        logger.exception(error_msg)
        return

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)

    async def process_question(q: dict) -> dict:
        """Process a single question with semaphore-controlled concurrency."""
        async with semaphore:
            job.current_question = q["id"]
            try:
                result = await asyncio.to_thread(
                    pipeline.process,
                    question_id=q["id"],
                    qti_xml=q["qti_xml"],
                    image_urls=q.get("image_urls"),
                    output_dir=Path(q["output_dir"]),
                )

                if result.success:
                    logger.info(f"Enrichment succeeded for {q['id']}")
                    return {"question_id": q["id"], "status": "success", "success": True}

                error_msg = result.error or "Unknown error"
                if result.xsd_errors:
                    error_msg = f"XSD validation failed: {result.xsd_errors}"
                logger.warning(f"Enrichment failed for {q['id']}: {error_msg}")
                return {
                    "question_id": q["id"],
                    "status": "failed",
                    "error": error_msg,
                    "success": False,
                }

            except Exception as e:
                logger.exception(f"Exception during enrichment for {q['id']}")
                return {
                    "question_id": q["id"],
                    "status": "failed",
                    "error": str(e),
                    "success": False,
                }

    # Run all questions in parallel (limited by semaphore)
    tasks = [process_question(q) for q in questions]
    results = await asyncio.gather(*tasks)

    # Update job with results
    for result in results:
        job.completed += 1
        if result.get("success"):
            job.successful += 1
            job.results.append({"question_id": result["question_id"], "status": "success"})
        else:
            job.failed += 1
            job.results.append({
                "question_id": result["question_id"],
                "status": "failed",
                "error": result.get("error", "Unknown error"),
            })

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
