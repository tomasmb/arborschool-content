#!/usr/bin/env python3
"""topup_variants.py — Fill deficit questions up to a target count.

Scans existing approved variants, identifies questions below a target,
and runs the full 7-phase pipeline only for those, deduplicating
against prior approved variants and offsetting new variant IDs to
avoid disk collisions.

Usage:
    # Auto-detect and top up all questions below 8 approved
    uv run python -m app.question_variants.scripts.topup_variants \
        --source-test "prueba-invierno-2025"

    # Custom target and specific test
    uv run python -m app.question_variants.scripts.topup_variants \
        --source-test "prueba-transicion-2025" --target 10

    # Resume a previous run
    uv run python -m app.question_variants.scripts.topup_variants \
        --source-test "prueba-invierno-2025" --job-id abc123
"""
from __future__ import annotations

import argparse
import logging
import os
import platform
import subprocess
import sys
import uuid
from pathlib import Path

from app.question_variants.io.artifacts import load_existing_approved
from app.question_variants.models import PipelineConfig, VariantQuestion

_logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT_DIR = "app/data/pruebas/hard_variants"
_DEFAULT_TARGET = 8
_DEFAULT_VARIANTS_TO_GENERATE = 10


# ------------------------------------------------------------------
# Deficit scanning
# ------------------------------------------------------------------


def find_questions_below_target(
    output_dir: str,
    test_id: str,
    target: int,
) -> list[tuple[str, int, int]]:
    """Scan disk for questions below target approved count.

    Returns:
        List of (question_id, current_count, deficit) tuples,
        sorted by question_id.
    """
    test_dir = Path(output_dir) / test_id
    if not test_dir.is_dir():
        _logger.warning("Test directory not found: %s", test_dir)
        return []

    results: list[tuple[str, int, int]] = []
    for q_dir in sorted(test_dir.iterdir()):
        if not q_dir.is_dir():
            continue
        approved_dir = q_dir / "variants" / "approved"
        count = 0
        if approved_dir.is_dir():
            count = sum(
                1 for d in approved_dir.iterdir()
                if d.is_dir() and (d / "question.xml").is_file()
            )
        deficit = target - count
        if deficit > 0:
            results.append((q_dir.name, count, deficit))

    return results


def build_topup_config(
    test_id: str,
    deficit_questions: list[tuple[str, int, int]],
    output_dir: str,
    *,
    model: str = "gpt-5.1",
    job_id: str | None = None,
    variants_to_generate: int = _DEFAULT_VARIANTS_TO_GENERATE,
    enrichment_model: str = "gpt-5.4",
    skip_enrichment: bool = False,
    dedup_threshold: float = 0.70,
    lenient: bool = False,
    generation_reasoning_effort: str = "medium",
) -> PipelineConfig:
    """Build a PipelineConfig pre-loaded with dedup and offset data."""
    prior_approved: dict[str, list[VariantQuestion]] = {}
    variant_id_offset: dict[str, int] = {}

    for q_id, current_count, _deficit in deficit_questions:
        existing = load_existing_approved(output_dir, test_id, q_id)
        prior_approved[q_id] = existing
        variant_id_offset[q_id] = len(existing)

    return PipelineConfig(
        variants_per_question=variants_to_generate,
        model=model,
        use_batch_api=True,
        job_id=job_id,
        output_dir=output_dir,
        skip_enrichment=skip_enrichment,
        enrichment_model=enrichment_model,
        prior_approved=prior_approved,
        variant_id_offset=variant_id_offset,
        dedup_threshold=dedup_threshold,
        lenient=lenient,
        generation_reasoning_effort=generation_reasoning_effort,
    )


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------


def main() -> None:
    args = _parse_args()
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if not args.no_caffeinate and _is_macos():
        _relaunch_with_caffeinate()

    target: int = args.target
    test_id: str = args.source_test
    output_dir: str = args.output_dir

    deficits = find_questions_below_target(output_dir, test_id, target)
    if not deficits:
        print(
            f"All questions in {test_id} already at or above "
            f"target ({target}).",
        )
        sys.exit(0)

    question_ids = [q_id for q_id, _, _ in deficits]

    _print_deficit_status(deficits, target, test_id)

    job_id = args.job_id or f"topup_{uuid.uuid4().hex[:8]}"

    config = build_topup_config(
        test_id=test_id,
        deficit_questions=deficits,
        output_dir=output_dir,
        model=args.model,
        job_id=job_id,
        variants_to_generate=args.variants_to_generate,
        enrichment_model=args.enrichment_model,
        skip_enrichment=args.skip_enrichment,
        dedup_threshold=args.dedup_threshold,
        lenient=args.lenient,
        generation_reasoning_effort=args.generation_reasoning,
    )

    from app.question_variants.pipeline import BatchVariantPipeline
    pipeline = BatchVariantPipeline(config)

    print(f"\nJob ID: {job_id}")
    print(f"Resume with: --job-id {job_id}\n")

    try:
        reports = pipeline.run(
            test_id=test_id,
            question_ids=question_ids,
            num_variants=args.variants_to_generate,
        )
    except KeyboardInterrupt:
        print(f"\nInterrupted. Resume with: --job-id {job_id}")
        sys.exit(130)
    except Exception:
        _logger.exception("Pipeline failed")
        print(f"\nFailed. Resume with: --job-id {job_id}")
        sys.exit(1)

    total_new = sum(r.total_approved for r in reports)
    print(f"\nTop-up complete: {total_new} new variants approved.")

    _print_final_status(output_dir, test_id, question_ids, target)


