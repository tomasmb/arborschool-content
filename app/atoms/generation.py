"""Atom generation module.

Handles standard-by-standard generation of learning atoms using Gemini
(`gemini-3-pro-preview`), following the guidelines in
`docs/learning-atom-granularity-guidelines.md`.

Flow per standard:
1. Generate atoms with Gemini
2. Validate structure (Pydantic)
3. Validate granularity (local checks)
4. If validation fails, retry or re-generate
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from app.gemini_client import GeminiService
from app.standards.helpers import parse_json_response
from app.atoms.models import Atom, validate_atom_id_matches_eje
from app.atoms.prompts import build_atom_generation_prompt

logger = logging.getLogger(__name__)


@dataclass
class AtomGenerationResult:
    """Result of generating atoms for a single standard."""

    success: bool
    atoms: list[Atom] = field(default_factory=list)
    raw_response: str = ""
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


def generate_atoms_for_standard(
    gemini: GeminiService,
    standard: dict[str, Any],
    habilidades: dict[str, Any],
    max_retries: int = 2,
) -> AtomGenerationResult:
    """
    Generate atoms for a single standard.

    This function implements the core generation loop:
    generate → validate → retry if needed.

    Args:
        gemini: Configured GeminiService instance.
        standard: Standard dict from canonical standards JSON.
        habilidades: Full habilidades dict from the temario.
        max_retries: Maximum retries on failure.

    Returns:
        AtomGenerationResult with success status and generated atoms or error.
    """
    standard_id = standard.get("id", "unknown")
    standard_title = standard.get("titulo", "unknown")

    logger.info(
        "Generating atoms for standard %s: %s",
        standard_id,
        standard_title,
    )

    prompt = build_atom_generation_prompt(
        standard=standard,
        habilidades=habilidades,
        atom_counter=1,  # Will be adjusted per atom in response
    )

    # Retry logic for robustness
    for attempt in range(max_retries + 1):
        try:
            # Step 1: Generate with Gemini
            raw_response = gemini.generate_text(
                prompt,
                thinking_level="high",
                response_mime_type="application/json",
                temperature=0.0,
            )
        except Exception as e:
            error_msg = f"Gemini generation failed: {e}"
            logger.error(error_msg)
            if attempt < max_retries:
                logger.warning("Retry %d/%d for standard %s", attempt + 1, max_retries, standard_id)
                continue
            return AtomGenerationResult(success=False, error=error_msg)

        # Step 2: Parse JSON response
        try:
            atoms_data = parse_json_response(raw_response)
            # Handle both array and single object responses
            if isinstance(atoms_data, dict):
                atoms_data = [atoms_data]
            elif not isinstance(atoms_data, list):
                error_msg = f"Expected array or object, got {type(atoms_data).__name__}"
                logger.error(error_msg)
                if attempt < max_retries:
                    continue
                return AtomGenerationResult(
                    success=False,
                    raw_response=raw_response,
                    error=error_msg,
                )
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON response: {e}"
            logger.error(error_msg)
            if attempt < max_retries:
                continue
            return AtomGenerationResult(
                success=False,
                raw_response=raw_response,
                error=error_msg,
            )

        # Step 3: Validate structure with Pydantic
        validated_atoms: list[Atom] = []
        warnings: list[str] = []

        for idx, atom_dict in enumerate(atoms_data):
            try:
                atom = Atom.model_validate(atom_dict)
                validate_atom_id_matches_eje(atom)

                # Validate standard_ids reference the current standard
                if standard_id not in atom.standard_ids:
                    warnings.append(
                        f"Atom {atom.id} standard_ids doesn't include {standard_id}"
                    )

                validated_atoms.append(atom)
                logger.debug("Validated atom %s", atom.id)

            except ValueError as e:
                error_msg = f"Validation error for atom {idx}: {e}"
                logger.error(error_msg)
                warnings.append(error_msg)

        if not validated_atoms:
            error_msg = "No valid atoms generated after validation"
            logger.error(error_msg)
            if attempt < max_retries:
                logger.warning("Retry %d/%d for standard %s", attempt + 1, max_retries, standard_id)
                continue
            return AtomGenerationResult(
                success=False,
                raw_response=raw_response,
                error=error_msg,
                warnings=warnings,
            )

        # Step 4: Validate granularity (basic checks)
        granularity_warnings = _validate_atom_granularity(validated_atoms)
        warnings.extend(granularity_warnings)

        logger.info(
            "Generated %d atoms for standard %s",
            len(validated_atoms),
            standard_id,
        )

        return AtomGenerationResult(
            success=True,
            atoms=validated_atoms,
            raw_response=raw_response,
            warnings=warnings,
        )

    # All retries exhausted
    return AtomGenerationResult(
        success=False,
        error=f"Failed after {max_retries + 1} attempts",
    )


def _validate_atom_granularity(atoms: list[Atom]) -> list[str]:
    """
    Perform basic granularity validation checks.

    Returns list of warning messages (empty if all valid).
    """
    warnings: list[str] = []

    for atom in atoms:
        # Check: one cognitive intention (heuristic: descripcion length)
        if len(atom.descripcion) > 300:
            warnings.append(
                f"Atom {atom.id}: descripcion may be too long "
                f"({len(atom.descripcion)} chars), might contain multiple intentions"
            )

        # Check: reasonable working memory load (heuristic: criterios count)
        if len(atom.criterios_atomicos) > 5:
            warnings.append(
                f"Atom {atom.id}: too many criterios_atomicos "
                f"({len(atom.criterios_atomicos)}), might overload working memory"
            )

        # Check: assessment independence (heuristic: multiple habilidades principales)
        if len(atom.habilidades_secundarias) > 2:
            warnings.append(
                f"Atom {atom.id}: many habilidades_secundarias "
                f"({len(atom.habilidades_secundarias)}), might need splitting"
            )

    return warnings

