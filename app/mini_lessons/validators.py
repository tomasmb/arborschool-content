"""Phases 3-5 — Validation, assembly, and quality gate.

- Phase 3: Section validation + retry
- Phase 4: Assembly + structural gate
- Phase 5: Quality gate (math + coverage + rubric)
"""

from __future__ import annotations

import json
import logging
import re

from app.llm_clients import LLMResponse, OpenAIClient
from app.mini_lessons.html_validator import (
    check_filler_phrases,
    check_full_lesson_structure,
    check_section_html,
    count_words,
)
from app.mini_lessons.models import (
    HARD_BUDGET_MULTIPLIER,
    SECTION_WORD_BUDGETS,
    LessonContext,
    LessonPlan,
    LessonSection,
    PhaseResult,
    QualityReport,
)
from app.mini_lessons.prompts.generation import (
    build_retry_prompt,
    extract_plan_section_for_block,
)
from app.mini_lessons.prompts.shared import build_lesson_context_section
from app.mini_lessons.prompts.validation import (
    build_quality_gate_prompt,
    build_section_math_prompt,
)

logger = logging.getLogger(__name__)

# Section types that need LLM math verification
_MATH_CHECK_SECTIONS = {"worked-example", "quick-check"}


# ===================================================================
# Phase 3 — Section Validation + Retry
# ===================================================================


class SectionValidator:
    """Validates sections (deterministic + LLM) with retry."""

    def __init__(
        self,
        client: OpenAIClient,
        max_retries: int = 1,
    ):
        self._client = client
        self._max_retries = max_retries

    def validate_sections(
        self,
        sections: list[LessonSection],
        ctx: LessonContext,
        plan: LessonPlan,
    ) -> tuple[PhaseResult, list[LessonSection]]:
        """Run Phase 3: validate each section, retry failures.

        Returns:
            Tuple of (PhaseResult, list of validated sections).
        """
        context_section = build_lesson_context_section(ctx)
        plan_data = plan.model_dump()
        validated: list[LessonSection] = []
        errors: list[str] = []

        for section in sections:
            result = self._validate_one(
                section, context_section, plan_data,
                ctx.template_type,
            )
            if result.validation_status == "passed":
                validated.append(result)
            else:
                errors.extend(result.validation_errors)
                logger.warning(
                    "Section %s failed validation: %s",
                    section.block_name,
                    result.validation_errors,
                )

        return PhaseResult(
            phase_name="section_validation",
            success=len(errors) == 0,
            data={"validated_count": len(validated)},
            errors=errors,
        ), validated

    def _validate_one(
        self,
        section: LessonSection,
        context_section: str,
        plan_data: dict,
        template_type: str,
    ) -> LessonSection:
        """Validate a single section with optional retry."""
        for attempt in range(1 + self._max_retries):
            det_errors = _deterministic_section_checks(section)
            llm_errors = self._llm_section_checks(section)
            all_errors = det_errors + llm_errors

            if not all_errors:
                section.validation_status = "passed"
                section.validation_errors = []
                return section

            if attempt < self._max_retries:
                logger.info(
                    "Retrying %s (attempt %d): %s",
                    section.block_name, attempt + 1, all_errors,
                )
                retried = self._retry_section(
                    section, context_section, plan_data,
                    template_type, all_errors,
                )
                if retried:
                    section = retried

        section.validation_status = "failed"
        section.validation_errors = all_errors
        return section

    def _llm_section_checks(
        self,
        section: LessonSection,
    ) -> list[str]:
        """Run LLM-based checks on a section."""
        if section.block_name not in _MATH_CHECK_SECTIONS:
            return []

        prompt = build_section_math_prompt(
            section.html, section.block_name,
        )
        try:
            resp: LLMResponse = self._client.call(
                prompt,
                response_format={"type": "json_object"},
                reasoning_effort="high",
            )
            data = json.loads(resp.text)
            if not data.get("math_correct", True):
                return data.get("errors", ["Math error detected"])
            return []
        except Exception as exc:
            logger.warning("LLM math check failed: %s", exc)
            return [f"LLM math check error: {exc}"]

    def _retry_section(
        self,
        section: LessonSection,
        context_section: str,
        plan_data: dict,
        template_type: str,
        errors: list[str],
    ) -> LessonSection | None:
        """Retry section generation with error feedback."""
        plan_section = extract_plan_section_for_block(
            plan_data, section.block_name, section.index,
        )
        prompt = build_retry_prompt(
            context_section=context_section,
            plan_section=plan_section,
            block_name=section.block_name,
            template_type=template_type,
            failed_html=section.html,
            validation_errors="\n".join(errors),
            index=section.index,
        )
        try:
            resp: LLMResponse = self._client.call(
                prompt,
                response_format={"type": "json_object"},
                reasoning_effort="medium",
            )
            data = json.loads(resp.text)
            html = data.get("html", "")
            return LessonSection(
                block_name=section.block_name,
                index=data.get("index", section.index),
                html=html,
                word_count=len(html.split()),
            )
        except Exception as exc:
            logger.warning("Section retry failed: %s", exc)
            return None


