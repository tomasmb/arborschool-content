"""Phase 4 orchestration — resume-aware generation + image gen.

Extracted from ``pipeline.py`` to keep the main orchestrator under
500 lines.  Contains:

- ``run_phase_4``: top-level Phase 4 + 4b entry point with
  slot-level resume, incremental checkpoints, and image generation.
- ``_generate_with_checkpoints``: wraps the generator with a
  callback that saves progress after each successful item.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from app.question_generation.generator import BaseQtiGenerator
from app.question_generation.helpers import (
    build_pipeline_meta,
    deserialize_items,
    load_checkpoint,
    save_checkpoint,
    serialize_items,
)
from app.question_generation.image_generator import ImageGenerator
from app.question_generation.models import (
    AtomContext,
    AtomEnrichment,
    GeneratedItem,
    PipelineResult,
    PlanSlot,
)

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


def run_phase_4(
    *,
    plan_slots: list[PlanSlot] | None,
    ctx: AtomContext,
    enrichment: AtomEnrichment | None,
    result: PipelineResult,
    generator: BaseQtiGenerator,
    image_generator: ImageGenerator,
    output_dir: Path,
    resume: bool,
    base_items: list[GeneratedItem] | None,
    skip_images: bool = False,
) -> list[GeneratedItem] | None:
    """Run Phase 4 + 4b with slot-level resume and incremental saves.

    Args:
        plan_slots: All planned slots from Phase 3.
        ctx: Atom context.
        enrichment: Optional enrichment from Phase 1.
        result: Pipeline result accumulator.
        generator: QTI generator instance.
        image_generator: Image generator instance.
        output_dir: Pipeline output directory.
        resume: Whether to attempt loading a partial checkpoint.
        base_items: Items already loaded from a prior checkpoint
            (e.g. via prerequisite loading in ``run()``).
        skip_images: When True, skip Phase 4b image generation.

    Returns:
        List of generated items, or None on total failure.
    """
    existing_items = _load_resume_items(
        output_dir=output_dir,
        resume=resume,
        base_items=base_items,
    )
    items = _generate_missing_items(
        plan_slots=plan_slots or [],
        existing_items=existing_items,
        ctx=ctx,
        enrichment=enrichment,
        result=result,
        generator=generator,
        output_dir=output_dir,
    )
    if items is None:
        return None

    with_images = _maybe_run_image_phase(
        items=items,
        plan_slots=plan_slots or [],
        ctx=ctx,
        result=result,
        image_generator=image_generator,
        skip_images=skip_images,
        output_dir=output_dir,
    )
    if with_images is None:
        return None
    return _save_and_filter_active(with_images, output_dir, result)


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _load_resume_items(
    *,
    output_dir: Path,
    resume: bool,
    base_items: list[GeneratedItem] | None,
) -> list[GeneratedItem]:
    """Load phase 4 checkpoint items when resuming."""
    if not (resume and base_items is None):
        return base_items or []

    ckpt = load_checkpoint(output_dir, 4, "generation")
    if ckpt and ckpt.get("items"):
        loaded = deserialize_items(ckpt["items"])
        logger.info(
            "Phase 4: loaded %d items from partial checkpoint",
            len(loaded),
        )
        return loaded
    return []


def _generate_missing_items(
    *,
    plan_slots: list[PlanSlot],
    existing_items: list[GeneratedItem],
    ctx: AtomContext,
    enrichment: AtomEnrichment | None,
    result: PipelineResult,
    generator: BaseQtiGenerator,
    output_dir: Path,
) -> list[GeneratedItem] | None:
    """Generate only slots that are not already checkpointed."""
    done_indices = {it.slot_index for it in existing_items}
    remaining = [
        s for s in plan_slots if s.slot_index not in done_indices
    ]
    if not remaining:
        logger.info(
            "Phase 4: all %d slots already generated",
            len(existing_items),
        )
        return existing_items

    total_planned = len(plan_slots)
    new_items = _generate_with_checkpoints(
        slots=remaining,
        ctx=ctx,
        enrichment=enrichment,
        result=result,
        generator=generator,
        existing_items=existing_items,
        output_dir=output_dir,
        progress_offset=len(existing_items),
        total_override=total_planned,
    )
    if new_items is None and not existing_items:
        return None
    return existing_items + (new_items or [])


def _maybe_run_image_phase(
    *,
    items: list[GeneratedItem],
    plan_slots: list[PlanSlot],
    ctx: AtomContext,
    result: PipelineResult,
    image_generator: ImageGenerator,
    skip_images: bool,
    output_dir: Path,
) -> list[GeneratedItem] | None:
    """Run phase 4b only when image generation is needed."""
    needs_images = any(slot.image_required for slot in plan_slots)
    if skip_images or not needs_images:
        return items
    return _run_image_gen(
        items, plan_slots, ctx, result, image_generator, output_dir,
    )


def _save_and_filter_active(
    items: list[GeneratedItem],
    output_dir: Path,
    result: PipelineResult,
) -> list[GeneratedItem] | None:
    """Persist all items and return only image-complete ones.

    Items that still contain IMAGE_PLACEHOLDER are marked as
    image_failed so they can be retried on resume.
    """
    for it in items:
        if "IMAGE_PLACEHOLDER" in it.qti_xml and not it.image_failed:
            it.image_failed = True
            logger.warning(
                "%s: placeholder still present — marking failed",
                it.item_id,
            )
    save_checkpoint(output_dir, 4, "generation", {
        "item_count": len(items),
        "items": serialize_items(items),
    })
    active = [it for it in items if not it.image_failed]
    result.total_generated = len(active)
    return active if active else None


def _generate_with_checkpoints(
    *,
    slots: list[PlanSlot],
    ctx: AtomContext,
    enrichment: AtomEnrichment | None,
    result: PipelineResult,
    generator: BaseQtiGenerator,
    existing_items: list[GeneratedItem],
    output_dir: Path,
    progress_offset: int,
    total_override: int,
) -> list[GeneratedItem] | None:
    """Generate QTI items with an incremental checkpoint callback.

    Each successful item triggers a checkpoint write so progress
    survives process interruptions.
    """
    slot_map = {s.slot_index: s for s in slots}
    ckpt_items: list[GeneratedItem] = list(existing_items)

    def _on_item(item: GeneratedItem) -> None:
        slot = slot_map.get(item.slot_index)
        if slot:
            item.pipeline_meta = build_pipeline_meta(
                ctx.atom_id, slot,
            )
        ckpt_items.append(item)
        save_checkpoint(output_dir, 4, "generation", {
            "item_count": len(ckpt_items),
            "items": serialize_items(ckpt_items),
        })

    phase = generator.generate(
        slots, ctx, enrichment,
        progress_offset=progress_offset,
        total_override=total_override,
        on_item_complete=_on_item,
    )
    result.phase_results.append(phase)

    if not phase.success:
        return None
    return phase.data


def _run_image_gen(
    items: list[GeneratedItem],
    slots: list[PlanSlot],
    ctx: AtomContext,
    result: PipelineResult,
    image_generator: ImageGenerator,
    output_dir: Path,
) -> list[GeneratedItem] | None:
    """Phase 4b: Generate, validate, and embed images.

    Returns ALL items (including image_failed ones) so the caller
    can save them in the checkpoint. The caller filters out failed
    items before passing them downstream.

    Saves an incremental checkpoint after each image completes so
    progress survives crashes mid-4b.
    """
    logger.info("Phase 4b: Image generation for %s", ctx.atom_id)
    slot_map = {s.slot_index: s for s in slots}

    ckpt_lock = threading.Lock()

    def _on_image_done(_item: GeneratedItem) -> None:
        """Save checkpoint after each image (thread-safe)."""
        with ckpt_lock:
            save_checkpoint(output_dir, 4, "generation", {
                "item_count": len(items),
                "items": serialize_items(items),
            })

    phase = image_generator.generate_images(
        items, slot_map, ctx.atom_id,
        on_image_complete=_on_image_done,
    )
    result.phase_results.append(phase)

    all_items: list[GeneratedItem] = phase.data.get("items", [])
    failed = sum(1 for it in all_items if it.image_failed)
    if failed:
        logger.warning(
            "Phase 4b: %d/%d items failed image generation",
            failed, len(all_items),
        )

    if not phase.success:
        return None
    return all_items if all_items else None
