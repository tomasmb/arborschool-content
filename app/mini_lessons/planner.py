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
    build_coherence_prompt,
    build_plan_prompt,
)
from app.mini_lessons.prompts.shared import build_lesson_context_section

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
        plan: LessonPlan | None = None

        for attempt in range(1 + self._max_retries):
            raw_plan = self._call_planner(
                context_section, ctx.atom_id, ctx.template_type,
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
    ) -> LessonPlan | None:
        """Call the LLM to generate a lesson plan."""
        prompt = build_plan_prompt(
            context_section, atom_id, template_type,
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

    if not plan.worked_example_1 or not plan.worked_example_2:
        errors.append("Must have exactly 2 worked examples")

    if len(plan.quick_checks) < 1 or len(plan.quick_checks) > 2:
        errors.append(
            f"Must have 1-2 quick checks, "
            f"got {len(plan.quick_checks)}",
        )

    _validate_template_qc_count(plan, errors)

    we1_ctx = plan.worked_example_1.mathematical_context
    we2_ctx = plan.worked_example_2.mathematical_context
    if we1_ctx and we2_ctx and we1_ctx == we2_ctx:
        errors.append(
            "WE1 and WE2 must have different mathematical "
            "contexts",
        )

    errors.extend(_check_coverage(plan, ctx))

    for section in plan.optional_sections:
        if not section.justification:
            errors.append(
                f"Optional section '{section.block_name}' "
                f"missing justification",
            )

    return errors


def _validate_template_qc_count(
    plan: LessonPlan,
    errors: list[str],
) -> None:
    """Warn if template-specific QC count is not met.

    P-template and M-template expect exactly 2 QCs.
    """
    qc_count = len(plan.quick_checks)
    if plan.template_type in ("P", "M") and qc_count < 2:
        errors.append(
            f"{plan.template_type}-template should have 2 "
            f"quick-checks, got {qc_count}",
        )


def _check_coverage(
    plan: LessonPlan,
    ctx: LessonContext,
) -> list[str]:
    """Check in_scope and error_family coverage in the plan."""
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
        plan.worked_example_1.in_scope_items_covered,
    )
    covered_scope.update(
        plan.worked_example_2.in_scope_items_covered,
    )

    for item in in_scope:
        if not any(item in c for c in covered_scope):
            errors.append(f"in_scope item not covered: {item[:60]}")

    covered_errors = set(
        plan.worked_example_1.error_families_addressed,
    )
    covered_errors.update(
        plan.worked_example_2.error_families_addressed,
    )
    for qc in plan.quick_checks:
        covered_errors.update(qc.error_families_addressed)
    covered_errors.update(plan.error_patterns_families)

    for name in error_names:
        if name not in covered_errors:
            errors.append(f"error_family not covered: {name}")

    return errors
