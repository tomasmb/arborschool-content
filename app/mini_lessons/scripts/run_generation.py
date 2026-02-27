"""CLI entry point for per-atom mini-lesson generation.

Usage:
    # Single atom (full pipeline)
    python -m app.mini_lessons.scripts.run_generation \
        --atom-id A-M1-ALG-01-02

    # Batch from file (parallel)
    python -m app.mini_lessons.scripts.run_generation \
        --atoms-file atoms_to_generate.txt --workers 8

    # Batch, skip atoms needing images
    python -m app.mini_lessons.scripts.run_generation \
        --atoms-file all_atoms.txt --skip-images --workers 10

    # Dry run (plan-only: Phase 0-1)
    python -m app.mini_lessons.scripts.run_generation \
        --atom-id A-M1-ALG-01-02 --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.llm_clients import OpenAIClient
from app.mini_lessons.models import (
    PHASE_GROUP_CHOICES,
    RUBRIC_DIMENSIONS,
    LessonConfig,
    LessonResult,
)
from app.mini_lessons.pipeline import MiniLessonPipeline
from app.utils.logging_config import setup_logging

_MAX_QUALITY_SCORE = len(RUBRIC_DIMENSIONS) * 2
_print_lock = threading.Lock()


def main() -> None:
    """CLI entry point."""
    args = _parse_args()
    setup_logging(verbose=args.verbose)

    atom_ids = _resolve_atom_ids(args)
    if not atom_ids:
        print("No atom IDs provided. Use --atom-id or --atoms-file.")
        sys.exit(1)

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        sys.exit(1)

    workers = min(args.workers, len(atom_ids))
    print(f"Processing {len(atom_ids)} atom(s) with {workers} worker(s)...")

    client = OpenAIClient(api_key=api_key)
    pipeline = MiniLessonPipeline(
        client,
        skip_images=args.skip_images,
        max_retries=args.max_retries,
    )

    phase = "plan" if args.dry_run else args.phase
    configs = [
        LessonConfig(
            atom_id=aid, phase=phase, resume=args.resume,
            max_retries=args.max_retries, output_dir=args.output_dir,
        )
        for aid in atom_ids
    ]

    if workers <= 1:
        results = _run_sequential(pipeline, configs)
    else:
        results = _run_parallel(pipeline, configs, workers)

    _print_summary(results)


def _run_sequential(
    pipeline: MiniLessonPipeline,
    configs: list[LessonConfig],
) -> list[LessonResult]:
    """Process atoms one at a time."""
    results: list[LessonResult] = []
    for cfg in configs:
        print(f"\n--- {cfg.atom_id} (phase={cfg.phase}) ---")
        result = pipeline.run(cfg)
        results.append(result)
        _print_result(result)
    return results


def _run_parallel(
    pipeline: MiniLessonPipeline,
    configs: list[LessonConfig],
    workers: int,
) -> list[LessonResult]:
    """Process atoms concurrently with a thread pool."""
    results: list[LessonResult] = []
    done_count = 0
    total = len(configs)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(pipeline.run, cfg): cfg
            for cfg in configs
        }
        for future in as_completed(futures):
            cfg = futures[future]
            done_count += 1
            try:
                result = future.result()
            except Exception as exc:
                result = LessonResult(atom_id=cfg.atom_id)
                from app.mini_lessons.models import PhaseResult
                result.phase_results.append(PhaseResult(
                    phase_name="worker_error", success=False,
                    errors=[str(exc)],
                ))
            results.append(result)
            with _print_lock:
                _print_progress(result, done_count, total)

    return results


def _print_progress(
    result: LessonResult, done: int, total: int,
) -> None:
    """Thread-safe progress line for a completed atom."""
    status = "OK" if result.success else "FAIL"
    is_skip = any(
        p.phase_name == "skip_images" for p in result.phase_results
    )
    if is_skip:
        status = "SKIP"
    score = ""
    if result.quality_report:
        score = f" score={result.quality_report.total_score}/{_MAX_QUALITY_SCORE}"
    cost = f" ${result.cost_usd:.2f}" if result.cost_usd > 0 else ""
    print(f"[{done}/{total}] [{status}] {result.atom_id}{score}{cost}")


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Generate mini-lessons for PAES M1 atoms.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--atom-id",
        help="Single atom ID (e.g. A-M1-ALG-01-02)",
    )
    group.add_argument(
        "--atoms-file",
        help="File with one atom ID per line",
    )
    parser.add_argument(
        "--phase", choices=PHASE_GROUP_CHOICES, default="all",
        help="Phase group to run (default: all)",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Resume from last checkpoint",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Plan-only mode (Phase 0-1)",
    )
    parser.add_argument(
        "--skip-images", action="store_true",
        help="Skip atoms whose enrichment requires images",
    )
    parser.add_argument(
        "--max-retries", type=int, default=1,
        help="Max retries per phase (default: 1)",
    )
    parser.add_argument(
        "--workers", type=int, default=1,
        help="Concurrent atoms to process (default: 1)",
    )
    parser.add_argument("--output-dir", help="Override output directory")
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()


def _resolve_atom_ids(args: argparse.Namespace) -> list[str]:
    """Resolve atom IDs from CLI arguments."""
    if args.atom_id:
        return [args.atom_id]
    if args.atoms_file:
        try:
            with open(args.atoms_file) as f:
                return [
                    line.strip() for line in f
                    if line.strip() and not line.startswith("#")
                ]
        except FileNotFoundError:
            print(f"Error: file not found: {args.atoms_file}")
            sys.exit(1)
    return []


# ---------------------------------------------------------------------------
# Result display
# ---------------------------------------------------------------------------


def _print_result(result: LessonResult) -> None:
    """Print a single atom result (sequential mode)."""
    status = "OK" if result.success else "FAILED"
    print(f"  Result: {status}")
    for pr in result.phase_results:
        icon = "+" if pr.success else "x"
        print(f"    [{icon}] {pr.phase_name}")
        for err in pr.errors:
            print(f"        ERROR: {err}")
        for warn in pr.warnings:
            print(f"        WARN: {warn}")
    if result.quality_report:
        qr = result.quality_report
        print(
            f"  Quality: {qr.total_score}/{_MAX_QUALITY_SCORE} "
            f"(publishable={qr.publishable})",
        )
    if result.cost_usd > 0:
        print(f"  Cost: ${result.cost_usd:.4f}")


def _print_summary(results: list[LessonResult]) -> None:
    """Print summary of all results."""
    total = len(results)
    ok = sum(1 for r in results if r.success)
    skipped = sum(
        1 for r in results
        if any(p.phase_name == "skip_images" for p in r.phase_results)
    )
    total_cost = sum(r.cost_usd for r in results)
    ran = total - skipped
    print(f"\n=== Summary: {ok}/{ran} succeeded, {skipped} skipped ===")
    for r in results:
        is_skipped = any(
            p.phase_name == "skip_images" for p in r.phase_results
        )
        if is_skipped:
            continue
        status = "OK" if r.success else "FAIL"
        pub = ""
        if r.quality_report:
            pub = (
                f" (score={r.quality_report.total_score}"
                f"/{_MAX_QUALITY_SCORE})"
            )
        print(f"  [{status}] {r.atom_id}{pub}")
    if skipped:
        print(f"  ... {skipped} atoms skipped (require images)")
    if total_cost > 0:
        print(f"\n  Total cost: ${total_cost:.4f}")


if __name__ == "__main__":
    main()
