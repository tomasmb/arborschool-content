"""Batch question generation — process all eligible atoms sequentially.

Runs the full question generation pipeline for each covered atom,
one at a time, with disk-persisted batch state for resume support.

Usage:
    # Generate all atoms that haven't been generated yet
    python -m app.question_generation.scripts.run_batch_generation \
        --mode pending_only

    # Re-run all covered atoms (skip completed phases via --resume)
    python -m app.question_generation.scripts.run_batch_generation \
        --mode all

    # Skip image generation (bypasses generatability gate)
    python -m app.question_generation.scripts.run_batch_generation \
        --mode pending_only --skip-images

    # Resume an interrupted batch run
    python -m app.question_generation.scripts.run_batch_generation \
        --mode pending_only --job-id batch_question_gen-20260218-abc123
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.question_generation.models import PipelineConfig, PipelineResult
from app.question_generation.pipeline import AtomQuestionPipeline
from app.question_generation.progress import report_progress
from app.utils.logging_config import setup_logging
from app.utils.paths import QUESTION_GENERATION_DIR, get_atoms_file

# Phase threshold: atoms with last_completed_phase >= this are "done"
_FULLY_GENERATED_PHASE = 9


def main() -> None:
    """CLI entry point."""
    args = _parse_args()
    setup_logging(verbose=args.verbose)

    atoms = _load_eligible_atoms(args.mode)
    if args.skip_images:
        atoms = _exclude_atoms_needing_images(atoms)
    if not atoms:
        print("No eligible atoms found.")
        sys.exit(0)

    state_path = _state_file_path(args.job_id)
    state = _load_state(state_path)

    # Filter out atoms already completed in a prior run
    remaining = _filter_already_done(atoms, state)
    total = len(atoms)
    done_before = total - len(remaining)

    print(f"Batch generation: {total} eligible, "
          f"{done_before} already done, {len(remaining)} to process")
    if args.skip_images:
        print("  (image generation SKIPPED)")

    report_progress(done_before, total)

    succeeded = state.get("succeeded", 0)
    failed_ids: list[str] = list(state.get("failed_ids", []))

    for i, atom in enumerate(remaining):
        atom_id = atom["id"]
        seq = done_before + i + 1
        print(f"\n{'=' * 60}")
        print(f"[{seq}/{total}] Processing {atom_id}")
        print(f"{'=' * 60}")

        result = _run_single_atom(atom_id, args)

        if result.success:
            succeeded += 1
        else:
            failed_ids.append(atom_id)

        # Persist state after every atom for crash resilience
        state["completed_ids"] = state.get("completed_ids", [])
        state["completed_ids"].append(atom_id)
        state["succeeded"] = succeeded
        state["failed_ids"] = failed_ids
        state["last_atom"] = atom_id
        state["last_updated"] = datetime.now(
            timezone.utc,
        ).isoformat()
        _save_state(state_path, state)

        report_progress(done_before + i + 1, total)

    _print_summary(total, succeeded, failed_ids)

    total_failed = len(failed_ids)
    sys.exit(0 if total_failed == 0 else 1)


# -------------------------------------------------------------------
# Atom loading and filtering
# -------------------------------------------------------------------


def _load_eligible_atoms(mode: str) -> list[dict[str, Any]]:
    """Load atoms with coverage, optionally filtering by gen status.

    Args:
        mode: "pending_only" skips atoms with phase >= 9.
              "all" includes every covered atom.

    Returns:
        List of raw atom dicts eligible for generation.
    """
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

    # pending_only: skip atoms already fully generated
    from app.question_generation.helpers import (
        get_last_completed_phase,
    )
    pending: list[dict[str, Any]] = []
    for atom in covered:
        phase = get_last_completed_phase(atom["id"])
        if phase is None or phase < _FULLY_GENERATED_PHASE:
            pending.append(atom)
    return pending


def _load_all_atoms() -> list[dict[str, Any]]:
    """Load all atoms from the canonical file."""
    path = get_atoms_file("paes_m1_2026")
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("atoms", [])


def _exclude_atoms_needing_images(
    atoms: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Keep only atoms whose enrichment shows no image requirements.

    Atoms without an enrichment checkpoint are excluded (we can't
    confirm they don't need images).
    """
    from app.question_generation.helpers import (
        get_enrichment_image_types,
    )

    kept: list[dict[str, Any]] = []
    skipped = 0
    for atom in atoms:
        image_types = get_enrichment_image_types(atom["id"])
        if image_types is None:
            skipped += 1
            continue
        if image_types:
            skipped += 1
            continue
        kept.append(atom)

    if skipped:
        print(f"  Excluded {skipped} atom(s) that require images "
              f"or lack enrichment data")
    return kept


