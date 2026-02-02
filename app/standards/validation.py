"""Standards validation module.

Two-stage validation:
1. Per-unidad: Immediate semantic check after generation
2. Per-eje: Cross-standard checks for coverage and consistency
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from app.gemini_client import GeminiService
from app.standards.helpers import parse_json_response
from app.standards.models import (
    Standard,
    validate_standard_id_matches_eje,
    validate_standards_coverage,
)
from app.standards.prompts import (
    build_eje_validation_prompt,
    build_single_standard_validation_prompt,
)

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Data classes
# -----------------------------------------------------------------------------


@dataclass
class ValidationIssue:
    """A single validation issue found during review."""

    standard_id: str | None
    issue_type: str
    description: str
    severity: str  # "error" or "warning"


@dataclass
class ValidationResult:
    """Result of validating standards."""

    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    corrected_standards: list[Standard] | None = None

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")


# -----------------------------------------------------------------------------
# Structural validation (Pydantic-based)
# -----------------------------------------------------------------------------


def validate_standard_structure(
    standard_dict: dict[str, Any],
) -> tuple[Standard | None, list[str]]:
    """Validate a single standard dict against the Pydantic schema."""
    try:
        standard = Standard.model_validate(standard_dict)
        validate_standard_id_matches_eje(standard)
        return standard, []
    except ValidationError as e:
        errors = [f"Field '{'.'.join(str(loc) for loc in err['loc'])}': {err['msg']}" for err in e.errors()]
        return None, errors
    except ValueError as e:
        return None, [str(e)]


# -----------------------------------------------------------------------------
# Per-unidad semantic validation
# -----------------------------------------------------------------------------


def validate_single_standard_with_gemini(
    gemini: GeminiService,
    standard: Standard,
    unidad_data: dict[str, Any],
    habilidades: dict[str, Any],
) -> ValidationResult:
    """
    Validate a single standard immediately after generation.

    Catches: content outside temario scope, coverage issues, granularity problems.
    """
    logger.info("Validating standard %s against source unidad", standard.id)

    prompt = build_single_standard_validation_prompt(
        standard_dict=standard.model_dump(),
        unidad_data=unidad_data,
        habilidades=habilidades,
    )

    return _call_gemini_validation(gemini, prompt, standard.id)


# -----------------------------------------------------------------------------
# Per-eje semantic validation
# -----------------------------------------------------------------------------


def validate_standards_eje_with_gemini(
    gemini: GeminiService,
    standards: list[Standard],
    eje_key: str,
    original_unidades: list[dict[str, Any]],
    habilidades: dict[str, Any],
) -> ValidationResult:
    """
    Validate a batch of standards for cross-standard issues.

    Catches: coverage gaps, duplicate content, inconsistent terminology.
    """
    logger.info(
        "Running cross-standard validation for eje '%s' (%d standards)",
        eje_key,
        len(standards),
    )

    prompt = build_eje_validation_prompt(
        standards=[s.model_dump() for s in standards],
        eje_key=eje_key,
        original_unidades=original_unidades,
        habilidades=habilidades,
    )

    return _call_gemini_validation(gemini, prompt, standard_id=None)


# -----------------------------------------------------------------------------
# Local validation
# -----------------------------------------------------------------------------


def validate_coverage_locally(
    standards: list[Standard],
    temario_conocimientos: dict[str, Any],
    eje_key: str | None = None,
) -> list[ValidationIssue]:
    """Check that all temario unidades are covered (fast, no Gemini).

    If eje_key is provided, only validates coverage for that specific eje.
    Otherwise validates all ejes (for full pipeline validation).
    """
    if eje_key:
        # Validate only the current eje
        if eje_key not in temario_conocimientos:
            return []
        eje_data = temario_conocimientos[eje_key]
        unidades = eje_data.get("unidades", [])
        temario_unidades = {eje_key: [u.get("nombre", "") for u in unidades]}
    else:
        # Validate all ejes
        temario_unidades = {}
        for eje, eje_data in temario_conocimientos.items():
            unidades = eje_data.get("unidades", [])
            temario_unidades[eje] = [u.get("nombre", "") for u in unidades]

    coverage_errors = validate_standards_coverage(standards, temario_unidades)

    return [
        ValidationIssue(
            standard_id=None,
            issue_type="coverage",
            description=error,
            severity="error",
        )
        for error in coverage_errors
    ]


# -----------------------------------------------------------------------------
# Combined validation
# -----------------------------------------------------------------------------


def run_full_eje_validation(
    gemini: GeminiService,
    standards: list[Standard],
    eje_key: str,
    original_unidades: list[dict[str, Any]],
    habilidades: dict[str, Any],
    temario_conocimientos: dict[str, Any],
) -> ValidationResult:
    """
    Run per-eje validation (after all standards passed per-unidad validation).

    Combines local coverage check + Gemini cross-standard validation.
    """
    all_issues: list[ValidationIssue] = []

    # Local coverage check (only for current eje)
    logger.info("Running local coverage validation for eje '%s'...", eje_key)
    coverage_issues = validate_coverage_locally(standards, temario_conocimientos, eje_key=eje_key)
    all_issues.extend(coverage_issues)

    if coverage_issues:
        logger.warning("Found %d coverage issues", len(coverage_issues))

    # Gemini cross-standard validation
    logger.info("Running Gemini cross-standard validation for eje '%s'...", eje_key)
    gemini_result = validate_standards_eje_with_gemini(
        gemini=gemini,
        standards=standards,
        eje_key=eje_key,
        original_unidades=original_unidades,
        habilidades=habilidades,
    )
    all_issues.extend(gemini_result.issues)

    has_errors = any(i.severity == "error" for i in all_issues)

    return ValidationResult(
        is_valid=not has_errors,
        issues=all_issues,
        corrected_standards=gemini_result.corrected_standards,
    )


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _call_gemini_validation(
    gemini: GeminiService,
    prompt: str,
    standard_id: str | None,
) -> ValidationResult:
    """Call Gemini for validation and parse the response."""
    try:
        raw_response = gemini.generate_text(
            prompt,
            thinking_level="high",
            response_mime_type="application/json",
            temperature=0.0,
        )
        parsed_response = parse_json_response(raw_response)
        if not isinstance(parsed_response, dict):
            raise ValueError(f"Expected dict from validation response, got {type(parsed_response)}")
        response_dict = parsed_response
        return _convert_validation_response(response_dict, standard_id)

    except json.JSONDecodeError as e:
        logger.error("Failed to parse Gemini validation response: %s", e)
        return _error_result(standard_id, "parse_error", f"JSON parse failed: {e}")

    except Exception as e:
        logger.exception("Unexpected validation error: %s", e)
        return _error_result(standard_id, "validation_error", f"Unexpected error: {e}")


def _convert_validation_response(
    response: dict[str, Any],
    default_standard_id: str | None,
) -> ValidationResult:
    """Convert Gemini's validation response to ValidationResult."""
    issues: list[ValidationIssue] = []

    for issue_dict in response.get("issues", []):
        issues.append(
            ValidationIssue(
                standard_id=issue_dict.get("standard_id", default_standard_id),
                issue_type=issue_dict.get("issue_type", "unknown"),
                description=issue_dict.get("description", ""),
                severity=issue_dict.get("severity", "warning"),
            )
        )

    # Parse corrected standard(s)
    corrected_standards = _parse_corrected_standards(response, issues)

    return ValidationResult(
        is_valid=response.get("is_valid", False),
        issues=issues,
        corrected_standards=corrected_standards,
    )


