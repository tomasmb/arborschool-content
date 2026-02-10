"""Apply FixResults to the canonical atoms file and cascade side effects.

Side effects handled:
  - Update/remove/add atoms in ``paes_m1_2026_atoms.json``.
  - Cascade prerequisite renames across ALL atoms (not just one standard).
  - Update ``atom_id`` references in every ``metadata_tags.json``.
  - Dry-run mode: produce a change report without writing any file.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.atoms.fixing.models import FixResult
from app.utils.paths import PRUEBAS_FINALIZADAS_DIR, get_atoms_file

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Dry-run report model
# -----------------------------------------------------------------------------


@dataclass
class ChangeReport:
    """Summary of all proposed changes (returned in dry-run mode)."""

    atoms_added: list[str] = field(default_factory=list)
    atoms_removed: list[str] = field(default_factory=list)
    atoms_modified: list[str] = field(default_factory=list)
    prerequisite_cascades: dict[str, list[str]] = field(default_factory=dict)
    question_mapping_updates: list[dict[str, str]] = field(default_factory=list)
    manual_review_needed: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"Atoms added:    {len(self.atoms_added)}",
            f"Atoms removed:  {len(self.atoms_removed)}",
            f"Atoms modified: {len(self.atoms_modified)}",
            f"Prereq cascades: {len(self.prerequisite_cascades)}",
            f"Q-mapping updates: {len(self.question_mapping_updates)}",
            f"Manual review:  {len(self.manual_review_needed)}",
        ]
        return "\n".join(lines)


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------


def apply_results(
    results: list[FixResult],
    *,
    dry_run: bool = True,
    atoms_file: Path | None = None,
) -> ChangeReport:
    """Apply a batch of FixResults to the codebase.

    Args:
        results: Successful FixResults to apply.
        dry_run: If True, compute the report but do not write files.
        atoms_file: Override path to atoms JSON (defaults to canonical).

    Returns:
        A ChangeReport summarising what was (or would be) changed.
    """
    atoms_path = atoms_file or get_atoms_file()
    atoms_data = _load_json(atoms_path)
    all_atoms: list[dict[str, Any]] = atoms_data.get("atoms", [])

    report = ChangeReport()

    # Aggregate ID mappings across all results.
    global_id_map: dict[str, list[str]] = {}
    global_removed: set[str] = set()
    global_qmap: dict[str, str] = {}

    for result in results:
        if not result.success:
            continue

        global_id_map.update(result.id_mapping)
        global_removed.update(result.removed_atom_ids)
        global_qmap.update(result.question_mapping_suggestions)

        # Apply atom-level changes.
        all_atoms = _apply_atom_changes(
            all_atoms, result, report,
        )

    # Cascade prerequisite renames across ALL atoms.
    if global_id_map or global_removed:
        all_atoms = _cascade_prerequisites(
            all_atoms, global_id_map, global_removed, report,
        )

    # Also apply explicit prerequisite_updates from results.
    for result in results:
        if not result.success:
            continue
        for atom_id, new_prereqs in result.prerequisite_updates.items():
            for atom in all_atoms:
                if atom.get("id") == atom_id:
                    atom["prerrequisitos"] = new_prereqs

    # Update question mappings.
    qmap_files = _find_metadata_files()
    _update_question_mappings(
        qmap_files, global_id_map, global_removed, global_qmap, report,
        dry_run=dry_run,
    )

    # Write atoms file.
    if not dry_run:
        atoms_data["atoms"] = all_atoms
        _write_json(atoms_path, atoms_data)
        logger.info("Wrote updated atoms to %s", atoms_path)
    else:
        logger.info("DRY RUN — atoms file not written.")

    return report


# -----------------------------------------------------------------------------
# Atom-level mutations
# -----------------------------------------------------------------------------


def _apply_atom_changes(
    all_atoms: list[dict[str, Any]],
    result: FixResult,
    report: ChangeReport,
) -> list[dict[str, Any]]:
    """Replace, remove, or add atoms based on a single FixResult."""
    removed_ids = set(result.removed_atom_ids)
    existing_ids = {a.get("id") for a in all_atoms}
    new_atom_ids = {a.get("id") for a in result.new_atoms}

    # Remove atoms.
    if removed_ids:
        all_atoms = [a for a in all_atoms if a.get("id") not in removed_ids]
        report.atoms_removed.extend(sorted(removed_ids))

    # Replace or add atoms.
    for new_atom in result.new_atoms:
        aid = new_atom.get("id", "")
        if aid in existing_ids and aid not in removed_ids:
            # In-place update.
            all_atoms = [
                new_atom if a.get("id") == aid else a for a in all_atoms
            ]
            report.atoms_modified.append(aid)
        elif aid not in existing_ids or aid in new_atom_ids:
            all_atoms.append(new_atom)
            report.atoms_added.append(aid)

    return all_atoms


# -----------------------------------------------------------------------------
# Prerequisite cascade
# -----------------------------------------------------------------------------


def _cascade_prerequisites(
    all_atoms: list[dict[str, Any]],
    id_map: dict[str, list[str]],
    removed: set[str],
    report: ChangeReport,
) -> list[dict[str, Any]]:
    """Rename / remove prerequisite references across all atoms."""
    for atom in all_atoms:
        prereqs: list[str] = atom.get("prerrequisitos", [])
        new_prereqs: list[str] = []
        changed = False

        for pid in prereqs:
            if pid in id_map:
                # Replace with mapped IDs (SPLIT → multiple, MERGE → one).
                new_prereqs.extend(id_map[pid])
                changed = True
            elif pid in removed:
                changed = True  # Drop the reference.
            else:
                new_prereqs.append(pid)

        if changed:
            # De-duplicate while preserving order.
            atom["prerrequisitos"] = list(dict.fromkeys(new_prereqs))
            report.prerequisite_cascades[atom["id"]] = atom["prerrequisitos"]

    return all_atoms


# -----------------------------------------------------------------------------
# Question-mapping updates
# -----------------------------------------------------------------------------


def _find_metadata_files() -> list[Path]:
    """Return all metadata_tags.json files under pruebas/finalizadas."""
    return sorted(PRUEBAS_FINALIZADAS_DIR.rglob("metadata_tags.json"))


def _update_question_mappings(
    files: list[Path],
    id_map: dict[str, list[str]],
    removed: set[str],
    qmap_suggestions: dict[str, str],
    report: ChangeReport,
    *,
    dry_run: bool,
) -> None:
    """Scan all metadata_tags.json and update atom_id references."""
    if not id_map and not removed:
        return

    for path in files:
        data = _load_json(path)
        if data is None:
            continue

        selected: list[dict[str, Any]] = data.get("selected_atoms", [])
        modified = False
        question_key = _question_key(path)

        new_selected: list[dict[str, Any]] = []
        for entry in selected:
            old_id: str = entry.get("atom_id", "")

            if old_id in id_map:
                # Use LLM suggestion if available, else first mapped ID.
                suggested = qmap_suggestions.get(question_key)
                replacement = suggested or id_map[old_id][0]
                entry["atom_id"] = replacement
                new_selected.append(entry)
                report.question_mapping_updates.append(
                    {"file": str(path), "old": old_id, "new": replacement},
                )
                modified = True
            elif old_id in removed:
                # Atom removed entirely — flag for manual review.
                report.manual_review_needed.append(
                    f"{path}: atom {old_id} removed, no mapping available",
                )
                modified = True
                # Keep entry but mark it.
                entry["atom_id"] = f"REMOVED:{old_id}"
                new_selected.append(entry)
            else:
                new_selected.append(entry)

        if modified:
            data["selected_atoms"] = new_selected
            if not dry_run:
                _write_json(path, data)


def _question_key(path: Path) -> str:
    """Derive a question key like ``Q1`` from the file path."""
    # .../qti/Q1/metadata_tags.json → "Q1"
    return path.parent.name


# -----------------------------------------------------------------------------
# JSON I/O
# -----------------------------------------------------------------------------


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to load %s: %s", path, exc)
        return None


def _write_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    # Ensure trailing newline.
    with path.open("a", encoding="utf-8") as f:
        f.write("\n")