def _deterministic_section_checks(
    section: LessonSection,
) -> list[str]:
    """Run all deterministic checks on a single section."""
    errors: list[str] = []

    html_errors = check_section_html(
        section.html, section.block_name, section.index,
    )
    errors.extend(html_errors)

    budget = SECTION_WORD_BUDGETS.get(section.block_name, 200)
    hard_limit = int(budget * HARD_BUDGET_MULTIPLIER)
    word_count = count_words(section.html)
    if word_count > hard_limit:
        errors.append(
            f"Word count {word_count} exceeds hard limit "
            f"{hard_limit} (2x budget {budget}) for "
            f"{section.block_name}",
        )

    text = re.sub(r"<[^>]+>", " ", section.html)
    fillers = check_filler_phrases(text)
    if fillers:
        errors.append(
            f"Forbidden filler phrases: {', '.join(fillers)}",
        )

    return errors


# ===================================================================
# Phase 4 — Assembly + Structural Gate
# ===================================================================


_EDUCATIONAL_WPM = 160


def estimate_duration_minutes(html: str) -> float:
    """Estimate reading time for educational content with MathML.

    Uses ~160 wpm for educational content (slower than casual
    reading due to math, step-by-step reasoning, and MCQ
    interaction time).
    """
    words = count_words(html)
    return round(words / _EDUCATIONAL_WPM, 1)


def assemble_lesson(
    sections: list[LessonSection],
    atom_id: str,
    template_type: str,
) -> tuple[PhaseResult, str]:
    """Assemble validated sections into final HTML.

    Returns:
        Tuple of (PhaseResult, assembled HTML string).
    """
    inner_html = "\n\n  ".join(s.html for s in sections)

    full_html = (
        f'<article data-kind="mini-class"\n'
        f'         data-atom-id="{atom_id}"\n'
        f'         data-template="{template_type}">\n'
        f"  {inner_html}\n"
        f"</article>"
    )

    gate_errors = check_full_lesson_structure(full_html)
    if gate_errors:
        return PhaseResult(
            phase_name="assembly",
            success=False,
            errors=gate_errors,
        ), full_html

    warnings: list[str] = []
    duration = estimate_duration_minutes(full_html)
    if duration > 7:
        warnings.append(
            f"Estimated duration {duration} min exceeds "
            f"7 min target window",
        )

    return PhaseResult(
        phase_name="assembly",
        success=True,
        data={
            "html_length": len(full_html),
            "estimated_duration_min": duration,
        },
        warnings=warnings,
    ), full_html


