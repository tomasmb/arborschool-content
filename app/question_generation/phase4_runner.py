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

    Returns:
        List of generated items, or None on total failure.
    """
    # Slot-level resume: load partial checkpoint if available
    if resume and base_items is None:
        ckpt = load_checkpoint(output_dir, 4, "generation")
        if ckpt and ckpt.get("items"):
            base_items = deserialize_items(ckpt["items"])
            logger.info(
                "Phase 4: loaded %d items from partial "
                "checkpoint", len(base_items),
            )

    existing_items = base_items or []
    done_indices = {it.slot_index for it in existing_items}
    remaining = [
        s for s in (plan_slots or [])
        if s.slot_index not in done_indices
    ]

    if remaining:
        total_planned = len(plan_slots or [])
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
        items = existing_items + (new_items or [])
    else:
        items = existing_items
        logger.info(
            "Phase 4: all %d slots already generated",
            len(items),
        )

    # Phase 4b — Images
    if any(s.image_required for s in (plan_slots or [])):
        items = _run_image_gen(
            items, plan_slots or [], ctx, result, image_generator,
        )
        if items is None:
            return None

    result.total_generated = len(items)
    save_checkpoint(output_dir, 4, "generation", {
        "item_count": len(items),
        "items": serialize_items(items),
    })
    return items


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


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
) -> list[GeneratedItem] | None:
    """Phase 4b: Generate and embed images via Gemini + S3."""
    logger.info("Phase 4b: Image generation for %s", ctx.atom_id)
    slot_map = {s.slot_index: s for s in slots}
    phase = image_generator.generate_images(
        items, slot_map, ctx.atom_id,
    )
    result.phase_results.append(phase)
    if not phase.success:
        return None
    enriched: list[GeneratedItem] = phase.data["items"]
    return enriched if enriched else None
