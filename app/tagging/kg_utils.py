from pathlib import Path
from typing import Any, Dict, List, Optional

from app.utils.data_loader import load_atoms_file
from app.utils.paths import get_atoms_file

# Default atoms file path (uses centralized path resolution)
DEFAULT_ATOMS_FILE = get_atoms_file("paes_m1_2026")


class KGManager:
    """Manages access to Knowledge Graph atoms."""

    def __init__(self, atoms_path: str | Path = DEFAULT_ATOMS_FILE):
        self.atoms_path = atoms_path
        self._atoms: List[Dict[str, Any]] = []
        self._atoms_by_id: Dict[str, Dict[str, Any]] = {}
        self._load_atoms()

    def _load_atoms(self):
        """Loads atoms from the JSON file."""
        path = Path(self.atoms_path)
        if not path.exists():
            raise FileNotFoundError(f"Atoms file not found at: {path}")

        try:
            # Use shared utility for loading (handles both list and dict formats)
            self._atoms, _ = load_atoms_file(self.atoms_path)

            # Create lookup index
            self._atoms_by_id = {atom["id"]: atom for atom in self._atoms if "id" in atom}

            print(f"Loaded {len(self._atoms)} atoms from {self.atoms_path}")

        except Exception as e:
            print(f"Error loading atoms: {e}")
            self._atoms = []
            self._atoms_by_id = {}

    def get_all_atoms(self) -> List[Dict[str, Any]]:
        """Returns all loaded atoms."""
        return self._atoms

    def get_atom_by_id(self, atom_id: str) -> Optional[Dict[str, Any]]:
        """Returns a specific atom by ID."""
        return self._atoms_by_id.get(atom_id)

    def find_atoms_by_standard(self, standard_id: str) -> List[Dict[str, Any]]:
        """Returns atoms associated with a specific standard."""
        # Simple string match in standard_ids list
        return [atom for atom in self._atoms if standard_id in atom.get("standard_ids", [])]

    def get_ancestors(self, atom_id: str) -> set:
        """Returns a set of all recursive prerequisite IDs for an atom."""
        ancestors = set()
        atom = self.get_atom_by_id(atom_id)
        if not atom:
            return ancestors

        prereqs = atom.get("prerrequisitos", [])
        for p_id in prereqs:
            if p_id not in ancestors:
                ancestors.add(p_id)
                ancestors.update(self.get_ancestors(p_id))
        return ancestors

    def filter_redundant_atoms(self, atom_ids: List[str]) -> List[str]:
        """Removes atoms that are prerequisites of other atoms in the list."""
        if not atom_ids:
            return []

        all_implicit_prereqs = set()
        for aid in atom_ids:
            all_implicit_prereqs.update(self.get_ancestors(aid))

        # Keep an atom only if it is NOT in the implied set of others
        # Edge case: Cycles? Assuming DAG.
        # Edge case: A is prereq of B. We select A and B. A is in ancestors of B. A is removed. Correct.
        return [aid for aid in atom_ids if aid not in all_implicit_prereqs]


# Global instance for easy import
_kg_manager = None


def get_kg_manager() -> KGManager:
    global _kg_manager
    if _kg_manager is None:
        _kg_manager = KGManager()
    return _kg_manager


def get_all_atoms() -> List[Dict[str, Any]]:
    return get_kg_manager().get_all_atoms()


def get_atom_by_id(atom_id: str) -> Optional[Dict[str, Any]]:
    return get_kg_manager().get_atom_by_id(atom_id)


def filter_redundant_atoms(atom_ids: List[str]) -> List[str]:
    return get_kg_manager().filter_redundant_atoms(atom_ids)
