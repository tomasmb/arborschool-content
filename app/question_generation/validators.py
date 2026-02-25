"""Phases 5, 6, 9 — Validation and Deduplication.

- Phase 5: Deterministic duplicate gate (fingerprinting + near-duplicate)
- Phase 6: Base validation (XSD, solvability, scope, exemplar non-copy)
- Phase 9: Final validation (re-run all checks on enriched items)

All phases are MANDATORY and BLOCKING.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.llm_clients import OpenAIClient
from app.question_feedback.utils.image_utils import extract_image_urls
from app.question_feedback.validator import (
    FinalValidator as LlmFinalValidator,
)
from app.question_generation.models import (
    Exemplar,
    GeneratedItem,
    PhaseResult,
)
from app.question_generation.planner import skeleton_repetition_cap
from app.question_generation.progress import report_progress
from app.question_generation.prompts.validation import (
    build_solvability_prompt,
)
from app.question_generation.validation_checks import (
    check_feedback_completeness,
    compute_fingerprint,
    extract_correct_option,
    extract_qti_skeleton,
    is_skeleton_near_duplicate,
    normalize_option_letter,
    run_deterministic_checks,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Phase 5 — Deterministic Duplicate Gate
# ---------------------------------------------------------------------------


class DuplicateGate:
    """Detects duplicate and near-duplicate items (Phase 5).

    SHA-256 fingerprinting + structural skeleton comparison.
    """

    def run(
        self,
        items: list[GeneratedItem],
        existing_fingerprints: set[str] | None = None,
        pool_total: int | None = None,
    ) -> PhaseResult:
        """Run dedupe on *items* against existing inventory + batch."""
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


# LLM reasoning depth for solvability check (medium = sufficient
# for solving high-school level multiple-choice math)
_SOLVABILITY_REASONING = "medium"

# Max parallel LLM calls for solvability checks
_MAX_PARALLEL_VALIDATION = 15


class BaseValidator:
    """Validates base QTI items before feedback enrichment (Phase 6).

    Checks: XSD, solvability (LLM), PAES structure, scope,
    exemplar distance.
    """

    def __init__(self, client: OpenAIClient) -> None:
        self._client = client

    def validate(
        self,
        items: list[GeneratedItem],
        exemplars: list[Exemplar] | None = None,
    ) -> PhaseResult:
        """Validate all items in parallel (solvability is LLM)."""
        total = len(items)
        logger.info(
            "Phase 6: Validating %d base items (parallel=%d)",
            total, _MAX_PARALLEL_VALIDATION,
        )

        passed: list[GeneratedItem] = []
        errors: list[str] = []
        completed = 0
        report_progress(0, total)

        with ThreadPoolExecutor(
            max_workers=_MAX_PARALLEL_VALIDATION,
        ) as pool:
            futures = {
                pool.submit(
                    self._validate_single, item, exemplars,
                ): item
                for item in items
            }

            for future in as_completed(futures):
                item = futures[future]
                item_errors = future.result()
                completed += 1
                if item_errors:
                    errors.extend(item_errors)
                    logger.warning(
                        "Item %s failed validation: %s",
                        item.item_id, item_errors,
                    )
                else:
                    passed.append(item)
                report_progress(completed, total)

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
        """LLM-solve the question, compare normalized answer to declared."""
        prompt = build_solvability_prompt(item.qti_xml)
        try:
            llm_resp = self._client.generate_text(
                prompt,
                response_mime_type="application/json",
                reasoning_effort=_SOLVABILITY_REASONING,
            )
            result = json.loads(llm_resp.text)
            raw_answer = result.get("answer", "").strip()
        except Exception as exc:
            logger.warning(
                "Solvability LLM call failed for %s: %s",
                item.item_id, exc,
            )
            return f"Solvability check LLM error: {exc}"

        model_letter = normalize_option_letter(raw_answer)
        if not model_letter:
            return (
                f"Solvability check: could not parse model "
                f"answer '{raw_answer}' into A-D"
            )

        declared = extract_correct_option(item.qti_xml)
        if not declared:
            return (
                "Could not extract declared correct option "
                "from QTI XML (missing qti-correct-response?)"
            )

        if model_letter != declared:
            steps = result.get("steps", "no steps provided")
            return (
                f"Solvability mismatch: model={model_letter}, "
                f"declared={declared} — {steps}"
            )

        logger.debug(
            "Solvability OK: %s → %s", item.item_id, model_letter,
        )
        return None

    def _validate_single(
        self,
        item: GeneratedItem,
        exemplars: list[Exemplar] | None,
        *,
        skip_solvability: bool = False,
    ) -> list[str]:
        """Run all checks on a single item. Returns errors (empty=pass)."""
        reports = (
            item.pipeline_meta.validators if item.pipeline_meta else None
        )

        # Deterministic checks (shared with batch pipeline)
        errors = run_deterministic_checks(
            item.qti_xml, item.item_id,
            exemplars=exemplars, meta=item.pipeline_meta,
        )

        # Update per-check report flags from the error strings
        if reports:
            has = lambda tag: any(tag in e for e in errors)  # noqa: E731
            if "IMAGE_PLACEHOLDER" in item.qti_xml:
                return errors  # fatal — no further reports
            reports.xsd = "fail" if has("XSD invalid") else "pass"
            reports.paes = (
                "fail" if has("options (A-D)")
                or has("Missing qti-") else "pass"
            )

        # Solvability (LLM-based) — skipped in Phase 9
        if not skip_solvability:
            solve_err = self._check_solvability(item)
            if solve_err:
                errors.append(f"{item.item_id}: {solve_err}")
                if reports:
                    reports.solve_check = "fail"
            elif reports:
                reports.solve_check = "pass"

        # Update exemplar report flag
        if reports:
            has_copy = any("exemplar" in e.lower() for e in errors)
            reports.exemplar_copy_check = (
                "fail" if has_copy else "pass"
            )
            reports.scope = "pass"

        return errors


# ---------------------------------------------------------------------------
# Phase 9 — Final Validation
# ---------------------------------------------------------------------------

# Max parallel LLM calls for final comprehensive validation
_MAX_PARALLEL_FINAL = 15


class FinalValidator:
    """Final validation on enriched items (Phase 9).

    Stage 1: fast deterministic checks (XSD, PAES, feedback).
    Stage 2: parallel LLM validation (re-solve + quality).
    """

    def __init__(self, client: OpenAIClient) -> None:
        self._client = client
        self._base_validator = BaseValidator(client)
        self._llm_validator = LlmFinalValidator(client=client)

    def validate(
        self,
        items: list[GeneratedItem],
        exemplars: list[Exemplar] | None = None,
    ) -> PhaseResult:
        """Run deterministic + LLM validation on enriched items."""
        total = len(items)
        logger.info("Phase 9: Final validation on %d items", total)

        # Stage 1: Deterministic checks (fast, sequential)
        deterministic_passed: list[GeneratedItem] = []
        errors: list[str] = []
        completed = 0
        report_progress(0, total)

        for item in items:
            item_errors = self._validate_deterministic(
                item, exemplars,
            )
            completed += 1
            if item_errors:
                errors.extend(item_errors)
            else:
                if item.pipeline_meta:
                    item.pipeline_meta.validators.feedback = "pass"
                deterministic_passed.append(item)
            report_progress(completed, total)

        logger.info(
            "Final validation deterministic: %d/%d passed",
            len(deterministic_passed), len(items),
        )

        if not deterministic_passed:
            return PhaseResult(
                phase_name="final_validation",
                success=False,
                data={"final_items": []},
                errors=errors,
            )

        # Stage 2: Comprehensive LLM validation (parallel)
        # Reset progress for LLM stage with new total
        llm_total = len(deterministic_passed)
        llm_completed = 0
        passed: list[GeneratedItem] = []
        report_progress(0, llm_total)

        with ThreadPoolExecutor(
            max_workers=_MAX_PARALLEL_FINAL,
        ) as pool:
            futures = {
                pool.submit(
                    self._llm_validate_item, item,
                ): item
                for item in deterministic_passed
            }

            for future in as_completed(futures):
                item = futures[future]
                llm_error = future.result()
                llm_completed += 1
                if llm_error:
                    errors.append(llm_error)
                    logger.warning(
                        "Item %s failed LLM validation: %s",
                        item.item_id, llm_error,
                    )
                else:
                    passed.append(item)
                report_progress(llm_completed, llm_total)

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

    def _validate_deterministic(
        self,
        item: GeneratedItem,
        exemplars: list[Exemplar] | None,
    ) -> list[str]:
        """Run fast deterministic checks on a single enriched item.

        Skips solvability: the stem and correct answer are unchanged
        since Phase 6, so re-solving is redundant (the LLM stage
        below re-checks anyway).
        """
        errors = self._base_validator._validate_single(
            item, exemplars, skip_solvability=True,
        )

        feedback_errors = check_feedback_completeness(item.qti_xml)
        errors.extend(f"{item.item_id}: {e}" for e in feedback_errors)

        return errors

    def _llm_validate_item(
        self, item: GeneratedItem,
    ) -> str | None:
        """LLM re-solve + quality check. Returns error or None."""
        reports = (
            item.pipeline_meta.validators
            if item.pipeline_meta else None
        )

        image_urls = extract_image_urls(item.qti_xml) or None

        try:
            result = self._llm_validator.validate(
                item.qti_xml, image_urls=image_urls,
            )
        except Exception as exc:
            logger.warning(
                "LLM final validation error for %s: %s",
                item.item_id, exc,
            )
            if reports:
                reports.final_llm_check = "fail"
            return (
                f"{item.item_id}: LLM final validation error "
                f"— {exc}"
            )

        if result.validation_result == "pass":
            if reports:
                reports.final_llm_check = "pass"
            return None

        if reports:
            reports.final_llm_check = "fail"
        return (
            f"{item.item_id}: LLM final validation failed "
            f"— {result.overall_reasoning}"
        )
