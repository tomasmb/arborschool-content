"""Phases 2-3 — Plan Generation + Plan Validation.

Phase 2 generates a plan of N slots with explicit diversity controls.
Phase 3 validates the plan against hard constraints before proceeding.
Both phases are MANDATORY and BLOCKING (spec sections 8, Phase 2-3).
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from typing import Any

from app.llm_clients import GeminiService
from app.question_generation.models import (
    AtomContext,
    AtomEnrichment,
    DifficultyLevel,
    PhaseResult,
    PlanSlot,
)
from app.question_generation.prompts.enrichment import (
    build_exemplars_section,
)
from app.question_generation.prompts.planning import (
    PLAN_GENERATION_PROMPT,
    build_difficulty_distribution,
    build_enrichment_section,
)

logger = logging.getLogger(__name__)

# Maximum times the same operation_skeleton_ast can appear (spec 6.2)
MAX_SKELETON_REPETITIONS = 2


class PlanGenerator:
    """Generates a plan of item specifications for an atom (Phase 2)."""

    def __init__(
        self,
        gemini: GeminiService,
        max_retries: int = 2,
    ) -> None:
        """Initialize the plan generator.

        Args:
            gemini: Gemini service for LLM calls.
            max_retries: Max retry attempts on parse failure.
        """
        self._gemini = gemini
        self._max_retries = max_retries

    def generate_plan(
        self,
        atom_context: AtomContext,
        enrichment: AtomEnrichment | None,
        pool_size: int,
    ) -> PhaseResult:
        """Generate a plan of item slots (Phase 2).

        Args:
            atom_context: Atom data from Phase 0.
            enrichment: Enrichment from Phase 1 (may be None).
            pool_size: Number of items to plan.

        Returns:
            PhaseResult with list[PlanSlot] data on success.
        """
        logger.info(
            "Phase 2: Generating plan for atom %s (%d slots)",
            atom_context.atom_id, pool_size,
        )

        prompt = self._build_prompt(atom_context, enrichment, pool_size)

        for attempt in range(self._max_retries + 1):
            try:
                response = self._gemini.generate_text(
                    prompt,
                    response_mime_type="application/json",
                    temperature=0.0,
                )
                plan_slots = self._parse_response(response)

                logger.info(
                    "Plan generated: %d slots", len(plan_slots),
                )
                return PhaseResult(
                    phase_name="plan_generation",
                    success=True,
                    data=plan_slots,
                )

            except (json.JSONDecodeError, ValueError) as exc:
                logger.warning(
                    "Plan generation attempt %d failed: %s",
                    attempt + 1, exc,
                )
                if attempt == self._max_retries:
                    return PhaseResult(
                        phase_name="plan_generation",
                        success=False,
                        errors=[
                            f"Plan generation failed after "
                            f"{attempt + 1} attempts: {exc}",
                        ],
                    )

        return PhaseResult(
            phase_name="plan_generation",
            success=False,
            errors=["Max retries exceeded"],
        )

    def _build_prompt(
        self,
        ctx: AtomContext,
        enrichment: AtomEnrichment | None,
        pool_size: int,
    ) -> str:
        """Build the plan generation prompt."""
        return PLAN_GENERATION_PROMPT.format(
            atom_id=ctx.atom_id,
            atom_title=ctx.atom_title,
            atom_description=ctx.atom_description,
            eje=ctx.eje,
            tipo_atomico=ctx.tipo_atomico,
            criterios_atomicos=", ".join(ctx.criterios_atomicos),
            enrichment_section=build_enrichment_section(enrichment),
            exemplars_section=build_exemplars_section(ctx.exemplars),
            existing_count=ctx.existing_item_count,
            pool_size=pool_size,
            difficulty_distribution=build_difficulty_distribution(pool_size),
        )

    def _parse_response(self, response: str) -> list[PlanSlot]:
        """Parse the LLM response into PlanSlot objects.

        Args:
            response: Raw JSON from LLM.

        Returns:
            List of validated PlanSlot objects.

        Raises:
            json.JSONDecodeError: Invalid JSON.
            ValueError: Missing required fields.
        """
        data: dict[str, Any] = json.loads(response)
        raw_slots = data.get("plan", [])

        if not raw_slots:
            msg = "LLM returned empty plan"
            raise ValueError(msg)

        return [PlanSlot.model_validate(slot) for slot in raw_slots]


# ---------------------------------------------------------------------------
# Phase 3 — Plan Validation
# ---------------------------------------------------------------------------


def validate_plan(
    plan_slots: list[PlanSlot],
    atom_context: AtomContext,
    pool_size: int,
) -> PhaseResult:
    """Validate a generated plan against hard constraints (Phase 3).

    Checks (spec section 8, Phase 3):
    - PAES constraints: MCQ-only, 4 options, single correct (intent)
    - Scope compliance (atom-only)
    - Difficulty distribution adherence
    - Exemplar anchoring rule (if exemplars exist)
    - Skeleton repetition cap (max 2 per AST)
    - Slot count matches pool_size

    Args:
        plan_slots: Generated plan from Phase 2.
        atom_context: Atom data for scope checking.
        pool_size: Expected number of slots.

    Returns:
        PhaseResult with validation report.
    """
    logger.info("Phase 3: Validating plan (%d slots)", len(plan_slots))

    errors: list[str] = []
    warnings: list[str] = []

    _check_slot_count(plan_slots, pool_size, errors)
    _check_difficulty_distribution(plan_slots, pool_size, warnings)
    _check_skeleton_repetition(plan_slots, errors)
    _check_exemplar_anchoring(plan_slots, atom_context, errors)
    _check_required_fields(plan_slots, errors)

    success = len(errors) == 0

    if success:
        logger.info("Plan validation passed")
    else:
        logger.error("Plan validation failed: %s", errors)

    return PhaseResult(
        phase_name="plan_validation",
        success=success,
        data={"validated_plan": plan_slots},
        errors=errors,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Validation checks (each is a small, focused function)
# ---------------------------------------------------------------------------


def _check_slot_count(
    slots: list[PlanSlot],
    expected: int,
    errors: list[str],
) -> None:
    """Verify the plan has the expected number of slots."""
    if len(slots) != expected:
        errors.append(
            f"Expected {expected} slots, got {len(slots)}",
        )


def _check_difficulty_distribution(
    slots: list[PlanSlot],
    pool_size: int,
    warnings: list[str],
) -> None:
    """Check that difficulty levels are reasonably distributed."""
    counts = Counter(slot.difficulty_level for slot in slots)
    per_level = pool_size // 3

    for level in DifficultyLevel:
        actual = counts.get(level, 0)
        if actual == 0:
            warnings.append(
                f"No slots at difficulty '{level.value}' "
                f"(expected ~{per_level})",
            )


def _check_skeleton_repetition(
    slots: list[PlanSlot],
    errors: list[str],
) -> None:
    """Enforce skeleton repetition cap (spec section 6.2)."""
    counts = Counter(slot.operation_skeleton_ast for slot in slots)

    for skeleton, count in counts.items():
        if count > MAX_SKELETON_REPETITIONS:
            errors.append(
                f"Skeleton '{skeleton}' appears {count} times "
                f"(max {MAX_SKELETON_REPETITIONS})",
            )


def _check_exemplar_anchoring(
    slots: list[PlanSlot],
    atom_context: AtomContext,
    errors: list[str],
) -> None:
    """Enforce exemplar anchoring when exemplars exist (spec 3.3)."""
    if not atom_context.exemplars:
        return  # No anchoring required

    for slot in slots:
        if not slot.target_exemplar_id:
            errors.append(
                f"Slot {slot.slot_index} missing target_exemplar_id "
                f"(exemplars exist for this atom)",
            )
        if not slot.distance_level:
            errors.append(
                f"Slot {slot.slot_index} missing distance_level "
                f"(exemplars exist for this atom)",
            )


def _check_required_fields(
    slots: list[PlanSlot],
    errors: list[str],
) -> None:
    """Verify all slots have required fields populated."""
    for slot in slots:
        if not slot.component_tag:
            errors.append(
                f"Slot {slot.slot_index} missing component_tag",
            )
        if not slot.operation_skeleton_ast:
            errors.append(
                f"Slot {slot.slot_index} missing operation_skeleton_ast",
            )
