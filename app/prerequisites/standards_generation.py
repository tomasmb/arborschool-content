"""Phase 1: Generate prerequisite standards from demand analysis.

Takes the prerequisite topics identified in Phase 0 and generates full
canonical standards for each, grouped by grade level and processed from
lowest to highest.

Usage:
    python -m app.prerequisites.standards_generation
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from app.llm_clients import LLMResponse, OpenAIClient, load_default_openai_client
from app.prerequisites.constants import GRADE_LEVELS, PREREQ_OUTPUT_DIR, grade_order
from app.prerequisites.demand_analysis import load_demand_analysis
from app.prerequisites.models import PrereqStandard
from app.prerequisites.prompts.standards_generation import (
    build_standards_generation_prompt,
)
from app.standards.helpers import parse_json_response

logger = logging.getLogger(__name__)

_REASONING_EFFORT = "high"
_REQUEST_TIMEOUT = 1800.0
_STANDARDS_FILE = PREREQ_OUTPUT_DIR / "standards.json"
_MAX_TOPICS_PER_CALL = 8
_MAX_WORKERS = 8


def _group_topics_by_grade(
    topics: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Group prerequisite topics by grade level, sorted low → high."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for topic in topics:
        grade = topic.get("grade_level", "")
        if grade not in grouped:
            grouped[grade] = []
        grouped[grade].append(topic)

    return dict(
        sorted(grouped.items(), key=lambda kv: grade_order(kv[0]))
    )


def generate_standards_for_grade(
    client: OpenAIClient,
    topics: list[dict[str, Any]],
    grade_level: str,
    existing_ids: list[str],
    max_retries: int = 2,
) -> list[PrereqStandard]:
    """Generate standards for one grade level.

    Args:
        client: GPT-5.1 client.
        topics: Prerequisite topics for this grade.
        grade_level: Grade prefix (e.g. "EB5").
        existing_ids: Standard IDs already generated for lower grades.
        max_retries: Retry count on failure.

    Returns:
        List of validated PrereqStandard objects.
    """
    prompt = build_standards_generation_prompt(
        topics, grade_level, existing_ids,
    )

    for attempt in range(max_retries + 1):
        try:
            resp: LLMResponse = client.generate_text(
                prompt,
                reasoning_effort=_REASONING_EFFORT,
                response_mime_type="application/json",
                request_timeout_seconds=_REQUEST_TIMEOUT,
                stream=True,
            )
            raw = parse_json_response(resp.text)
            if isinstance(raw, dict):
                for key in ("standards", "estandares"):
                    if key in raw:
                        raw = raw[key]
                        break
            if not isinstance(raw, list):
                raw = [raw]

            standards: list[PrereqStandard] = []
            for item in raw:
                std = PrereqStandard.model_validate(item)
                standards.append(std)

            logger.info(
                "Generated %d standards for %s",
                len(standards), grade_level,
            )
            return standards

        except Exception as e:
            logger.error(
                "Attempt %d/%d failed for %s: %s",
                attempt + 1, max_retries + 1, grade_level, e,
            )
            if attempt == max_retries:
                raise

    return []  # unreachable but satisfies type checker


def _split_topic_batches(
    topics: list[dict[str, Any]],
) -> list[list[dict[str, Any]]]:
    """Split topics into batches of _MAX_TOPICS_PER_CALL."""
    if len(topics) <= _MAX_TOPICS_PER_CALL:
        return [topics]
    return [
        topics[i:i + _MAX_TOPICS_PER_CALL]
        for i in range(0, len(topics), _MAX_TOPICS_PER_CALL)
    ]


def run_standards_generation(
    client: OpenAIClient,
    demand: dict[str, Any] | None = None,
) -> list[PrereqStandard]:
    """Run full standards generation for all grade levels.

    Processes grades bottom-up so each level can see IDs from below.
    Within a grade, topic batches run in parallel.

    Args:
        client: GPT-5.1 client.
        demand: Optional pre-loaded demand analysis. Loaded from disk if None.

    Returns:
        Complete list of generated prerequisite standards.
    """
    if demand is None:
        demand = load_demand_analysis()

    topics = demand.get("prerequisite_topics", [])
    grouped = _group_topics_by_grade(topics)

    logger.info(
        "Generating standards for %d grade levels: %s",
        len(grouped), list(grouped.keys()),
    )

    all_standards: list[PrereqStandard] = []
    existing_ids: list[str] = []

    for grade_level in GRADE_LEVELS:
        grade_topics = grouped.get(grade_level, [])
        if not grade_topics:
            continue

        batches = _split_topic_batches(grade_topics)
        n = len(batches)
        workers = min(_MAX_WORKERS, n)
        logger.info(
            "--- %s: %d topics (%d batch%s, %d workers) ---",
            grade_level, len(grade_topics),
            n, "es" if n > 1 else "", workers,
        )

        if n == 1:
            standards = generate_standards_for_grade(
                client, grade_topics, grade_level, existing_ids,
            )
        else:
            frozen_ids = list(existing_ids)
            grade_standards: list[PrereqStandard] = []
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {
                    pool.submit(
                        generate_standards_for_grade,
                        client, batch, grade_level, frozen_ids,
                    ): i
                    for i, batch in enumerate(batches)
                }
                for future in as_completed(futures):
                    batch_idx = futures[future]
                    batch_result = future.result()
                    grade_standards.extend(batch_result)
                    logger.info(
                        "  Batch %d/%d: %d standards",
                        batch_idx + 1, n, len(batch_result),
                    )
            standards = grade_standards

        all_standards.extend(standards)
        existing_ids.extend(s.id for s in standards)

    return all_standards


def save_standards(standards: list[PrereqStandard]) -> Path:
    """Save prerequisite standards to disk."""
    PREREQ_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "metadata": {
            "type": "prerequisite_standards",
            "generated_with": "gpt-5.1",
            "total_standards": len(standards),
        },
        "standards": [s.model_dump() for s in standards],
    }
    with _STANDARDS_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info("Saved %d standards to %s", len(standards), _STANDARDS_FILE)
    return _STANDARDS_FILE


def load_standards() -> list[PrereqStandard]:
    """Load previously saved prerequisite standards."""
    if not _STANDARDS_FILE.exists():
        raise FileNotFoundError(
            f"No standards file at {_STANDARDS_FILE}. Run phase 1 first."
        )
    with _STANDARDS_FILE.open(encoding="utf-8") as f:
        data = json.load(f)
    return [
        PrereqStandard.model_validate(s)
        for s in data.get("standards", [])
    ]


def main() -> None:
    """CLI entry point for Phase 1."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    client = load_default_openai_client()
    standards = run_standards_generation(client)
    save_standards(standards)

    print(f"\n{'=' * 60}")
    print("STANDARDS GENERATION COMPLETE")
    print(f"{'=' * 60}")
    print(f"Total standards: {len(standards)}")
    by_grade: dict[str, int] = {}
    for s in standards:
        by_grade[s.grade_level] = by_grade.get(s.grade_level, 0) + 1
    for grade, count in by_grade.items():
        print(f"  {grade}: {count}")
    print(f"Output: {_STANDARDS_FILE}")


if __name__ == "__main__":
    main()
