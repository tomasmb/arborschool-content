"""Script para exportar el grafo de átomos en formato JSON para visualización.

Convierte los átomos y sus prerrequisitos a un formato compatible con
librerías de visualización como D3.js o react-d3-tree.

Usage:
    python -m app.atoms.scripts.export_skill_tree \
        --atoms app/data/atoms/paes_m1_2026_atoms.json \
        --output app/diagnostico/config/skill_tree.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict, deque
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def calculate_depths(atoms: list[dict]) -> dict[str, int]:
    """
    Calculate the depth of each atom using topological sort.

    Atoms with no prerequisites have depth 0.
    Atoms with prerequisites have depth = max(prereq depths) + 1.
    """
    # Build adjacency list and in-degree count
    graph: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = defaultdict(int)
    atom_ids = {a["id"] for a in atoms}

    for atom in atoms:
        atom_id = atom["id"]
        in_degree.setdefault(atom_id, 0)
        for prereq in atom.get("prerrequisitos", []):
            if prereq in atom_ids:
                graph[prereq].append(atom_id)
                in_degree[atom_id] += 1

    # Kahn's algorithm for topological sort with depth tracking
    depths: dict[str, int] = {}
    queue = deque()

    # Start with nodes that have no prerequisites
    for atom_id in atom_ids:
        if in_degree[atom_id] == 0:
            queue.append(atom_id)
            depths[atom_id] = 0

    while queue:
        current = queue.popleft()
        current_depth = depths[current]

        for neighbor in graph[current]:
            in_degree[neighbor] -= 1
            # Update depth to be max of all prereq depths + 1
            depths[neighbor] = max(depths.get(neighbor, 0), current_depth + 1)
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return depths


def build_hierarchical_tree(atoms: list[dict], depths: dict[str, int]) -> list[dict]:
    """
    Build a hierarchical tree structure for react-d3-tree.

    Groups atoms by eje, with each eje being a root node.
    """
    # Group atoms by eje
    by_eje: dict[str, list[dict]] = defaultdict(list)
    for atom in atoms:
        by_eje[atom["eje"]].append(atom)

    # Create root nodes for each eje
    eje_names = {
        "algebra_y_funciones": "Álgebra y Funciones",
        "numeros": "Números",
        "geometria": "Geometría",
        "probabilidad_y_estadistica": "Probabilidad y Estadística",
    }

    roots = []
    for eje, eje_atoms in by_eje.items():
        # Sort by depth, then by id
        sorted_atoms = sorted(eje_atoms, key=lambda a: (depths.get(a["id"], 0), a["id"]))

        children = []
        for atom in sorted_atoms:
            children.append({
                "name": atom["id"],
                "attributes": {
                    "title": atom["titulo"],
                    "depth": depths.get(atom["id"], 0),
                    "habilidad": atom["habilidad_principal"],
                },
                "children": [],  # Leaf nodes for now
            })

        roots.append({
            "name": eje_names.get(eje, eje),
            "attributes": {"type": "eje", "count": len(eje_atoms)},
            "children": children,
        })

    return roots


def export_skill_tree(atoms_path: Path, output_path: Path, output_format: str = "both") -> None:
    """Export atoms as a skill tree JSON."""
    # Load atoms
    logger.info("Loading atoms from: %s", atoms_path)
    with atoms_path.open(encoding="utf-8") as f:
        data = json.load(f)

    atoms = data["atoms"]
    logger.info("Loaded %d atoms", len(atoms))

    # Calculate depths
    depths = calculate_depths(atoms)
    max_depth = max(depths.values()) if depths else 0
    logger.info("Max depth: %d", max_depth)

    # Build flat format (nodes + edges)
    nodes = []
    edges = []

    for atom in atoms:
        atom_id = atom["id"]
        nodes.append({
            "id": atom_id,
            "title": atom["titulo"],
            "eje": atom["eje"],
            "habilidad": atom["habilidad_principal"],
            "depth": depths.get(atom_id, 0),
        })

        for prereq in atom.get("prerrequisitos", []):
            edges.append({
                "source": prereq,
                "target": atom_id,
            })

    # Build hierarchical format
    hierarchical = build_hierarchical_tree(atoms, depths)

    # Statistics
    stats = {
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "max_depth": max_depth,
        "nodes_by_eje": {},
        "nodes_by_depth": {},
    }

    for node in nodes:
        eje = node["eje"]
        depth = node["depth"]
        stats["nodes_by_eje"][eje] = stats["nodes_by_eje"].get(eje, 0) + 1
        stats["nodes_by_depth"][depth] = stats["nodes_by_depth"].get(depth, 0) + 1

    # Build output
    output = {
        "metadata": stats,
        "flat": {
            "nodes": nodes,
            "edges": edges,
        },
        "hierarchical": hierarchical,
    }

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info("Skill tree exported to: %s", output_path)

    # Print summary
    print("=" * 60)
    print("SKILL TREE EXPORT SUMMARY")
    print("=" * 60)
    print(f"Total nodes: {stats['total_nodes']}")
    print(f"Total edges: {stats['total_edges']}")
    print(f"Max depth: {stats['max_depth']}")
    print()
    print("Nodes by eje:")
    for eje, count in sorted(stats["nodes_by_eje"].items()):
        print(f"  {eje}: {count}")
    print()
    print("Nodes by depth:")
    for depth, count in sorted(stats["nodes_by_depth"].items()):
        print(f"  Depth {depth}: {count}")
    print("=" * 60)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Export atoms as a skill tree JSON for visualization.",
    )
    parser.add_argument(
        "--atoms",
        type=Path,
        default=Path("app/data/atoms/paes_m1_2026_atoms.json"),
        help="Canonical atoms JSON file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("app/diagnostico/config/skill_tree.json"),
        help="Output JSON file for skill tree",
    )
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.atoms.exists():
        logger.error("Atoms file not found: %s", args.atoms)
        sys.exit(1)

    export_skill_tree(args.atoms, args.output)


if __name__ == "__main__":
    main()
