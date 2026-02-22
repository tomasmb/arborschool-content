"""Partial re-run: generate questions for a specific list of atoms.

Used after a full run where some atoms didn't reach the 46-item minimum
for PP100. Pass atom IDs explicitly — skips the 'already completed' filter
so we can re-run atoms that completed phase 9 but need more items.

Usage:
    # Re-run atoms listed in a JSON file (list of atom ID strings)
    python -m app.question_generation.scripts.run_partial_rerun \
        --atoms-file rerun_atoms.json --no-caffeinate -v

    # Re-run specific atoms
    python -m app.question_generation.scripts.run_partial_rerun \
        --atoms A-M1-ALG-01-03 A-M1-ALG-01-04 --no-caffeinate -v

    # Resume a partial re-run
    python -m app.question_generation.scripts.run_partial_rerun \
        --job-id batch_api_XXXXXX --no-caffeinate -v
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

from app.utils.logging_config import setup_logging


_logger = logging.getLogger(__name__)


def main() -> None:
    args = _parse_args()
    setup_logging(verbose=args.verbose)

    if not args.no_caffeinate and _is_macos():
        _relaunch_with_caffeinate()

    # Load atom IDs
    atom_ids: list[str] = []
    if args.atoms_file:
        with open(args.atoms_file, encoding="utf-8") as f:
            atom_ids = json.load(f)
        print(f"Loaded {len(atom_ids)} atoms from {args.atoms_file}")
    elif args.atoms:
        atom_ids = args.atoms
        print(f"Using {len(atom_ids)} atoms from --atoms flag")
    elif not args.job_id:
        print("ERROR: must specify --atoms-file, --atoms, or --job-id")
        sys.exit(1)

    job_id = args.job_id or _generate_job_id()

    print(f"Partial re-run: {len(atom_ids)} atoms")
    print(f"Job ID: {job_id}")
    print(f"Poll interval: {args.poll_interval}s")

    from app.question_generation.batch_pipeline import BatchAtomPipeline

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

    # Print summary
    total = summary.get("total_atoms", 0)
    completed = summary.get("completed_atoms", 0)
    failed = len(summary.get("failed_atoms", {}))
    print(f"\nDone: {completed}/{total} atoms completed, {failed} failed")
    if failed:
        for atom_id, err in summary.get("failed_atoms", {}).items():
            print(f"  FAILED: {atom_id} — {err}")

    sys.exit(0 if failed == 0 else 1)


def _is_macos() -> bool:
    return platform.system() == "Darwin"


def _relaunch_with_caffeinate() -> None:
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


def _generate_job_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"batch_api_{ts}"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Partial pipeline re-run for specific atoms")
    p.add_argument("--atoms-file", help="JSON file with list of atom IDs")
    p.add_argument("--atoms", nargs="+", help="Atom IDs to process")
    p.add_argument("--job-id", help="Resume a previous run")
    p.add_argument("--skip-images", action="store_true")
    p.add_argument("--no-caffeinate", action="store_true")
    p.add_argument("--poll-interval", type=int, default=60)
    p.add_argument("--max-wait", type=int, default=86400)
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    main()
