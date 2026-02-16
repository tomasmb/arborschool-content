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
