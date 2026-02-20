"""Phase 8 orchestration — feedback enrichment with resume support.

Extracted from ``pipeline.py`` to keep the main orchestrator under
500 lines.  Contains:

- ``run_feedback``: top-level Phase 7-8 entry point with
  resume-aware carry-forward for already-enriched items.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from app.question_feedback.models import PipelineResult as FeedbackResult
from app.question_feedback.pipeline import QuestionPipeline
from app.question_generation.helpers import (
    deserialize_items,
    load_checkpoint,
    save_checkpoint,
    serialize_items,
)
from app.question_generation.models import (
    GeneratedItem,
    PhaseResult,
    PipelineResult,
)
from app.question_generation.progress import report_progress

logger = logging.getLogger(__name__)

_MAX_PARALLEL_FEEDBACK = 15


def run_feedback(
    items: list[GeneratedItem],
    result: PipelineResult,
    feedback_pipeline: QuestionPipeline,
    *,
    resume: bool = False,
    output_dir: Path | None = None,
) -> list[GeneratedItem] | None:
    """Run Phase 7-8 feedback enrichment.

    On resume, items with feedback='pass' are carried forward;
    only feedback_failed items are re-processed.  All items
    (enriched + failed) are saved in the checkpoint so failed
    ones can be retried on the next resume.
    """
    carried, to_process = _split_for_resume(
        items, resume, output_dir,
    )
    if not to_process:
        if carried:
            result.phase_results.append(PhaseResult(
                phase_name="feedback_enrichment",
                success=True,
                data={"enriched_items": carried},
            ))
        return carried or None

    total = len(to_process)
    logger.info(
        "Phases 7-8: Feedback for %d items (%d carried)",
        total, len(carried),
    )
    report_progress(0, total)

    enriched: list[GeneratedItem] = list(carried)
    all_items: list[GeneratedItem] = list(carried)
    errors: list[str] = []
    completed = 0
    ckpt_lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=_MAX_PARALLEL_FEEDBACK) as pool:
        futures = {
            pool.submit(
                _enrich_single, feedback_pipeline, it,
            ): it
            for it in to_process
        }
        for future in as_completed(futures):
            item = futures[future]
            fb = future.result()
            with ckpt_lock:
                completed += 1
                if fb.success and fb.qti_xml_final:
                    item.qti_xml = fb.qti_xml_final
                    item.feedback_failed = False
                    if item.pipeline_meta:
                        item.pipeline_meta.validators.feedback = (
                            "pass"
                        )
                    enriched.append(item)
                else:
                    item.feedback_failed = True
                    errors.append(
                        f"{item.item_id}: "
                        f"{fb.stage_failed}: {fb.error}",
                    )
                all_items.append(item)
                report_progress(completed, total)
                if output_dir:
                    save_checkpoint(
                        output_dir, 8, "feedback",
                        {
                            "enriched_count": len(enriched),
                            "items": serialize_items(all_items),
                        },
                    )

    phase = PhaseResult(
        phase_name="feedback_enrichment",
        success=len(enriched) > 0,
        data={"enriched_items": enriched},
        errors=errors,
    )
    result.phase_results.append(phase)
    return enriched if enriched else None


def _enrich_single(
    pipeline: QuestionPipeline, item: GeneratedItem,
) -> FeedbackResult:
    """Run feedback enrichment on a single item."""
    return pipeline.process(
        question_id=item.item_id,
        qti_xml=item.qti_xml,
        output_dir=None,
    )


def _split_for_resume(
    items: list[GeneratedItem],
    resume: bool,
    output_dir: Path | None = None,
) -> tuple[list[GeneratedItem], list[GeneratedItem]]:
    """Split items into carried (feedback=pass) vs to-process.

    Loads the phase_8 checkpoint to identify already-enriched items,
    mirroring the approach phase 6 uses.  Checkpoint versions are
    returned for carried items because they contain the feedback-
    enriched XML that the incoming (phase-4-origin) items lack.
    """
    if not resume:
        return [], items

    # Primary path: load checkpoint to find already-enriched items
    if output_dir:
        ckpt = load_checkpoint(output_dir, 8, "feedback")
        if ckpt and ckpt.get("items"):
            ckpt_items = deserialize_items(ckpt["items"])
            passed_map = {
                it.item_id: it
                for it in ckpt_items
                if (
                    it.pipeline_meta
                    and it.pipeline_meta.validators.feedback
                    == "pass"
                    and not it.feedback_failed
                )
            }
            if passed_map:
                incoming_ids = {it.item_id for it in items}
                carried = [
                    passed_map[iid]
                    for iid in incoming_ids
                    if iid in passed_map
                ]
                carried_ids = {it.item_id for it in carried}
                to_process = [
                    it for it in items
                    if it.item_id not in carried_ids
                ]
                logger.info(
                    "Phase 8 resume: %d carried from "
                    "checkpoint, %d to process",
                    len(carried), len(to_process),
                )
                return carried, to_process

    # Fallback: check items themselves (backward compat /
    # no checkpoint on disk)
    carried = [
        it for it in items
        if (
            it.pipeline_meta
            and it.pipeline_meta.validators.feedback == "pass"
            and not it.feedback_failed
        )
    ]
    to_process = [it for it in items if it not in carried]
    if carried:
        logger.info(
            "Phase 8 resume: %d carried, %d to retry",
            len(carried), len(to_process),
        )
    return carried, to_process
