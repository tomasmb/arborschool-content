"""Batch request builders — create BatchRequest objects for each pipeline phase.

Each builder replicates the exact prompt-construction logic from the
corresponding phase module so that Batch API responses are identical to
what the synchronous pipeline would produce.

No LLM calls happen here; the output is a list of BatchRequest objects
ready for JSONL serialization and Batch API submission.
"""

from __future__ import annotations

import json
from typing import Any

from app.question_generation.batch_api import (
    BatchRequest,
    build_multimodal_messages,
    build_text_messages,
)
from app.question_generation.image_types import (
    ALL_SPECS,
    NOT_IMAGES_DESCRIPTION,
    build_image_type_catalog,
)
from app.question_generation.models import (
    AtomContext,
    AtomEnrichment,
    DifficultyDistribution,
    GeneratedItem,
    PlanSlot,
)
from app.question_generation.planner import skeleton_repetition_cap
from app.question_generation.prompts.enrichment import (
    ATOM_ENRICHMENT_PROMPT,
    build_exemplars_section,
)
from app.question_generation.prompts.generation import (
    build_context_section,
    build_single_generation_prompt,
    build_xsd_retry_prompt,
)
from app.question_generation.prompts.planning import (
    PLAN_GENERATION_PROMPT,
    build_difficulty_distribution,
    build_enrichment_section,
    build_image_instruction,
)
from app.question_generation.prompts.validation import (
    SOLVABILITY_PROMPT,
)
from app.question_feedback.prompts import (
    FEEDBACK_CORRECTION_PROMPT,
    FEEDBACK_ENHANCEMENT_PROMPT,
    FINAL_VALIDATION_PROMPT,
    FEEDBACK_REVIEW_PROMPT,
)
from app.question_feedback.schemas import (
    FEEDBACK_REVIEW_SCHEMA,
    FINAL_VALIDATION_SCHEMA,
)
from app.question_generation.prompts.reference_examples import (
    FEEDBACK_QTI_REFERENCE,
)

_DEFAULT_MODEL = "gpt-5.1"


# ------------------------------------------------------------------
# Phase 1 — Enrichment
# ------------------------------------------------------------------


def build_enrichment_request(
    ctx: AtomContext,
    model: str = _DEFAULT_MODEL,
) -> BatchRequest:
    """Build a BatchRequest for Phase 1 atom enrichment."""
    prompt = ATOM_ENRICHMENT_PROMPT.format(
        atom_id=ctx.atom_id,
        atom_title=ctx.atom_title,
        atom_description=ctx.atom_description,
        eje=ctx.eje,
        tipo_atomico=ctx.tipo_atomico,
        criterios_atomicos=", ".join(ctx.criterios_atomicos),
        ejemplos_conceptuales=", ".join(
            ctx.ejemplos_conceptuales,
        ),
        notas_alcance=", ".join(ctx.notas_alcance) or "N/A",
        standard_ids=", ".join(ctx.standard_ids),
        exemplars_section=build_exemplars_section(ctx.exemplars),
        image_type_catalog=build_image_type_catalog(
            ALL_SPECS, group_by_generatability=True,
        ),
        not_images_description=NOT_IMAGES_DESCRIPTION,
    )
    return BatchRequest(
        custom_id=f"p1:{ctx.atom_id}",
        model=model,
        messages=build_text_messages(prompt),
        reasoning_effort="low",
        response_format={"type": "json_object"},
    )


# ------------------------------------------------------------------
# Phase 2 — Plan Generation
# ------------------------------------------------------------------


