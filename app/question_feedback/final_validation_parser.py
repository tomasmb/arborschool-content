"""Shared parser for final-validation LLM JSON payloads."""

from __future__ import annotations

import logging
from typing import Any

from app.question_feedback.models import (
    CheckResult,
    CheckStatus,
    ContentQualityCheck,
    CorrectAnswerCheck,
    ValidationResult,
)

logger = logging.getLogger(__name__)


def parse_final_validation_payload(
    payload: dict[str, Any],
) -> ValidationResult:
    """Parse and normalize a final-validation payload from the LLM."""
    ca_check = payload.get("correct_answer_check", {})
    correct_answer_check = CorrectAnswerCheck(
        status=_coerce_status(ca_check.get("status", "fail")),
        expected_answer=ca_check.get("expected_answer", ""),
        marked_answer=ca_check.get("marked_answer", ""),
        verification_steps=ca_check.get("verification_steps", ""),
        issues=_as_str_list(ca_check.get("issues", [])),
    )

    fb_check = payload.get("feedback_check", {})
    feedback_check = CheckResult(
        status=_coerce_status(fb_check.get("status", "fail")),
        issues=_as_str_list(fb_check.get("issues", [])),
        reasoning=str(fb_check.get("reasoning", "")),
    )

    cq_check = payload.get("content_quality_check", {})
    content_quality_check = ContentQualityCheck(
        status=_coerce_status(cq_check.get("status", "fail")),
        typos_found=_as_str_list(cq_check.get("typos_found", [])),
        character_issues=_as_str_list(cq_check.get("character_issues", [])),
        clarity_issues=_as_str_list(cq_check.get("clarity_issues", [])),
    )

    img_check = payload.get("image_check", {})
    image_check = CheckResult(
        status=_coerce_status(
            img_check.get("status", "not_applicable"),
            default=CheckStatus.NOT_APPLICABLE,
        ),
        issues=_as_str_list(img_check.get("issues", [])),
        reasoning=str(img_check.get("reasoning", "")),
    )

    math_check = payload.get("math_validity_check", {})
    math_validity_check = CheckResult(
        status=_coerce_status(math_check.get("status", "fail")),
        issues=_as_str_list(math_check.get("issues", [])),
        reasoning=str(math_check.get("reasoning", "")),
    )

    all_checks: list[
        CorrectAnswerCheck | CheckResult | ContentQualityCheck
    ] = [
        correct_answer_check,
        feedback_check,
        content_quality_check,
        image_check,
        math_validity_check,
    ]
    raw_verdict = str(payload.get("validation_result", "fail"))
    validation_result = _compute_consistent_verdict(
        all_checks, raw_verdict,
    )

    return ValidationResult(
        validation_result=validation_result,
        correct_answer_check=correct_answer_check,
        feedback_check=feedback_check,
        content_quality_check=content_quality_check,
        image_check=image_check,
        math_validity_check=math_validity_check,
        overall_reasoning=str(payload.get("overall_reasoning", "")),
    )


def _coerce_status(
    value: str,
    *,
    default: CheckStatus = CheckStatus.FAIL,
) -> CheckStatus:
    try:
        return CheckStatus(str(value))
    except ValueError:
        return default


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(v) for v in value if str(v).strip()]


def _compute_consistent_verdict(
    checks: list[CorrectAnswerCheck | CheckResult | ContentQualityCheck],
    raw_verdict: str,
) -> str:
    any_real_failure = False

    for check in checks:
        if check.status == CheckStatus.FAIL:
            if _check_has_issues(check):
                any_real_failure = True
            else:
                check.status = CheckStatus.PASS
                logger.warning(
                    "Auto-corrected check with fail status but no "
                    "issues to pass",
                )

    computed = "fail" if any_real_failure else "pass"
    if raw_verdict not in {"pass", "fail"}:
        logger.warning(
            "Invalid raw validation_result '%s'; using '%s'",
            raw_verdict,
            computed,
        )
        return computed

    if computed != raw_verdict:
        logger.warning(
            "Verdict inconsistency: LLM said '%s' but checks "
            "compute to '%s'. Using computed verdict.",
            raw_verdict,
            computed,
        )

    return computed


def _check_has_issues(
    check: CorrectAnswerCheck | CheckResult | ContentQualityCheck,
) -> bool:
    if isinstance(check, ContentQualityCheck):
        return bool(
            check.typos_found
            or check.character_issues
            or check.clarity_issues
        )
    return bool(check.issues)
