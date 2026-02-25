"""retry_quarantined.py — Re-run Phase 7-9 for items quarantined in Phase 7.

Recovers items that passed Phases 1-6 (valid QTI XML) but failed XSD
validation during Phase 7 feedback enhancement. Only processes the
quarantined items; existing Phase 9 results are never touched.

Safety protocol:
  1. Loads quarantined item IDs from a previous batch run.
  2. Reloads their Phase 6 versions (pre-feedback, valid XML).
  3. Runs only Phases 7-8-9 on those items via a fresh batch job.
  4. Merges results ADDITIVELY into Phase 9 (never removes existing items).

Usage:
    # Retry quarantined items from a previous job
    uv run python -m app.question_generation.scripts.retry_quarantined \
        --source-job batch_api_20260224_202852

    # With verbose logging
    uv run python -m app.question_generation.scripts.retry_quarantined \
        --source-job batch_api_20260224_202852 -v
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

_logger = logging.getLogger(__name__)


def main() -> None:
    args = _parse_args()
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    load_dotenv()

    from app.utils.paths import QUESTION_GENERATION_DIR

    source_dir = (
        QUESTION_GENERATION_DIR / ".batch_runs" / args.source_job
    )
    quarantine_path = source_dir / "phase_7_quarantine.json"
    if not quarantine_path.exists():
        print(f"No quarantine file found at {quarantine_path}")
        sys.exit(1)

    quarantined = json.loads(
        quarantine_path.read_text(encoding="utf-8"),
    )
    quarantined_ids = {
        item["item_id"] for item in quarantined["items"]
    }
    print(
        f"Found {len(quarantined_ids)} quarantined items "
        f"from job {args.source_job}"
    )

    items = _load_quarantined_from_phase6(
        quarantined_ids, QUESTION_GENERATION_DIR,
    )
    total = sum(len(v) for v in items.values())
    if total == 0:
        print("No Phase 6 items found for quarantined IDs.")
        sys.exit(1)

    for atom_id, atom_items in items.items():
        print(f"  {atom_id}: {len(atom_items)} items to retry")

    # Pre-save current Phase 9 items for additive merge
    atom_ids = list(items.keys())
    existing_p9 = _snapshot_p9(atom_ids, QUESTION_GENERATION_DIR)

    # Run phases 7-9 in a fresh batch job
    rescued = _run_phases_78_9(
        items, args.poll_interval, args.max_wait,
    )
    rescued_total = sum(len(v) for v in rescued.values())
    print(f"\n{rescued_total}/{total} items rescued through Phase 9")

    # Additive merge into Phase 9
    _additive_merge(atom_ids, existing_p9, rescued, QUESTION_GENERATION_DIR)


def _load_quarantined_from_phase6(
    quarantined_ids: set[str],
    qg_dir: Path,
) -> dict[str, list]:
    """Load Phase 6 (pre-feedback) versions of quarantined items."""
    from app.question_generation.helpers import (
        deserialize_items,
        load_checkpoint,
    )

    items_by_atom: dict[str, list] = {}
    for atom_dir in sorted(qg_dir.glob("A-M1-*")):
        if not atom_dir.is_dir():
            continue
        ckpt = load_checkpoint(atom_dir, 6, "base_validation")
        if not ckpt or not ckpt.get("items"):
            continue
        atom_items = deserialize_items(ckpt["items"])
        matched = [
            it for it in atom_items if it.item_id in quarantined_ids
        ]
        if matched:
            items_by_atom[atom_dir.name] = matched
    return items_by_atom


def _snapshot_p9(
    atom_ids: list[str], qg_dir: Path,
) -> dict[str, list[dict]]:
    """Read current Phase 9 items for each atom."""
    snapshot: dict[str, list[dict]] = {}
    for atom_id in atom_ids:
        p = qg_dir / atom_id / "checkpoints" / (
            "phase_9_final_validation.json"
        )
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
    return snapshot


def _run_phases_78_9(
    items: dict[str, list],
    poll_interval: int,
    max_wait: int,
) -> dict[str, list]:
    """Run Phase 7-8-9 on the given items via batch API."""
    from app.question_generation.batch_api import (
        OpenAIBatchSubmitter,
    )
    from app.question_generation.batch_checkpoint import (
        new_run_state,
        save_run_state,
    )
    from app.question_generation.batch_pipeline_stages import (
        run_phase_78,
        run_phase_9,
    )
    from app.utils.paths import QUESTION_GENERATION_DIR

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required")

    job_id = _generate_job_id()
    model = "gpt-5.1"
    submitter = OpenAIBatchSubmitter(api_key, poll_interval, max_wait)
    batch_dir = QUESTION_GENERATION_DIR / ".batch_runs" / job_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = batch_dir / "batch_state.json"

    atom_ids = list(items.keys())
    state = new_run_state(job_id, atom_ids)
    save_run_state(ckpt_path, state)

    _logger.info("Retry job %s — running Phase 7-9 only", job_id)

    def submit_fn(
        phase_key: str, reqs: list,
    ) -> list:
        from app.question_generation.batch_checkpoint import (
            get_phase,
            update_phase,
        )

        p = get_phase(state, phase_key)
        st = p.get("status", "pending")
        meta = {"job_id": job_id, "phase": phase_key}

        if st in ("pending", None):
            jp = batch_dir / f"{phase_key}_input.jsonl"
            jp, sha = submitter.write_jsonl(reqs, jp)
            fid = submitter.upload_file(jp)
            update_phase(
                state, phase_key, ckpt_path,
                status="file_uploaded",
                file_id=fid,
                input_jsonl=str(jp),
                jsonl_sha256=sha,
                request_count=len(reqs),
                metadata=meta,
            )
            st = "file_uploaded"

        if st == "file_uploaded":
            fid = p.get("file_id", "")
            bid = submitter.create_batch(fid, meta)
            update_phase(
                state, phase_key, ckpt_path,
                status="submitted", batch_id=bid, metadata=meta,
            )
            st = "submitted"

        if st == "submitted":
            bid = p.get("batch_id", "")
            obj = submitter.poll_until_done(bid)
            if obj.get("status") != "completed":
                raise RuntimeError(
                    f"Batch {bid}: {obj.get('status')}"
                )
            ofid = obj.get("output_file_id", "")
            rp = batch_dir / f"{phase_key}_results.jsonl"
            submitter.download_file(ofid, rp)
            update_phase(
                state, phase_key, ckpt_path,
                status="results_downloaded",
                results_jsonl=str(rp),
            )

        rp = Path(
            get_phase(state, phase_key).get("results_jsonl", ""),
        )
        return submitter.parse_results_file(rp)

    try:
        items = run_phase_78(state, ckpt_path, items, model, submit_fn)
        items = run_phase_9(state, ckpt_path, items, model, submit_fn)
    except KeyboardInterrupt:
        print(f"\nInterrupted. Job: {job_id}")
        sys.exit(130)
    except Exception:
        _logger.exception("Retry pipeline failed (job: %s)", job_id)
        sys.exit(1)

    return items


def _additive_merge(
    atom_ids: list[str],
    existing_p9: dict[str, list[dict]],
    rescued: dict[str, list],
    qg_dir: Path,
) -> None:
    """Merge rescued items into Phase 9 without losing existing ones."""
    from app.question_generation.helpers import serialize_items

    print("\nAdditive merge into Phase 9:")
    for atom_id in atom_ids:
        old_items = existing_p9.get(atom_id, [])
        old_ids = {item["item_id"] for item in old_items}

        rescued_items = rescued.get(atom_id, [])
        new_serialized = serialize_items(rescued_items)
        truly_new = [
            it for it in new_serialized
            if it["item_id"] not in old_ids
        ]

        merged = old_items + truly_new
        p = qg_dir / atom_id / "checkpoints" / (
            "phase_9_final_validation.json"
        )
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(
                {"final_count": len(merged), "items": merged},
                ensure_ascii=False, indent=2,
            ),
            encoding="utf-8",
        )
        print(
            f"  {atom_id}: {len(old_items)} existing "
            f"+ {len(truly_new)} rescued = {len(merged)} total"
        )


def _generate_job_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"retry_q7_{ts}"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Retry quarantined Phase 7 items through Phase 7-9",
    )
    p.add_argument(
        "--source-job", required=True,
        help="Job ID of the original run with quarantined items",
    )
    p.add_argument("--poll-interval", type=int, default=60)
    p.add_argument("--max-wait", type=int, default=86400)
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    main()
