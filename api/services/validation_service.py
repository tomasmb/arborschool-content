"""Validation service for test-level LLM validation.

Manages async validation jobs that run the FinalValidator to check
questions AND variants that have been enriched with feedback.

Follows DRY/SOLID - same validation logic handles both questions and variants.
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
from api.utils.validation_io import is_can_sync, read_validation_data
from app.question_feedback.utils.image_utils import extract_image_urls
from app.question_feedback.validator import FinalValidator

logger = logging.getLogger(__name__)


@dataclass
class ValidationJob:
    """State for a validation job."""

    job_id: str
    status: str  # started, in_progress, completed, failed
    total: int
    completed: int
    passed: int
    failed: int
    results: list[dict] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


# In-memory job storage (use Redis in production)
_validation_jobs: dict[str, ValidationJob] = {}


def _get_items_to_validate_from_path(
    base_path: Path,
    id_prefix: str,
    item_ids: list[str] | None = None,
    revalidate_passed: bool = False,
) -> list[dict]:
    """Get list of items to validate from a folder containing enriched XML files.

    This is the core function that handles both questions and variants.
    Only returns items that have been enriched (have question_validated.xml).
    """
    items: list[dict] = []

    if not base_path.exists():
        logger.warning(f"Path not found: {base_path}")
        return items

    # Get all subfolders
    folders = sorted(
        [f for f in base_path.iterdir() if f.is_dir()],
        key=lambda p: p.name,
    )

    for folder in folders:
        item_name = folder.name
        item_id = f"{id_prefix}-{item_name}"

        # Filter by specific ids if provided
        if item_ids and item_name not in item_ids:
            continue

        # Must have validated XML (enriched)
        validated_xml_path = folder / "question_validated.xml"
        if not validated_xml_path.exists():
            continue

        # Skip items that already passed validation
        if not revalidate_passed and is_can_sync(read_validation_data(folder)):
            continue

        try:
            qti_xml = validated_xml_path.read_text(encoding="utf-8")
        except OSError as e:
            logger.warning(f"Failed to read validated XML for {item_id}: {e}")
            continue

        image_urls = extract_image_urls(qti_xml)

        items.append({
            "id": item_id,
            "item_name": item_name,
            "qti_xml": qti_xml,
            "image_urls": image_urls if image_urls else None,
            "output_dir": str(folder),
        })

    return items


def _get_questions_to_validate(
    test_id: str,
    question_ids: list[str] | None = None,
    all_enriched: bool = False,
    revalidate_passed: bool = False,
) -> list[dict]:
    """Get list of questions to validate from the test folder."""
    base_path = PRUEBAS_FINALIZADAS_DIR / test_id / "qti"
    return _get_items_to_validate_from_path(
        base_path=base_path,
        id_prefix=test_id,
        item_ids=question_ids,
        revalidate_passed=revalidate_passed,
    )


def _get_variants_to_validate(
    test_id: str,
    question_num: str | None = None,
    revalidate_passed: bool = False,
) -> list[dict]:
    """Get list of variants to validate from the alternativas folder.

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
        items = _get_items_to_validate_from_path(
            base_path=approved_dir,
            id_prefix=f"{test_id}-{q_name}",
            item_ids=None,
            revalidate_passed=revalidate_passed,
        )
        variants.extend(items)

    return variants


async def start_validation_job(
    test_id: str,
    question_ids: list[str] | None = None,
    all_enriched: bool = False,
    revalidate_passed: bool = False,
) -> tuple[str, int, float]:
    """Start async validation job for questions.

    Returns:
        Tuple of (job_id, questions_to_process, estimated_cost_usd)
    """
    job_id = f"validate-{uuid.uuid4().hex[:8]}"

    questions = _get_questions_to_validate(
        test_id, question_ids, all_enriched, revalidate_passed
    )

    job = ValidationJob(
        job_id=job_id,
        status="started",
        total=len(questions),
        completed=0,
        passed=0,
        failed=0,
        results=[],
    )
    _validation_jobs[job_id] = job

    estimated_cost = get_validation_cost_estimate(len(questions))

    # Start background task
    asyncio.create_task(_run_validation(job_id, questions))

    return job_id, len(questions), estimated_cost


async def start_variant_validation_job(
    test_id: str,
    question_num: str | None = None,
    revalidate_passed: bool = False,
) -> tuple[str, int, float]:
    """Start async validation job for variants.

    Uses the same validation logic as questions - DRY principle.

    Args:
        test_id: Test identifier
        question_num: Optional - only validate variants for this question (e.g. "Q1")
        revalidate_passed: Re-validate variants that already passed

    Returns:
        Tuple of (job_id, variants_to_process, estimated_cost_usd)
    """
    job_id = f"validate-variant-{uuid.uuid4().hex[:8]}"

    # Get variants to process (same logic, different source)
    variants = _get_variants_to_validate(test_id, question_num, revalidate_passed)

    job = ValidationJob(
        job_id=job_id,
        status="started",
        total=len(variants),
        completed=0,
        passed=0,
        failed=0,
        results=[],
    )
    _validation_jobs[job_id] = job

    estimated_cost = get_validation_cost_estimate(len(variants))

    # Uses the same _run_validation function - DRY!
    asyncio.create_task(_run_validation(job_id, variants))

    return job_id, len(variants), estimated_cost


# Concurrency limit for parallel processing
MAX_CONCURRENT_JOBS = 10


