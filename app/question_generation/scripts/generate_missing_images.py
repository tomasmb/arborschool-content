"""generate_missing_images.py — Generate images for existing items.

Processes items that already have IMAGE_PLACEHOLDER in their QTI XML
and a populated image_description field. Loads from the Phase 9
checkpoint (final enriched QTI with feedback) and saves back after
replacing placeholders with real S3 URLs.

Uses Gemini for image generation and GPT-5.1 vision for validation.
See the AI Cost Guard rule — run --dry-run first to see the estimate.

Usage:
    # Dry run — show what would be generated (no API calls)
    uv run python -m app.question_generation.scripts.generate_missing_images \
        --dry-run

    # Generate images for all atoms (up to N items total)
    uv run python -m app.question_generation.scripts.generate_missing_images \
        --limit 10

    # Generate images for specific atoms
    uv run python -m app.question_generation.scripts.generate_missing_images \
        --atoms A-M1-GEO-01-01 A-M1-PROB-01-04
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import threading

from app.question_generation.helpers import (
    deserialize_items,
    save_checkpoint,
    serialize_items,
)
from app.question_generation.image_generator import ImageGenerator
from app.question_generation.models import GeneratedItem
from app.utils.paths import QUESTION_GENERATION_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _needs_image(item: GeneratedItem) -> bool:
    """Check if an item needs image generation."""
    return (
        "IMAGE_PLACEHOLDER" in item.qti_xml
        and bool(item.image_description)
    )


def _count_needing_images(
    items: list[GeneratedItem],
) -> int:
    """Count items that need image generation."""
    return sum(1 for it in items if _needs_image(it))


def _load_placeholder_items(
    atom_ids: list[str] | None = None,
) -> dict[str, list[GeneratedItem]]:
    """Load items with IMAGE_PLACEHOLDER from Phase 9 checkpoints.

    Returns:
        Dict mapping atom_id -> ALL items for atoms that have
        at least one item needing an image.
    """
    result: dict[str, list[GeneratedItem]] = {}
    for atom_dir in sorted(QUESTION_GENERATION_DIR.iterdir()):
        if not atom_dir.is_dir() or atom_dir.name.startswith("."):
            continue
        if atom_ids and atom_dir.name not in atom_ids:
            continue
        p9 = atom_dir / "checkpoints" / "phase_9_final_validation.json"
        if not p9.exists():
            continue

        data = json.loads(p9.read_text(encoding="utf-8"))
        raw_items = data.get("items", [])
        if not raw_items:
            continue

        items = deserialize_items(raw_items)
        if any(_needs_image(it) for it in items):
            result[atom_dir.name] = items
    return result


def _apply_limit(
    items_by_atom: dict[str, list[GeneratedItem]],
    limit: int | None,
) -> int:
    """Count total placeholder items, optionally truncate to limit.

    When limit is set, prunes atoms to stay within the budget.
    Returns total placeholder items that will be processed.
    """
    total = 0
    for atom_id in list(items_by_atom):
        count = _count_needing_images(items_by_atom[atom_id])
        if limit is not None and total + count > limit:
            if limit - total <= 0:
                del items_by_atom[atom_id]
                continue
        total += count
    return total


def _run_dry(
    items_by_atom: dict[str, list[GeneratedItem]],
) -> None:
    """Print summary without making any API calls."""
    total = 0
    print("\n=== DRY RUN — Image Generation Preview ===\n")
    for atom_id, items in sorted(items_by_atom.items()):
        count = _count_needing_images(items)
        if count:
            print(f"  {atom_id}: {count} items need images")
            total += count
    print(f"\n  Total: {total} images to generate")
    print("  Per image: 1 Gemini call + 1 GPT-5.1 vision call")
    print(f"  Max retries: 3 attempts per image")
    print(f"  Worst-case API calls: {total * 3 * 2}")
    print("\n  Run without --dry-run to proceed.\n")


def _run_generation(
    items_by_atom: dict[str, list[GeneratedItem]],
) -> None:
    """Generate images and save updated checkpoints."""
    from app.llm_clients import OpenAIClient

    image_gen = ImageGenerator(OpenAIClient())
    total_ok = 0
    total_fail = 0

    for atom_id, all_items in sorted(items_by_atom.items()):
        logger.info(
            "Processing %s: %d items need images",
            atom_id, _count_needing_images(all_items),
        )

        ckpt_lock = threading.Lock()

        def _on_image_done(_item: GeneratedItem) -> None:
            with ckpt_lock:
                save_checkpoint(
                    QUESTION_GENERATION_DIR / atom_id,
                    9, "final_validation",
                    {
                        "final_count": len(all_items),
                        "items": serialize_items(all_items),
                    },
                )

        phase = image_gen.generate_for_placeholders(
            all_items, atom_id,
            on_image_complete=_on_image_done,
        )

        ok = sum(
            1 for it in all_items
            if "IMAGE_PLACEHOLDER" not in it.qti_xml
        )
        failed = sum(1 for it in all_items if it.image_failed)
        total_ok += ok
        total_fail += failed

        save_checkpoint(
            QUESTION_GENERATION_DIR / atom_id,
            9, "final_validation",
            {
                "final_count": len(all_items),
                "items": serialize_items(all_items),
            },
        )
        logger.info(
            "%s: %d images OK, %d failed, %d errors",
            atom_id, ok, failed, len(phase.errors),
        )

    logger.info(
        "DONE: %d images generated, %d failed across %d atoms",
        total_ok, total_fail, len(items_by_atom),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate images for items with IMAGE_PLACEHOLDER",
    )
    parser.add_argument(
        "--atoms", nargs="+", default=None,
        help="Only process these atom IDs",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Max number of images to generate",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be generated without API calls",
    )
    args = parser.parse_args()

    items_by_atom = _load_placeholder_items(args.atoms)
    if not items_by_atom:
        print("No items with IMAGE_PLACEHOLDER found.")
        sys.exit(0)

    total = _apply_limit(items_by_atom, args.limit)
    logger.info(
        "Found %d placeholder items across %d atoms",
        total, len(items_by_atom),
    )

    if args.dry_run:
        _run_dry(items_by_atom)
        return

    _run_generation(items_by_atom)


if __name__ == "__main__":
    main()
