"""Standards generation module.

Handles unidad-by-unidad generation of canonical standards using Gemini (`gemini-3-pro-preview`),
with immediate per-unidad validation following the two-stage approach in
`docs/standards-from-temarios.md` section 3.5.

Flow per unidad:
1. Generate standard with Gemini
2. Validate structure (Pydantic)
3. Validate semantics with Gemini (per-unidad)
4. If validation fails, retry with corrections or re-generate
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from app.gemini_client import GeminiService
from app.standards.helpers import parse_json_response
from app.standards.models import Standard, validate_standard_id_matches_eje
from app.standards.prompts import EJE_PREFIX_MAP, build_generation_prompt

logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    """Result of generating a single standard."""

    success: bool
    standard: Standard | None = None
    raw_response: str = ""
    error: str | None = None
    validation_warnings: list[str] = field(default_factory=list)


@dataclass
class EjeGenerationResult:
    """Result of generating all standards for an eje."""

    eje: str
    standards: list[Standard] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0 and len(self.standards) > 0


def generate_and_validate_standard_for_unidad(
    gemini: GeminiService,
    unidad_data: dict[str, Any],
    eje_key: str,
    unidad_index: int,
    habilidades: dict[str, Any],
    standard_number: int,
    validate_with_gemini: bool = True,
) -> GenerationResult:
    """
    Generate a single standard and immediately validate it.

    This is the core function that implements the tight feedback loop:
    generate → validate → apply corrections if needed.

    Args:
        gemini: Configured GeminiService instance.
        unidad_data: Dict with 'nombre' and 'descripcion' from the temario.
        eje_key: The eje key (e.g. 'numeros').
        unidad_index: Index of this unidad within its eje.
        habilidades: Full habilidades dict from the temario.
        standard_number: Sequential number for this standard.
        validate_with_gemini: Whether to run Gemini semantic validation.

    Returns:
        GenerationResult with success status and either a Standard or error.
    """
    # Import here to avoid circular imports
    from app.standards.validation import validate_single_standard_with_gemini

    prompt = build_generation_prompt(
        unidad_data=unidad_data,
        eje_key=eje_key,
        unidad_index=unidad_index,
        habilidades=habilidades,
        standard_number=standard_number,
    )

    logger.info(
        "Generating standard M1-%s-%02d for unidad '%s'",
        EJE_PREFIX_MAP[eje_key],
        standard_number,
        unidad_data.get("nombre", "unknown"),
    )

    # Step 1: Generate with Gemini
    try:
        raw_response = gemini.generate_text(
            prompt,
            thinking_level="high",
            response_mime_type="application/json",
            temperature=0.0,
        )
    except Exception as e:
        error_msg = f"Gemini generation failed: {e}"
        logger.error(error_msg)
        return GenerationResult(success=False, error=error_msg)

    # Step 2: Parse JSON response
    try:
        parsed_response = parse_json_response(raw_response)
        if not isinstance(parsed_response, dict):
            raise ValueError(f"Expected dict from standard generation, got {type(parsed_response)}")
        standard_dict = parsed_response
    except (json.JSONDecodeError, ValueError) as e:
        error_msg = f"Failed to parse JSON response: {e}"
        logger.error(error_msg)
        return GenerationResult(success=False, raw_response=raw_response, error=error_msg)

    # Step 3: Validate structure with Pydantic
    try:
        standard = Standard.model_validate(standard_dict)
        validate_standard_id_matches_eje(standard)
    except ValueError as e:
        error_msg = f"Structural validation error: {e}"
        logger.error(error_msg)
        return GenerationResult(success=False, raw_response=raw_response, error=error_msg)

    logger.info("Generated standard %s, running semantic validation...", standard.id)

    # Step 4: Validate semantics with Gemini (per-unidad)
    if validate_with_gemini:
        validation_result = validate_single_standard_with_gemini(
            gemini=gemini,
            standard=standard,
            unidad_data=unidad_data,
            habilidades=habilidades,
        )

        # Collect warnings
        warnings = [f"{i.issue_type}: {i.description}" for i in validation_result.issues if i.severity == "warning"]

        # Check for errors
        if validation_result.has_errors:
            # If Gemini provided a correction, use it
            if validation_result.corrected_standards:
                corrected = validation_result.corrected_standards[0]
                logger.info(
                    "Using Gemini's corrected version for %s",
                    standard.id,
                )
                return GenerationResult(
                    success=True,
                    standard=corrected,
                    raw_response=raw_response,
                    validation_warnings=warnings,
                )
            else:
                # Validation failed without correction
                error_msgs = [f"{i.issue_type}: {i.description}" for i in validation_result.issues if i.severity == "error"]
                error_msg = f"Semantic validation failed: {'; '.join(error_msgs)}"
                logger.error(error_msg)
                return GenerationResult(
                    success=False,
                    raw_response=raw_response,
                    error=error_msg,
                    validation_warnings=warnings,
                )

        logger.info("Standard %s passed semantic validation", standard.id)
        return GenerationResult(
            success=True,
            standard=standard,
            raw_response=raw_response,
            validation_warnings=warnings,
        )

    # Skip Gemini validation
    logger.info("Standard %s generated (Gemini validation skipped)", standard.id)
    return GenerationResult(
        success=True,
        standard=standard,
        raw_response=raw_response,
    )


def generate_standards_for_eje(
    gemini: GeminiService,
    eje_key: str,
    unidades: list[dict[str, Any]],
    habilidades: dict[str, Any],
    starting_number: int = 1,
    max_retries: int = 2,
    validate_per_unidad: bool = True,
) -> EjeGenerationResult:
    """
    Generate all standards for a single eje, processing unidad-by-unidad.

    Each unidad goes through: generate → validate → retry if needed.

    Args:
        gemini: Configured GeminiService instance.
        eje_key: The eje key (e.g. 'numeros').
        unidades: List of unidad dicts from the temario for this eje.
        habilidades: Full habilidades dict from the temario.
        starting_number: Starting number for standard IDs.
        max_retries: Maximum retries per unidad on failure.
        validate_per_unidad: Whether to validate each standard immediately.

    Returns:
        EjeGenerationResult with all generated standards and any errors.
    """
    logger.info(
        "Starting generation for eje '%s' with %d unidades (per-unidad validation: %s)",
        eje_key,
        len(unidades),
        validate_per_unidad,
    )

    result = EjeGenerationResult(eje=eje_key)
    current_number = starting_number

    for idx, unidad_data in enumerate(unidades):
        unidad_name = unidad_data.get("nombre", f"unidad_{idx}")

        # Retry logic for robustness
        gen_result: GenerationResult | None = None
        for attempt in range(max_retries + 1):
            gen_result = generate_and_validate_standard_for_unidad(
                gemini=gemini,
                unidad_data=unidad_data,
                eje_key=eje_key,
                unidad_index=idx,
                habilidades=habilidades,
                standard_number=current_number,
                validate_with_gemini=validate_per_unidad,
            )

            if gen_result.success:
                break

            if attempt < max_retries:
                logger.warning(
                    "Retry %d/%d for unidad '%s': %s",
                    attempt + 1,
                    max_retries,
                    unidad_name,
                    gen_result.error,
                )

        # Process result
        if gen_result and gen_result.success and gen_result.standard:
            result.standards.append(gen_result.standard)
            result.warnings.extend(gen_result.validation_warnings)
            current_number += 1
            logger.info(
                "✓ Standard %s generated and validated for '%s'",
                gen_result.standard.id,
                unidad_name,
            )
        else:
            error_msg = (
                f"Failed to generate standard for unidad '{unidad_name}' "
                f"after {max_retries + 1} attempts: {gen_result.error if gen_result else 'unknown'}"
            )
            result.errors.append(error_msg)
            logger.error("✗ %s", error_msg)

    logger.info(
        "Completed eje '%s': %d standards generated, %d errors, %d warnings",
        eje_key,
        len(result.standards),
        len(result.errors),
        len(result.warnings),
    )

    return result
