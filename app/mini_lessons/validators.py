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
from app.mini_lessons.helpers import extract_enrichment_for_gate
from app.mini_lessons.html_validator import (
    check_decimal_notation,
    check_filler_phrases,
    check_full_lesson_structure,
    check_section_html,
    count_words,
)
from app.mini_lessons.models import (
    HARD_BUDGET_MULTIPLIER,
    SECTION_WORD_BUDGETS,
    ImagePlanEntry,
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
    build_garbled_text_prompt,
    build_quality_gate_prompt,
    build_section_math_prompt,
)

logger = logging.getLogger(__name__)

_MATH_CHECK_SECTIONS = {"worked-example"}
_IMAGE_PLACEHOLDER = "IMAGE_PLACEHOLDER"
_IMG_TAG_PATTERN = re.compile(r"<img\s[^>]*src=", re.IGNORECASE)


def _has_img_tag(html: str) -> bool:
    """Return True if the HTML contains an <img> tag with a src."""
    return bool(_IMG_TAG_PATTERN.search(html))


def _llm_check(
    client: OpenAIClient, prompt: str,
    pass_key: str, block: str, *, effort: str = "low",
) -> list[str]:
    """Generic LLM validation check; returns errors when *pass_key* is False."""
    try:
        resp: LLMResponse = client.call(
            prompt,
            response_format={"type": "json_object"},
            reasoning_effort=effort,
        )
        data = json.loads(resp.text)
        if not data.get(pass_key, True):
            return (
                data.get("errors", [])
                or data.get("issues", [])
                or [f"{pass_key} failed: {block}"]
            )
        return []
    except Exception as exc:
        logger.warning("LLM check %s failed: %s", pass_key, exc)
        return [f"LLM check error ({pass_key}): {exc}"]


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
        """Run Phase 3: validate each section, retry failures."""
        context_section = build_lesson_context_section(ctx)
        plan_data = plan.model_dump()
        image_map = _build_image_map(plan)
        validated: list[LessonSection] = []
        errors: list[str] = []

        for section in sections:
            ie = image_map.get(section.block_name)
            result = self._validate_one(
                section, context_section, plan_data,
                ctx.template_type, image_entry=ie,
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
        image_entry: ImagePlanEntry | None = None,
    ) -> LessonSection:
        """Validate a single section with optional retry."""
        for attempt in range(1 + self._max_retries):
            det_errors = deterministic_section_checks(section)
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
                    image_entry=image_entry,
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
        """Run LLM-based checks: garbled text (all) + math (worked-example)."""
        errors = _llm_check(
            self._client,
            build_garbled_text_prompt(section.html),
            "text_clean", section.block_name, effort="low",
        )
        if section.block_name in _MATH_CHECK_SECTIONS:
            errors.extend(_llm_check(
                self._client,
                build_section_math_prompt(
                    section.html, section.block_name,
                ),
                "math_correct", section.block_name,
                effort="high",
            ))
        return errors

    def _retry_section(
        self,
        section: LessonSection,
        context_section: str,
        plan_data: dict,
        template_type: str,
        errors: list[str],
        image_entry: ImagePlanEntry | None = None,
    ) -> LessonSection | None:
        """Retry section generation; preserves image_description + img tag."""
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
            image_entry=image_entry,
        )
        try:
            resp: LLMResponse = self._client.call(
                prompt,
                response_format={"type": "json_object"},
                reasoning_effort="medium",
            )
            data = json.loads(resp.text)
            html = data.get("html", "")
            retried = LessonSection(
                block_name=section.block_name,
                index=data.get("index", section.index),
                html=html,
                word_count=count_words(html),
                image_description=section.image_description,
            )
            if section.image_description and not _has_img_tag(retried.html):
                retried.image_failed = True
                logger.warning(
                    "Retry of %s dropped <img> tag — "
                    "marked image_failed",
                    section.block_name,
                )
            return retried
        except Exception as exc:
            logger.warning("Section retry failed: %s", exc)
            return None


def _build_image_map(plan: LessonPlan) -> dict[str, ImagePlanEntry]:
    """Map target_section -> ImagePlanEntry for quick lookup."""
    m: dict[str, ImagePlanEntry] = {}
    for e in plan.image_plan:
        m.setdefault(e.target_section, e)
    return m


def deterministic_section_checks(
    section: LessonSection,
) -> list[str]:
    """Run all deterministic checks on a single section."""
    errors: list[str] = []

    html_errors = check_section_html(
        section.html, section.block_name, section.index,
    )
    errors.extend(html_errors)

    budget = SECTION_WORD_BUDGETS.get(section.block_name, 180)
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

    errors.extend(check_decimal_notation(section.html))

    if _IMAGE_PLACEHOLDER in section.html:
        errors.append(
            f"Section {section.block_name} still contains "
            f"IMAGE_PLACEHOLDER — image generation failed or "
            f"was not run",
        )

    return errors


# ===================================================================
# Phase 4 — Assembly + Structural Gate
# ===================================================================

_EDUCATIONAL_WPM = 120


def estimate_duration_minutes(html: str) -> float:
    """Estimate reading time (~120 wpm for math-heavy educational content)."""
    return round(count_words(html) / _EDUCATIONAL_WPM, 1)


def assemble_lesson(
    sections: list[LessonSection],
    atom_id: str,
    template_type: str,
) -> tuple[PhaseResult, str]:
    """Assemble validated sections into final HTML."""
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
    if duration > 4:
        warnings.append(
            f"Estimated duration {duration} min exceeds "
            f"4 min target window",
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
    sections: list[LessonSection] | None = None,
) -> dict:
    """Build the mini-class.meta.json content with provenance."""
    from datetime import datetime, timezone

    image_failures = [
        s.block_name for s in (sections or [])
        if s.image_failed
    ]
    meta: dict = {
        "atom_id": atom_id,
        "template_type": template_type,
        "eje": ctx.eje,
        "title": ctx.atom_title,
        "has_prerequisite_refresh": plan.include_prerequisite_refresh,
        "planned_images": [
            e.target_section for e in plan.image_plan
        ],
        "image_failures": image_failures,
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
            "pipeline_version": "2.1.0",
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
        plan: LessonPlan | None = None,
        image_failures: list[str] | None = None,
    ) -> tuple[PhaseResult, QualityReport]:
        """Run Phase 5: math + coverage + rubric evaluation.

        Uses plan's selected families for coverage check when
        provided. ``image_failures`` flags sections with missing images.
        """
        in_scope, error_families, rubric = (
            extract_enrichment_for_gate(ctx, plan=plan)
        )

        prompt = build_quality_gate_prompt(
            full_html=full_html,
            in_scope_items=in_scope,
            error_families=error_families,
            rubric=rubric,
            image_failures=image_failures,
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


def _is_publishable(report: QualityReport) -> bool:
    """Determine if the lesson meets publication criteria.

    4 dimensions x 2 max each = 8 total.
    Every dimension must score 2/2 -- no partial credit.
    """
    if report.auto_fail_triggered:
        return False
    if not report.math_correct:
        return False
    if not report.coverage_pass:
        return False
    if report.total_score < 8:
        return False
    for score in report.dimension_scores.values():
        if score < 2:
            return False
    return True


def identify_weak_sections(
    report: QualityReport,
    sections: list[LessonSection],
) -> list[LessonSection]:
    """Map low-scoring rubric dimensions to their sections."""
    dimension_to_blocks: dict[str, list[str]] = {
        "objective_clarity": ["objective"],
        "brevity_cognitive_load": ["concept", "worked-example"],
        "worked_example_correctness": ["worked-example"],
        "step_rationale_clarity": ["worked-example"],
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
