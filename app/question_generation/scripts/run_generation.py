"""CLI entry point for per-atom question generation.

Usage:
    # Single atom
    python -m app.question_generation.scripts.run_generation \
        --atom-id A-M1-ALG-01-02

    # Batch from file (one atom ID per line)
    python -m app.question_generation.scripts.run_generation \
        --atoms-file atoms_to_generate.txt

    # Dry run (skip DB sync)
    python -m app.question_generation.scripts.run_generation \
        --atom-id A-M1-ALG-01-02 --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.question_generation.models import PipelineConfig, PipelineResult
from app.question_generation.pipeline import AtomQuestionPipeline
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

    results: list[PipelineResult] = []
    for atom_id in atom_ids:
        config = PipelineConfig(
            atom_id=atom_id,
            pool_size=args.pool_size,
            max_retries=args.max_retries,
            skip_sync=args.skip_sync,
            dry_run=args.dry_run,
            skip_enrichment=args.skip_enrichment,
        )
        pipeline = AtomQuestionPipeline(config=config)
        result = pipeline.run(atom_id)
        results.append(result)

    _print_batch_summary(results)
    success_count = sum(1 for r in results if r.success)
    sys.exit(0 if success_count == len(results) else 1)


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate PAES-style question pools per atom.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--atom-id",
        help="Single atom ID to process (e.g. A-M1-ALG-01-02)",
    )
    group.add_argument(
        "--atoms-file",
        type=Path,
        help="File with one atom ID per line",
    )
    parser.add_argument(
        "--pool-size", type=int, default=9,
        help="Items per atom (default 9 = 3 per difficulty)",
    )
    parser.add_argument(
        "--max-retries", type=int, default=2,
        help="Max LLM retries per phase (default 2)",
    )
    parser.add_argument(
        "--skip-sync", action="store_true",
        help="Skip Phase 10 DB sync",
    )
    parser.add_argument(
        "--skip-enrichment", action="store_true",
        help="Skip Phase 1 atom enrichment",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run through Phase 9 but skip DB sync",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()


def _resolve_atom_ids(args: argparse.Namespace) -> list[str]:
    """Resolve atom IDs from CLI arguments.

    Args:
        args: Parsed CLI arguments.

    Returns:
        List of atom IDs to process.
    """
    if args.atom_id:
        return [args.atom_id]

    if args.atoms_file and args.atoms_file.exists():
        text = args.atoms_file.read_text(encoding="utf-8")
        return [
            line.strip()
            for line in text.splitlines()
            if line.strip() and not line.startswith("#")
        ]

    return []


def _print_batch_summary(results: list[PipelineResult]) -> None:
    """Print summary for a batch run.

    Args:
        results: List of pipeline results.
    """
    total = len(results)
    succeeded = sum(1 for r in results if r.success)
    total_items = sum(r.total_final for r in results)

    print(f"\n{'=' * 60}")
    print("RESUMEN DE LOTE")
    print(f"{'=' * 60}")
    print(f"Átomos procesados: {total}")
    print(f"Exitosos:          {succeeded}")
    print(f"Fallidos:          {total - succeeded}")
    print(f"Items finales:     {total_items}")

    if total - succeeded > 0:
        print("\nFallidos:")
        for r in results:
            if not r.success:
                print(f"  - {r.atom_id}")

    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
