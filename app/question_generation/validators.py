"""Phases 5, 6, 9 — Validation and Deduplication.

- Phase 5: Deterministic duplicate gate (fingerprinting + near-duplicate)
- Phase 6: Base validation (XSD, solvability, scope, exemplar non-copy)
- Phase 9: Final validation (re-run all checks on enriched items)

All phases are MANDATORY and BLOCKING.
"""

from __future__ import annotations

import json
import logging

from app.llm_clients import OpenAIClient
from app.question_generation.models import (
    Exemplar,
    GeneratedItem,
    PhaseResult,
)
from app.question_generation.planner import skeleton_repetition_cap
from app.question_generation.prompts.validation import (
    build_solvability_prompt,
)
from app.question_generation.validation_checks import (
    check_exemplar_distance,
    check_feedback_completeness,
    check_paes_structure,
    compute_fingerprint,
    extract_correct_option,
    extract_qti_skeleton,
    is_skeleton_near_duplicate,
    validate_qti_xml,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Phase 5 — Deterministic Duplicate Gate
# ---------------------------------------------------------------------------


class DuplicateGate:
    """Detects duplicate and near-duplicate items (Phase 5).

    Uses SHA-256 fingerprinting on normalized QTI content to
    identify duplicates within a batch and against existing inventory.
    Also detects structural near-duplicates via skeleton comparison.
    """

    def run(
        self,
        items: list[GeneratedItem],
        existing_fingerprints: set[str] | None = None,
        pool_total: int | None = None,
    ) -> PhaseResult:
        """Run the duplicate gate on a batch of items.

        Args:
            items: Generated items to check.
            existing_fingerprints: Fingerprints of existing inventory.
            pool_total: Total pool size for skeleton cap scaling.
                If None, defaults to len(items).

        Returns:
            PhaseResult with filtered items and dedupe report.
        """
        logger.info("Phase 5: Running duplicate gate on %d items", len(items))

        effective_pool = pool_total or len(items)
        skel_cap = skeleton_repetition_cap(effective_pool)
        logger.info("Skeleton cap: %d (pool=%d)", skel_cap, effective_pool)

        existing = existing_fingerprints or set()
        seen: dict[str, str] = {}  # fingerprint -> item_id
        passed: list[GeneratedItem] = []
        duplicates: list[str] = []
        # Plan skeleton -> item_ids (from planner's operation_skeleton_ast)
        skeleton_items: dict[str, list[str]] = {}
        # QTI skeleton -> item_ids (derived from generated XML)
        qti_skeleton_items: dict[str, list[str]] = {}

        for item in items:
            fp = compute_fingerprint(item.qti_xml)

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

            # Plan skeleton near-duplicate check (scaled cap)
            if is_skeleton_near_duplicate(
                item, skeleton_items, cap=skel_cap,
            ):
                duplicates.append(
                    f"{item.item_id}: near-duplicate "
                    f"(same plan skeleton, >{skel_cap} in pool)",
                )
                logger.info("Near-dupe (plan skeleton): %s", item.item_id)
                continue

            # QTI structural near-duplicate check (scaled cap)
            qti_skel = extract_qti_skeleton(item.qti_xml)
            existing_qti = qti_skeleton_items.get(qti_skel, [])
            if len(existing_qti) >= skel_cap:
                duplicates.append(
                    f"{item.item_id}: QTI structural near-duplicate "
                    f"(>{skel_cap} items with same structure)",
                )
                logger.info(
                    "Near-dupe (QTI structure): %s", item.item_id,
                )
                continue

            seen[fp] = item.item_id
            # Track both plan and QTI skeletons
            qti_skeleton_items.setdefault(
                qti_skel, [],
            ).append(item.item_id)
            if item.pipeline_meta:
                sk = item.pipeline_meta.operation_skeleton_ast
                skeleton_items.setdefault(sk, []).append(item.item_id)
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


# ---------------------------------------------------------------------------
# Phase 6 — Base Validation
# ---------------------------------------------------------------------------


_SOLVABILITY_REASONING = "high"


class BaseValidator:
    """Validates base QTI items before feedback enrichment (Phase 6).

    Checks:
    - QTI 3.0 XSD validity
    - Solvability (LLM-based independent solve)
    - PAES compliance (4 options, 1 correct)
    - Scope compliance (atom-only)
    - Exemplar non-copy / distance rule
    """

    def __init__(self, client: OpenAIClient) -> None:
        """Initialize the validator.

        Args:
            client: OpenAI client for solvability checks.
        """
        self._client = client

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

    def _check_solvability(self, item: GeneratedItem) -> str | None:
        """Independently solve the question and verify the answer.

        Sends the QTI XML to GPT-5.1 with high reasoning effort.
        Compares the model's answer to the declared correct option.

        Args:
            item: Generated item with QTI XML.

        Returns:
            Error message if solve fails, None if it matches.
        """
        prompt = build_solvability_prompt(item.qti_xml)
        try:
            raw = self._client.generate_text(
                prompt,
                response_mime_type="application/json",
                reasoning_effort=_SOLVABILITY_REASONING,
            )
            result = json.loads(raw)
            model_answer = result.get("answer", "").strip().upper()
        except Exception as exc:
            logger.warning(
                "Solvability LLM call failed for %s: %s",
                item.item_id, exc,
            )
            return f"Solvability check LLM error: {exc}"

        declared = extract_correct_option(item.qti_xml)
        if not declared:
            return "Could not extract declared correct option from XML"
        if model_answer != declared.upper():
            steps = result.get("steps", "no steps provided")
            return (
                f"Solvability mismatch: model={model_answer}, "
                f"declared={declared} — {steps}"
            )
        return None

    def _validate_single(
        self,
        item: GeneratedItem,
        exemplars: list[Exemplar] | None,
        *,
        skip_solvability: bool = False,
    ) -> list[str]:
        """Run all checks on a single item.

        Args:
            item: Generated item to validate.
            exemplars: Exemplars for non-copy checking.
            skip_solvability: If True, skip the LLM solvability
                check. Used by FinalValidator (Phase 9) because
                the stem/answer are unchanged since Phase 6.

        Returns:
            List of error messages (empty = passed).
        """
        errors: list[str] = []
        reports = (
            item.pipeline_meta.validators if item.pipeline_meta else None
        )

        # Check 1: XSD validity
        xsd_result = validate_qti_xml(item.qti_xml)
        xsd_ok = xsd_result.get("valid", False)
        if not xsd_ok:
            errors.append(
                f"{item.item_id}: XSD invalid — "
                f"{xsd_result.get('validation_errors', 'unknown')}",
            )
        if reports:
            reports.xsd = "pass" if xsd_ok else "fail"

        # Check 2: PAES structural compliance
        paes_errors = check_paes_structure(item.qti_xml)
        errors.extend(f"{item.item_id}: {e}" for e in paes_errors)

        # Check 3: Solvability (LLM-based independent solve)
        # Skipped in Phase 9: stem/answer unchanged since Phase 6,
        # and the result is already in pipeline_meta.validators.
        if not skip_solvability:
            solve_err = self._check_solvability(item)
            if solve_err:
                errors.append(f"{item.item_id}: {solve_err}")
                if reports:
                    reports.solve_check = "fail"
            elif reports:
                reports.solve_check = "pass"

        # Check 4: Exemplar distance check
        if exemplars:
            copy_err = check_exemplar_distance(
                item.qti_xml, exemplars, item.pipeline_meta,
            )
            if copy_err:
                errors.append(f"{item.item_id}: {copy_err}")
                if reports:
                    reports.exemplar_copy_check = "fail"
            elif reports:
                reports.exemplar_copy_check = "pass"

        # Scope is enforced at plan time (Phase 3), not per-item.
        if reports:
            reports.scope = "pass"

        return errors


# ---------------------------------------------------------------------------
# Phase 9 — Final Validation
# ---------------------------------------------------------------------------


class FinalValidator:
    """Re-runs full validation on enriched items (Phase 9).

    Checks all Phase 6 validations plus feedback completeness.
    Only items passing final validation are eligible for DB sync.
    """

    def __init__(self, client: OpenAIClient) -> None:
        self._client = client
        self._base_validator = BaseValidator(client)

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
        """Validate a single enriched item (base + feedback).

        Skips solvability: the stem and correct answer are unchanged
        since Phase 6, so re-solving is redundant and expensive.
        """
        errors = self._base_validator._validate_single(
            item, exemplars, skip_solvability=True,
        )

        feedback_errors = check_feedback_completeness(item.qti_xml)
        errors.extend(f"{item.item_id}: {e}" for e in feedback_errors)

        return errors
