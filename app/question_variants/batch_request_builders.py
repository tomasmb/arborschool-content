"""Batch request builders for the variant pipeline.

Each builder calls the corresponding extracted prompt function and wraps
the result in a BatchRequest object.  No LLM calls happen here; the
output is a list of BatchRequest objects ready for Batch API submission.
"""

from __future__ import annotations

import json

from app.question_feedback.prompts import FINAL_VALIDATION_PROMPT
from app.question_feedback.schemas import FINAL_VALIDATION_SCHEMA
from app.question_generation.batch_api import BatchRequest, build_text_messages
from app.question_generation.prompts.validation import build_solvability_prompt
from app.question_variants.generation_prompt import build_generation_prompt
from app.question_variants.models import (
    SourceQuestion,
    VariantBlueprint,
    VariantQuestion,
)
from app.question_variants.variant_planner import build_planning_prompt
from app.question_variants.variant_validator import build_validation_prompt

_DEFAULT_MODEL = "gpt-5.1"


# ------------------------------------------------------------------
# Phase 1 -- Planning
# ------------------------------------------------------------------


def build_plan_request(
    source: SourceQuestion,
    n: int,
    model: str = _DEFAULT_MODEL,
) -> BatchRequest:
    """Build a BatchRequest for the planning phase (1 per source question)."""
    prompt = build_planning_prompt(source, n)
    return BatchRequest(
        custom_id=f"plan:{source.test_id}__{source.question_id}",
        model=model,
        messages=build_text_messages(prompt),
        reasoning_effort="medium",
        response_format={"type": "json_object"},
    )


# ------------------------------------------------------------------
# Phase 2 -- Generation
# ------------------------------------------------------------------


def build_generation_request(
    source: SourceQuestion,
    blueprint: VariantBlueprint,
    model: str = _DEFAULT_MODEL,
    reasoning_effort: str = "medium",
) -> BatchRequest:
    """Build a BatchRequest for a single variant generation.

    One request per blueprint -- the batch will contain N * Q requests
    where N = variants per question and Q = number of source questions.
    """
    prompt = build_generation_prompt(source, 1, [blueprint])
    custom_id = (
        f"gen:{source.test_id}__{source.question_id}"
        f"__{blueprint.variant_id}"
    )
    return BatchRequest(
        custom_id=custom_id,
        model=model,
        messages=build_text_messages(prompt),
        reasoning_effort=reasoning_effort,
        response_format={"type": "json_object"},
        temperature=0.3,
    )


# ------------------------------------------------------------------
# Phase 4 -- Validation
# ------------------------------------------------------------------


def build_validation_request(
    variant: VariantQuestion,
    source: SourceQuestion,
    model: str = _DEFAULT_MODEL,
) -> BatchRequest:
    """Build a BatchRequest for the simplified 3-gate LLM validation."""
    prompt = build_validation_prompt(variant, source)
    custom_id = (
        f"val:{source.test_id}__{source.question_id}"
        f"__{variant.variant_id}"
    )
    return BatchRequest(
        custom_id=custom_id,
        model=model,
        messages=build_text_messages(prompt),
        reasoning_effort="medium",
        response_format={"type": "json_object"},
        temperature=0.0,
    )


# ------------------------------------------------------------------
# Phase 5 -- Solvability
# ------------------------------------------------------------------


def build_solvability_request(
    variant: VariantQuestion,
    model: str = _DEFAULT_MODEL,
) -> BatchRequest:
    """Build a BatchRequest for the solvability gate.

    The LLM independently solves the question and returns its answer
    so we can compare it to the declared correct option.
    """
    prompt = build_solvability_prompt(variant.qti_xml)
    custom_id = (
        f"solve:{variant.source_test_id}__{variant.source_question_id}"
        f"__{variant.variant_id}"
    )
    return BatchRequest(
        custom_id=custom_id,
        model=model,
        messages=build_text_messages(prompt),
        reasoning_effort="medium",
        response_format={"type": "json_object"},
        temperature=0.0,
    )


# ------------------------------------------------------------------
# Phase 7 -- Final Validation
# ------------------------------------------------------------------


def build_final_validation_request(
    variant: VariantQuestion,
    model: str = _DEFAULT_MODEL,
    image_urls: list[str] | None = None,
) -> BatchRequest:
    """Build a BatchRequest for the final comprehensive validation.

    Validates the enriched QTI XML (with feedback) for correctness,
    feedback quality, content quality, and math validity.
    """
    images_section = (
        "No hay imágenes adjuntas."
        if not image_urls
        else "\n".join(f"Imagen: {url}" for url in image_urls)
    )
    prompt = FINAL_VALIDATION_PROMPT.format(
        qti_xml_with_feedback=variant.qti_xml,
        images_section=images_section,
    )
    prompt += "\n\nRespuesta en formato JSON siguiendo este schema:\n"
    prompt += json.dumps(
        FINAL_VALIDATION_SCHEMA, indent=2, ensure_ascii=False,
    )

    custom_id = (
        f"fval:{variant.source_test_id}__{variant.source_question_id}"
        f"__{variant.variant_id}"
    )
    return BatchRequest(
        custom_id=custom_id,
        model=model,
        messages=build_text_messages(prompt),
        reasoning_effort="medium",
        response_format={"type": "json_object"},
        temperature=0.0,
    )


# ------------------------------------------------------------------
# Custom ID parsing
# ------------------------------------------------------------------


def parse_variant_custom_id(custom_id: str) -> dict[str, str]:
    """Parse a variant batch custom_id into its components.

    Format: "{phase}:{test_id}__{question_id}[__{variant_id}]"

    Returns a dict with keys: phase, test_id, question_id,
    and optionally variant_id.
    """
    phase, _, rest = custom_id.partition(":")
    parts = rest.split("__")
    result = {"phase": phase}
    if len(parts) >= 2:
        result["test_id"] = parts[0]
        result["question_id"] = parts[1]
    if len(parts) >= 3:
        result["variant_id"] = parts[2]
    return result
