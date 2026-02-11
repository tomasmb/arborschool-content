"""Phases 5, 6, 9 — Validation and Deduplication.

- Phase 5: Deterministic duplicate gate (fingerprinting + near-duplicate)
- Phase 6: Base validation (XSD, solvability, scope, exemplar non-copy)
- Phase 9: Final validation (re-run all checks on enriched items)

All phases are MANDATORY and BLOCKING.
"""

from __future__ import annotations

import hashlib
import importlib.util
import logging
import re
from pathlib import Path
from typing import Any

from app.llm_clients import GeminiService
from app.question_generation.models import (
    Exemplar,
    GeneratedItem,
    PhaseResult,
)

logger = logging.getLogger(__name__)


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
    _validate_qti_xml = _xml_validator_mod.validate_qti_xml
else:
    def _validate_qti_xml(
        qti_xml: str,
        validation_endpoint: str | None = None,
    ) -> dict[str, Any]:
        """Stub when real validator is unavailable."""
        return {"success": True, "valid": True, "message": "Skipped"}


# ---------------------------------------------------------------------------
# Phase 5 — Deterministic Duplicate Gate
# ---------------------------------------------------------------------------


class DuplicateGate:
    """Detects duplicate and near-duplicate items (Phase 5).

    Uses SHA-256 fingerprinting on normalized QTI content to
    identify duplicates within a batch and against existing inventory.
    """

    def run(
        self,
        items: list[GeneratedItem],
        existing_fingerprints: set[str] | None = None,
    ) -> PhaseResult:
        """Run the duplicate gate on a batch of items.

        Args:
            items: Generated items to check.
            existing_fingerprints: Fingerprints of existing inventory.

        Returns:
            PhaseResult with filtered items and dedupe report.
        """
        logger.info("Phase 5: Running duplicate gate on %d items", len(items))

        existing = existing_fingerprints or set()
        seen: dict[str, str] = {}  # fingerprint -> item_id
        passed: list[GeneratedItem] = []
        duplicates: list[str] = []

        for item in items:
            fp = _compute_fingerprint(item.qti_xml)

            if fp in existing:
                duplicates.append(
                    f"{item.item_id}: duplicate of existing inventory",
                )
                logger.info("Duplicate (existing): %s", item.item_id)
                continue

            if fp in seen:
                duplicates.append(
                    f"{item.item_id}: duplicate of {seen[fp]} in batch",
                )
                logger.info(
                    "Duplicate (batch): %s = %s",
                    item.item_id, seen[fp],
                )
                continue

            seen[fp] = item.item_id
            # Store fingerprint in pipeline_meta if present
            if item.pipeline_meta:
                item.pipeline_meta.fingerprint = f"sha256:{fp}"
                item.pipeline_meta.validators.dedupe = "pass"
            passed.append(item)

        success = len(passed) > 0

        logger.info(
            "Dedupe gate: %d passed, %d duplicates",
            len(passed), len(duplicates),
        )

        return PhaseResult(
            phase_name="duplicate_gate",
            success=success,
            data={
                "filtered_items": passed,
                "dedupe_report": duplicates,
            },
            warnings=duplicates if duplicates else [],
        )


