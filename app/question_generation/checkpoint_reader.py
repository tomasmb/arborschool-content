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
        feedback_items, final_items. Each section is None if the
        corresponding checkpoint file doesn't exist.
    """
    available_phases = _scan_available_phases(output_dir)
    pipeline_report = _read_pipeline_report(output_dir)

    enrichment = _read_enrichment(output_dir)
    plan_slots = _read_plan_slots(output_dir)
    generated_items = _read_items(output_dir, 4, "generation")
    validation_results = _read_items(output_dir, 6, "base_validation")
    feedback_items = _read_items(output_dir, 8, "feedback")
    final_items = _read_items(output_dir, 9, "final_validation")

    return {
        "atom_id": atom_id,
        "available_phases": available_phases,
        "pipeline_report": pipeline_report,
        "enrichment": enrichment,
        "plan_slots": plan_slots,
        "generated_items": generated_items,
        "validation_results": validation_results,
        "feedback_items": feedback_items,
        "final_items": final_items,
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
    """Read pipeline_report.json and reconcile with checkpoints.

    The report can become stale when partial/resume runs overwrite
    it without counts from earlier phases. We cross-check each
    count against the actual checkpoint item lists and use the
    higher value.
    """
    report_path = output_dir / "pipeline_report.json"
    if not report_path.exists():
        return None
    try:
        report = json.loads(
            report_path.read_text(encoding="utf-8"),
        )
    except (json.JSONDecodeError, OSError):
        return None

    return _reconcile_report_with_checkpoints(output_dir, report)


def _reconcile_report_with_checkpoints(
    output_dir: Path,
    report: dict,
) -> dict:
    """Ensure report counts match actual checkpoint item counts.

    For each phase that has a checkpoint file, compare the report
    count with the checkpoint item list length and keep the higher.
    Phase 4 is special: only non-image-failed items count as
    "generated" (matching pipeline.py's active-item logic).
    """
    # Phase 4: count only active (non-image-failed) items
    p4 = load_checkpoint(output_dir, 4, "generation")
    if p4 is not None:
        active = sum(
            1 for it in p4.get("items", [])
            if not it.get("image_failed")
        )
        if active > report.get("total_generated", 0):
            report["total_generated"] = active

    # Phase 8: count only non-feedback-failed items
    # (checkpoint stores both passed and failed items)
    p8 = load_checkpoint(output_dir, 8, "feedback")
    if p8 is not None:
        passed_fb = sum(
            1 for it in p8.get("items", [])
            if not it.get("feedback_failed")
        )
        if passed_fb > report.get("total_passed_feedback", 0):
            report["total_passed_feedback"] = passed_fb

    # Phases 6/9: all checkpoint items are "passed" items
    pass_only_phases: list[tuple[int, str, str]] = [
        (6, "base_validation", "total_passed_base_validation"),
        (9, "final_validation", "total_final"),
    ]
    for phase_num, phase_name, report_key in pass_only_phases:
        ckpt = load_checkpoint(output_dir, phase_num, phase_name)
        if ckpt is None:
            continue
        ckpt_count = len(ckpt.get("items", []))
        if ckpt_count > report.get(report_key, 0):
            report[report_key] = ckpt_count

    # Dedupe has no separate checkpoint; ensure it is at least
    # as large as validated so the funnel stays monotonic.
    validated = report.get("total_passed_base_validation", 0)
    deduped = report.get("total_passed_dedupe", 0)
    if validated > deduped:
        report["total_passed_dedupe"] = validated

    return report


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

    Prefers the phase 6 (validated) version of the item; falls
    back to phase 4 (generated) for items that failed validation.
    Blocks revalidation of image_failed items.

    Raises:
        ValueError: If item not found or is image_failed.
    """
    from app.llm_clients import load_default_openai_client
    from app.question_generation.helpers import deserialize_items
    from app.question_generation.validators import BaseValidator

    target, all_gen_items = _find_revalidation_target(
        output_dir, item_id,
    )

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

    _persist_revalidation(
        output_dir, all_gen_items, target, passed, errors,
    )

    return {
        "item_id": item_id,
        "passed": passed,
        "errors": errors,
        "validators": validators,
    }


def _find_revalidation_target(
    output_dir: Path,
    item_id: str,
) -> tuple:
    """Find an item for single-item revalidation.

    Checks phase 6 first (already validated), then phase 4 (generated).
    Blocks image_failed items since they can't pass validation.

    Returns:
        (target_item, all_gen_items) tuple.
    """
    from app.question_generation.helpers import deserialize_items

    # Prefer the phase 6 version (has post-validation statuses)
    val_ckpt = load_checkpoint(output_dir, 6, "base_validation")
    if val_ckpt and val_ckpt.get("items"):
        val_items = deserialize_items(val_ckpt["items"])
        target = next(
            (i for i in val_items if i.item_id == item_id),
            None,
        )
        if target:
            gen_ckpt = load_checkpoint(
                output_dir, 4, "generation",
            )
            gen_items = deserialize_items(
                gen_ckpt["items"],
            ) if gen_ckpt else []
            return target, gen_items

    # Fall back to phase 4 (failed validation, not deduped)
    gen_ckpt = load_checkpoint(output_dir, 4, "generation")
    if not gen_ckpt or not gen_ckpt.get("items"):
        raise ValueError("No generated items checkpoint found")

    gen_items = deserialize_items(gen_ckpt["items"])
    target = next(
        (i for i in gen_items if i.item_id == item_id),
        None,
    )
    if not target:
        raise ValueError(
            f"Item '{item_id}' not found in checkpoints",
        )
    if target.image_failed:
        raise ValueError(
            f"Item '{item_id}' has image_failed — cannot "
            f"revalidate until images are regenerated",
        )
    return target, gen_items


def _persist_revalidation(
    output_dir: Path,
    gen_items: list,
    revalidated_item: object,
    passed: bool,
    new_errors: list[str],
) -> None:
    """Update phase 4, phase 6 checkpoints and report after reval."""
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

    valid_count = len(val_items)
    save_checkpoint(output_dir, 6, "base_validation", {
        "valid_count": valid_count,
        "items": serialize_items(val_items),
    })

    # 3. Update pipeline report so the UI stays in sync
    _update_pipeline_report(
        output_dir, revalidated_item.item_id,
        new_errors, valid_count,
    )


def _update_pipeline_report(
    output_dir: Path,
    item_id: str,
    new_errors: list[str],
    valid_count: int,
) -> None:
    """Update report errors and validation count after reval."""
    report_path = output_dir / "pipeline_report.json"
    if not report_path.exists():
        return

    try:
        report = json.loads(
            report_path.read_text(encoding="utf-8"),
        )
    except (json.JSONDecodeError, OSError):
        return

    prefix = f"{item_id}:"
    for phase in report.get("phases", []):
        if phase.get("name") != "base_validation":
            continue
        # Remove old errors for this item
        phase["errors"] = [
            e for e in phase.get("errors", [])
            if not e.startswith(prefix)
        ]
        # Add new errors (already prefixed with item_id)
        phase["errors"].extend(new_errors)
        break

    report["total_passed_base_validation"] = valid_count

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


def revalidate_single_item_final(
    output_dir: Path,
    item_id: str,
) -> dict[str, Any]:
    """Re-run final validation on one feedback-enriched item."""
    from app.llm_clients import load_default_openai_client
    from app.question_generation.helpers import deserialize_items
    from app.question_generation.validators import FinalValidator

    ckpt = load_checkpoint(output_dir, 8, "feedback")
    if not ckpt or not ckpt.get("items"):
        raise ValueError("No feedback checkpoint found")

    all_items = deserialize_items(ckpt["items"])
    target = next(
        (i for i in all_items if i.item_id == item_id), None,
    )
    if not target:
        raise ValueError(
            f"Item '{item_id}' not found in feedback checkpoint",
        )

    client = load_default_openai_client()
    validator = FinalValidator(client)

    # Stage 1: deterministic checks
    det_errors = validator._validate_deterministic(
        target, exemplars=None,
    )

    # Stage 2: LLM validation (only if deterministic passed)
    llm_error: str | None = None
    if not det_errors:
        llm_error = validator._llm_validate_item(target)

    errors = det_errors if det_errors else []
    if llm_error:
        errors.append(llm_error)

    passed = len(errors) == 0
    validators: dict[str, str] = {}
    if target.pipeline_meta:
        validators = target.pipeline_meta.validators.model_dump()

    _persist_final_revalidation(
        output_dir, target, passed, errors,
    )

    return {
        "item_id": item_id,
        "passed": passed,
        "errors": errors,
        "validators": validators,
    }


def _persist_final_revalidation(
    output_dir: Path,
    revalidated_item: object,
    passed: bool,
    new_errors: list[str],
) -> None:
    """Update phase 9 checkpoint and report after final reval."""
    from app.question_generation.helpers import (
        deserialize_items,
        save_checkpoint,
        serialize_items,
    )

    # Update phase 9 checkpoint
    final_ckpt = load_checkpoint(output_dir, 9, "final_validation")
    if final_ckpt is None:
        final_ckpt = {"final_count": 0, "items": []}

    final_items = deserialize_items(final_ckpt.get("items", []))
    # Remove existing entry for this item
    final_items = [
        i for i in final_items
        if i.item_id != revalidated_item.item_id
    ]
    if passed:
        final_items.append(revalidated_item)

    final_count = len(final_items)
    save_checkpoint(output_dir, 9, "final_validation", {
        "final_count": final_count,
        "items": serialize_items(final_items),
    })

    # Update pipeline report
    _update_pipeline_report_final(
        output_dir, revalidated_item.item_id,
        new_errors, final_count,
    )


def _update_pipeline_report_final(
    output_dir: Path,
    item_id: str,
    new_errors: list[str],
    final_count: int,
) -> None:
    """Update report errors and final count after final reval."""
    report_path = output_dir / "pipeline_report.json"
    if not report_path.exists():
        return

    try:
        report = json.loads(
            report_path.read_text(encoding="utf-8"),
        )
    except (json.JSONDecodeError, OSError):
        return

    prefix = f"{item_id}:"
    for phase in report.get("phases", []):
        if phase.get("name") != "final_validation":
            continue
        phase["errors"] = [
            e for e in phase.get("errors", [])
            if not e.startswith(prefix)
        ]
        phase["errors"].extend(new_errors)
        break

    report["total_final"] = final_count

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


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
