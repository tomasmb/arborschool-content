"""Phase 5 solvability gate -- dedicated independent solve check.

Reuses the solvability prompt and answer-parsing helpers from
``app.question_generation`` (DRY) and exposes:

- ``parse_solvability_response``  -- pure parser shared by sync & batch
- ``check_solvability_sync``      -- sync single-variant checker
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.question_generation.prompts.validation import (
    build_solvability_prompt,
)
from app.question_generation.validation_checks import (
    extract_correct_option,
    normalize_option_letter,
)
from app.question_variants.models import VariantQuestion

logger = logging.getLogger(__name__)

SOLVABILITY_REASONING = "medium"


def parse_solvability_response(
    raw_json: str,
    variant: VariantQuestion,
) -> tuple[bool, str]:
    """Parse a solvability LLM response and compare to declared answer.

    Returns (passed, reason).  *reason* is empty on success.
    Pure function -- shared by the sync validator and the batch
    response processor.
    """
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        return False, f"JSON parse error: {exc}"

    raw_answer = data.get("answer", "").strip()
    model_letter = normalize_option_letter(raw_answer)
    if not model_letter:
        return False, (
            f"Could not normalise model answer '{raw_answer}' to A-D"
        )

    declared = extract_correct_option(variant.qti_xml)
    if not declared:
        return False, (
            "Could not extract declared correct option from QTI XML"
        )

    if model_letter != declared:
        steps = data.get("steps", "no steps provided")
        return False, (
            f"Solvability mismatch: model={model_letter}, "
            f"declared={declared} — {steps}"
        )

    return True, ""


def check_solvability_sync(
    variant: VariantQuestion,
    client: Any,
) -> tuple[bool, str]:
    """Run a solvability check via a synchronous LLM call.

    *client* must expose ``generate_text(prompt, **kwargs) -> resp``
    where ``resp.text`` (or ``str(resp)``) contains the JSON payload.

    Returns (passed, reason).
    """
    prompt = build_solvability_prompt(variant.qti_xml)
    try:
        resp = client.generate_text(
            prompt,
            response_mime_type="application/json",
            reasoning_effort=SOLVABILITY_REASONING,
        )
        raw = resp.text if hasattr(resp, "text") else str(resp)
        return parse_solvability_response(raw, variant)
    except Exception as exc:
        logger.warning(
            "Solvability LLM error for %s: %s",
            variant.variant_id, exc,
        )
        return False, f"Solvability LLM error: {exc}"
