"""Phase 1 — Lesson planning: generation + validation + coherence.

Generates a LessonPlan, validates it deterministically, then
runs a lightweight LLM coherence check.
"""

from __future__ import annotations

import json
import logging

from app.llm_clients import LLMResponse, OpenAIClient
from app.mini_lessons.models import LessonContext, LessonPlan, PhaseResult
from app.mini_lessons.prompts.planning import (
    _VALID_IMAGE_SECTIONS,
    build_coherence_prompt,
    build_plan_prompt,
)
from app.mini_lessons.prompts.shared import build_lesson_context_section
from app.question_generation.image_types import GENERATABLE_TYPES

logger = logging.getLogger(__name__)


class LessonPlanner:
    """Generates and validates a lesson plan for an atom."""

    def __init__(self, client: OpenAIClient, max_retries: int = 1):
        self._client = client
        self._max_retries = max_retries

    def generate_plan(
        self,
        ctx: LessonContext,
    ) -> tuple[PhaseResult, LessonPlan | None]:
        """Run Phase 1: plan generation + validation + coherence.

        Returns:
            Tuple of (PhaseResult, LessonPlan or None on failure).
        """
        context_section = build_lesson_context_section(ctx)
        image_types: list[str] | None = None
        if ctx.enrichment is not None:
            image_types = ctx.enrichment.required_image_types or None
        plan: LessonPlan | None = None

        for attempt in range(1 + self._max_retries):
            raw_plan = self._call_planner(
                context_section, ctx.atom_id,
                ctx.template_type, image_types,
            )
            if raw_plan is None:
                continue

            errors = validate_plan(raw_plan, ctx)
            if errors:
                logger.warning(
                    "Plan validation failed (attempt %d): %s",
                    attempt + 1, errors,
                )
                continue

            plan = raw_plan
            break

        if plan is None:
            return PhaseResult(
                phase_name="planning",
                success=False,
                errors=["Plan generation failed after retries"],
            ), None

        coherence = self._check_coherence(plan, ctx)
        warnings = coherence if coherence else []

        return PhaseResult(
            phase_name="planning",
            success=True,
            data=plan.model_dump(),
            warnings=warnings,
        ), plan

    def _call_planner(
        self,
        context_section: str,
        atom_id: str,
        template_type: str,
        required_image_types: list[str] | None = None,
    ) -> LessonPlan | None:
        """Call the LLM to generate a lesson plan."""
        prompt = build_plan_prompt(
            context_section, atom_id, template_type,
            required_image_types=required_image_types,
        )
        try:
            resp: LLMResponse = self._client.call(
                prompt,
                response_format={"type": "json_object"},
                reasoning_effort="medium",
            )
            data = json.loads(resp.text)
            return LessonPlan.model_validate(data)
        except Exception as exc:
            logger.warning("Plan LLM call failed: %s", exc)
            return None

    def _check_coherence(
        self,
        plan: LessonPlan,
        ctx: LessonContext,
    ) -> list[str]:
        """Lightweight LLM coherence check on the plan."""
        plan_json = json.dumps(
            plan.model_dump(), indent=2, ensure_ascii=False,
        )
        atom_summary = (
            f"ID: {ctx.atom_id}, Título: {ctx.atom_title}, "
            f"Template: {ctx.template_type}"
        )
        prompt = build_coherence_prompt(plan_json, atom_summary)

        try:
            resp: LLMResponse = self._client.call(
                prompt,
                response_format={"type": "json_object"},
                reasoning_effort="low",
            )
            data = json.loads(resp.text)
            if not data.get("coherent", True):
                return data.get("issues", ["Coherence check failed"])
            return []
        except Exception as exc:
            logger.warning("Coherence check failed: %s", exc)
            return [f"Coherence check error: {exc}"]


# ---------------------------------------------------------------------------
# Deterministic plan validation
# ---------------------------------------------------------------------------


def validate_plan(
    plan: LessonPlan,
    ctx: LessonContext,
) -> list[str]:
    """Validate a lesson plan against deterministic rules.

    Returns list of error messages (empty = passed).
    """
    errors: list[str] = []

    if plan.template_type not in ("P", "C", "M"):
        errors.append(
            f"Invalid template_type: {plan.template_type}",
        )

    if not plan.worked_example:
        errors.append("Must have a worked example")

    if len(plan.checklist_items) != 3:
        errors.append(
            f"Must have exactly 3 checklist items, "
            f"got {len(plan.checklist_items)}",
        )

    errors.extend(_check_spec_lengths(plan))
    errors.extend(_check_coverage(plan, ctx))
    errors.extend(_check_image_plan(plan, ctx))

    return errors


_MAX_OBJECTIVE_SPEC_WORDS = 40
_MAX_CONCEPT_SPEC_WORDS = 60


def _check_spec_lengths(plan: LessonPlan) -> list[str]:
    """Reject plans with bloated spec fields."""
    errors: list[str] = []
    obj_words = len(plan.objective_spec.split())
    if obj_words > _MAX_OBJECTIVE_SPEC_WORDS:
        errors.append(
            f"objective_spec too long: {obj_words} words "
            f"(max {_MAX_OBJECTIVE_SPEC_WORDS})",
        )
    con_words = len(plan.concept_spec.split())
    if con_words > _MAX_CONCEPT_SPEC_WORDS:
        errors.append(
            f"concept_spec too long: {con_words} words "
            f"(max {_MAX_CONCEPT_SPEC_WORDS})",
        )
    return errors


def _check_coverage(
    plan: LessonPlan,
    ctx: LessonContext,
) -> list[str]:
    """Check in_scope coverage and error-family selection."""
    errors: list[str] = []

    if ctx.enrichment is None:
        return errors

    enrichment_data = ctx.enrichment.model_dump()
    scope = enrichment_data.get("scope_guardrails", {})
    in_scope = scope.get("in_scope", [])
    error_fams = enrichment_data.get("error_families", [])
    error_names = [e.get("name", "") for e in error_fams]

    covered_scope = set(plan.concept_in_scope_items)
    covered_scope.update(
        plan.worked_example.in_scope_items_covered,
    )

    for item in in_scope:
        if not any(item in c for c in covered_scope):
            errors.append(f"in_scope item not covered: {item[:60]}")

    covered_errors = set(
        plan.worked_example.error_families_addressed,
    )

    enrichment_set = set(error_names)
    for name in covered_errors:
        if name not in enrichment_set:
            errors.append(
                f"plan references unknown error family: {name}",
            )

    if covered_errors and len(covered_errors) < 2:
        errors.append(
            "worked example should address at least 2 error families",
        )

    return errors


def _check_image_plan(
    plan: LessonPlan,
    ctx: LessonContext,
) -> list[str]:
    """Validate image_plan entries against enrichment and sections."""
    errors: list[str] = []

    allowed_types: set[str] = set()
    if ctx.enrichment is not None:
        allowed_types = set(ctx.enrichment.required_image_types)

    for entry in plan.image_plan:
        if entry.target_section not in _VALID_IMAGE_SECTIONS:
            errors.append(
                f"image_plan target_section "
                f"'{entry.target_section}' is not a valid "
                f"section (allowed: "
                f"{', '.join(sorted(_VALID_IMAGE_SECTIONS))})",
            )
        if entry.image_type not in GENERATABLE_TYPES:
            errors.append(
                f"image_plan image_type '{entry.image_type}' "
                f"is not a generatable type",
            )
        elif allowed_types and entry.image_type not in allowed_types:
            errors.append(
                f"image_plan image_type '{entry.image_type}' "
                f"not in atom's required_image_types: "
                f"{sorted(allowed_types)}",
            )

    return errors
