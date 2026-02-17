"""Shared helpers for the question generation pipeline.

Contains atom loading, metadata building, result saving, checkpoint
management, prerequisite validation, and console output formatting.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.atoms.models import Atom, CanonicalAtomsFile
from app.question_generation.models import (
    AtomEnrichment,
    GeneratedItem,
    PipelineMeta,
    PipelineResult,
    PlanSlot,
)
from app.utils.paths import ATOMS_DIR

logger = logging.getLogger(__name__)


# Phase group -> required checkpoints that MUST exist before running.
PHASE_PREREQUISITES: dict[str, list[tuple[int, str]]] = {
    "all": [],
    "enrich": [],
    "plan": [(1, "enrichment")],
    "generate": [(1, "enrichment"), (3, "plan")],
    "validate": [(4, "generation")],
    "feedback": [(6, "base_validation")],
    "final_validate": [(8, "feedback")],
}



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


def _scan_max_checkpoint_phase(ckpt_dir: Path) -> int | None:
    """Scan a checkpoint directory for the highest phase number.

    Args:
        ckpt_dir: Directory containing phase_*_*.json files.

    Returns:
        Highest phase number found, or None if no checkpoints.
    """
    if not ckpt_dir.exists():
        return None

    max_phase: int | None = None
    for path in ckpt_dir.glob("phase_*_*.json"):
        try:
            phase_num = int(path.stem.split("_")[1])
            if max_phase is None or phase_num > max_phase:
                max_phase = phase_num
        except (IndexError, ValueError):
            continue

    return max_phase


def get_last_completed_phase(atom_id: str) -> int | None:
    """Get the highest completed phase for an atom.

    Used by the API to enable/disable frontend phase buttons.

    Args:
        atom_id: Atom identifier.

    Returns:
        Highest completed phase number, or None.
    """
    from app.utils.paths import QUESTION_GENERATION_DIR

    ckpt_dir = QUESTION_GENERATION_DIR / atom_id / "checkpoints"
    return _scan_max_checkpoint_phase(ckpt_dir)



def get_enrichment_image_types(atom_id: str) -> list[str] | None:
    """Read required_image_types from the enrichment checkpoint."""
    from app.utils.paths import QUESTION_GENERATION_DIR

    ckpt = load_checkpoint(
        QUESTION_GENERATION_DIR / atom_id, 1, "enrichment",
    )
    if ckpt is None:
        return None

    enrichment_data = ckpt.get("enrichment_data")
    if not enrichment_data:
        return None

    return enrichment_data.get("required_image_types", [])


def classify_image_status(image_types: list[str] | None) -> str:
    """Classify image handling: not_enriched/no_images/images_supported/images_unsupported."""
    if image_types is None:
        return "not_enriched"
    if not image_types:
        return "no_images"

    from app.question_generation.image_types import can_generate_all

    if can_generate_all(image_types):
        return "images_supported"
    return "images_unsupported"


# Checkpoint phase → next phase group for --resume.
# Phase 4→"generate" so partial gen re-enters slot-level resume.
_CHECKPOINT_TO_NEXT_GROUP: dict[int, str] = {
    8: "final_validate",
    6: "feedback",
    4: "generate",
    3: "generate",
    1: "plan",
}


def find_resume_phase_group(output_dir: Path) -> str | None:
    """Find the phase group to resume from based on checkpoints."""
    ckpt_dir = output_dir / "checkpoints"
    max_phase = _scan_max_checkpoint_phase(ckpt_dir)
    if max_phase is None:
        return None

    return _CHECKPOINT_TO_NEXT_GROUP.get(max_phase)


def check_prerequisites(
    phase_group: str,
    output_dir: Path,
) -> tuple[bool, list[str]]:
    """Validate required checkpoints exist for a phase group."""
    reqs = PHASE_PREREQUISITES.get(phase_group, [])
    missing: list[str] = []

    for phase_num, phase_name in reqs:
        ckpt = load_checkpoint(output_dir, phase_num, phase_name)
        if ckpt is None:
            missing.append(
                f"Phase {phase_num} ({phase_name}) must "
                f"complete before '{phase_group}' can run"
            )

    return len(missing) == 0, missing


def load_phase_state(
    phase_group: str,
    output_dir: Path,
) -> dict:
    """Load prior phase state from checkpoints.

    Returns whatever state the requested phase group needs from
    earlier checkpoints (enrichment, plan slots, items, etc.).
    Prerequisites must have been validated first.

    Args:
        phase_group: The phase group being started.
        output_dir: Pipeline output directory with checkpoints.

    Returns:
        Dict with available loaded state. Keys:
        - "enrichment": AtomEnrichment | None
        - "plan_slots": list[PlanSlot] | None
        - "items": list[GeneratedItem] | None
    """
    state: dict = {}
    reqs = PHASE_PREREQUISITES.get(phase_group, [])

    for phase_num, phase_name in reqs:
        ckpt = load_checkpoint(output_dir, phase_num, phase_name)
        if ckpt is None:
            continue

        if phase_name == "enrichment":
            raw = ckpt.get("enrichment_data")
            if raw:
                state["enrichment"] = (
                    AtomEnrichment.model_validate(raw)
                )

        elif phase_name == "plan":
            raw_slots = ckpt.get("slots", [])
            state["plan_slots"] = [
                PlanSlot.model_validate(s) for s in raw_slots
            ]

        elif phase_name in (
            "generation", "base_validation", "feedback",
        ):
            raw_items = ckpt.get("items", [])
            state["items"] = deserialize_items(raw_items)

    return state



def serialize_items(items: list[GeneratedItem]) -> list[dict]:
    """Serialize GeneratedItem list for checkpoint storage.

    Args:
        items: Items to serialize.

    Returns:
        List of JSON-serializable dicts.
    """
    result = []
    for item in items:
        d: dict = {
            "item_id": item.item_id,
            "qti_xml": item.qti_xml,
            "slot_index": item.slot_index,
        }
        if item.pipeline_meta:
            d["pipeline_meta"] = item.pipeline_meta.model_dump()
        result.append(d)
    return result


def deserialize_items(data: list[dict]) -> list[GeneratedItem]:
    """Deserialize GeneratedItem list from checkpoint data.

    Args:
        data: Raw dicts from checkpoint JSON.

    Returns:
        List of reconstructed GeneratedItem objects.
    """
    items = []
    for d in data:
        meta = None
        if d.get("pipeline_meta"):
            meta = PipelineMeta.model_validate(
                d["pipeline_meta"],
            )
        items.append(GeneratedItem(
            item_id=d["item_id"],
            qti_xml=d["qti_xml"],
            slot_index=d.get("slot_index", 0),
            pipeline_meta=meta,
        ))
    return items



def load_existing_fingerprints(atom_id: str) -> set[str]:
    """Load fingerprints of existing DB questions for an atom.

    Queries the question_atoms + questions tables for all items
    already linked to this atom, computes SHA-256 fingerprints
    of their QTI XML, and returns the set.

    Args:
        atom_id: Atom identifier (e.g. "A-M1-ALG-01-02").

    Returns:
        Set of hex-encoded SHA-256 fingerprints. Empty set if
        the DB is unreachable or the atom has no questions.
    """
    from app.question_generation.validation_checks import (
        compute_fingerprint,
    )
    from app.sync.config import DBConfig
    from app.sync.db_client import DBClient

    try:
        config = DBConfig.for_environment("local")
        client = DBClient(config)
        with client.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT q.qti_xml
                    FROM questions q
                    JOIN question_atoms qa ON qa.question_id = q.id
                    WHERE qa.atom_id = %(atom_id)s
                      AND q.qti_xml IS NOT NULL
                    """,
                    {"atom_id": atom_id},
                )
                rows = cur.fetchall()

        fingerprints = {
            compute_fingerprint(row["qti_xml"]) for row in rows
        }
        if fingerprints:
            logger.info(
                "Loaded %d existing fingerprints for atom %s",
                len(fingerprints), atom_id,
            )
        return fingerprints

    except Exception as exc:
        logger.warning(
            "Could not load existing fingerprints for %s: %s",
            atom_id, exc,
        )
        return set()



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
