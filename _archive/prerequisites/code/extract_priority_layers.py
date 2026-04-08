"""extract_priority_layers.py — BFS from M1 to produce layer files.

Walks the prerequisite graph starting from M1 atoms and writes one
text file per BFS layer (layer_1_atoms.txt, layer_2_atoms.txt, …)
plus a combined priority_atoms_all.txt with layer comments.
"""
from __future__ import annotations

import json
from collections import deque
from pathlib import Path

REPO = Path(__file__).resolve().parent
ATOMS_DIR = REPO / "app" / "data" / "atoms"
PREREQ_DIR = REPO / "app" / "data" / "prerequisites"


def _load_m1_atom_ids() -> set[str]:
    """Load all M1 atom IDs from canonical atoms files."""
    ids: set[str] = set()
    for f in ATOMS_DIR.glob("*_atoms.json"):
        data = json.loads(f.read_text(encoding="utf-8"))
        for a in data.get("atoms", []):
            ids.add(a["id"])
    return ids


def main() -> None:
    m1_ids = _load_m1_atom_ids()

    prereq_data = json.loads(
        (PREREQ_DIR / "atoms.json").read_text(encoding="utf-8"),
    )
    prereq_atoms = {a["id"]: a for a in prereq_data["atoms"]}

    conn_data = json.loads(
        (PREREQ_DIR / "connections.json").read_text(encoding="utf-8"),
    )
    m1_prereqs: dict[str, set[str]] = {}
    for c in conn_data["connections"]:
        m1_prereqs.setdefault(
            c["m1_atom_id"], set(),
        ).update(c["new_prerequisites"])

    prereq_graph: dict[str, set[str]] = {}
    for a in prereq_data["atoms"]:
        prereq_graph[a["id"]] = set(a.get("prerrequisitos", []))

    layers: dict[int, list[str]] = {}
    visited: set[str] = set()
    queue: deque[tuple[str, int]] = deque()

    for m1_id in sorted(m1_ids):
        for pid in sorted(m1_prereqs.get(m1_id, [])):
            if pid in prereq_atoms and pid not in visited:
                visited.add(pid)
                layers.setdefault(1, []).append(pid)
                queue.append((pid, 1))

    while queue:
        atom_id, layer = queue.popleft()
        for pid in sorted(prereq_graph.get(atom_id, [])):
            if pid in prereq_atoms and pid not in visited:
                visited.add(pid)
                layers.setdefault(layer + 1, []).append(pid)
                queue.append((pid, layer + 1))

    for layer_num, ids in sorted(layers.items()):
        out = REPO / f"layer_{layer_num}_atoms.txt"
        out.write_text(
            "\n".join(sorted(ids)) + "\n", encoding="utf-8",
        )
        print(f"Layer {layer_num}: {len(ids)} atoms -> {out.name}")

    combined = REPO / "priority_atoms_all.txt"
    lines: list[str] = []
    for layer_num in sorted(layers):
        lines.append(f"# --- Layer {layer_num} ---")
        lines.extend(sorted(layers[layer_num]))
    combined.write_text("\n".join(lines) + "\n", encoding="utf-8")
    total = sum(len(v) for v in layers.values())
    print(f"Combined: {total} atoms -> {combined.name}")


if __name__ == "__main__":
    main()