def build_lesson_meta(
    atom_id: str,
    template_type: str,
    ctx: LessonContext,
    plan: LessonPlan,
    html: str = "",
) -> dict:
    """Build the mini-class.meta.json content with provenance."""
    from datetime import datetime, timezone

    meta: dict = {
        "atom_id": atom_id,
        "template_type": template_type,
        "eje": ctx.eje,
        "title": ctx.atom_title,
        "has_prerequisite_refresh": plan.include_prerequisite_refresh,
        "optional_sections": [
            s.block_name for s in plan.optional_sections
        ],
        "quick_check_count": len(plan.quick_checks),
        "provenance": {
            "model": "gpt-5.1",
            "reasoning_efforts": {
                "planning": "medium",
                "coherence_check": "low",
                "section_generation_text": "medium",
                "section_generation_math": "high",
                "math_verification": "high",
                "quality_gate": "high",
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "pipeline_version": "1.0.0",
        },
    }
    if html:
        meta["estimated_duration_min"] = (
            estimate_duration_minutes(html)
        )
    return meta


# ===================================================================
# Phase 5 — Quality Gate
# ===================================================================


class QualityGate:
    """Runs the final quality gate on the assembled lesson."""

    def __init__(self, client: OpenAIClient):
        self._client = client

    def evaluate(
        self,
        full_html: str,
        ctx: LessonContext,
    ) -> tuple[PhaseResult, QualityReport]:
        """Run Phase 5: math + coverage + rubric evaluation.

        Returns:
            Tuple of (PhaseResult, QualityReport).
        """
        in_scope, error_families, rubric = (
            _extract_enrichment_for_gate(ctx)
        )

        prompt = build_quality_gate_prompt(
            full_html=full_html,
            in_scope_items=in_scope,
            error_families=error_families,
            rubric=rubric,
        )

        report = QualityReport()

        try:
            resp: LLMResponse = self._client.call(
                prompt,
                response_format={"type": "json_object"},
                reasoning_effort="high",
            )
            data = json.loads(resp.text)
            report = QualityReport.model_validate(data)
        except Exception as exc:
            logger.error("Quality gate LLM call failed: %s", exc)
            report.auto_fail_triggered = True
            report.auto_fail_reasons.append(
                f"Quality gate error: {exc}",
            )

        report.publishable = _is_publishable(report)

        phase = PhaseResult(
            phase_name="quality_gate",
            success=report.publishable,
            data=report.model_dump(),
        )
        if not report.publishable:
            phase.errors = report.auto_fail_reasons

        return phase, report


def _extract_enrichment_for_gate(
    ctx: LessonContext,
) -> tuple[list[str], list[str], dict[str, list[str]]]:
    """Extract enrichment data needed for the quality gate."""
    if ctx.enrichment is None:
        return [], [], {}

    data = ctx.enrichment.model_dump()
    scope = data.get("scope_guardrails", {})
    in_scope = scope.get("in_scope", [])

    error_fams = data.get("error_families", [])
    error_names = [e.get("name", "") for e in error_fams]

    rubric = data.get("difficulty_rubric", {})

    return in_scope, error_names, rubric


def _is_publishable(report: QualityReport) -> bool:
    """Determine if the lesson meets publication criteria.

    Spec Gate 5: total >= 12/14 AND minimum 1/2 per dimension.
    """
    if report.auto_fail_triggered:
        return False
    if not report.math_correct:
        return False
    if not report.coverage_pass:
        return False
    if report.total_score < 12:
        return False
    for score in report.dimension_scores.values():
        if score < 1:
            return False
    return True


def identify_weak_sections(
    report: QualityReport,
    sections: list[LessonSection],
) -> list[LessonSection]:
    """Map low-scoring rubric dimensions to their sections."""
    dimension_to_blocks: dict[str, list[str]] = {
        "objective_clarity": ["objective"],
        "brevity_cognitive_load": [
            "concept", "worked-example", "error-patterns",
        ],
        "worked_example_correctness": ["worked-example"],
        "step_rationale_clarity": ["worked-example"],
        "quick_check_quality": ["quick-check"],
        "feedback_quality": ["quick-check"],
        "transition_readiness": ["transition-to-adaptive"],
    }
    weak_blocks: set[str] = set()
    for dim, score in report.dimension_scores.items():
        if score < 2:
            weak_blocks.update(
                dimension_to_blocks.get(dim, []),
            )
    return [
        s for s in sections if s.block_name in weak_blocks
    ]
