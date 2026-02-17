"""Extractor for pipeline-generated questions.

Reads Phase 9 (final_validation) checkpoints from disk and
transforms them into GeneratedQuestionRow objects for DB sync.

Follows the same pattern as extractors.py (standards, atoms,
official questions): extract from disk → transform → sync.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.sync.models import GeneratedQuestionRow
from app.utils.paths import QUESTION_GENERATION_DIR

logger = logging.getLogger(__name__)

# Checkpoint file written by Phase 9 of the pipeline
_CHECKPOINT_FILENAME = "phase_9_final_validation.json"


def extract_generated_questions(
    atom_ids: list[str] | None = None,
) -> list[GeneratedQuestionRow]:
    """Extract generated questions from pipeline checkpoints.

    Reads Phase 9 checkpoints from disk for each atom that has
    completed the pipeline. Returns GeneratedQuestionRow objects
    ready for DB upsert.

    Args:
        atom_ids: Specific atoms to extract. If None, scans all
            atom directories under question-generation/.

    Returns:
        List of GeneratedQuestionRow objects.
    """
    if atom_ids:
        dirs = [
            (aid, QUESTION_GENERATION_DIR / aid)
            for aid in atom_ids
        ]
    else:
        dirs = _discover_atom_dirs()

    rows: list[GeneratedQuestionRow] = []
    for atom_id, atom_dir in dirs:
        atom_rows = _extract_atom(atom_id, atom_dir)
        rows.extend(atom_rows)

    logger.info(
        "Extracted %d generated questions from %d atoms",
        len(rows), len(dirs),
    )
    return rows


def _discover_atom_dirs() -> list[tuple[str, Path]]:
    """Discover all atom directories with Phase 9 checkpoints.

    Returns:
        List of (atom_id, atom_dir) tuples.
    """
    if not QUESTION_GENERATION_DIR.exists():
        return []

    results: list[tuple[str, Path]] = []
    for atom_dir in sorted(QUESTION_GENERATION_DIR.iterdir()):
        if not atom_dir.is_dir():
            continue
        ckpt = atom_dir / "checkpoints" / _CHECKPOINT_FILENAME
        if ckpt.exists():
            results.append((atom_dir.name, atom_dir))

    return results


def _extract_atom(
    atom_id: str, atom_dir: Path,
) -> list[GeneratedQuestionRow]:
    """Extract generated questions for a single atom.

    Args:
        atom_id: Atom identifier.
        atom_dir: Path to the atom's pipeline output directory.

    Returns:
        List of GeneratedQuestionRow for this atom.
    """
    ckpt_path = atom_dir / "checkpoints" / _CHECKPOINT_FILENAME
    if not ckpt_path.exists():
        logger.debug(
            "No Phase 9 checkpoint for %s — skipping", atom_id,
        )
        return []

    try:
        with open(ckpt_path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning(
            "Failed to read checkpoint for %s: %s",
            atom_id, exc,
        )
        return []

    items = data.get("items", [])
    if not items:
        logger.debug(
            "Phase 9 checkpoint for %s has no items", atom_id,
        )
        return []

    rows: list[GeneratedQuestionRow] = []
    for item in items:
        row = _item_dict_to_row(item, atom_id)
        if row:
            rows.append(row)

    logger.info(
        "Extracted %d generated questions for atom %s",
        len(rows), atom_id,
    )
    return rows


def _item_dict_to_row(
    item: dict, atom_id: str,
) -> GeneratedQuestionRow | None:
    """Convert a serialized item dict to a GeneratedQuestionRow.

    Args:
        item: Dict from the checkpoint's items list.
        atom_id: Atom identifier.

    Returns:
        GeneratedQuestionRow or None if essential fields are missing.
    """
    item_id = item.get("item_id")
    qti_xml = item.get("qti_xml")
    if not item_id or not qti_xml:
        return None

    meta = item.get("pipeline_meta") or {}
    validators = meta.get("validators", {})
    diff_raw = meta.get("difficulty_level", "medium")
    diff_map = {"easy": "low", "medium": "medium", "hard": "high"}

    return GeneratedQuestionRow(
        id=item_id,
        atom_id=atom_id,
        qti_xml=qti_xml,
        difficulty_level=diff_map.get(diff_raw, "medium"),
        component_tag=meta.get("component_tag", ""),
        operation_skeleton_ast=meta.get(
            "operation_skeleton_ast", "",
        ),
        surface_context=meta.get("surface_context", "pure_math"),
        numbers_profile=meta.get(
            "numbers_profile", "small_integers",
        ),
        fingerprint=meta.get("fingerprint", ""),
        validators=json.dumps(validators),
        target_exemplar_id=meta.get("target_exemplar_id"),
        distance_level=meta.get("distance_level"),
    )
