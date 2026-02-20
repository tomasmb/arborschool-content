"""Late-stage batch pipeline phases (5-9).

Extracted from BatchAtomPipeline to keep files under 500 lines.
Each function receives the pipeline's state objects and the batch
submitter rather than operating on ``self``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.question_generation.batch_api import (
    BatchRequest,
    BatchResponse,
    OpenAIBatchSubmitter,
)
from app.question_generation.batch_checkpoint import (
    get_active_atoms,
    is_phase_completed,
    update_phase,
)
from app.question_generation.batch_phase_processors import (
    process_enhancement_responses,
    process_final_validation_responses,
    process_review_responses,
    process_solvability_responses,
)
from app.question_generation.batch_request_builders import (
    build_correction_request,
    build_enhancement_request,
    build_final_validation_request,
    build_review_request,
    build_solvability_request,
)
from app.question_generation.helpers import (
    deserialize_items,
    load_checkpoint,
    save_checkpoint,
    serialize_items,
)
from app.question_generation.models import GeneratedItem
from app.question_generation.validators import DuplicateGate
from app.utils.paths import QUESTION_GENERATION_DIR

logger = logging.getLogger(__name__)

_MAX_CORRECTION_ROUNDS = 2


# ------------------------------------------------------------------
# Types for passing pipeline state without self
# ------------------------------------------------------------------


SubmitFn = Any  # Callable[[str, list[BatchRequest]], list[BatchResponse]]


# ------------------------------------------------------------------
# Phase 5 — Dedupe (local)
# ------------------------------------------------------------------


def run_phase_5(
    state: dict[str, Any],
    ckpt_path: Path,
    items: dict[str, list[GeneratedItem]],
) -> dict[str, list[GeneratedItem]]:
    """Phase 5: Deduplication gate (local, no LLM)."""
    if is_phase_completed(state, "phase_5"):
        return items

    logger.info("Phase 5: Deduplication gate")
    gate = DuplicateGate()
    for atom_id in list(items):
        atom_items = items[atom_id]
        result = gate.run(atom_items, pool_total=len(atom_items))
        if result.success and result.data:
            items[atom_id] = result.data["filtered_items"]

    update_phase(state, "phase_5", ckpt_path, status="completed")
    return items


# ------------------------------------------------------------------
# Phase 6 — Base Validation (batch)
# ------------------------------------------------------------------


def run_phase_6(
    state: dict[str, Any],
    ckpt_path: Path,
    items: dict[str, list[GeneratedItem]],
    model: str,
    submit_fn: SubmitFn,
) -> dict[str, list[GeneratedItem]]:
    """Phase 6: Solvability validation via batch."""
    if is_phase_completed(state, "phase_6"):
        return _reload_items(state, 6, "base_validation", items)

    logger.info("Phase 6: Solvability validation")
    requests: list[BatchRequest] = []
    items_by_id: dict[str, GeneratedItem] = {}

    for atom_id, atom_items in items.items():
        for item in atom_items:
            requests.append(
                build_solvability_request(item, atom_id, model),
            )
            items_by_id[item.item_id] = item

    if not requests:
        update_phase(
            state, "phase_6", ckpt_path,
            status="completed", request_count=0,
        )
        return items

    responses = submit_fn("phase_6", requests)
    passed, errors = process_solvability_responses(
        responses, items_by_id,
    )
    if errors:
        logger.warning("Phase 6: %d validation errors", len(errors))

    passed_by_atom = _group_items_by_atom(passed, items)
    for atom_id, atom_items in passed_by_atom.items():
        out_dir = QUESTION_GENERATION_DIR / atom_id
        save_checkpoint(out_dir, 6, "base_validation", {
            "valid_count": len(atom_items),
            "items": serialize_items(atom_items),
        })

    update_phase(state, "phase_6", ckpt_path, status="completed")
    return passed_by_atom


# ------------------------------------------------------------------
# Phases 7-8 — Feedback (batch, multi-round)
# ------------------------------------------------------------------


def run_phase_78(
    state: dict[str, Any],
    ckpt_path: Path,
    items: dict[str, list[GeneratedItem]],
    model: str,
    submit_fn: SubmitFn,
) -> dict[str, list[GeneratedItem]]:
    """Phases 7-8: Enhancement + review + correction cycle."""
    if is_phase_completed(state, "phase_78_review"):
        return _reload_items(state, 8, "feedback", items)

    items = _run_enhance(state, ckpt_path, items, model, submit_fn)
    items = _run_review(state, ckpt_path, items, model, submit_fn)
    return items


def _run_enhance(
    state: dict[str, Any],
    ckpt_path: Path,
    items: dict[str, list[GeneratedItem]],
    model: str,
    submit_fn: SubmitFn,
) -> dict[str, list[GeneratedItem]]:
    if is_phase_completed(state, "phase_78_enhance"):
        return items

    logger.info("Phase 7: Feedback enhancement")
    requests: list[BatchRequest] = []
    items_by_id: dict[str, GeneratedItem] = {}

    for atom_id, atom_items in items.items():
        for item in atom_items:
            requests.append(
                build_enhancement_request(
                    item, atom_id, model=model,
                ),
            )
            items_by_id[item.item_id] = item

    if not requests:
        update_phase(
            state, "phase_78_enhance", ckpt_path,
            status="completed", request_count=0,
        )
        return items

    responses = submit_fn("phase_78_enhance", requests)
    succeeded, failures = process_enhancement_responses(
        responses, items_by_id,
    )

    if failures:
        logger.warning(
            "Phase 7: %d enhancement failures", len(failures),
        )
        for item_id in failures:
            for atom_id in list(items):
                items[atom_id] = [
                    i for i in items[atom_id]
                    if i.item_id != item_id
                ]

    update_phase(
        state, "phase_78_enhance", ckpt_path, status="completed",
    )
    return items


def _run_review(
    state: dict[str, Any],
    ckpt_path: Path,
    items: dict[str, list[GeneratedItem]],
    model: str,
    submit_fn: SubmitFn,
) -> dict[str, list[GeneratedItem]]:
    if is_phase_completed(state, "phase_78_review"):
        return items

    logger.info("Phase 8: Feedback review")
    requests: list[BatchRequest] = []
    items_by_id: dict[str, GeneratedItem] = {}

    for atom_id, atom_items in items.items():
        for item in atom_items:
            requests.append(
                build_review_request(item, atom_id, model),
            )
            items_by_id[item.item_id] = item

    if not requests:
        update_phase(
            state, "phase_78_review", ckpt_path,
            status="completed", request_count=0,
        )
        return items

    responses = submit_fn("phase_78_review", requests)
    passed, failed_issues = process_review_responses(responses)

    if failed_issues:
        logger.info(
            "Phase 8: %d items need correction",
            len(failed_issues),
        )
        items = _correction_cycle(
            failed_issues, items_by_id, items,
            model, submit_fn,
        )

    for atom_id, atom_items in items.items():
        out_dir = QUESTION_GENERATION_DIR / atom_id
        save_checkpoint(out_dir, 8, "feedback", {
            "item_count": len(atom_items),
            "items": serialize_items(atom_items),
        })

    update_phase(
        state, "phase_78_review", ckpt_path, status="completed",
    )
    return items


def _correction_cycle(
    failed_issues: dict[str, str],
    items_by_id: dict[str, GeneratedItem],
    items: dict[str, list[GeneratedItem]],
    model: str,
    submit_fn: SubmitFn,
) -> dict[str, list[GeneratedItem]]:
    """Run correction + re-review for items that failed review."""
    for round_num in range(1, _MAX_CORRECTION_ROUNDS + 1):
        if not failed_issues:
            break

        logger.info(
            "Correction round %d: %d items",
            round_num, len(failed_issues),
        )
        requests: list[BatchRequest] = []
        for item_id, issues in failed_issues.items():
            item = items_by_id.get(item_id)
            if not item:
                continue
            atom_id = _find_atom_for_item(item_id, items)
            if not atom_id:
                continue
            requests.append(build_correction_request(
                item, atom_id, issues, model=model,
            ))

        if not requests:
            break

        responses = submit_fn(
            f"phase_78_correct_r{round_num}", requests,
        )
        corr_ok, _ = process_enhancement_responses(
            responses, items_by_id,
        )
        for item_id, item in corr_ok.items():
            items_by_id[item_id] = item

        review_reqs: list[BatchRequest] = []
        for iid in corr_ok:
            atom_id = _find_atom_for_item(iid, items)
            if atom_id and iid in items_by_id:
                review_reqs.append(build_review_request(
                    items_by_id[iid], atom_id, model,
                ))

        if not review_reqs:
            break

        review_resp = submit_fn(
            f"phase_78_re_review_r{round_num}", review_reqs,
        )
        _, re_failed = process_review_responses(review_resp)
        failed_issues = re_failed

    still_failed = set(failed_issues.keys())
    if still_failed:
        logger.warning(
            "%d items still failing after correction, removing",
            len(still_failed),
        )
        for atom_id in list(items):
            items[atom_id] = [
                i for i in items[atom_id]
                if i.item_id not in still_failed
            ]
    return items


# ------------------------------------------------------------------
# Phase 9 — Final Validation (batch)
# ------------------------------------------------------------------


def run_phase_9(
    state: dict[str, Any],
    ckpt_path: Path,
    items: dict[str, list[GeneratedItem]],
    model: str,
    submit_fn: SubmitFn,
) -> dict[str, list[GeneratedItem]]:
    """Phase 9: Final LLM validation via batch."""
    if is_phase_completed(state, "phase_9"):
        return items

    logger.info("Phase 9: Final validation")
    requests: list[BatchRequest] = []
    items_by_id: dict[str, GeneratedItem] = {}

    for atom_id, atom_items in items.items():
        for item in atom_items:
            requests.append(build_final_validation_request(
                item, atom_id, model=model,
            ))
            items_by_id[item.item_id] = item

    if not requests:
        update_phase(
            state, "phase_9", ckpt_path,
            status="completed", request_count=0,
        )
        return items

    responses = submit_fn("phase_9", requests)
    passed, errors = process_final_validation_responses(
        responses, items_by_id,
    )
    if errors:
        logger.warning("Phase 9: %d validation failures", len(errors))

    final_by_atom = _group_items_by_atom(passed, items)
    for atom_id, atom_items in final_by_atom.items():
        out_dir = QUESTION_GENERATION_DIR / atom_id
        save_checkpoint(out_dir, 9, "final_validation", {
            "final_count": len(atom_items),
            "items": serialize_items(atom_items),
        })

    update_phase(state, "phase_9", ckpt_path, status="completed")
    return final_by_atom


# ------------------------------------------------------------------
# Shared helpers
# ------------------------------------------------------------------


def _group_items_by_atom(
    flat_items: list[GeneratedItem],
    original_items: dict[str, list[GeneratedItem]],
) -> dict[str, list[GeneratedItem]]:
    """Group a flat item list back into per-atom dicts."""
    result: dict[str, list[GeneratedItem]] = {}
    for item in flat_items:
        atom_id = _find_atom_for_item(
            item.item_id, original_items,
        )
        if atom_id:
            result.setdefault(atom_id, []).append(item)
    return result


def _find_atom_for_item(
    item_id: str,
    items: dict[str, list[GeneratedItem]],
) -> str | None:
    for atom_id, atom_items in items.items():
        if any(i.item_id == item_id for i in atom_items):
            return atom_id
    return None


def _reload_items(
    state: dict[str, Any],
    phase_num: int,
    phase_name: str,
    existing: dict[str, list[GeneratedItem]],
) -> dict[str, list[GeneratedItem]]:
    """Reload items from per-atom checkpoints if not already loaded."""
    for atom_id in get_active_atoms(state):
        if atom_id in existing:
            continue
        out_dir = QUESTION_GENERATION_DIR / atom_id
        ckpt = load_checkpoint(out_dir, phase_num, phase_name)
        if ckpt and ckpt.get("items"):
            existing[atom_id] = deserialize_items(ckpt["items"])
    return existing
