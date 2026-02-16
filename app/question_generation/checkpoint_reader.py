"""Read-only checkpoint reader for the question generation pipeline.

Aggregates checkpoint data from disk into a single dict
suitable for the frontend inspector API.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.question_generation.helpers import load_checkpoint


def read_atom_checkpoints(
    output_dir: Path,
    atom_id: str,
) -> dict[str, Any]:
    """Build a checkpoint response dict from files on disk.

    Reads all available phase checkpoints and the pipeline report
    for a given atom, returning structured data for the frontend.

    Args:
        output_dir: Root directory for this atom's pipeline output.
        atom_id: Atom identifier (for the response payload).

    Returns:
        Dict with keys: atom_id, available_phases, pipeline_report,
        enrichment, plan_slots, generated_items, validation_results,
        feedback_items. Each section is None if the corresponding
        checkpoint file doesn't exist.
    """
    available_phases = _scan_available_phases(output_dir)
    pipeline_report = _read_pipeline_report(output_dir)

    enrichment = _read_enrichment(output_dir)
    plan_slots = _read_plan_slots(output_dir)
    generated_items = _read_items(output_dir, 4, "generation")
    validation_results = _read_items(output_dir, 6, "base_validation")
    feedback_items = _read_items(output_dir, 8, "feedback")

    return {
        "atom_id": atom_id,
        "available_phases": available_phases,
        "pipeline_report": pipeline_report,
        "enrichment": enrichment,
        "plan_slots": plan_slots,
        "generated_items": generated_items,
        "validation_results": validation_results,
        "feedback_items": feedback_items,
    }


def _scan_available_phases(output_dir: Path) -> list[int]:
    """Return sorted list of phase numbers with checkpoint files."""
    ckpt_dir = output_dir / "checkpoints"
    if not ckpt_dir.exists():
        return []

    phases: list[int] = []
    for p in sorted(ckpt_dir.glob("phase_*_*.json")):
        try:
            phase_num = int(p.stem.split("_")[1])
            phases.append(phase_num)
        except (IndexError, ValueError):
            continue
    return phases


def _read_pipeline_report(output_dir: Path) -> dict | None:
    """Read pipeline_report.json if it exists."""
    report_path = output_dir / "pipeline_report.json"
    if not report_path.exists():
        return None
    try:
        return json.loads(
            report_path.read_text(encoding="utf-8"),
        )
    except (json.JSONDecodeError, OSError):
        return None


def _read_enrichment(output_dir: Path) -> dict | None:
    """Read enrichment data from phase 1 checkpoint."""
    ckpt = load_checkpoint(output_dir, 1, "enrichment")
    if ckpt and ckpt.get("enrichment_data"):
        return ckpt["enrichment_data"]
    return None


def _read_plan_slots(output_dir: Path) -> list[dict] | None:
    """Read plan slots from phase 3 checkpoint."""
    ckpt = load_checkpoint(output_dir, 3, "plan")
    if ckpt and ckpt.get("slots"):
        return ckpt["slots"]
    return None


def revalidate_single_item(
    output_dir: Path,
    item_id: str,
) -> dict[str, Any]:
    """Re-run base validation on one generated item.

    Loads the item from the generation checkpoint, resets its validator
    statuses, runs all base checks (XSD, PAES, solvability-LLM,
    exemplar distance), and persists the result to checkpoint files.

    Args:
        output_dir: Root directory for this atom's pipeline output.
        item_id: ID of the item to revalidate.

    Returns:
        Dict with keys: item_id, passed, errors, validators.

    Raises:
        ValueError: If no generation checkpoint or item not found.
    """
    from app.llm_clients import load_default_openai_client
    from app.question_generation.helpers import deserialize_items
    from app.question_generation.validators import BaseValidator

    ckpt = load_checkpoint(output_dir, 4, "generation")
    if not ckpt or not ckpt.get("items"):
        raise ValueError("No generated items checkpoint found")

    all_items = deserialize_items(ckpt["items"])
    target = next(
        (i for i in all_items if i.item_id == item_id), None,
    )
    if not target:
        raise ValueError(
            f"Item '{item_id}' not found in generation checkpoint",
        )

    # Reset validator statuses so they get freshly populated
    if target.pipeline_meta:
        v = target.pipeline_meta.validators
        v.xsd = "pending"
        v.paes = "pending"
        v.solve_check = "pending"
        v.scope = "pending"
        v.exemplar_copy_check = "pending"

    client = load_default_openai_client()
    validator = BaseValidator(client)
    errors = validator._validate_single(target, exemplars=None)

    passed = len(errors) == 0
    validators: dict[str, str] = {}
    if target.pipeline_meta:
        validators = target.pipeline_meta.validators.model_dump()

    # Persist updated validators to checkpoint files
    _persist_revalidation(output_dir, all_items, target, passed)

    return {
        "item_id": item_id,
        "passed": passed,
        "errors": errors,
        "validators": validators,
    }


def _persist_revalidation(
    output_dir: Path,
    gen_items: list,
    revalidated_item: object,
    passed: bool,
) -> None:
    """Persist single-item revalidation result to checkpoints.

    Updates the generation checkpoint (phase 4) with new validator
    statuses and adds/removes the item from the validation
    checkpoint (phase 6) based on the result.
    """
    from app.question_generation.helpers import (
        deserialize_items,
        save_checkpoint,
        serialize_items,
    )

    # 1. Update generation checkpoint with refreshed validators
    save_checkpoint(output_dir, 4, "generation", {
        "item_count": len(gen_items),
        "items": serialize_items(gen_items),
    })

    # 2. Update validation checkpoint (phase 6)
    val_ckpt = load_checkpoint(output_dir, 6, "base_validation")
    if val_ckpt is None:
        val_ckpt = {"valid_count": 0, "items": []}

    val_items = deserialize_items(val_ckpt.get("items", []))
    # Remove existing entry for this item
    val_items = [
        i for i in val_items
        if i.item_id != revalidated_item.item_id
    ]
    if passed:
        val_items.append(revalidated_item)

    save_checkpoint(output_dir, 6, "base_validation", {
        "valid_count": len(val_items),
        "items": serialize_items(val_items),
    })


def _read_items(
    output_dir: Path,
    phase_num: int,
    phase_name: str,
) -> list[dict] | None:
    """Read items array from a phase checkpoint."""
    ckpt = load_checkpoint(output_dir, phase_num, phase_name)
    if ckpt and ckpt.get("items"):
        return ckpt["items"]
    return None
