"""Batch request builders for the mini-lesson pipeline.

Creates BatchRequest objects ready for JSONL serialization and
OpenAI Batch API submission. Replicates the exact prompt logic
from each phase so batch responses match synchronous output.

Reuses BatchRequest and build_text_messages from the question
generation batch_api module (DRY).
"""

from __future__ import annotations

from app.mini_lessons.generator import (
    _build_image_map,
    reasoning_for_block,
)
from app.mini_lessons.helpers import extract_enrichment_for_gate
from app.mini_lessons.models import LessonContext, LessonPlan
from app.mini_lessons.prompts.generation import (
    build_section_prompt,
    extract_plan_section_for_block,
)
from app.mini_lessons.prompts.planning import (
    build_coherence_prompt,
    build_plan_prompt,
)
from app.mini_lessons.prompts.shared import build_lesson_context_section
from app.mini_lessons.prompts.validation import (
    build_quality_gate_prompt,
    build_section_math_prompt,
)
from app.question_generation.batch_api import (
    BatchRequest,
    build_text_messages,
)

_DEFAULT_MODEL = "gpt-5.1"


# ------------------------------------------------------------------
# Phase 1 — Planning
# ------------------------------------------------------------------


def build_plan_request(
    ctx: LessonContext,
    model: str = _DEFAULT_MODEL,
) -> BatchRequest:
    """Build a BatchRequest for lesson plan generation."""
    context_section = build_lesson_context_section(ctx)
    img_types = (
        ctx.enrichment.required_image_types
        if ctx.enrichment else None
    )
    prompt = build_plan_prompt(
        context_section, ctx.atom_id, ctx.template_type,
        required_image_types=img_types,
    )
    return BatchRequest(
        custom_id=f"ml-p1:{ctx.atom_id}",
        model=model,
        messages=build_text_messages(prompt),
        reasoning_effort="medium",
        response_format={"type": "json_object"},
    )


def build_coherence_request(
    plan_json: str,
    atom_summary: str,
    atom_id: str,
    model: str = _DEFAULT_MODEL,
) -> BatchRequest:
    """Build a BatchRequest for plan coherence check."""
    prompt = build_coherence_prompt(plan_json, atom_summary)
    return BatchRequest(
        custom_id=f"ml-coh:{atom_id}",
        model=model,
        messages=build_text_messages(prompt),
        reasoning_effort="low",
        response_format={"type": "json_object"},
    )


# ------------------------------------------------------------------
# Phase 2 — Section generation
# ------------------------------------------------------------------


def build_section_request(
    ctx: LessonContext,
    plan: LessonPlan,
    block_name: str,
    index: int | None,
    model: str = _DEFAULT_MODEL,
) -> BatchRequest:
    """Build a BatchRequest for a single section generation."""
    context_section = build_lesson_context_section(ctx)
    plan_section = extract_plan_section_for_block(
        plan.model_dump(), block_name, index,
    )
    image_map = _build_image_map(plan)
    image_entry = image_map.get(block_name)
    prompt = build_section_prompt(
        context_section=context_section,
        plan_section=plan_section,
        block_name=block_name,
        atom_id=ctx.atom_id,
        template_type=ctx.template_type,
        index=index,
        image_entry=image_entry,
    )
    idx_label = f":{index}" if index else ""
    return BatchRequest(
        custom_id=f"ml-p2:{ctx.atom_id}:{block_name}{idx_label}",
        model=model,
        messages=build_text_messages(prompt),
        reasoning_effort=reasoning_for_block(block_name),
        response_format={"type": "json_object"},
    )


# ------------------------------------------------------------------
# Phase 3 — Math verification
# ------------------------------------------------------------------


def build_math_check_request(
    section_html: str,
    block_name: str,
    atom_id: str,
    index: int | None = None,
    model: str = _DEFAULT_MODEL,
) -> BatchRequest:
    """Build a BatchRequest for section-level math checking."""
    prompt = build_section_math_prompt(section_html, block_name)
    idx_label = f":{index}" if index else ""
    return BatchRequest(
        custom_id=(
            f"ml-p3:{atom_id}:{block_name}{idx_label}"
        ),
        model=model,
        messages=build_text_messages(prompt),
        reasoning_effort="high",
        response_format={"type": "json_object"},
    )


# ------------------------------------------------------------------
# Phase 5 — Quality gate
# ------------------------------------------------------------------


def build_quality_gate_request(
    full_html: str,
    ctx: LessonContext,
    atom_id: str,
    plan: LessonPlan | None = None,
    model: str = _DEFAULT_MODEL,
) -> BatchRequest:
    """Build a BatchRequest for the full quality gate."""
    in_scope, error_families, rubric = (
        extract_enrichment_for_gate(ctx, plan=plan)
    )
    prompt = build_quality_gate_prompt(
        full_html=full_html,
        in_scope_items=in_scope,
        error_families=error_families,
        rubric=rubric,
    )
    return BatchRequest(
        custom_id=f"ml-p5:{atom_id}",
        model=model,
        messages=build_text_messages(prompt),
        reasoning_effort="high",
        response_format={"type": "json_object"},
    )


