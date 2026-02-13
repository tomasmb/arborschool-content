"""Shared validation helper functions for the question generation pipeline.

Contains pure functions used by DuplicateGate, BaseValidator, and
FinalValidator: fingerprinting, PAES structure checks, exemplar
distance checking, feedback completeness, and correct-option extraction.
"""

from __future__ import annotations

import hashlib
import importlib.util
import re
from pathlib import Path
from typing import Any

from app.question_generation.models import Exemplar, GeneratedItem

# ---------------------------------------------------------------------------
# XSD validator import (same approach as question_feedback/enhancer.py)
# ---------------------------------------------------------------------------

def _import_xsd_validator() -> Any:
    """Import validate_qti_xml from the pdf-to-qti module."""
    module_path = (
        Path(__file__).parent.parent
        / "pruebas"
        / "pdf-to-qti"
        / "modules"
        / "validation"
        / "xml_validator.py"
    )
    if not module_path.exists():
        return None

    spec = importlib.util.spec_from_file_location(
        "xml_validator", module_path,
    )
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_xml_validator_mod = _import_xsd_validator()
if _xml_validator_mod:
    validate_qti_xml = _xml_validator_mod.validate_qti_xml
else:
    import logging as _stub_logging
    _stub_logging.getLogger(__name__).warning(
        "XSD validator unavailable (import failed) — "
        "all XSD checks will REJECT items as a safety measure",
    )

    def validate_qti_xml(
        qti_xml: str,
        validation_endpoint: str | None = None,
    ) -> dict[str, Any]:
        """Fail-safe stub: rejects items when validator is missing."""
        return {
            "valid": False,
            "message": "XSD validator unavailable",
        }


# ---------------------------------------------------------------------------
# Fingerprinting (Phase 5 support)
# ---------------------------------------------------------------------------


def compute_fingerprint(qti_xml: str) -> str:
    """Compute a SHA-256 fingerprint of normalized QTI content.

    Normalizes whitespace, removes identifiers, and sorts choice
    options alphabetically so that commuted option order does not
    produce a different fingerprint.

    Args:
        qti_xml: Raw QTI XML string.

    Returns:
        Hex-encoded SHA-256 hash.
    """
    normalized = qti_xml.strip()
    # Remove XML comments
    normalized = re.sub(r"<!--.*?-->", "", normalized, flags=re.DOTALL)
    # Normalize whitespace
    normalized = re.sub(r"\s+", " ", normalized)
    # Remove identifier attributes (they're always unique)
    normalized = re.sub(r'identifier="[^"]*"', "", normalized)
    # Remove title attributes
    normalized = re.sub(r'title="[^"]*"', "", normalized)
    # Sort choice options alphabetically to catch reordered duplicates
    normalized = _sort_choices(normalized)

    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _sort_choices(xml_text: str) -> str:
    """Sort <qti-simple-choice> blocks alphabetically by content.

    This ensures that items differing only in option order share
    the same fingerprint.

    Args:
        xml_text: Normalized XML string.

    Returns:
        XML with choice elements sorted.
    """
    pattern = re.compile(
        r"(<qti-simple-choice\b[^>]*>.*?</qti-simple-choice>)",
        re.DOTALL,
    )
    choices = pattern.findall(xml_text)
    if len(choices) < 2:
        return xml_text
    sorted_choices = sorted(choices)
    result = xml_text
    for original, replacement in zip(choices, sorted_choices):
        result = result.replace(original, f"__SLOT_{id(replacement)}__", 1)
    for replacement in sorted_choices:
        result = result.replace(
            f"__SLOT_{id(replacement)}__", replacement, 1,
        )
    return result


def is_skeleton_near_duplicate(
    item: GeneratedItem,
    skeleton_items: dict[str, list[str]],
    cap: int = 2,
) -> bool:
    """Check if item is a near-duplicate by skeleton repetition.

    Uses the same cap as plan validation (skeleton_repetition_cap)
    to avoid contradictory constraints between phases 3 and 5.

    Args:
        item: Item to check.
        skeleton_items: Map of skeleton -> list of existing item_ids.
        cap: Max items per skeleton (from skeleton_repetition_cap).

    Returns:
        True if the item is a near-duplicate.
    """
    if not item.pipeline_meta:
        return False
    skeleton = item.pipeline_meta.operation_skeleton_ast
    if skeleton not in skeleton_items:
        return False
    return len(skeleton_items[skeleton]) >= cap


# ---------------------------------------------------------------------------
# QTI Structural Analysis (Phase 5 near-dupe + Phase 6 exemplar)
# ---------------------------------------------------------------------------


def extract_qti_text(qti_xml: str) -> str:
    """Strip XML tags to get plain text content from QTI.

    Args:
        qti_xml: Raw QTI XML string.

    Returns:
        Plain text content with tags removed.
    """
    text = re.sub(r"<[^>]+>", " ", qti_xml)
    return re.sub(r"\s+", " ", text).strip()


def extract_qti_skeleton(qti_xml: str) -> str:
    """Extract a structural skeleton from QTI XML content.

    Replaces all numbers with 'N' and normalizes text to
    capture mathematical structure without specific values.
    Items with identical structure but different numbers will
    share the same skeleton.

    Args:
        qti_xml: Raw QTI XML string.

    Returns:
        Normalized skeleton string.
    """
    text = extract_qti_text(qti_xml)
    # Replace decimal numbers (e.g. 3.14) before integers
    skeleton = re.sub(r"\d+\.\d+", "N", text)
    # Replace remaining integers
    skeleton = re.sub(r"\d+", "N", skeleton)
    # Normalize whitespace and case
    return re.sub(r"\s+", " ", skeleton).strip().lower()


