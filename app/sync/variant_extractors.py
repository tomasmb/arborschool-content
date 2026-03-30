"""Extract variant questions from alternativas/ and hard_variants/.

This module extracts approved question variants that are generated from
official test questions. Variants inherit atom associations from their parent
via parent_question_id - no separate question_atoms are synced for variants.

Variant sources:
    alternativas/{test_id}/Q{n}/approved/Q{n}_v{m}/
    hard_variants/{test_id}/Q{n}/variants/approved/Q{n}_v{m}/
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Import shared helpers from extractors
from app.sync.extractors import (
    _find_images_in_qti,
    extract_all_tests,
)
from app.utils.paths import (
    PRUEBAS_ALTERNATIVAS_DIR,
    PRUEBAS_HARD_VARIANTS_DIR,
)

# -----------------------------------------------------------------------------
# Data container
# -----------------------------------------------------------------------------


@dataclass
class ExtractedVariant:
    """Variant question extracted from alternativas/.

    Variants inherit atom associations from their parent question via parent_question_id.
    No separate question_atoms are stored for variants - queries should resolve atoms
    through the parent question.

    Note: correct_answer and feedback are now stored in QTI XML and parsed at display time.
    """

    id: str  # e.g., "alt-prueba-invierno-2025-Q1-001"
    variant_id: str  # e.g., "Q1_v1"
    parent_question_id: str  # e.g., "prueba-invierno-2025-Q1"
    source_test_id: str  # Source test, e.g., "prueba-invierno-2025"
    source_question_number: int  # e.g., 1
    qti_xml: str
    difficulty_level: str | None
    difficulty_score: float | None
    # Variant-specific metadata
    change_description: str | None  # What was changed from the original
    validation_verdict: str | None  # APROBADA/RECHAZADA
    validation_steps: str | None  # Calculation steps from validation
    # Image paths found in QTI
    image_paths: list[str]


# -----------------------------------------------------------------------------
# Extraction functions
# -----------------------------------------------------------------------------


def _extract_single_variant(
    variant_dir: Path,
    test_id: str,
    question_number: int,
    variant_seq: int,
) -> ExtractedVariant | None:
    """Extract a single variant from its directory.

    Args:
        variant_dir: Path to the variant directory (e.g., Q1_v1/)
        test_id: The source test ID
        question_number: The question number in the test
        variant_seq: The variant sequence number (1, 2, etc.)

    Returns:
        ExtractedVariant if successful, None if files are missing
    """
    qti_file = variant_dir / "question.xml"
    if not qti_file.exists():
        return None

    with open(qti_file, encoding="utf-8") as f:
        qti_xml = f.read()

    # Read variant_info.json
    variant_info_file = variant_dir / "variant_info.json"
    variant_info: dict[str, Any] = {}
    if variant_info_file.exists():
        with open(variant_info_file, encoding="utf-8") as f:
            variant_info = json.load(f)

    # Read metadata_tags.json
    metadata_file = variant_dir / "metadata_tags.json"
    metadata: dict[str, Any] = {}
    if metadata_file.exists():
        with open(metadata_file, encoding="utf-8") as f:
            metadata = json.load(f)

    # Build variant ID: alt-{test_id}-Q{n}-{seq:03d}
    variant_id = variant_info.get("variant_id", variant_dir.name)
    canonical_id = f"alt-{test_id}-Q{question_number}-{variant_seq:03d}"
    parent_question_id = f"{test_id}-Q{question_number}"

    # Extract difficulty
    difficulty = metadata.get("difficulty", {})
    difficulty_level = difficulty.get("level", "medium").lower() if difficulty else "medium"
    if difficulty_level not in ("low", "medium", "high"):
        difficulty_level = "medium"

    # Extract validation info
    validation = metadata.get("validation", {})

    # Extract change description from source_info
    source_info = metadata.get("source_info", {})
    change_description = source_info.get("change_description")

    return ExtractedVariant(
        id=canonical_id,
        variant_id=variant_id,
        parent_question_id=parent_question_id,
        source_test_id=test_id,
        source_question_number=question_number,
        qti_xml=qti_xml,
        difficulty_level=difficulty_level,
        difficulty_score=difficulty.get("score") if difficulty else None,
        change_description=change_description,
        validation_verdict=validation.get("verdict") if validation else None,
        validation_steps=validation.get("calculation_steps") if validation else None,
        image_paths=_find_images_in_qti(qti_xml),
    )


def _walk_approved_dirs(
    base_dir: Path,
    approved_subpath: str = "approved",
) -> list[tuple[str, int, int, Path]]:
    """Walk a variant tree and yield (test_id, q_num, seq, dir).

    Works for both directory layouts:
      alternativas/{test}/Q{n}/approved/Q{n}_v{m}/
      hard_variants/{test}/Q{n}/variants/approved/Q{n}_v{m}/
    """
    results: list[tuple[str, int, int, Path]] = []
    if not base_dir.exists():
        return results

    for test_dir in sorted(base_dir.iterdir()):
        if not test_dir.is_dir():
            continue
        test_id = test_dir.name.lower()

        for q_dir in sorted(test_dir.iterdir()):
            if not q_dir.is_dir() or not q_dir.name.startswith("Q"):
                continue
            q_num_match = re.search(r"(\d+)", q_dir.name)
            if not q_num_match:
                continue
            q_num = int(q_num_match.group(1))

            approved_dir = q_dir / approved_subpath
            if not approved_dir.exists():
                continue

            variant_seq = 0
            for v_dir in sorted(approved_dir.iterdir()):
                if not v_dir.is_dir():
                    continue
                v_match = re.search(r"_v(\d+)$", v_dir.name)
                if v_match:
                    variant_seq = int(v_match.group(1))
                else:
                    variant_seq += 1
                results.append((test_id, q_num, variant_seq, v_dir))

    return results


def extract_variants(
    alternativas_dir: Path | None = None,
    hard_variants_dir: Path | None = None,
) -> list[ExtractedVariant]:
    """Extract all approved variants from both data sources.

    Sources (both optional, deduplicated by canonical ID):
      alternativas/{test_id}/Q{n}/approved/Q{n}_v{m}/
      hard_variants/{test_id}/Q{n}/variants/approved/Q{n}_v{m}/

    Args:
        alternativas_dir: Defaults to PRUEBAS_ALTERNATIVAS_DIR.
        hard_variants_dir: Defaults to PRUEBAS_HARD_VARIANTS_DIR.

    Returns:
        Deduplicated list of ExtractedVariant (hard_variants wins ties).
    """
    if alternativas_dir is None:
        alternativas_dir = PRUEBAS_ALTERNATIVAS_DIR
    if hard_variants_dir is None:
        hard_variants_dir = PRUEBAS_HARD_VARIANTS_DIR

    by_id: dict[str, ExtractedVariant] = {}

    # alternativas: {test}/Q{n}/approved/...
    for test_id, q_num, seq, v_dir in _walk_approved_dirs(
        alternativas_dir, "approved",
    ):
        v = _extract_single_variant(v_dir, test_id, q_num, seq)
        if v:
            by_id[v.id] = v

    # hard_variants: {test}/Q{n}/variants/approved/...
    for test_id, q_num, seq, v_dir in _walk_approved_dirs(
        hard_variants_dir, "variants/approved",
    ):
        v = _extract_single_variant(v_dir, test_id, q_num, seq)
        if v:
            by_id[v.id] = v  # overwrites alternativas duplicate

    return sorted(by_id.values(), key=lambda v: v.id)


def extract_all_variants() -> list[ExtractedVariant]:
    """Extract all variants from alternativas/.

    Returns:
        List of all ExtractedVariant instances.
    """
    return extract_variants()


def extract_all_with_variants() -> tuple[
    list,  # list[ExtractedTest] - imported type
    list,  # list[ExtractedQuestion] - imported type
    list[ExtractedVariant],
]:
    """Extract all tests, questions, and variants.

    Convenience function that calls extract_all_tests() and extract_variants().

    Returns:
        Tuple of (tests, questions, variants)
    """
    tests, questions = extract_all_tests()
    variants = extract_all_variants()
    return tests, questions, variants
