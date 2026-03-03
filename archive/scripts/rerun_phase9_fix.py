"""ARCHIVED 2026-03-02: One-off data repair script. The underlying cache bug
is already fixed in batch_pipeline_stages.py and all affected atoms have been
reprocessed.

Original description:
Surgical Phase 9 re-run for atoms affected by the _reload_items cache bug.

Root cause: when the pipeline resumed after Phase 78, _reload_items() skipped
Phase 8 checkpoints because Phase 4 atoms were already in the `items` dict.
Phase 9 then saved Phase 4 XML (no feedback) instead of Phase 8 XML (with
feedback enrichment).

Fix (already applied to batch_pipeline_stages.py): pass {} instead of `items`
when reloading Phase 6 and Phase 8 checkpoints so Phase 4 cache doesn't block.

DATA INTEGRITY GUARANTEE:
  - ALL existing Phase 9 checkpoints are backed up to .rerun_backups/<job_id>_p9_backup.json
    BEFORE any checkpoint is touched.
  - Checkpoints are only overwritten if the new Phase 9 run produces results for that atom.
  - If Phase 9 fails completely for an atom, its checkpoint is left untouched.
  - Backup can be used to restore at any time.

Usage:
    uv run python -m app.question_generation.scripts.rerun_phase9_fix [--dry-run] [-v]
    uv run python -m app.question_generation.scripts.rerun_phase9_fix --atoms ALG-01-03 ALG-01-04

Test on 3-5 atoms first:
    uv run python -m app.question_generation.scripts.rerun_phase9_fix --atoms ALG-01-03 ALG-01-04 ALG-01-05 --dry-run
    uv run python -m app.question_generation.scripts.rerun_phase9_fix --atoms ALG-01-03 ALG-01-04 ALG-01-05
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

QUESTION_GENERATION_DIR = Path("app/data/question-generation")
BACKUP_DIR = QUESTION_GENERATION_DIR / ".rerun_backups"

# Atoms in active re-runs — skip, they'll get fresh Phase 9 from their own runs
SKIP_ATOMS = {
    # 17-atom re-run (batch_api_20260223_224106)
    "A-M1-ALG-01-09", "A-M1-ALG-02-04", "A-M1-ALG-03-10", "A-M1-ALG-03-14",
    "A-M1-ALG-04-02", "A-M1-ALG-04-05", "A-M1-ALG-06-04", "A-M1-GEO-02-16",
    "A-M1-GEO-03-06", "A-M1-PROB-01-04", "A-M1-PROB-01-05", "A-M1-PROB-01-07",
    "A-M1-PROB-01-08", "A-M1-PROB-01-10", "A-M1-PROB-02-01", "A-M1-PROB-03-07",
    "A-M1-PROB-03-08",
    # 8-atom new run (batch_api_20260223_140518)
    "A-M1-ALG-02-06", "A-M1-ALG-05-01", "A-M1-ALG-05-10", "A-M1-GEO-01-01",
    "A-M1-GEO-02-15", "A-M1-GEO-03-10", "A-M1-NUM-01-22", "A-M1-NUM-03-17",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("rerun_phase9_fix")


def _generate_job_id() -> str:
    return f"batch_phase9fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def _make_completed_state(job_id: str, atom_ids: list[str]) -> dict:
    """Build a batch state with phases 0-78 completed, phase_9 pending."""
    completed = {"status": "completed"}
    return {
        "job_id": job_id,
        "active_atom_ids": atom_ids,
        "failed_atoms": {},
        "phases": {
            "phase_0": completed,
            "phase_1": completed,
            "phase_2": completed,
            "phase_3": completed,
            "phase_4": completed,
            "phase_5": completed,
            "phase_6": completed,
            "phase_78_enhance": completed,
            "phase_78_review": completed,
            # phase_9 intentionally absent → will run fresh
        },
    }


def pre_save_phase9(job_id: str, affected_atoms: list[str]) -> Path:
    """
    Back up ALL existing Phase 9 checkpoints before touching anything.
    Returns path to the backup file.
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / f"{job_id}_p9_backup.json"

    backup = {}
    for atom_id in affected_atoms:
        p9_ckpt = QUESTION_GENERATION_DIR / atom_id / "checkpoints/phase_9_final_validation.json"
        if p9_ckpt.exists():
            backup[atom_id] = json.loads(p9_ckpt.read_text())

    backup_path.write_text(json.dumps(backup, ensure_ascii=False, indent=2))
    logger.info(
        "Pre-save complete: backed up Phase 9 for %d atoms → %s",
        len(backup), backup_path,
    )
    return backup_path