def _print_deficit_status(
    deficits: list[tuple[str, int, int]],
    target: int,
    test_id: str,
) -> None:
    """Print per-question deficit summary before running."""
    total_deficit = sum(d for _, _, d in deficits)
    print(f"\nTop-up plan for {test_id} (target={target}):")
    print(f"  {len(deficits)} questions below target")
    print(f"  Total deficit: {total_deficit} variants\n")
    for q_id, have, deficit in deficits:
        print(f"  {q_id}: has {have}, needs {deficit}")
    print()


def _print_final_status(
    output_dir: str,
    test_id: str,
    question_ids: list[str],
    target: int,
) -> None:
    """Print post-run approved counts for targeted questions."""
    print(f"\nFinal approved counts (target={target}):")
    ok = 0
    still_below: list[tuple[str, int]] = []
    for q_id in question_ids:
        existing = load_existing_approved(output_dir, test_id, q_id)
        count = len(existing)
        flag = "OK" if count >= target else "BELOW"
        print(f"  [{flag}] {q_id}: {count}")
        if count >= target:
            ok += 1
        else:
            still_below.append((q_id, count))

    print(f"\n{ok}/{len(question_ids)} questions at or above target.")
    if still_below:
        print(f"{len(still_below)} questions still below:")
        for q_id, count in still_below:
            print(f"   {q_id}: {count}/{target}")


# ------------------------------------------------------------------
# Utilities
# ------------------------------------------------------------------


def _is_macos() -> bool:
    return platform.system() == "Darwin"


def _relaunch_with_caffeinate() -> None:
    if os.environ.get("_TOPUP_CAFFEINATED"):
        return
    _logger.info("Re-launching under caffeinate -i")
    env = {**os.environ, "_TOPUP_CAFFEINATED": "1"}
    try:
        result = subprocess.run(
            ["caffeinate", "-i", sys.executable, *sys.argv],
            env=env,
        )
        sys.exit(result.returncode)
    except FileNotFoundError:
        _logger.warning("caffeinate not found, continuing without")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Top up variant questions below a target count.",
    )
    p.add_argument(
        "--source-test", required=True,
        help="Test ID (e.g., 'prueba-invierno-2025')",
    )
    p.add_argument(
        "--target", type=int, default=_DEFAULT_TARGET,
        help=f"Target approved variants per question "
        f"(default: {_DEFAULT_TARGET})",
    )
    p.add_argument(
        "--variants-to-generate", type=int,
        default=_DEFAULT_VARIANTS_TO_GENERATE,
        help="Variants to generate per deficit question "
        f"(default: {_DEFAULT_VARIANTS_TO_GENERATE})",
    )
    p.add_argument(
        "--output-dir", default=_DEFAULT_OUTPUT_DIR,
        help="Output directory for generated variants",
    )
    p.add_argument(
        "--model", default="gpt-5.1",
        help="OpenAI model for all LLM phases (default: gpt-5.1)",
    )
    p.add_argument(
        "--enrichment-model", default="gpt-5.4",
        help="Model for feedback enrichment (default: gpt-5.4)",
    )
    p.add_argument(
        "--skip-enrichment", action="store_true",
        help="Skip phases 5-7 for quick iterations",
    )
    p.add_argument(
        "--dedup-threshold", type=float, default=0.70,
        help="Surface-similarity threshold for dedup "
        "(default: 0.70, lower = more permissive)",
    )
    p.add_argument(
        "--job-id", default=None,
        help="Resume a previous top-up run",
    )
    p.add_argument(
        "--lenient", action="store_true",
        help="Lenient mode: approve if answer is correct (skip "
        "concept/differentiation gates and phases 5+7)",
    )
    p.add_argument(
        "--generation-reasoning", default="medium",
        choices=["low", "medium", "high"],
        help="Reasoning effort for generation phase "
        "(default: medium, use high for stubborn questions)",
    )
    p.add_argument("--no-caffeinate", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    main()