def build_plan_request(
    ctx: AtomContext,
    enrichment: AtomEnrichment | None,
    distribution: DifficultyDistribution,
    model: str = _DEFAULT_MODEL,
) -> BatchRequest:
    """Build a BatchRequest for Phase 2 plan generation."""
    image_types = (
        enrichment.required_image_types if enrichment else None
    )
    image_instruction, image_rules = build_image_instruction(
        image_types,
    )
    prompt = PLAN_GENERATION_PROMPT.format(
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
    return BatchRequest(
        custom_id=f"p2:{ctx.atom_id}",
        model=model,
        messages=build_text_messages(prompt),
        reasoning_effort="medium",
        response_format={"type": "json_object"},
    )


# ------------------------------------------------------------------
# Phase 4 — Base QTI Generation
# ------------------------------------------------------------------


def build_generation_request(
    slot: PlanSlot,
    context_section: str,
    atom_id: str,
    model: str = _DEFAULT_MODEL,
) -> BatchRequest:
    """Build a BatchRequest for Phase 4 single-slot generation."""
    prompt = build_single_generation_prompt(
        context_section, slot, atom_id,
    )
    return BatchRequest(
        custom_id=f"p4:{atom_id}:s{slot.slot_index}",
        model=model,
        messages=build_text_messages(prompt),
        reasoning_effort="medium",
        response_format={"type": "json_object"},
    )


def build_xsd_retry_request(
    slot: PlanSlot,
    context_section: str,
    atom_id: str,
    failed_xml: str,
    xsd_errors: str,
    attempt: int,
    model: str = _DEFAULT_MODEL,
) -> BatchRequest:
    """Build a BatchRequest for Phase 4 XSD retry."""
    prompt = build_xsd_retry_prompt(
        context_section, slot, failed_xml, xsd_errors, atom_id,
    )
    return BatchRequest(
        custom_id=(
            f"p4:{atom_id}:s{slot.slot_index}:r{attempt}"
        ),
        model=model,
        messages=build_text_messages(prompt),
        reasoning_effort="medium",
        response_format={"type": "json_object"},
    )


# ------------------------------------------------------------------
# Phase 6 — Base Validation (solvability check)
# ------------------------------------------------------------------


def build_solvability_request(
    item: GeneratedItem,
    atom_id: str,
    model: str = _DEFAULT_MODEL,
) -> BatchRequest:
    """Build a BatchRequest for Phase 6 solvability check."""
    prompt = SOLVABILITY_PROMPT.format(qti_xml=item.qti_xml)
    return BatchRequest(
        custom_id=f"p6:{atom_id}:{item.item_id}",
        model=model,
        messages=build_text_messages(prompt),
        reasoning_effort="medium",
        response_format={"type": "json_object"},
    )


# ------------------------------------------------------------------
# Phase 7-8 — Feedback Enhancement
# ------------------------------------------------------------------


def build_enhancement_request(
    item: GeneratedItem,
    atom_id: str,
    images_section: str = "",
    image_b64s: list[str] | None = None,
    model: str = _DEFAULT_MODEL,
) -> BatchRequest:
    """Build a BatchRequest for Phase 7 feedback enhancement."""
    prompt = FEEDBACK_ENHANCEMENT_PROMPT.format(
        original_qti_xml=item.qti_xml,
        images_section=images_section,
        feedback_reference_example=FEEDBACK_QTI_REFERENCE,
    )
    if image_b64s:
        messages = build_multimodal_messages(prompt, image_b64s)
    else:
        messages = build_text_messages(prompt)

    return BatchRequest(
        custom_id=f"p7e:{atom_id}:{item.item_id}",
        model=model,
        messages=messages,
        reasoning_effort="low",
    )


def build_correction_request(
    item: GeneratedItem,
    atom_id: str,
    review_issues: str,
    images_section: str = "",
    image_b64s: list[str] | None = None,
    model: str = _DEFAULT_MODEL,
) -> BatchRequest:
    """Build a BatchRequest for Phase 7 feedback correction."""
    prompt = FEEDBACK_CORRECTION_PROMPT.format(
        qti_xml_with_errors=item.qti_xml,
        images_section=images_section,
        review_issues=review_issues,
    )
    if image_b64s:
        messages = build_multimodal_messages(prompt, image_b64s)
    else:
        messages = build_text_messages(prompt)

    return BatchRequest(
        custom_id=f"p7c:{atom_id}:{item.item_id}",
        model=model,
        messages=messages,
        reasoning_effort="low",
    )


# ------------------------------------------------------------------
# Phase 7-8 — Feedback Review
# ------------------------------------------------------------------


def build_review_request(
    item: GeneratedItem,
    atom_id: str,
    model: str = _DEFAULT_MODEL,
) -> BatchRequest:
    """Build a BatchRequest for Phase 8 feedback review."""
    prompt = FEEDBACK_REVIEW_PROMPT.format(
        qti_xml_with_feedback=item.qti_xml,
    )
    prompt += (
        "\n\nResponde en formato JSON siguiendo este schema:\n"
    )
    prompt += json.dumps(
        FEEDBACK_REVIEW_SCHEMA, indent=2, ensure_ascii=False,
    )
    return BatchRequest(
        custom_id=f"p7r:{atom_id}:{item.item_id}",
        model=model,
        messages=build_text_messages(prompt),
        response_format={"type": "json_object"},
        temperature=0.0,
    )


# ------------------------------------------------------------------
# Phase 9 — Final Validation
# ------------------------------------------------------------------


def build_final_validation_request(
    item: GeneratedItem,
    atom_id: str,
    images_section: str = "",
    image_b64s: list[str] | None = None,
    model: str = _DEFAULT_MODEL,
) -> BatchRequest:
    """Build a BatchRequest for Phase 9 final validation."""
    prompt = FINAL_VALIDATION_PROMPT.format(
        qti_xml_with_feedback=item.qti_xml,
        images_section=images_section,
    )
    prompt += (
        "\n\nRespuesta en formato JSON siguiendo este schema:\n"
    )
    prompt += json.dumps(
        FINAL_VALIDATION_SCHEMA, indent=2, ensure_ascii=False,
    )
    if image_b64s:
        messages = build_multimodal_messages(prompt, image_b64s)
    else:
        messages = build_text_messages(prompt)

    return BatchRequest(
        custom_id=f"p9:{atom_id}:{item.item_id}",
        model=model,
        messages=messages,
        reasoning_effort="medium",
        response_format={"type": "json_object"},
    )


# ------------------------------------------------------------------
# Custom ID parsing
# ------------------------------------------------------------------


def parse_custom_id(custom_id: str) -> dict[str, str]:
    """Parse a custom_id into its components.

    Returns a dict with at least 'phase' and 'atom_id' keys.
    Phase 4 also has 'slot_index' (and optionally 'attempt').
    Phase 6/7/9 also has 'item_id'.

    Raises ValueError if the format is unrecognized.
    """
    parts = custom_id.split(":")
    if len(parts) < 2:
        raise ValueError(f"Invalid custom_id: {custom_id}")

    phase = parts[0]
    atom_id = parts[1]
    result: dict[str, str] = {
        "phase": phase, "atom_id": atom_id,
    }

    if phase == "p4" and len(parts) >= 3:
        result["slot_index"] = parts[2].lstrip("s")
        if len(parts) >= 4:
            result["attempt"] = parts[3].lstrip("r")
    elif phase in ("p6", "p7e", "p7r", "p7c", "p9"):
        if len(parts) >= 3:
            result["item_id"] = parts[2]

    return result
