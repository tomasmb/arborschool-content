"""Script para verificar dependencias circulares en los átomos.

Detecta ciclos en el grafo de prerrequisitos usando DFS.

Usage:
    python -m app.atoms.scripts.check_circular_dependencies \\
        --atoms app/data/atoms/paes_m1_2026_atoms.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from app.atoms.models import Atom, CanonicalAtomsFile
from app.utils.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def find_cycles(
    atoms: list[Atom],
) -> list[list[str]]:
    """
    Find all cycles in the prerequisite graph using DFS.

    Returns:
        List of cycles, where each cycle is a list of atom IDs forming a cycle.
    """
    # Build graph: atom_id -> list of prerequisite IDs
    graph: dict[str, list[str]] = {}
    atom_ids = set()

    for atom in atoms:
        atom_id = atom.id
        atom_ids.add(atom_id)
        graph[atom_id] = atom.prerrequisitos.copy()

    # Verify all prerequisites exist
    all_prereqs = set()
    for prereqs in graph.values():
        all_prereqs.update(prereqs)

    missing_prereqs = all_prereqs - atom_ids
    if missing_prereqs:
        logger.warning(
            "Found prerequisites that don't exist as atoms: %s",
            sorted(missing_prereqs),
        )

    # Find cycles using DFS
    cycles: list[list[str]] = []
    visited: set[str] = set()
    rec_stack: set[str] = set()
    path: list[str] = []

    def dfs(node: str) -> None:
        """DFS to detect cycles."""
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in atom_ids:
                # Skip missing prerequisites
                continue
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in rec_stack:
                # Found a cycle
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                # Normalize cycle (start from smallest ID)
                min_idx = min(range(len(cycle) - 1), key=lambda i: cycle[i])
                normalized_cycle = cycle[min_idx:-1] + [cycle[min_idx]]
                if normalized_cycle not in cycles:
                    cycles.append(normalized_cycle)

        rec_stack.remove(node)
        path.pop()

    # Run DFS on all nodes
    for atom_id in sorted(atom_ids):
        if atom_id not in visited:
            dfs(atom_id)

    return cycles


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Check for circular dependencies in atoms.",
    )
    parser.add_argument(
        "--atoms",
        type=Path,
        default=Path("app/data/atoms/paes_m1_2026_atoms.json"),
        help="Canonical atoms JSON file (default: app/data/atoms/paes_m1_2026_atoms.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON file for cycles report (optional)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.atoms.exists():
        logger.error("Atoms file not found: %s", args.atoms)
        sys.exit(1)

    # Load atoms
    logger.info("Loading atoms: %s", args.atoms)
    with args.atoms.open(encoding="utf-8") as f:
        atoms_data = json.load(f)

    canonical_file = CanonicalAtomsFile.model_validate(atoms_data)
    atoms = canonical_file.atoms

    logger.info("Loaded %d atoms", len(atoms))

    # Find cycles
    logger.info("Checking for circular dependencies...")
    cycles = find_cycles(atoms)

    # Print results
    print("=" * 70)
    print("VERIFICACIÓN DE DEPENDENCIAS CIRCULARES")
    print("=" * 70)
    print()

    if not cycles:
        print("✅ No se encontraron dependencias circulares")
        print()
        print("El grafo de prerrequisitos es acíclico (DAG).")
        print("Todos los átomos pueden ordenarse en una secuencia válida.")
    else:
        print(f"❌ Se encontraron {len(cycles)} ciclo(s) de dependencias:")
        print()
        for i, cycle in enumerate(cycles, 1):
            print(f"Ciclo {i}:")
            print("  " + " → ".join(cycle))
            print()

        print("=" * 70)
        print("ANÁLISIS")
        print("=" * 70)
        print()
        print("Estos ciclos impiden ordenar los átomos en una secuencia válida.")
        print("Cada ciclo debe resolverse eliminando o modificando al menos")
        print("un prerrequisito en el ciclo.")
        print()

    # Build statistics
    total_prereqs = sum(len(atom.prerrequisitos) for atom in atoms)
    atoms_with_prereqs = sum(1 for atom in atoms if atom.prerrequisitos)
    atoms_without_prereqs = len(atoms) - atoms_with_prereqs

    print("=" * 70)
    print("ESTADÍSTICAS DEL GRAFO")
    print("=" * 70)
    print(f"Total átomos: {len(atoms)}")
    print(f"Átomos con prerrequisitos: {atoms_with_prereqs}")
    print(f"Átomos sin prerrequisitos: {atoms_without_prereqs}")
    print(f"Total prerrequisitos: {total_prereqs}")
    print(f"Ciclos encontrados: {len(cycles)}")
    print("=" * 70)

    # Save report if requested
    if args.output:
        report = {
            "total_atoms": len(atoms),
            "cycles_found": len(cycles),
            "cycles": cycles,
            "statistics": {
                "atoms_with_prereqs": atoms_with_prereqs,
                "atoms_without_prereqs": atoms_without_prereqs,
                "total_prereqs": total_prereqs,
            },
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info("Report saved to: %s", args.output)

    if cycles:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