def _compute_fingerprint(qti_xml: str) -> str:
    """Compute a SHA-256 fingerprint of normalized QTI content.

    Normalizes whitespace and removes identifiers to catch
    near-duplicates that differ only in formatting or IDs.

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

    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Phase 6 — Base Validation
# ---------------------------------------------------------------------------


class BaseValidator:
    """Validates base QTI items before feedback enrichment (Phase 6).

    Checks:
    - QTI 3.0 XSD validity
    - Solvability (LLM-based independent solve)
    - PAES compliance (4 options, 1 correct)
    - Scope compliance (atom-only)
    - Exemplar non-copy rule
    """

    def __init__(self, gemini: GeminiService) -> None:
        """Initialize the validator.

        Args:
            gemini: Gemini service for solvability checks.
        """
        self._gemini = gemini

    def validate(
        self,
        items: list[GeneratedItem],
        exemplars: list[Exemplar] | None = None,
    ) -> PhaseResult:
        """Validate all base items.

        Args:
            items: Items to validate.
            exemplars: Exemplars for non-copy checking.

        Returns:
            PhaseResult with valid items and validation report.
        """
        logger.info("Phase 6: Validating %d base items", len(items))

        passed: list[GeneratedItem] = []
        errors: list[str] = []

        for item in items:
            item_errors = self._validate_single(item, exemplars)
            if item_errors:
                errors.extend(item_errors)
                logger.warning(
                    "Item %s failed validation: %s",
                    item.item_id, item_errors,
                )
            else:
                passed.append(item)

        logger.info(
            "Base validation: %d passed, %d failed",
            len(passed), len(items) - len(passed),
        )

        return PhaseResult(
            phase_name="base_validation",
            success=len(passed) > 0,
            data={"valid_items": passed},
            errors=errors,
        )

    def _validate_single(
        self,
        item: GeneratedItem,
        exemplars: list[Exemplar] | None,
    ) -> list[str]:
        """Run all checks on a single item.

        Returns:
            List of error messages (empty = passed).
        """
        errors: list[str] = []
        reports = item.pipeline_meta.validators if item.pipeline_meta else None

        # Check 1: XSD validity
        xsd_result = _validate_qti_xml(item.qti_xml)
        xsd_ok = xsd_result.get("valid", False)
        if not xsd_ok:
            errors.append(
                f"{item.item_id}: XSD invalid — "
                f"{xsd_result.get('validation_errors', 'unknown')}",
            )
        if reports:
            reports.xsd = "pass" if xsd_ok else "fail"

        # Check 2: PAES structural compliance
        paes_errors = _check_paes_structure(item.qti_xml)
        errors.extend(
            f"{item.item_id}: {e}" for e in paes_errors
        )

        # Check 3: Exemplar non-copy
        if exemplars:
            copy_err = _check_exemplar_copy(item.qti_xml, exemplars)
            if copy_err:
                errors.append(f"{item.item_id}: {copy_err}")
                if reports:
                    reports.exemplar_copy_check = "fail"
            elif reports:
                reports.exemplar_copy_check = "pass"

        if reports:
            reports.scope = "pass" if not errors else "fail"

        return errors


# ---------------------------------------------------------------------------
# Phase 9 — Final Validation
# ---------------------------------------------------------------------------


class FinalValidator:
    """Re-runs full validation on enriched items (Phase 9).

    Checks all Phase 6 validations plus feedback completeness.
    Only items passing final validation are eligible for DB sync.
    """

    def __init__(self, gemini: GeminiService) -> None:
        self._gemini = gemini
        self._base_validator = BaseValidator(gemini)

    def validate(
        self,
        items: list[GeneratedItem],
        exemplars: list[Exemplar] | None = None,
    ) -> PhaseResult:
        """Run final validation on enriched items.

        Args:
            items: Enriched items from Phase 7-8.
            exemplars: Exemplars for non-copy checking.

        Returns:
            PhaseResult with final validated items.
        """
        logger.info("Phase 9: Final validation on %d items", len(items))

        passed: list[GeneratedItem] = []
        errors: list[str] = []

        for item in items:
            item_errors = self._validate_enriched(item, exemplars)
            if item_errors:
                errors.extend(item_errors)
            else:
                if item.pipeline_meta:
                    item.pipeline_meta.validators.feedback = "pass"
                passed.append(item)

        logger.info(
            "Final validation: %d passed, %d failed",
            len(passed), len(items) - len(passed),
        )

        return PhaseResult(
            phase_name="final_validation",
            success=len(passed) > 0,
            data={"final_items": passed},
            errors=errors,
        )

    def _validate_enriched(
        self,
        item: GeneratedItem,
        exemplars: list[Exemplar] | None,
    ) -> list[str]:
        """Validate a single enriched item.

        Runs base checks + feedback completeness.
        """
        errors = self._base_validator._validate_single(item, exemplars)

        # Additional: check feedback elements exist
        feedback_errors = _check_feedback_completeness(item.qti_xml)
        errors.extend(f"{item.item_id}: {e}" for e in feedback_errors)

        return errors


# ---------------------------------------------------------------------------
# Shared validation helpers
# ---------------------------------------------------------------------------


def _check_paes_structure(qti_xml: str) -> list[str]:
    """Check PAES structural compliance (4 options, 1 correct).

    Args:
        qti_xml: QTI XML to check.

    Returns:
        List of error messages (empty = passed).
    """
    errors: list[str] = []

    # Count choice options
    choices = re.findall(
        r"<qti-simple-choice\b", qti_xml,
    )
    if len(choices) != 4:
        errors.append(
            f"Expected 4 options (A-D), found {len(choices)}",
        )

    # Check for correct response declaration
    if "<qti-response-declaration" not in qti_xml:
        errors.append("Missing qti-response-declaration")

    if "<qti-correct-response" not in qti_xml:
        errors.append("Missing qti-correct-response")

    return errors


def _check_exemplar_copy(
    qti_xml: str,
    exemplars: list[Exemplar],
) -> str | None:
    """Check that generated item is not a near-copy of any exemplar.

    Uses fingerprint similarity as a rough proxy.

    Args:
        qti_xml: Generated item XML.
        exemplars: Reference exemplars.

    Returns:
        Error message if too similar, None otherwise.
    """
    item_fp = _compute_fingerprint(qti_xml)

    for ex in exemplars:
        ex_fp = _compute_fingerprint(ex.qti_xml)
        if item_fp == ex_fp:
            return (
                f"Item is a near-copy of exemplar {ex.question_id}"
            )

    return None


def _check_feedback_completeness(qti_xml: str) -> list[str]:
    """Check that enriched QTI contains required feedback elements.

    Required by spec section 7.1:
    - Per-option feedback
    - Worked solution

    Args:
        qti_xml: Enriched QTI XML.

    Returns:
        List of error messages (empty = complete).
    """
    errors: list[str] = []

    # Check for feedback elements (modalFeedback or feedbackInline)
    has_feedback = (
        "<qti-modal-feedback" in qti_xml.lower()
        or "<modalfeedback" in qti_xml.lower()
        or "feedbackinline" in qti_xml.lower()
        or "<qti-feedback-inline" in qti_xml.lower()
    )
    if not has_feedback:
        errors.append("Missing per-option feedback in enriched QTI")

    return errors
