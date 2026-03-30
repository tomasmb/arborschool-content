"""Batch response processors for the variant pipeline.

Each processor takes raw BatchResponse lists and converts them into
domain objects, reusing the same parsing functions used by the sync path.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.question_feedback.final_validation_parser import (
    parse_final_validation_payload,
)
from app.question_feedback.models import ValidationResult as FinalValidationResult
from app.question_generation.batch_api import BatchResponse
from app.question_variants.batch_request_builders import (
    parse_variant_custom_id,
)
from app.question_variants.contracts.structural_profile import (
    build_construct_contract,
)
from app.question_variants.models import (
    SourceQuestion,
    ValidationResult,
    ValidationVerdict,
    VariantBlueprint,
    VariantQuestion,
)
from app.question_variants.postprocess.generation_parsing import (
    parse_generation_response,
)
from app.question_variants.generation_prompt import build_variant_metadata
from app.question_variants.variant_planner import parse_planning_response
from app.question_variants.variant_solvability import parse_solvability_response
from app.question_variants.variant_validator import parse_validation_json

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Phase 1 -- Planning
# ------------------------------------------------------------------


def process_plan_responses(
    responses: list[BatchResponse],
    sources_by_key: dict[str, SourceQuestion],
) -> dict[str, list[VariantBlueprint]]:
    """Parse planning batch responses into blueprints per question.

    Args:
        responses: Raw batch responses from phase 1.
        sources_by_key: Mapping of "{test_id}__{question_id}" to source.

    Returns:
        Dict mapping "{test_id}__{question_id}" to list of blueprints.
    """
    results: dict[str, list[VariantBlueprint]] = {}
    for resp in responses:
        parsed = parse_variant_custom_id(resp.custom_id)
        key = f"{parsed.get('test_id', '')}__{parsed.get('question_id', '')}"
        source = sources_by_key.get(key)

        if resp.error:
            logger.warning("Plan error for %s: %s", key, resp.error)
            results[key] = []
            continue

        contract = None
        if source:
            contract = build_construct_contract(
                source.question_text,
                source.qti_xml,
                bool(source.image_urls),
                source.primary_atoms,
                source.metadata,
                source.choices,
                source.correct_answer,
            )

        blueprints = parse_planning_response(
            resp.text, construct_contract=contract,
        )
        results[key] = blueprints
        logger.info(
            "Phase 1 parsed %d blueprints for %s", len(blueprints), key,
        )
    return results


# ------------------------------------------------------------------
# Phase 2 -- Generation
# ------------------------------------------------------------------


def process_generation_responses(
    responses: list[BatchResponse],
    sources_by_key: dict[str, SourceQuestion],
    blueprints_by_key: dict[str, list[VariantBlueprint]],
) -> list[VariantQuestion]:
    """Parse generation batch responses into VariantQuestion objects.

    Args:
        responses: Raw batch responses from phase 2.
        sources_by_key: Mapping of "{test_id}__{question_id}" to source.
        blueprints_by_key: Mapping of "{test_id}__{question_id}" to
            blueprints list, used to match variant_id -> blueprint.

    Returns:
        List of VariantQuestion objects (unvalidated).
    """
    variants: list[VariantQuestion] = []
    for resp in responses:
        parsed = parse_variant_custom_id(resp.custom_id)
        key = f"{parsed.get('test_id', '')}__{parsed.get('question_id', '')}"
        variant_id = parsed.get("variant_id", "")
        source = sources_by_key.get(key)

        if resp.error or not source:
            logger.warning(
                "Gen error for %s/%s: %s",
                key, variant_id, resp.error or "source not found",
            )
            continue

        parsed_data = parse_generation_response(resp.text)
        if not parsed_data:
            logger.warning("Gen parse failed for %s/%s", key, variant_id)
            continue

        blueprint = _find_blueprint(
            blueprints_by_key.get(key, []), variant_id,
        )
        vdata = parsed_data[0]
        variants.append(
            VariantQuestion(
                variant_id=variant_id or vdata.get("variant_id", ""),
                source_question_id=source.question_id,
                source_test_id=source.test_id,
                qti_xml=vdata.get("qti_xml", ""),
                metadata=build_variant_metadata(source, vdata, blueprint),
            )
        )

    logger.info("Phase 2 parsed %d variants total", len(variants))
    return variants


# ------------------------------------------------------------------
# Phase 4 -- Validation
# ------------------------------------------------------------------


def process_validation_responses(
    responses: list[BatchResponse],
) -> dict[str, ValidationResult]:
    """Parse validation batch responses into ValidationResults.

    Args:
        responses: Raw batch responses from phase 4.

    Returns:
        Dict mapping variant_id to ValidationResult.
    """
    results: dict[str, ValidationResult] = {}
    for resp in responses:
        parsed = parse_variant_custom_id(resp.custom_id)
        variant_id = parsed.get("variant_id", resp.custom_id)

        if resp.error:
            logger.warning("Val error for %s: %s", variant_id, resp.error)
            results[variant_id] = ValidationResult(
                verdict=ValidationVerdict.REJECTED,
                concept_aligned=False,
                difficulty_equal=True,
                answer_correct=False,
                rejection_reason=f"Batch API error: {resp.error}",
            )
            continue

        results[variant_id] = parse_validation_json(resp.text)

    approved = sum(1 for r in results.values() if r.is_approved)
    logger.info(
        "Phase 4 parsed %d results: %d approved, %d rejected",
        len(results), approved, len(results) - approved,
    )
    return results


# ------------------------------------------------------------------
# Phase 5 -- Solvability
# ------------------------------------------------------------------


def process_solvability_responses(
    responses: list[BatchResponse],
    variants_by_id: dict[str, VariantQuestion],
) -> dict[str, tuple[bool, str]]:
    """Parse solvability batch responses.

    Returns a dict mapping variant_id to (passed, reason).
    """
    results: dict[str, tuple[bool, str]] = {}
    for resp in responses:
        parsed = parse_variant_custom_id(resp.custom_id)
        variant_id = parsed.get("variant_id", resp.custom_id)
        variant = variants_by_id.get(variant_id)

        if resp.error or not variant:
            reason = resp.error or "variant not found"
            logger.warning("Solve error for %s: %s", variant_id, reason)
            results[variant_id] = (False, f"Batch API error: {reason}")
            continue

        results[variant_id] = parse_solvability_response(
            resp.text, variant,
        )

    passed = sum(1 for ok, _ in results.values() if ok)
    logger.info(
        "Phase 5 parsed %d results: %d passed, %d failed",
        len(results), passed, len(results) - passed,
    )
    return results


# ------------------------------------------------------------------
# Phase 7 -- Final Validation
# ------------------------------------------------------------------


def process_final_validation_responses(
    responses: list[BatchResponse],
) -> dict[str, FinalValidationResult]:
    """Parse final-validation batch responses.

    Returns a dict mapping variant_id to a ``FinalValidationResult``
    (from ``app.question_feedback.models``).
    """
    results: dict[str, FinalValidationResult] = {}
    for resp in responses:
        parsed = parse_variant_custom_id(resp.custom_id)
        variant_id = parsed.get("variant_id", resp.custom_id)

        if resp.error:
            logger.warning(
                "Final-val error for %s: %s", variant_id, resp.error,
            )
            results[variant_id] = _error_final_result(resp.error)
            continue

        try:
            payload = json.loads(resp.text)
            results[variant_id] = parse_final_validation_payload(payload)
        except (json.JSONDecodeError, Exception) as exc:
            logger.warning(
                "Final-val parse error for %s: %s", variant_id, exc,
            )
            results[variant_id] = _error_final_result(str(exc))

    passed = sum(
        1 for r in results.values()
        if r.validation_result == "pass"
    )
    logger.info(
        "Phase 7 parsed %d results: %d passed, %d failed",
        len(results), passed, len(results) - passed,
    )
    return results


def _error_final_result(error: str) -> FinalValidationResult:
    """Build an error FinalValidationResult."""
    from app.question_feedback.models import (
        CheckResult,
        CheckStatus,
        ContentQualityCheck,
        CorrectAnswerCheck,
    )
    fail_check = CheckResult(
        status=CheckStatus.FAIL, issues=[error], reasoning=error,
    )
    return FinalValidationResult(
        validation_result="fail",
        correct_answer_check=CorrectAnswerCheck(
            status=CheckStatus.FAIL,
            expected_answer="", marked_answer="",
            verification_steps="", issues=[error],
        ),
        feedback_check=fail_check,
        content_quality_check=ContentQualityCheck(
            status=CheckStatus.FAIL,
        ),
        image_check=CheckResult(
            status=CheckStatus.NOT_APPLICABLE,
            issues=[], reasoning="Skipped due to error",
        ),
        math_validity_check=fail_check,
        overall_reasoning=f"Validation failed: {error}",
    )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _find_blueprint(
    blueprints: list[VariantBlueprint],
    variant_id: str,
) -> VariantBlueprint | None:
    """Find the blueprint matching a variant_id."""
    for bp in blueprints:
        if bp.variant_id == variant_id:
            return bp
    return None
