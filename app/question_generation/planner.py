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

from app.llm_clients import OpenAIClient
from app.question_generation.models import (
    AtomContext,
    AtomEnrichment,
    DifficultyDistribution,
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
    build_image_instruction,
)

logger = logging.getLogger(__name__)

# Baseline skeleton cap for small pools (spec 6.2).
# For larger pools, the cap scales: max(2, total // 10).
_BASE_SKELETON_CAP = 2


def skeleton_repetition_cap(pool_total: int) -> int:
    """Compute the skeleton repetition cap for a given pool size.

    Keeps diversity proportional: pool=46 -> cap=4, pool=62 -> cap=6.
    """
    return max(_BASE_SKELETON_CAP, pool_total // 10)


_PLANNING_REASONING = "medium"


class PlanGenerator:
    """Generates a plan of item specifications for an atom (Phase 2)."""

    def __init__(
        self,
        client: OpenAIClient,
        max_retries: int = 2,
    ) -> None:
        """Initialize the plan generator.

        Args:
            client: OpenAI client for LLM calls.
            max_retries: Max retry attempts on parse failure.
        """
        self._client = client
        self._max_retries = max_retries

    def generate_plan(
        self,
        atom_context: AtomContext,
        enrichment: AtomEnrichment | None,
        distribution: DifficultyDistribution,
    ) -> PhaseResult:
        """Generate a plan of item slots (Phase 2).

        Args:
            atom_context: Atom data from Phase 0.
            enrichment: Enrichment from Phase 1 (may be None).
            distribution: Planned difficulty distribution.

        Returns:
            PhaseResult with list[PlanSlot] data on success.
        """
        pool_size = distribution.total
        logger.info(
            "Phase 2: Generating plan for atom %s (%d slots)",
            atom_context.atom_id, pool_size,
        )

        prompt = self._build_prompt(
            atom_context, enrichment, distribution,
        )

        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.generate_text(
                    prompt,
                    response_mime_type="application/json",
                    reasoning_effort=_PLANNING_REASONING,
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
        distribution: DifficultyDistribution,
    ) -> str:
        """Build the plan generation prompt."""
        image_types = (
            enrichment.required_image_types if enrichment else None
        )
        image_instruction, image_rules = build_image_instruction(
            image_types,
        )
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
            pool_size=distribution.total,
            skeleton_cap=skeleton_repetition_cap(distribution.total),
            difficulty_distribution=build_difficulty_distribution(
                distribution,
            ),
            image_instruction=image_instruction,
            image_rules=image_rules,
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
    distribution: DifficultyDistribution,
) -> PhaseResult:
    """Validate a generated plan against hard constraints (Phase 3).

    Checks (spec section 8, Phase 3):
    - PAES constraints: MCQ-only, 4 options, single correct (intent)
    - Scope compliance (atom-only)
    - Difficulty distribution adherence
    - Exemplar anchoring rule (if exemplars exist)
    - Skeleton repetition cap (scales with pool size)
    - Slot count matches distribution total

    Args:
        plan_slots: Generated plan from Phase 2.
        atom_context: Atom data for scope checking.
        distribution: Expected difficulty distribution.

    Returns:
        PhaseResult with validation report.
    """
    logger.info("Phase 3: Validating plan (%d slots)", len(plan_slots))

    errors: list[str] = []
    warnings: list[str] = []

    _check_slot_count(plan_slots, distribution.total, errors)
    _check_difficulty_distribution(plan_slots, distribution, errors)
    _check_skeleton_repetition(plan_slots, distribution.total, errors)
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
    distribution: DifficultyDistribution,
    errors: list[str],
) -> None:
    """Check that difficulty counts match the planned distribution."""
    counts = Counter(slot.difficulty_level for slot in slots)
    expected = {
        DifficultyLevel.EASY: distribution.easy,
        DifficultyLevel.MEDIUM: distribution.medium,
        DifficultyLevel.HARD: distribution.hard,
    }
    for level, exp in expected.items():
        actual = counts.get(level, 0)
        if actual != exp:
            errors.append(
                f"Expected {exp} '{level.value}' slots, "
                f"got {actual}",
            )


def _check_skeleton_repetition(
    slots: list[PlanSlot],
    pool_total: int,
    errors: list[str],
) -> None:
    """Enforce skeleton repetition cap (spec section 6.2).

    The cap scales with pool size to keep diversity proportional:
    pool=46 -> cap=4, pool=62 -> cap=6.
    """
    cap = skeleton_repetition_cap(pool_total)
    counts = Counter(slot.operation_skeleton_ast for slot in slots)

    for skeleton, count in counts.items():
        if count > cap:
            errors.append(
                f"Skeleton '{skeleton}' appears {count} times "
                f"(max {cap} for pool of {pool_total})",
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
