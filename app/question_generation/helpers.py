"""Shared helpers for the question generation pipeline.

Contains atom loading, metadata building, result saving, and
console output formatting used by the pipeline orchestrator.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.atoms.models import Atom, CanonicalAtomsFile
from app.question_generation.models import (
    PipelineMeta,
    PipelineResult,
    PlanSlot,
)
from app.utils.paths import ATOMS_DIR

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Atom loading
# ---------------------------------------------------------------------------


def load_atom(atom_id: str) -> Atom | None:
    """Load an atom by ID from the canonical atoms files.

    Searches all *_atoms.json files in the atoms data directory.

    Args:
        atom_id: Atom identifier to find.

    Returns:
        Atom object if found, None otherwise.
    """
    if not ATOMS_DIR.exists():
        logger.error("Atoms directory not found: %s", ATOMS_DIR)
        return None

    for atoms_file in ATOMS_DIR.glob("*_atoms.json"):
        try:
            data = json.loads(atoms_file.read_text(encoding="utf-8"))
            canonical = CanonicalAtomsFile.model_validate(data)
            atom = canonical.get_atom_by_id(atom_id)
            if atom:
                return atom
        except Exception as exc:
            logger.warning("Error reading %s: %s", atoms_file, exc)

    logger.error("Atom %s not found in any atoms file", atom_id)
    return None


# ---------------------------------------------------------------------------
# Metadata building
# ---------------------------------------------------------------------------


def build_pipeline_meta(atom_id: str, slot: PlanSlot) -> PipelineMeta:
    """Build pipeline metadata from a plan slot.

    Args:
        atom_id: Atom identifier.
        slot: Plan slot specification.

    Returns:
        PipelineMeta populated with slot data.
    """
    return PipelineMeta(
        atom_id=atom_id,
        component_tag=slot.component_tag,
        difficulty_level=slot.difficulty_level,
        operation_skeleton_ast=slot.operation_skeleton_ast,
        surface_context=slot.surface_context,
        numbers_profile=slot.numbers_profile,
        target_exemplar_id=slot.target_exemplar_id,
        distance_level=slot.distance_level,
    )


# ---------------------------------------------------------------------------
# Result saving
# ---------------------------------------------------------------------------


def save_pipeline_results(
    output_dir: Path,
    result: PipelineResult,
) -> None:
    """Save pipeline results to disk for traceability.

    Writes a JSON report and individual QTI XML files for each
    final item.

    Args:
        output_dir: Directory to write files into.
        result: Pipeline result to save.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    report = _build_report_dict(result)
    report_path = output_dir / "pipeline_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Save final QTI XML items
    items_dir = output_dir / "items"
    items_dir.mkdir(exist_ok=True)
    for item in result.final_items:
        item_path = items_dir / f"{item.item_id}.xml"
        with open(item_path, "w", encoding="utf-8") as f:
            f.write(item.qti_xml)

    logger.info("Results saved to %s", output_dir)


def _build_report_dict(result: PipelineResult) -> dict:
    """Build a serializable report dict from PipelineResult."""
    return {
        "atom_id": result.atom_id,
        "success": result.success,
        "total_planned": result.total_planned,
        "total_generated": result.total_generated,
        "total_passed_dedupe": result.total_passed_dedupe,
        "total_passed_base_validation":
            result.total_passed_base_validation,
        "total_passed_feedback": result.total_passed_feedback,
        "total_final": result.total_final,
        "total_synced": result.total_synced,
        "phases": [
            {
                "name": p.phase_name,
                "success": p.success,
                "errors": p.errors,
                "warnings": p.warnings,
            }
            for p in result.phase_results
        ],
    }


# ---------------------------------------------------------------------------
# Checkpoint save / load (resume support)
# ---------------------------------------------------------------------------


def save_checkpoint(
    output_dir: Path,
    phase_num: int,
    phase_name: str,
    data: dict,
) -> None:
    """Save a phase checkpoint to disk.

    Args:
        output_dir: Pipeline output directory.
        phase_num: Phase number (0-10).
        phase_name: Human-readable phase name.
        data: Serializable data to checkpoint.
    """
    ckpt_dir = output_dir / "checkpoints"
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    path = ckpt_dir / f"phase_{phase_num}_{phase_name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    logger.info("Checkpoint saved: %s", path.name)


def load_checkpoint(
    output_dir: Path,
    phase_num: int,
    phase_name: str,
) -> dict | None:
    """Load a phase checkpoint from disk if it exists.

    Args:
        output_dir: Pipeline output directory.
        phase_num: Phase number (0-10).
        phase_name: Human-readable phase name.

    Returns:
        Checkpoint data dict, or None if not found.
    """
    path = output_dir / "checkpoints" / f"phase_{phase_num}_{phase_name}.json"
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        logger.info("Checkpoint loaded: %s", path.name)
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Invalid checkpoint %s: %s", path.name, exc)
        return None


# ---------------------------------------------------------------------------
# Console output
# ---------------------------------------------------------------------------


def print_pipeline_header(atom_id: str) -> None:
    """Print pipeline header to console."""
    print(f"\n{'=' * 60}")
    print("PIPELINE: Generación de Preguntas por Átomo")
    print(f"Átomo: {atom_id}")
    print(f"{'=' * 60}\n")


def print_pipeline_summary(result: PipelineResult) -> None:
    """Print pipeline summary to console."""
    print(f"\n{'=' * 60}")
    print("RESUMEN")
    print(f"{'=' * 60}")
    print(f"Átomo: {result.atom_id}")
    print(f"Planificados:       {result.total_planned}")
    print(f"Generados:          {result.total_generated}")
    print(f"Pasaron dedupe:     {result.total_passed_dedupe}")
    print(f"Pasaron validación: {result.total_passed_base_validation}")
    print(f"Pasaron feedback:   {result.total_passed_feedback}")
    print(f"Finales:            {result.total_final}")
    print(f"Sincronizados:      {result.total_synced}")

    # Print phase errors/warnings
    for phase in result.phase_results:
        if phase.errors:
            print(f"\n  Errores [{phase.phase_name}]:")
            for err in phase.errors:
                print(f"    - {err}")
        if phase.warnings:
            print(f"\n  Advertencias [{phase.phase_name}]:")
            for w in phase.warnings:
                print(f"    - {w}")

    print(f"{'=' * 60}\n")
