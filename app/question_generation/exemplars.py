"""Exemplar loading from finalized tests.

Scans finalized test directories and builds an atom-indexed mapping
of real PAES questions to use as generation anchors. Exemplars are
NEVER served to students -- they provide scope, style, and difficulty
references for the planner (spec section 3).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.question_generation.models import Exemplar
from app.utils.paths import PRUEBAS_FINALIZADAS_DIR
from app.utils.qti_extractor import parse_qti_xml

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_exemplars_for_atom(
    atom_id: str,
    finalized_dir: Path | None = None,
) -> list[Exemplar]:
    """Load all finalized questions tagged with the given atom.

    Args:
        atom_id: Atom identifier (e.g. "A-M1-ALG-01-02").
        finalized_dir: Override for finalized tests root.

    Returns:
        List of Exemplar objects matching the atom.
    """
    index = build_exemplar_index(finalized_dir)
    return index.get(atom_id, [])


def build_exemplar_index(
    finalized_dir: Path | None = None,
) -> dict[str, list[Exemplar]]:
    """Build a mapping of atom_id -> list[Exemplar] from all finalized tests.

    Scans every question directory under pruebas/finalizadas/*/qti/,
    reads metadata_tags.json for atom tags, and indexes by atom ID.

    Args:
        finalized_dir: Override for finalized tests root directory.

    Returns:
        Dict mapping atom IDs to their exemplar questions.
    """
    root = finalized_dir or PRUEBAS_FINALIZADAS_DIR
    index: dict[str, list[Exemplar]] = {}

    if not root.exists():
        logger.warning("Finalized tests directory not found: %s", root)
        return index

    # Iterate over test directories
    for test_dir in sorted(root.iterdir()):
        if not test_dir.is_dir():
            continue

        qti_dir = test_dir / "qti"
        if not qti_dir.exists():
            continue

        test_id = test_dir.name
        _index_test_questions(qti_dir, test_id, index)

    total = sum(len(v) for v in index.values())
    logger.info(
        "Built exemplar index: %d atoms, %d total exemplars",
        len(index), total,
    )
    return index


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _index_test_questions(
    qti_dir: Path,
    test_id: str,
    index: dict[str, list[Exemplar]],
) -> None:
    """Index all questions in a single test's QTI directory.

    Args:
        qti_dir: Path to the test's qti/ subdirectory.
        test_id: Test identifier for the exemplar.
        index: Mutable index to populate.
    """
    for q_dir in sorted(qti_dir.iterdir()):
        if not q_dir.is_dir():
            continue

        xml_path = q_dir / "question.xml"
        meta_path = q_dir / "metadata_tags.json"

        if not xml_path.exists() or not meta_path.exists():
            continue

        exemplar = _load_single_exemplar(q_dir, test_id)
        if exemplar is None:
            continue

        # Index by each tagged atom
        for atom_id in exemplar.atom_ids:
            index.setdefault(atom_id, []).append(exemplar)


def _load_single_exemplar(
    q_dir: Path,
    test_id: str,
) -> Exemplar | None:
    """Load a single exemplar from a question directory.

    Args:
        q_dir: Path to the question directory.
        test_id: Parent test identifier.

    Returns:
        Exemplar if loading succeeds, None otherwise.
    """
    try:
        qti_xml = (q_dir / "question.xml").read_text(encoding="utf-8")
        metadata = json.loads(
            (q_dir / "metadata_tags.json").read_text(encoding="utf-8"),
        )
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to load exemplar %s: %s", q_dir.name, exc)
        return None

    # Extract atom IDs from metadata
    atom_ids = _extract_atom_ids(metadata)
    if not atom_ids:
        return None

    # Extract difficulty from metadata
    difficulty = metadata.get("difficulty", {})
    diff_level = difficulty.get("level", "medium")

    # Parse question text for context
    parsed = parse_qti_xml(qti_xml)

    return Exemplar(
        question_id=q_dir.name,
        test_id=test_id,
        qti_xml=qti_xml,
        atom_ids=atom_ids,
        difficulty_level=diff_level,
        question_text=parsed.text or "",
    )


def _extract_atom_ids(metadata: dict) -> list[str]:
    """Extract atom IDs from a question's metadata_tags.json.

    Args:
        metadata: Parsed metadata_tags.json content.

    Returns:
        List of atom ID strings.
    """
    selected = metadata.get("selected_atoms", [])
    return [
        atom.get("atom_id", "")
        for atom in selected
        if atom.get("atom_id")
    ]