def _parse_corrected_standards(
    response: dict[str, Any],
    issues: list[ValidationIssue],
) -> list[Standard] | None:
    """Parse corrected standards from validation response."""
    # Handle single standard (per-unidad validation)
    if "corrected_standard" in response and response["corrected_standard"]:
        try:
            return [Standard.model_validate(response["corrected_standard"])]
        except ValidationError as e:
            logger.warning("Failed to parse corrected standard: %s", e)
            issues.append(
                ValidationIssue(
                    standard_id=response["corrected_standard"].get("id"),
                    issue_type="correction_parse_error",
                    description=f"Correction failed validation: {e}",
                    severity="warning",
                )
            )
            return None

    # Handle multiple standards (per-eje validation)
    if "corrected_standards" in response and response["corrected_standards"]:
        corrected: list[Standard] = []
        for std_dict in response["corrected_standards"]:
            try:
                corrected.append(Standard.model_validate(std_dict))
            except ValidationError as e:
                logger.warning("Failed to parse corrected standard: %s", e)
                issues.append(
                    ValidationIssue(
                        standard_id=std_dict.get("id"),
                        issue_type="correction_parse_error",
                        description=f"Correction failed validation: {e}",
                        severity="warning",
                    )
                )
        return corrected if corrected else None

    return None


def _error_result(
    standard_id: str | None,
    issue_type: str,
    description: str,
) -> ValidationResult:
    """Create an error ValidationResult."""
    return ValidationResult(
        is_valid=False,
        issues=[
            ValidationIssue(
                standard_id=standard_id,
                issue_type=issue_type,
                description=description,
                severity="error",
            )
        ],
    )
