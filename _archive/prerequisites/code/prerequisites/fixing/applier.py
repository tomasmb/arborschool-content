"""Apply FixResults to the prerequisite atoms file.

Simpler than the M1 applier: no pruebas metadata, no question refs.
Only handles atom mutations and prerequisite cascade within the
prereq graph.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.atoms.fixing.models import FixResult
from app.utils.paths import PREREQ_ATOMS_FILE

logger = logging.getLogger(__name__)


@dataclass
class PrereqChangeReport:
    """Summary of all proposed changes."""

    atoms_added: list[str] = field(default_factory=list)
    atoms_removed: list[str] = field(default_factory=list)
    atoms_modified: list[str] = field(default_factory=list)
    prerequisite_cascades: dict[str, list[str]] = field(
        default_factory=dict,
    )

    def summary(self) -> str:
        return "\n".join([
            f"Atoms added:     {len(self.atoms_added)}",
            f"Atoms removed:   {len(self.atoms_removed)}",
            f"Atoms modified:  {len(self.atoms_modified)}",
            f"Prereq cascades: {len(self.prerequisite_cascades)}",
        ])


def apply_prereq_results(
    results: list[FixResult],
    *,
    dry_run: bool = True,
    atoms_file: Path | None = None,
) -> PrereqChangeReport:
    """Apply a batch of FixResults to the prereq atoms file.

    Args:
        results: Successful FixResults to apply.
        dry_run: If True, compute the report but do not write files.
        atoms_file: Override path (defaults to PREREQ_ATOMS_FILE).

    Returns:
        A PrereqChangeReport summarising changes.
    """
    path = atoms_file or PREREQ_ATOMS_FILE
    atoms_data = _load_json(path)
    all_atoms: list[dict[str, Any]] = atoms_data.get("atoms", [])
    report = PrereqChangeReport()

    global_id_map: dict[str, list[str]] = {}
    global_removed: set[str] = set()

    for result in results:
        if not result.success:
            continue
        global_id_map.update(result.id_mapping)
        global_removed.update(result.removed_atom_ids)
        all_atoms = _apply_atom_changes(all_atoms, result, report)

    if global_id_map or global_removed:
        all_atoms = _cascade_prerequisites(
            all_atoms, global_id_map, global_removed, report,
        )

    for result in results:
        if not result.success:
            continue
        for atom_id, new_prereqs in result.prerequisite_updates.items():
            for atom in all_atoms:
                if atom.get("id") == atom_id:
                    atom["prerrequisitos"] = new_prereqs

    if not dry_run:
        atoms_data["atoms"] = all_atoms
        atoms_data["metadata"]["total_atoms"] = len(all_atoms)
        _write_json(path, atoms_data)
        logger.info("Wrote updated prereq atoms to %s", path)
    else:
        logger.info("DRY RUN — prereq atoms file not written.")

    return report


def _apply_atom_changes(
    all_atoms: list[dict[str, Any]],
    result: FixResult,
    report: PrereqChangeReport,
) -> list[dict[str, Any]]:
    """Replace, remove, or add atoms based on a single FixResult."""
    removed_ids = set(result.removed_atom_ids)
    existing_ids = {a.get("id") for a in all_atoms}
    new_atom_ids = {a.get("id") for a in result.new_atoms}

    if removed_ids:
        all_atoms = [
            a for a in all_atoms if a.get("id") not in removed_ids
        ]
        report.atoms_removed.extend(sorted(removed_ids))

    for new_atom in result.new_atoms:
        aid = new_atom.get("id", "")
        if aid in existing_ids and aid not in removed_ids:
            all_atoms = [
                new_atom if a.get("id") == aid else a
                for a in all_atoms
            ]
            report.atoms_modified.append(aid)
        elif aid not in existing_ids or aid in new_atom_ids:
            all_atoms.append(new_atom)
            report.atoms_added.append(aid)

    return all_atoms


def _cascade_prerequisites(
    all_atoms: list[dict[str, Any]],
    id_map: dict[str, list[str]],
    removed: set[str],
    report: PrereqChangeReport,
) -> list[dict[str, Any]]:
    """Rename / remove prerequisite references across all atoms."""
    for atom in all_atoms:
        prereqs: list[str] = atom.get("prerrequisitos", [])
        new_prereqs: list[str] = []
        changed = False

        for pid in prereqs:
            if pid in id_map:
                new_prereqs.extend(id_map[pid])
                changed = True
            elif pid in removed:
                changed = True
            else:
                new_prereqs.append(pid)

        if changed:
            atom["prerrequisitos"] = list(dict.fromkeys(new_prereqs))
            report.prerequisite_cascades[atom["id"]] = (
                atom["prerrequisitos"]
            )

    return all_atoms


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    with path.open("a", encoding="utf-8") as f:
        f.write("\n")