def _filter_already_done(
    atoms: list[dict[str, Any]],
    state: dict[str, Any],
) -> list[dict[str, Any]]:
    """Remove atoms that were already processed in this batch run."""
    done = set(state.get("completed_ids", []))
    return [a for a in atoms if a["id"] not in done]


# -------------------------------------------------------------------
# Pipeline execution
# -------------------------------------------------------------------


def _run_single_atom(
    atom_id: str,
    args: argparse.Namespace,
) -> PipelineResult:
    """Run the full pipeline for one atom."""
    config = PipelineConfig(
        atom_id=atom_id,
        resume=True,
        skip_images=args.skip_images,
        dry_run=args.dry_run,
    )
    pipeline = AtomQuestionPipeline(config=config)
    return pipeline.run(atom_id)


# -------------------------------------------------------------------
# Batch state persistence
# -------------------------------------------------------------------


def _state_file_path(job_id: str | None) -> Path:
    """Resolve the batch state file path.

    State is stored inside the question-generation directory so it
    co-locates with per-atom checkpoint data.
    """
    name = job_id or "default"
    return QUESTION_GENERATION_DIR / f".batch_state_{name}.json"


def _load_state(path: Path) -> dict[str, Any]:
    """Load batch state from disk, or return empty state."""
    if not path.exists():
        return {
            "completed_ids": [],
            "succeeded": 0,
            "failed_ids": [],
            "accumulated_cost_usd": 0.0,
        }
    try:
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            return {"completed_ids": [], "succeeded": 0,
                    "failed_ids": [], "accumulated_cost_usd": 0.0}
        return json.loads(text)
    except (json.JSONDecodeError, OSError):
        return {"completed_ids": [], "succeeded": 0,
                "failed_ids": [], "accumulated_cost_usd": 0.0}


def _save_state(path: Path, state: dict[str, Any]) -> None:
    """Save batch state atomically (temp + rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        dir=str(path.parent), suffix=".tmp",
    )
    try:
        with open(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, default=str)
        Path(tmp).replace(path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


# -------------------------------------------------------------------
# Output
# -------------------------------------------------------------------


def _print_summary(
    total: int,
    succeeded: int,
    failed_ids: list[str],
) -> None:
    """Print a final summary of the batch run."""
    print(f"\n{'=' * 60}")
    print("BATCH GENERATION SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total atoms:  {total}")
    print(f"Succeeded:    {succeeded}")
    print(f"Failed:       {len(failed_ids)}")

    if failed_ids:
        print("\nFailed atoms:")
        for aid in failed_ids:
            print(f"  - {aid}")

    print(f"{'=' * 60}\n")


# -------------------------------------------------------------------
# CLI
# -------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Batch question generation for all "
                    "eligible atoms (sequential).",
    )
    parser.add_argument(
        "--mode",
        choices=["pending_only", "all"],
        default="pending_only",
        help="pending_only: skip fully-generated atoms. "
             "all: re-run every covered atom. (default: pending_only)",
    )
    parser.add_argument(
        "--skip-images", action="store_true",
        help="Skip Phase 4b image generation and bypass "
             "the generatability gate",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run through Phase 9 but skip DB sync",
    )
    parser.add_argument(
        "--job-id",
        help="Job ID for state file naming (for resume support)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
