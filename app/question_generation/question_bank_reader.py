"""Read questions across all atoms for the question bank API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.question_generation.helpers import load_checkpoint

_LATEST_PHASES: list[tuple[int, str]] = [
    (9, "final_validation"),
    (8, "feedback"),
    (6, "base_validation"),
    (4, "generation"),
]


def _compute_item_status(
    item: dict,
    phase_num: int,
) -> str:
    """Derive a simple status string from phase + validators."""
    if phase_num == 9:
        return "pass"
    if phase_num in (6, 8):
        return "pass"
    meta = item.get("pipeline_meta")
    if not meta:
        return "pending"
    vals = meta.get("validators", {})
    if any(v == "fail" for v in vals.values()):
        return "fail"
    if all(v == "pending" for v in vals.values()):
        return "pending"
    return "pass"


def read_all_questions(
    qg_root: Path,
    atom_eje_map: dict[str, str],
    atom_titulo_map: dict[str, str],
    *,
    eje: str | None = None,
    difficulty: str | None = None,
    status: str | None = None,
    search: str | None = None,
    has_images: bool | None = None,
    offset: int = 0,
    limit: int = 50,
) -> dict[str, Any]:
    """Read questions across all atoms with filtering and pagination.

    Returns dict with keys: items, total, filters (available values).
    """
    all_items: list[dict[str, Any]] = []
    eje_set: set[str] = set()
    diff_set: set[str] = set()
    status_counts = {"pass": 0, "fail": 0, "pending": 0}

    for atom_dir in sorted(qg_root.iterdir()):
        if not atom_dir.is_dir() or atom_dir.name.startswith("."):
            continue
        atom_id = atom_dir.name
        atom_eje = atom_eje_map.get(atom_id, _eje_from_id(atom_id))
        atom_titulo = atom_titulo_map.get(atom_id, atom_id)

        items, phase_num = _read_latest_items(atom_dir)
        if not items:
            continue

        eje_set.add(atom_eje)

        for item in items:
            if item.get("image_failed"):
                continue
            item_status = _compute_item_status(item, phase_num)
            meta = item.get("pipeline_meta") or {}
            diff = meta.get("difficulty_level", "unknown")
            diff_set.add(diff)
            status_counts[item_status] = (
                status_counts.get(item_status, 0) + 1
            )

            qti_xml = item.get("qti_xml", "")
            item_has_images = "<img" in qti_xml

            if eje and atom_eje != eje:
                continue
            if difficulty and diff != difficulty:
                continue
            if status and item_status != status:
                continue
            if search and search.lower() not in atom_id.lower():
                continue
            if has_images is not None and item_has_images != has_images:
                continue

            all_items.append({
                "item_id": item.get("item_id"),
                "atom_id": atom_id,
                "atom_titulo": atom_titulo,
                "eje": atom_eje,
                "slot_index": item.get("slot_index"),
                "qti_xml": qti_xml,
                "difficulty": diff,
                "context": meta.get("surface_context", "unknown"),
                "status": item_status,
                "phase": phase_num,
                "has_images": item_has_images,
                "pipeline_meta": meta or None,
            })

    total = len(all_items)
    page_items = all_items[offset: offset + limit]

    return {
        "items": page_items,
        "total": total,
        "status_counts": status_counts,
        "filters": {
            "ejes": sorted(eje_set),
            "difficulties": sorted(diff_set),
        },
    }


def _read_latest_items(
    atom_dir: Path,
) -> tuple[list[dict], int]:
    """Read items from the latest available phase checkpoint."""
    for phase_num, phase_name in _LATEST_PHASES:
        ckpt = load_checkpoint(atom_dir, phase_num, phase_name)
        if ckpt and ckpt.get("items"):
            return ckpt["items"], phase_num
    return [], 0


def _eje_from_id(atom_id: str) -> str:
    """Derive eje from atom ID pattern like A-M1-ALG-01-12."""
    parts = atom_id.split("-")
    if len(parts) >= 3:
        prefix = parts[2].upper()
        mapping = {
            "ALG": "algebra_y_funciones",
            "NUM": "numeros",
            "GEO": "geometria",
            "PROB": "probabilidades_y_estadistica",
        }
        return mapping.get(prefix, prefix.lower())
    return "unknown"


def load_atom_maps(
    atoms_file: Path,
) -> tuple[dict[str, str], dict[str, str]]:
    """Load eje and titulo maps from the canonical atoms JSON."""
    eje_map: dict[str, str] = {}
    titulo_map: dict[str, str] = {}
    if not atoms_file.exists():
        return eje_map, titulo_map
    data = json.loads(atoms_file.read_text(encoding="utf-8"))
    for a in data.get("atoms", []):
        aid = a.get("id", "")
        eje_map[aid] = a.get("eje", "unknown")
        titulo_map[aid] = a.get("titulo", aid)
    return eje_map, titulo_map
