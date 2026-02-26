"""CLI entry point for per-atom mini-lesson generation.

Usage:
    # Single atom (full pipeline)
    python -m app.mini_lessons.scripts.run_generation \
        --atom-id A-M1-ALG-01-02

    # Single atom with resume
    python -m app.mini_lessons.scripts.run_generation \
        --atom-id A-M1-ALG-01-02 --resume

    # Batch from file
    python -m app.mini_lessons.scripts.run_generation \
        --atoms-file atoms_to_generate.txt

    # Dry run (plan-only: Phase 0-1)
    python -m app.mini_lessons.scripts.run_generation \
        --atom-id A-M1-ALG-01-02 --dry-run

    # Selective phase
    python -m app.mini_lessons.scripts.run_generation \
        --atom-id A-M1-ALG-01-02 --phase generate
"""

from __future__ import annotations

import argparse
import os
import sys

from app.llm_clients import OpenAIClient
from app.mini_lessons.models import (
    PHASE_GROUP_CHOICES,
    RUBRIC_DIMENSIONS,
    LessonConfig,
    LessonResult,
)

_MAX_QUALITY_SCORE = len(RUBRIC_DIMENSIONS) * 2
from app.mini_lessons.pipeline import MiniLessonPipeline
from app.utils.logging_config import setup_logging


def main() -> None:
    """CLI entry point."""
    args = _parse_args()
    setup_logging(verbose=args.verbose)

    atom_ids = _resolve_atom_ids(args)
    if not atom_ids:
        print("No atom IDs provided. Use --atom-id or --atoms-file.")
        sys.exit(1)

    print(f"Processing {len(atom_ids)} atom(s)...")

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        sys.exit(1)

    client = OpenAIClient(api_key=api_key)
    pipeline = MiniLessonPipeline(
        client,
        skip_images=args.skip_images,
        max_retries=args.max_retries,
    )

    results: list[LessonResult] = []
    for atom_id in atom_ids:
        phase = "plan" if args.dry_run else args.phase
        config = LessonConfig(
            atom_id=atom_id,
            phase=phase,
            resume=args.resume,
            max_retries=args.max_retries,
            output_dir=args.output_dir,
        )
        print(f"\n--- {atom_id} (phase={phase}) ---")
        result = pipeline.run(config)
        results.append(result)
        _print_result(result)

    _print_summary(results)


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
        "--phase",
        choices=PHASE_GROUP_CHOICES,
        default="all",
        help="Phase group to run (default: all)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last checkpoint",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan-only mode (Phase 0-1)",
    )
    parser.add_argument(
        "--skip-images",
        action="store_true",
        help="Skip atoms whose enrichment requires images",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=1,
        help="Max retries per phase (default: 1)",
    )
    parser.add_argument(
        "--output-dir",
        help="Override output directory",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
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


def _print_result(result: LessonResult) -> None:
    """Print a single atom result."""
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
            print(f"  [SKIP] {r.atom_id} (requires images)")
            continue
        status = "OK" if r.success else "FAIL"
        pub = ""
        if r.quality_report:
            pub = (
                f" (score="
                f"{r.quality_report.total_score}"
                f"/{_MAX_QUALITY_SCORE})"
            )
        print(f"  [{status}] {r.atom_id}{pub}")
    if total_cost > 0:
        print(f"\n  Total cost: ${total_cost:.4f}")


if __name__ == "__main__":
    main()
