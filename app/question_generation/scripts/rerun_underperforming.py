"""rerun_underperforming.py
------------------------
Safe re-run for atoms below the minimum passing-item threshold.

Safety protocol (NEVER loses existing passing items):
  1. Pre-saves Phase 9 passing items for all target atoms BEFORE the run.
  2. Runs phases 0–9 for target atoms in a fresh job (same as run_partial_rerun).
  3. Post-merges: combines pre-saved items + new Phase 9 passing items per atom.
  4. Updates per-atom Phase 9 checkpoints with the merged result.

Why this is necessary:
  BatchAtomPipeline._run_phase_9 calls save_checkpoint() which OVERWRITES
  the per-atom Phase 9 checkpoint with only the new items.  Without the
  merge step, existing passing items would be silently lost.

Usage:
    # Re-run the default 17 underperforming atoms
    uv run python -m app.question_generation.scripts.rerun_underperforming \\
        --no-caffeinate -v

    # Re-run specific atoms
    uv run python -m app.question_generation.scripts.rerun_underperforming \\
        --atoms A-M1-ALG-01-09 A-M1-PROB-01-04 --no-caffeinate -v

    # Resume a previous run (skips pre-save; uses backup written at run start)
    uv run python -m app.question_generation.scripts.rerun_underperforming \\
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
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default atoms: the 17 below the 30-item threshold as of 2026-02-23.
DEFAULT_ATOMS = [
    "A-M1-ALG-01-09",
    "A-M1-ALG-02-04",
    "A-M1-ALG-03-10",
    "A-M1-ALG-03-14",
    "A-M1-ALG-04-02",
    "A-M1-ALG-04-05",
    "A-M1-ALG-06-04",
    "A-M1-GEO-02-16",
    "A-M1-GEO-03-06",
    "A-M1-PROB-01-04",
    "A-M1-PROB-01-05",
    "A-M1-PROB-01-07",
    "A-M1-PROB-01-08",
    "A-M1-PROB-01-10",
    "A-M1-PROB-02-01",
    "A-M1-PROB-03-07",
    "A-M1-PROB-03-08",
]

MIN_THRESHOLD = 30  # items per atom to be considered complete

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pre-save helpers
# ---------------------------------------------------------------------------


def _p9_ckpt_path(atom_id: str) -> Path:
    from app.utils.paths import QUESTION_GENERATION_DIR
    return QUESTION_GENERATION_DIR / atom_id / "checkpoints" / "phase_9_final_validation.json"


def presave_p9_items(atom_ids: list[str], backup_path: Path) -> dict[str, list[dict]]:
    """Read current Phase 9 passing items for each atom and write to backup_path.

    Returns a dict of atom_id -> list of serialized GeneratedItem dicts.
    """
    snapshot: dict[str, list[dict]] = {}
    for atom_id in atom_ids:
        p = _p9_ckpt_path(atom_id)
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                items = data.get("items", [])
                snapshot[atom_id] = items
                _logger.info(
                    "Pre-saved %d Phase 9 items for %s", len(items), atom_id
                )
            except Exception as exc:
                _logger.warning("Could not read Phase 9 checkpoint for %s: %s", atom_id, exc)
                snapshot[atom_id] = []
        else:
            _logger.info("No Phase 9 checkpoint yet for %s (new atom)", atom_id)
            snapshot[atom_id] = []

    backup_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    _logger.info("Phase 9 backup written to %s", backup_path)
    return snapshot


# ---------------------------------------------------------------------------
# Post-merge helpers
# ---------------------------------------------------------------------------


def merge_p9_items(
    atom_ids: list[str],
    backup: dict[str, list[dict]],
) -> dict[str, int]:
    """For each atom, merge pre-saved items + new Phase 9 items, save merged checkpoint.

    Returns atom_id -> final merged count.
    """
    from app.question_generation.helpers import deserialize_items, serialize_items

    final_counts: dict[str, int] = {}

    for atom_id in atom_ids:
        p = _p9_ckpt_path(atom_id)

        # Load new items written by the pipeline (or empty if atom failed)
        new_items: list[dict] = []
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                new_items = data.get("items", [])
            except Exception as exc:
                _logger.warning("Could not read new Phase 9 checkpoint for %s: %s", atom_id, exc)

        # Load pre-saved items
        old_items = backup.get(atom_id, [])

        # Deduplicate by item_id (old takes precedence if duplicate)
        old_ids = {item["item_id"] for item in old_items}
        truly_new = [item for item in new_items if item["item_id"] not in old_ids]

        merged = old_items + truly_new
        merged_count = len(merged)
        final_counts[atom_id] = merged_count

        # Save merged checkpoint
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(
                {"final_count": merged_count, "items": merged},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        _logger.info(
            "%s: merged %d old + %d new = %d total (threshold %d) %s",
            atom_id,
            len(old_items),
            len(truly_new),
            merged_count,
            MIN_THRESHOLD,
            "✅" if merged_count >= MIN_THRESHOLD else "❌ STILL BELOW",
        )

    return final_counts


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    args = _parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(message)s")

    if not args.no_caffeinate and _is_macos():
        _relaunch_with_caffeinate()

    # Determine atom list
    atom_ids: list[str] = []
    if args.atoms:
        atom_ids = args.atoms
    elif args.atoms_file:
        with open(args.atoms_file, encoding="utf-8") as f:
            atom_ids = json.load(f)
    elif not args.job_id:
        atom_ids = DEFAULT_ATOMS
        _logger.info("No atoms specified — using default 17 underperforming atoms")

    # Determine backup path
    job_id = args.job_id or _generate_job_id()
    from app.utils.paths import QUESTION_GENERATION_DIR
    backup_dir = QUESTION_GENERATION_DIR / ".rerun_backups"
    backup_path = backup_dir / f"{job_id}_p9_backup.json"

    # If resuming, try to load existing backup
    backup: dict[str, list[dict]] = {}
    if args.job_id and backup_path.exists():
        _logger.info("Resuming job %s — loading existing Phase 9 backup from %s", job_id, backup_path)
        backup = json.loads(backup_path.read_text(encoding="utf-8"))
        # For resuming, we still need the atom list from backup if not provided
        if not atom_ids:
            atom_ids = list(backup.keys())
            _logger.info("Loaded %d atoms from backup: %s", len(atom_ids), atom_ids)
    elif not args.job_id:
        # New run: pre-save Phase 9 items BEFORE the pipeline overwrites them
        _logger.info("Pre-saving current Phase 9 items for %d atoms...", len(atom_ids))
        backup = presave_p9_items(atom_ids, backup_path)

        # Print current status
        print("\n📊 Current Phase 9 status (before re-run):")
        for atom_id in atom_ids:
            count = len(backup.get(atom_id, []))
            needed = max(0, MIN_THRESHOLD - count)
            print(f"  {atom_id}: {count}/{MIN_THRESHOLD} passing (need {needed} more)")
        print()
    else:
        # Job ID specified but no backup found — this is likely a fresh --job-id for a new run
        _logger.info("No backup found for job %s — running pre-save...", job_id)
        backup = presave_p9_items(atom_ids, backup_path)

    # Run the pipeline
    print(f"🚀 Starting pipeline for {len(atom_ids)} atoms (job: {job_id})")

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
        print(f"\n⚠️  Interrupted. Resume with:")
        print(f"   --job-id {job_id}")
        sys.exit(130)
    except Exception:
        _logger.exception("Pipeline failed")
        print(f"\n❌ Failed. Resume with: --job-id {job_id}")
        print(f"   Backup is safe at: {backup_path}")
        sys.exit(1)

    # Print pipeline summary
    total = summary.get("total_atoms", 0)
    completed = summary.get("completed_atoms", 0)
    failed_atoms = summary.get("failed_atoms", {})
    print(f"\nPipeline done: {completed}/{total} atoms, {len(failed_atoms)} failed")
    if failed_atoms:
        for atom_id, err in failed_atoms.items():
            print(f"  FAILED: {atom_id} — {err}")

    # Post-merge: combine old + new Phase 9 items
    print("\n🔀 Merging Phase 9 results (old passing + new passing)...")
    final_counts = merge_p9_items(atom_ids, backup)

    # Final report
    print("\n📋 Final Phase 9 counts after merge:")
    ok = 0
    still_below = []
    for atom_id in atom_ids:
        count = final_counts.get(atom_id, 0)
        status = "✅" if count >= MIN_THRESHOLD else "❌"
        print(f"  {status} {atom_id}: {count} passing")
        if count >= MIN_THRESHOLD:
            ok += 1
        else:
            still_below.append((atom_id, count))

    print(f"\n✅ {ok}/{len(atom_ids)} atoms now at or above threshold ({MIN_THRESHOLD})")
    if still_below:
        print(f"❌ {len(still_below)} atoms still below threshold:")
        for atom_id, count in still_below:
            print(f"   {atom_id}: {count}/{MIN_THRESHOLD}")
        print("\nThese atoms may need another re-run or manual review.")
        sys.exit(1)

    print("\n🎉 All atoms above threshold. Ready for DB sync.")
    sys.exit(0)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_macos() -> bool:
    return platform.system() == "Darwin"


def _relaunch_with_caffeinate() -> None:
    if os.environ.get("_BATCH_CAFFEINATED"):
        return
    _logger.info("Re-launching under caffeinate -i")
    env = {**os.environ, "_BATCH_CAFFEINATED": "1"}
    try:
        result = subprocess.run(["caffeinate", "-i", sys.executable, *sys.argv], env=env)
        sys.exit(result.returncode)
    except FileNotFoundError:
        _logger.warning("caffeinate not found, continuing without")


def _generate_job_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"batch_api_{ts}"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Safe re-run for atoms below the passing-item threshold"
    )
    p.add_argument("--atoms", nargs="+", help="Atom IDs to re-run (default: all 17 underperforming)")
    p.add_argument("--atoms-file", help="JSON file with list of atom IDs")
    p.add_argument("--job-id", help="Resume a previous run")
    p.add_argument("--skip-images", action="store_true")
    p.add_argument("--no-caffeinate", action="store_true")
    p.add_argument("--poll-interval", type=int, default=60)
    p.add_argument("--max-wait", type=int, default=86400)
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    main()