def compute_numeric_signature(qti_xml: str) -> str:
    """Extract a numeric signature from QTI XML content.

    Collects all numbers and creates a sorted hash. Items
    with the same structure but different numbers will differ.

    Args:
        qti_xml: Raw QTI XML string.

    Returns:
        Short hex hash of sorted numeric values.
    """
    text = extract_qti_text(qti_xml)
    numbers = re.findall(r"\d+\.?\d*", text)
    sorted_nums = sorted(numbers, key=float)
    signature = "|".join(sorted_nums)
    return hashlib.sha256(signature.encode("utf-8")).hexdigest()[:16]


def is_qti_structurally_similar(
    xml_a: str,
    xml_b: str,
) -> bool:
    """Check if two QTI XMLs share the same mathematical structure.

    Compares normalized skeletons where numbers are replaced
    with N. Two items are structurally similar when they differ
    only in their specific numeric values.

    Args:
        xml_a: First QTI XML.
        xml_b: Second QTI XML.

    Returns:
        True if items share the same skeleton.
    """
    return extract_qti_skeleton(xml_a) == extract_qti_skeleton(xml_b)


# ---------------------------------------------------------------------------
# Structural checks (Phase 6 / Phase 9 support)
# ---------------------------------------------------------------------------


def check_paes_structure(qti_xml: str) -> list[str]:
    """Check PAES structural compliance (4 options, 1 correct).

    Args:
        qti_xml: QTI XML to check.

    Returns:
        List of error messages (empty = passed).
    """
    errors: list[str] = []

    choices = re.findall(r"<qti-simple-choice\b", qti_xml)
    if len(choices) != 4:
        errors.append(
            f"Expected 4 options (A-D), found {len(choices)}",
        )

    if "<qti-response-declaration" not in qti_xml:
        errors.append("Missing qti-response-declaration")
    if "<qti-correct-response" not in qti_xml:
        errors.append("Missing qti-correct-response")

    return errors


def extract_correct_option(qti_xml: str) -> str | None:
    """Extract the declared correct option identifier from QTI XML.

    Looks for <qti-value> inside <qti-correct-response>.

    Args:
        qti_xml: QTI XML string.

    Returns:
        The correct option identifier (e.g. "A") or None.
    """
    match = re.search(
        r"<qti-correct-response>\s*<qti-value>([^<]+)</qti-value>",
        qti_xml,
    )
    return match.group(1).strip() if match else None


def check_exemplar_distance(
    qti_xml: str,
    exemplars: list[Exemplar],
    meta: Any | None = None,
) -> str | None:
    """Check that generated item is sufficiently far from exemplars.

    Uses distance_level from pipeline_meta to enforce thresholds:
    - "near":   reject only identical fingerprints (lenient).
    - "medium": also reject items with identical QTI skeleton.
    - "far":    also reject items with similar numeric profiles.
    - None/unset: behaves like "near" for backward compatibility.

    Args:
        qti_xml: Generated item XML.
        exemplars: Reference exemplars.
        meta: Optional PipelineMeta with distance_level.

    Returns:
        Error message if too similar, None otherwise.
    """
    item_fp = compute_fingerprint(qti_xml)
    distance_level = meta.distance_level if meta else None

    for ex in exemplars:
        ex_fp = compute_fingerprint(ex.qti_xml)

        # All levels: reject identical fingerprints
        if item_fp == ex_fp:
            return (
                f"Identical to exemplar {ex.question_id} "
                f"(distance_level={distance_level})"
            )

        # Medium + Far: reject same structural skeleton
        if distance_level in ("medium", "far"):
            if is_qti_structurally_similar(qti_xml, ex.qti_xml):
                return (
                    f"Same structure as exemplar "
                    f"{ex.question_id} "
                    f"(distance_level={distance_level})"
                )

        # Far: also reject similar numeric profile
        if distance_level == "far":
            item_sig = compute_numeric_signature(qti_xml)
            ex_sig = compute_numeric_signature(ex.qti_xml)
            if item_sig == ex_sig:
                return (
                    f"Similar numbers to exemplar "
                    f"{ex.question_id} "
                    f"(distance_level={distance_level})"
                )

    return None


def check_feedback_completeness(qti_xml: str) -> list[str]:
    """Check that enriched QTI contains required feedback elements.

    Expected structure (from feedback enhancement prompt):
    - 4 x qti-feedback-inline (one per option A-D)
    - 1 x qti-feedback-block  (step-by-step solution)

    Args:
        qti_xml: Enriched QTI XML.

    Returns:
        List of error messages (empty = complete).
    """
    errors: list[str] = []
    xml_lower = qti_xml.lower()

    # Check per-option inline feedback (expect 4, one per A-D)
    inline_count = len(re.findall(
        r"<qti-feedback-inline\b", xml_lower,
    ))
    if inline_count < 4:
        errors.append(
            f"Expected 4 qti-feedback-inline elements "
            f"(one per option), found {inline_count}",
        )

    # Check step-by-step solution block
    if "<qti-feedback-block" not in xml_lower:
        errors.append(
            "Missing qti-feedback-block (step-by-step solution)",
        )

    return errors
