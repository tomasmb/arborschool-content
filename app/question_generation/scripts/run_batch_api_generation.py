"""Batch API question generation — process all eligible atoms via the
OpenAI Batch API (50% cost discount).

Runs the full pipeline phase-by-phase across all atoms using batch
submissions.  Wraps execution with ``caffeinate`` on macOS to prevent
sleep during polling.

Usage:
    # Generate all pending atoms
    python -m app.question_generation.scripts.run_batch_api_generation

    # Resume a previous run
    python -m app.question_generation.scripts.run_batch_api_generation \
        --job-id batch_api_20260219_abc123

    # Skip images, custom poll interval
    python -m app.question_generation.scripts.run_batch_api_generation \
        --skip-images --poll-interval 60

    # Disable caffeinate (e.g. on Linux)
    python -m app.question_generation.scripts.run_batch_api_generation \
        --no-caffeinate
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any

from app.utils.logging_config import setup_logging
from app.utils.paths import QUESTION_GENERATION_DIR, get_atoms_file

_logger = logging.getLogger(__name__)

_FULLY_GENERATED_PHASE = 9


def main() -> None:
    """CLI entry point."""
    args = _parse_args()
    setup_logging(verbose=args.verbose)

    if not args.no_caffeinate and _is_macos():
        _relaunch_with_caffeinate()

    atoms = _load_eligible_atoms(args.mode)
    if args.skip_images:
        atoms = _exclude_atoms_needing_images(atoms)
    if not atoms:
        print("No eligible atoms found.")
        sys.exit(0)

    atom_ids = [a["id"] for a in atoms]
    job_id = args.job_id or _generate_job_id()

    print(f"Batch API generation: {len(atom_ids)} atoms")
    print(f"Job ID: {job_id}")
    print(f"Poll interval: {args.poll_interval}s")
    if args.skip_images:
        print("  (image generation SKIPPED)")

    from app.question_generation.batch_pipeline import (
        BatchAtomPipeline,
    )

    pipeline = BatchAtomPipeline(
        job_id=job_id,
        atom_ids=atom_ids,
        skip_images=args.skip_images,
        poll_interval=args.poll_interval,
        max_wait=args.max_wait,
    )

    try:
        summary = pipeline.run()
    except KeyboardInterrupt:
        print("\nInterrupted. Resume with:")
        print(f"  --job-id {job_id}")
        sys.exit(130)
    except Exception:
        _logger.exception("Pipeline failed")
        print(f"\nFailed. Resume with: --job-id {job_id}")
        sys.exit(1)

    _print_summary(summary)
    failed_count = len(summary.get("failed_atoms", {}))
    sys.exit(0 if failed_count == 0 else 1)


# -------------------------------------------------------------------
# Caffeinate (macOS sleep prevention)
# -------------------------------------------------------------------


def _is_macos() -> bool:
    return platform.system() == "Darwin"


def _relaunch_with_caffeinate() -> None:
    """If not already under caffeinate, re-exec via caffeinate -i."""
    if os.environ.get("_BATCH_CAFFEINATED"):
        return

    _logger.info("Re-launching under caffeinate -i")
    env = {**os.environ, "_BATCH_CAFFEINATED": "1"}
    try:
        result = subprocess.run(
            ["caffeinate", "-i", sys.executable, *sys.argv],
            env=env,
        )
        sys.exit(result.returncode)
    except FileNotFoundError:
        _logger.warning("caffeinate not found, continuing without")


# -------------------------------------------------------------------
# Atom loading (reuses logic from run_batch_generation.py)
# -------------------------------------------------------------------


def _load_eligible_atoms(mode: str) -> list[dict[str, Any]]:
    """Load atoms with coverage, optionally filter by gen status."""
    from api.services.atom_coverage_service import (
        compute_atom_coverage_status,
        load_atom_coverage_maps,
    )

    atoms_data = _load_all_atoms()
    if not atoms_data:
        return []

    atom_qs, deps = load_atom_coverage_maps(atoms_data)
    covered: list[dict[str, Any]] = []
    for atom in atoms_data:
        aid = atom["id"]
        direct = len(atom_qs.get(aid, set()))
        status = compute_atom_coverage_status(
            aid, direct, deps, atom_qs,
        )
        if status != "none":
            covered.append(atom)

    if mode == "all":
        return covered

    from app.question_generation.helpers import (
        get_last_completed_phase,
    )
    return [
        a for a in covered
        if (get_last_completed_phase(a["id"]) or 0)
        < _FULLY_GENERATED_PHASE
    ]


def _load_all_atoms() -> list[dict[str, Any]]:
    path = get_atoms_file("paes_m1_2026")
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("atoms", [])


def _exclude_atoms_needing_images(
    atoms: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Keep only atoms whose enrichment shows no image requirements."""
    from app.question_generation.helpers import (
        get_enrichment_image_types,
    )

    kept: list[dict[str, Any]] = []
    for atom in atoms:
        image_types = get_enrichment_image_types(atom["id"])
        if image_types is None or image_types:
            continue
        kept.append(atom)
    return kept


# -------------------------------------------------------------------
# Output
# -------------------------------------------------------------------


def _generate_job_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"batch_api_{ts}"


def _print_summary(summary: dict[str, Any]) -> None:
    total = summary.get("total_atoms", 0)
    active = summary.get("active_atoms", 0)
    failed = summary.get("failed_atoms", {})
    final_items = summary.get("total_final_items", 0)

    print(f"\n{'=' * 60}")
    print("BATCH API GENERATION SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total atoms:       {total}")
    print(f"Succeeded:         {active}")
    print(f"Failed:            {len(failed)}")
    print(f"Final items:       {final_items}")

    if failed:
        print("\nFailed atoms:")
        for aid, reason in failed.items():
            print(f"  - {aid}: {reason}")

    items_per_atom = summary.get("items_per_atom", {})
    if items_per_atom:
        avg = final_items / max(len(items_per_atom), 1)
        print(f"\nAverage items/atom: {avg:.1f}")

    print(f"{'=' * 60}\n")


# -------------------------------------------------------------------
# CLI
# -------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Batch API question generation for all "
            "eligible atoms (50%% cost discount)."
        ),
    )
    parser.add_argument(
        "--mode",
        choices=["pending_only", "all"],
        default="pending_only",
        help=(
            "pending_only: skip fully-generated atoms. "
            "all: re-run every covered atom. "
            "(default: pending_only)"
        ),
    )
    parser.add_argument(
        "--skip-images", action="store_true",
        help="Skip image generation and bypass generatability gate",
    )
    parser.add_argument(
        "--job-id",
        help="Job ID for resume support (reuses existing state)",
    )
    parser.add_argument(
        "--poll-interval",
        type=int, default=30,
        help="Seconds between batch status polls (default: 30)",
    )
    parser.add_argument(
        "--max-wait",
        type=int, default=86400,
        help=(
            "Max seconds to wait per batch before timeout "
            "(default: 86400 = 24h)"
        ),
    )
    parser.add_argument(
        "--no-caffeinate", action="store_true",
        help="Disable macOS caffeinate sleep prevention",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
