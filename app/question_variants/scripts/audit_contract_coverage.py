#!/usr/bin/env python3
"""Audit family-catalog coverage over official finalized questions."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from app.question_variants.contracts.family_catalog import resolve_family_spec

FINALIZED_ROOT = Path("app/data/pruebas/finalizadas")


def collect_atom_hints(metadata: dict) -> list[str]:
    """Return normalized atom titles and ids used for family resolution."""
    hints: list[str] = []
    for atom in metadata.get("selected_atoms", []):
        if atom.get("relevance") != "primary":
            continue
        atom_title = str(atom.get("atom_title", "")).strip().lower()
        atom_id = str(atom.get("atom_id", "")).strip().lower()
        if atom_title:
            hints.append(atom_title)
        if atom_id:
            hints.append(atom_id)
    return hints


def main() -> None:
    matched = Counter()
    unmatched = Counter()

    for metadata_path in FINALIZED_ROOT.glob("*/qti/Q*/metadata_tags.json"):
        metadata = json.loads(metadata_path.read_text())
        hints = collect_atom_hints(metadata)
        skill = (metadata.get("habilidad_principal") or {}).get("habilidad_principal") or ""
        family_spec = resolve_family_spec(hints, skill)
        if family_spec.get("family_id"):
            matched[str(family_spec["family_id"])] += 1
        else:
            unmatched[" | ".join(hints) or "NO_PRIMARY_ATOM"] += 1

    matched_total = sum(matched.values())
    unmatched_total = sum(unmatched.values())

    print(f"matched_total\t{matched_total}")
    print(f"unmatched_total\t{unmatched_total}")
    print()
    print("matched_by_family")
    for family_id, count in matched.most_common():
        print(f"{count}\t{family_id}")

    if unmatched:
        print()
        print("unmatched")
        for family_hint, count in unmatched.most_common():
            print(f"{count}\t{family_hint}")


if __name__ == "__main__":
    main()