def find_affected_atoms(atom_filter: set[str] | None) -> list[str]:
    """Find atoms needing Phase 9 re-run: Phase 8 has feedback, Phase 9 doesn't.

    When atom_filter is provided (--atoms flag), SKIP_ATOMS is bypassed so that
    explicitly requested atoms are always processed.
    """
    affected = []
    for atom_dir in sorted(QUESTION_GENERATION_DIR.glob("A-M1-*")):
        atom_id = atom_dir.name
        # Only apply SKIP_ATOMS when no explicit atom list was given
        if not atom_filter and atom_id in SKIP_ATOMS:
            continue
        if atom_filter and atom_id not in atom_filter:
            continue

        p8_ckpt = atom_dir / "checkpoints/phase_8_feedback.json"
        p9_ckpt = atom_dir / "checkpoints/phase_9_final_validation.json"

        if not p8_ckpt.exists():
            continue

        # Skip if Phase 9 already has feedback (clean atom)
        if p9_ckpt.exists():
            try:
                p9 = json.loads(p9_ckpt.read_text())
                items9 = p9.get("items", [])
                if items9 and isinstance(items9, list):
                    if "qti-feedback-inline" in items9[0].get("qti_xml", ""):
                        continue  # already clean
            except Exception:
                pass

        # Only include if Phase 8 actually has items with feedback to recover
        try:
            p8 = json.loads(p8_ckpt.read_text())
            items8 = p8.get("items", [])
            has_fb = any(
                "qti-feedback-inline" in i.get("qti_xml", "")
                for i in items8 if isinstance(i, dict)
            )
            if not has_fb:
                logger.warning("%s: Phase 8 has no feedback items — cannot recover", atom_id)
                continue
        except Exception:
            continue

        affected.append(atom_id)
    return affected


def run(dry_run: bool = False, atom_filter: set[str] | None = None, verbose: bool = False) -> None:
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Verify fix is in place BEFORE doing anything
    import inspect
    import app.question_generation.batch_pipeline_stages as stages
    src = inspect.getsource(stages.run_phase_78)
    if '_reload_items(state, 8, "feedback", items)' in src:
        logger.error("_reload_items bug NOT fixed in batch_pipeline_stages.py — aborting")
        logger.error("Fix: change _reload_items(state, 8, 'feedback', items) → _reload_items(state, 8, 'feedback', {})")
        sys.exit(1)
    logger.info("Fix verified: _reload_items uses {} for Phase 8 reload ✅")

    affected = find_affected_atoms(atom_filter)
    logger.info("Atoms requiring Phase 9 re-run: %d", len(affected))

    if not affected:
        logger.info("Nothing to do.")
        return

    if dry_run:
        print(f"\nDRY RUN — {len(affected)} atoms would be processed:")
        total_p8 = 0
        for a in affected:
            p8 = json.loads((QUESTION_GENERATION_DIR / a / "checkpoints/phase_8_feedback.json").read_text())
            items8 = p8.get("items", [])
            fb = sum(1 for i in items8 if isinstance(i, dict) and "qti-feedback-inline" in i.get("qti_xml", ""))
            p9_ckpt = QUESTION_GENERATION_DIR / a / "checkpoints/phase_9_final_validation.json"
            p9_count = 0
            if p9_ckpt.exists():
                p9 = json.loads(p9_ckpt.read_text())
                p9_count = len(p9.get("items", []))
            print(f"  {a}: {fb}/{len(items8)} Phase8 w/feedback | current Phase9 count: {p9_count}")
            total_p8 += fb
        print(f"\nTotal items to validate via Phase 9: {total_p8}")
        return

    from app.question_generation.batch_pipeline import BatchAtomPipeline
    from app.question_generation.batch_checkpoint import save_run_state

    job_id = _generate_job_id()
    logger.info("Job ID: %s", job_id)

    # === STEP 1: PRE-SAVE ALL PHASE 9 CHECKPOINTS ===
    backup_path = pre_save_phase9(job_id, affected)
    logger.info("Backup saved. Safe to proceed.")

    # === STEP 2: Create batch state with phases 0-78 completed ===
    batch_dir = QUESTION_GENERATION_DIR / ".batch_runs" / job_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = batch_dir / "batch_state.json"
    state = _make_completed_state(job_id, affected)
    save_run_state(ckpt_path, state)
    logger.info("Batch state created: phases 0-78 completed, phase_9 pending")

    # === STEP 3: Run pipeline (only Phase 9 will execute) ===
    pipeline = BatchAtomPipeline(
        job_id=job_id,
        atom_ids=affected,
        model="gpt-4.1",
    )
    logger.info("Starting Phase 9 for %d atoms...", len(affected))
    summary = pipeline.run()

    # === STEP 4: Report results ===
    counts = summary.get("counts", {})
    clean = sum(1 for c in counts.values() if c >= 30)
    total = len(counts)

    print(f"\n=== PHASE 9 FIX COMPLETE ===")
    print(f"Atoms with ≥30 items: {clean}/{total}")
    print(f"Backup: {backup_path}")
    print(f"\nPer-atom counts:")
    for atom_id, count in sorted(counts.items()):
        flag = "✅" if count >= 30 else "⚠️ UNDER 30"
        print(f"  {atom_id}: {count} {flag}")

    # Atoms that got NO results from Phase 9 → checkpoint untouched (safe)
    no_result = [a for a in affected if a not in counts]
    if no_result:
        logger.warning(
            "%d atoms got no Phase 9 results — their checkpoints were NOT touched: %s",
            len(no_result), no_result,
        )

    logger.info("Job ID: %s", job_id)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 9 surgical fix — adds feedback integrity to 139 affected atoms"
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done, no changes")
    parser.add_argument(
        "--atoms", nargs="*", metavar="ALG-01-03",
        help="Short atom IDs (without A-M1- prefix). Omit for all affected atoms.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    atom_filter = None
    if args.atoms:
        atom_filter = {f"A-M1-{a}" if not a.startswith("A-M1-") else a for a in args.atoms}

    run(dry_run=args.dry_run, atom_filter=atom_filter, verbose=args.verbose)


if __name__ == "__main__":
    main()