async def _run_validation(job_id: str, questions: list[dict]) -> None:
    """Run validation in background with parallel processing.

    Uses asyncio.Semaphore to limit concurrency to MAX_CONCURRENT_JOBS.
    Each question is validated in a separate thread via asyncio.to_thread().
    """
    job = _validation_jobs.get(job_id)
    if not job:
        logger.error(f"Job {job_id} not found")
        return

    job.status = "in_progress"

    # Create validator instance
    validator = FinalValidator()

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)

    async def validate_question(q: dict) -> dict:
        """Validate a single question with semaphore-controlled concurrency."""
        async with semaphore:
            try:
                result = await asyncio.to_thread(
                    validator.validate,
                    qti_xml_with_feedback=q["qti_xml"],
                    image_urls=q.get("image_urls"),
                )

                if result.validation_result == "pass":
                    _update_validation_result(q["output_dir"], result, can_sync=True)
                    logger.info(f"Validation passed for {q['id']}")
                    return {
                        "question_id": q["id"],
                        "status": "pass",
                        "passed": True,
                        "result": result,
                    }

                # Collect failed checks
                failed_checks = []
                check_statuses = {
                    "correct_answer_check": result.correct_answer_check.status.value,
                    "feedback_check": result.feedback_check.status.value,
                    "content_quality_check": result.content_quality_check.status.value,
                    "image_check": result.image_check.status.value,
                    "math_validity_check": result.math_validity_check.status.value,
                }
                for check_name, status in check_statuses.items():
                    if status == "fail":
                        failed_checks.append(check_name)

                # Collect all issues
                issues: list[str] = []
                issues.extend(result.correct_answer_check.issues)
                issues.extend(result.feedback_check.issues)
                issues.extend(result.math_validity_check.issues)

                _update_validation_result(q["output_dir"], result, can_sync=False)
                logger.warning(f"Validation failed for {q['id']}: {failed_checks}")

                return {
                    "question_id": q["id"],
                    "status": "fail",
                    "passed": False,
                    "failed_checks": failed_checks,
                    "issues": issues[:3],
                }

            except Exception as e:
                logger.exception(f"Exception during validation for {q['id']}")
                return {
                    "question_id": q["id"],
                    "status": "fail",
                    "passed": False,
                    "failed_checks": ["exception"],
                    "issues": [str(e)],
                }

    # Run all questions in parallel (limited by semaphore)
    tasks = [validate_question(q) for q in questions]
    results = await asyncio.gather(*tasks)

    # Update job with results
    for result in results:
        job.completed += 1
        if result.get("passed"):
            job.passed += 1
            job.results.append({"question_id": result["question_id"], "status": "pass"})
        else:
            job.failed += 1
            job.results.append({
                "question_id": result["question_id"],
                "status": "fail",
                "failed_checks": result.get("failed_checks", []),
                "issues": result.get("issues", []),
            })

    job.status = "completed"
    job.completed_at = datetime.now(timezone.utc)
    logger.info(
        f"Validation job {job_id} completed: "
        f"{job.passed} passed, {job.failed} failed"
    )


def _update_validation_result(
    output_dir: str,
    result,  # ValidationResult from app.question_feedback.models
    can_sync: bool,
) -> None:
    """Update validation_result.json with final validation results."""
    path = Path(output_dir) / "validation_result.json"

    # Load existing or create new
    data: dict = {}
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}

    # Ensure stages dict exists
    if "stages" not in data:
        data["stages"] = {}

    data["stages"]["final_validation"] = {
        "status": result.validation_result,
        "model": "gpt-5.1",
        "reasoning_effort": "high",
        "checks": {
            "correct_answer_check": result.correct_answer_check.status.value,
            "feedback_check": result.feedback_check.status.value,
            "content_quality_check": result.content_quality_check.status.value,
            "image_check": result.image_check.status.value,
            "math_validity_check": result.math_validity_check.status.value,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    data["can_sync"] = can_sync

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError as e:
        logger.error(f"Failed to write validation result to {path}: {e}")


def get_validation_job_status(job_id: str) -> ValidationJob | None:
    """Get validation job status by ID."""
    return _validation_jobs.get(job_id)


def get_validation_cost_estimate(
    question_count: int,
    avg_images_per_question: float = 0.5,
) -> float:
    """Calculate estimated cost for validation with GPT-5.1.

    Pricing (as of Feb 2026):
    - GPT-5.1 Input: $1.25 per 1M tokens
    - GPT-5.1 Output: $10.00 per 1M tokens

    Token estimates per question:
    - Text input (QTI XML + prompt): ~3,000 tokens
    - Text output (validation JSON): ~800 tokens
    - Images: ~700 tokens per image (high detail, typical 800x600 image)
      Formula: base(70) + tiles(4) × 140 = 630 tokens, rounded up for safety

    Args:
        question_count: Number of questions to validate.
        avg_images_per_question: Average images per question (default 0.5).

    Returns:
        Estimated cost in USD.
    """
    # Token estimates
    text_input_tokens = 3000
    text_output_tokens = 800
    tokens_per_image = 700

    # Pricing per token
    input_price_per_token = 1.25 / 1_000_000  # $1.25 per 1M
    output_price_per_token = 10.00 / 1_000_000  # $10.00 per 1M

    # Calculate per-question cost
    input_tokens = text_input_tokens + (tokens_per_image * avg_images_per_question)
    output_tokens = text_output_tokens

    cost_per_question = (
        input_tokens * input_price_per_token +
        output_tokens * output_price_per_token
    )

    total_cost = question_count * cost_per_question
    return round(total_cost, 3)
