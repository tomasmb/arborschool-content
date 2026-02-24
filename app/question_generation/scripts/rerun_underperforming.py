"""rerun_underperforming.py — Deficit-based re-run for underperforming atoms.

Safety protocol (NEVER loses existing passing items):
  1. Pre-saves Phase 9 passing items for all target atoms BEFORE the run.
  2. Computes per-atom deficit distributions (only generates what's needed).
  3. Passes existing item summaries to the planner (avoids duplicate patterns).
  4. Passes existing fingerprints to Phase 5 (blocks content-duplicates).
  5. Post-merges: combines pre-saved items + new Phase 9 items per atom.

Usage:
    # Auto-detect and re-run all atoms below 46 items
    uv run python -m app.question_generation.scripts.rerun_underperforming

    # Re-run atoms below a custom target
    uv run python -m app.question_generation.scripts.rerun_underperforming --target 50

    # Re-run specific atoms
    uv run python -m app.question_generation.scripts.rerun_underperforming \
        --atoms A-M1-ALG-06-06 A-M1-ALG-06-03

    # Resume a previous run
    uv run python -m app.question_generation.scripts.rerun_underperforming \
        --job-id batch_api_XXXXXX
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_logger = logging.getLogger(__name__)

# Mastery target distribution: 14E + 18M + 14H = 46
_TARGET_EASY, _TARGET_MEDIUM, _TARGET_HARD = 14, 18, 14
_DEFAULT_TARGET = _TARGET_EASY + _TARGET_MEDIUM + _TARGET_HARD  # 46
_DEFAULT_BUFFER = 1.3
_MIN_SLOTS = 10  # floor to ensure enough material after attrition


# ---------------------------------------------------------------------------
# Deficit computation
# ---------------------------------------------------------------------------


def _p9_ckpt_path(atom_id: str) -> Path:
    from app.utils.paths import QUESTION_GENERATION_DIR
    return (
        QUESTION_GENERATION_DIR / atom_id
        / "checkpoints" / "phase_9_final_validation.json"
    )


def find_atoms_below_target(target: int) -> list[str]:
    """Scan all atom directories and return those below target."""
    from app.utils.paths import QUESTION_GENERATION_DIR

    below: list[str] = []
    for atom_dir in sorted(QUESTION_GENERATION_DIR.glob("A-M1-*")):
        if not atom_dir.is_dir():
            continue
        p9 = atom_dir / "checkpoints" / "phase_9_final_validation.json"
        count = 0
        if p9.exists():
            try:
                data = json.loads(p9.read_text(encoding="utf-8"))
                count = len(data.get("items", []))
            except Exception:
                pass
        if count < target:
            below.append(atom_dir.name)
    return below


def compute_per_atom_deficits(
    atom_ids: list[str],
    target: int = _DEFAULT_TARGET,
    buffer_ratio: float = _DEFAULT_BUFFER,
) -> tuple[
    dict[str, "DifficultyDistribution"],
    dict[str, dict],
    dict[str, set[str]],
]:
    """Compute deficit distributions, summaries, and fingerprints.

    Returns:
        (per_atom_distributions, existing_summaries, fingerprints)
    """
    from app.question_generation.helpers import (
        load_checkpoint_fingerprints,
        load_existing_items_summary,
    )
    from app.question_generation.models import DifficultyDistribution

    # Scale per-difficulty targets proportionally to overall target
    ratio = target / _DEFAULT_TARGET if _DEFAULT_TARGET > 0 else 1.0
    t_easy = round(_TARGET_EASY * ratio)
    t_med = round(_TARGET_MEDIUM * ratio)
    t_hard = round(_TARGET_HARD * ratio)

    distributions: dict[str, DifficultyDistribution] = {}
    summaries: dict[str, dict] = {}
    fingerprints: dict[str, set[str]] = {}

    for atom_id in atom_ids:
        summary = load_existing_items_summary(atom_id)
        summaries[atom_id] = summary or {
            "total": 0, "by_difficulty": {},
            "skeleton_counts": {}, "surface_contexts": {},
            "numbers_profiles": {},
        }
        fingerprints[atom_id] = load_checkpoint_fingerprints(atom_id)

        by_diff = summaries[atom_id].get("by_difficulty", {})
        have_e = by_diff.get("easy", 0)
        have_m = by_diff.get("medium", 0)
        have_h = by_diff.get("hard", 0)

        deficit_e = max(0, t_easy - have_e)
        deficit_m = max(0, t_med - have_m)
        deficit_h = max(0, t_hard - have_h)
        raw_total = deficit_e + deficit_m + deficit_h

        # Apply minimum slot floor
        if raw_total > 0 and raw_total < _MIN_SLOTS:
            scale = _MIN_SLOTS / raw_total
            deficit_e = max(1, round(deficit_e * scale))
            deficit_m = max(1, round(deficit_m * scale))
            deficit_h = max(1, round(deficit_h * scale))

        distributions[atom_id] = DifficultyDistribution(
            easy=math.ceil(deficit_e * buffer_ratio),
            medium=math.ceil(deficit_m * buffer_ratio),
            hard=math.ceil(deficit_h * buffer_ratio),
        )

    return distributions, summaries, fingerprints


# ---------------------------------------------------------------------------
# Pre-save / post-merge (safety protocol)
# ---------------------------------------------------------------------------


def presave_p9_items(
    atom_ids: list[str], backup_path: Path,
) -> dict[str, list[dict]]:
    """Back up existing Phase 9 items before the pipeline overwrites them."""
    snapshot: dict[str, list[dict]] = {}
    for atom_id in atom_ids:
        p = _p9_ckpt_path(atom_id)
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                snapshot[atom_id] = data.get("items", [])
            except Exception as exc:
                _logger.warning(
                    "Could not read Phase 9 for %s: %s",
                    atom_id, exc,
                )
                snapshot[atom_id] = []
        else:
            snapshot[atom_id] = []

    backup_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _logger.info("Phase 9 backup written to %s", backup_path)
    return snapshot


def merge_p9_items(
    atom_ids: list[str],
    backup: dict[str, list[dict]],
    target: int,
) -> dict[str, int]:
    """Merge pre-saved + new Phase 9 items, save merged checkpoint."""
    final_counts: dict[str, int] = {}

    for atom_id in atom_ids:
        p = _p9_ckpt_path(atom_id)
        new_items: list[dict] = []
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                new_items = data.get("items", [])
            except Exception as exc:
                _logger.warning(
                    "Could not read new Phase 9 for %s: %s",
                    atom_id, exc,
                )

        old_items = backup.get(atom_id, [])
        old_ids = {item["item_id"] for item in old_items}
        truly_new = [
            i for i in new_items if i["item_id"] not in old_ids
        ]
        merged = old_items + truly_new
        final_counts[atom_id] = len(merged)

        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(
                {"final_count": len(merged), "items": merged},
                ensure_ascii=False, indent=2,
            ),
            encoding="utf-8",
        )
        status = "OK" if len(merged) >= target else "STILL BELOW"
        _logger.info(
            "%s: %d old + %d new = %d total [%s]",
            atom_id, len(old_items), len(truly_new),
            len(merged), status,
        )

    return final_counts


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


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

    # Determine atom list
    atom_ids: list[str] = []
    if args.atoms:
        atom_ids = args.atoms
    elif args.atoms_file:
        with open(args.atoms_file, encoding="utf-8") as f:
            atom_ids = json.load(f)
    elif not args.job_id:
        atom_ids = find_atoms_below_target(target)
        _logger.info(
            "Found %d atoms below target (%d)",
            len(atom_ids), target,
        )

    if not atom_ids and not args.job_id:
        print(f"All atoms already at or above target ({target}).")
        sys.exit(0)

    job_id = args.job_id or _generate_job_id()
    from app.utils.paths import QUESTION_GENERATION_DIR
    backup_dir = QUESTION_GENERATION_DIR / ".rerun_backups"
    backup_path = backup_dir / f"{job_id}_p9_backup.json"

    # Compute deficits and prepare pipeline inputs
    dists, summaries, fps = compute_per_atom_deficits(
        atom_ids, target, _DEFAULT_BUFFER,
    )

    # Filter out atoms with 0-slot distributions
    atom_ids = [
        a for a in atom_ids if dists[a].total > 0
    ]
    if not atom_ids:
        print("No atoms need additional questions.")
        sys.exit(0)

    # Resume or pre-save
    backup: dict[str, list[dict]] = {}
    if args.job_id and backup_path.exists():
        _logger.info("Resuming job %s", job_id)
        backup = json.loads(
            backup_path.read_text(encoding="utf-8"),
        )
        if not atom_ids:
            atom_ids = list(backup.keys())
    else:
        backup = presave_p9_items(atom_ids, backup_path)

    _print_deficit_status(atom_ids, summaries, dists, target)

    # Run pipeline
    from app.question_generation.batch_pipeline import (
        BatchAtomPipeline,
    )
    pipeline = BatchAtomPipeline(
        job_id=job_id,
        atom_ids=atom_ids,
        skip_images=args.skip_images,
        poll_interval=args.poll_interval,
        max_wait=args.max_wait,
        per_atom_distributions=dists,
        existing_fingerprints=fps,
        existing_summaries=summaries,
    )

    try:
        summary = pipeline.run()
    except KeyboardInterrupt:
        print(f"\nInterrupted. Resume with: --job-id {job_id}")
        sys.exit(130)
    except Exception:
        _logger.exception("Pipeline failed")
        print(f"\nFailed. Resume with: --job-id {job_id}")
        sys.exit(1)

    failed_atoms = summary.get("failed_atoms", {})
    if failed_atoms:
        for aid, err in failed_atoms.items():
            print(f"  FAILED: {aid} — {err}")

    # Post-merge
    print("\nMerging Phase 9 results (old + new)...")
    final_counts = merge_p9_items(atom_ids, backup, target)

    # Final report
    print(f"\nFinal Phase 9 counts (target={target}):")
    ok = 0
    still_below: list[tuple[str, int]] = []
    for atom_id in atom_ids:
        count = final_counts.get(atom_id, 0)
        flag = "OK" if count >= target else "BELOW"
        print(f"  [{flag}] {atom_id}: {count}")
        if count >= target:
            ok += 1
        else:
            still_below.append((atom_id, count))

    print(f"\n{ok}/{len(atom_ids)} atoms at or above target.")
    if still_below:
        print(f"{len(still_below)} atoms still below:")
        for aid, count in still_below:
            print(f"   {aid}: {count}/{target}")
    sys.exit(0 if not still_below else 1)


def _print_deficit_status(
    atom_ids: list[str],
    summaries: dict[str, dict],
    dists: dict[str, "DifficultyDistribution"],
    target: int,
) -> None:
    """Print per-atom deficit status before starting the pipeline."""
    print(f"\nDeficit plan (target={target}):")
    for aid in atom_ids:
        s = summaries.get(aid, {})
        d = dists[aid]
        by = s.get("by_difficulty", {})
        have = s.get("total", 0)
        print(
            f"  {aid}: has {have} "
            f"({by.get('easy',0)}E/{by.get('medium',0)}M"
            f"/{by.get('hard',0)}H)"
            f" -> planning {d.total} new "
            f"({d.easy}E/{d.medium}M/{d.hard}H)"
        )
    print()


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


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
    p = argparse.ArgumentParser(
        description="Deficit-based re-run for underperforming atoms",
    )
    p.add_argument(
        "--target", type=int, default=_DEFAULT_TARGET,
        help=f"Target total questions per atom (default: {_DEFAULT_TARGET})",
    )
    p.add_argument(
        "--atoms", nargs="+",
        help="Atom IDs to re-run (default: auto-detect below target)",
    )
    p.add_argument("--atoms-file", help="JSON file with atom IDs")
    p.add_argument("--job-id", help="Resume a previous run")
    p.add_argument("--skip-images", action="store_true")
    p.add_argument("--no-caffeinate", action="store_true")
    p.add_argument("--poll-interval", type=int, default=60)
    p.add_argument("--max-wait", type=int, default=86400)
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    main()
