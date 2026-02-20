"""Phase-specific response processors for the batch pipeline.

Each processor takes the raw BatchResponse list for a phase and converts
the results into the same data structures used by the synchronous pipeline.
Also includes the retry-request builders for multi-round phases (Phase 4
XSD retry, Phase 7-8 correction cycle).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.question_generation.batch_api import BatchResponse
from app.question_generation.batch_request_builders import (
    build_correction_request,
    build_review_request,
    build_xsd_retry_request,
    parse_custom_id,
)
from app.question_generation.models import (
    AtomEnrichment,
    GeneratedItem,
    PlanSlot,
)
from app.question_generation.image_types import filter_valid_types
from app.question_generation.validation_checks import (
    extract_correct_option,
    normalize_option_letter,
    validate_qti_xml,
)
from app.question_feedback.models import (
    CheckResult,
    CheckStatus,
    FeedbackReviewResult,
)

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Phase 1 — Enrichment response processing
# ------------------------------------------------------------------


def process_enrichment_responses(
    responses: list[BatchResponse],
) -> dict[str, AtomEnrichment | None]:
    """Parse enrichment responses.  Returns atom_id -> enrichment."""
    results: dict[str, AtomEnrichment | None] = {}
    for resp in responses:
        parsed = parse_custom_id(resp.custom_id)
        atom_id = parsed["atom_id"]

        if resp.error:
            logger.warning(
                "Enrichment failed for %s: %s", atom_id, resp.error,
            )
            results[atom_id] = None
            continue

        try:
            data = json.loads(resp.text)
            enrichment = AtomEnrichment.model_validate(data)
            raw_types = enrichment.required_image_types
            enrichment.required_image_types = filter_valid_types(
                raw_types,
            )
            results[atom_id] = enrichment
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                "Enrichment parse error for %s: %s", atom_id, exc,
            )
            results[atom_id] = None

    return results


# ------------------------------------------------------------------
# Phase 2 — Plan response processing
# ------------------------------------------------------------------


def process_plan_responses(
    responses: list[BatchResponse],
) -> tuple[dict[str, list[PlanSlot]], dict[str, str]]:
    """Parse plan responses.

    Returns (atom_id -> plan_slots, atom_id -> error_reason).
    """
    plans: dict[str, list[PlanSlot]] = {}
    failures: dict[str, str] = {}

    for resp in responses:
        parsed = parse_custom_id(resp.custom_id)
        atom_id = parsed["atom_id"]

        if resp.error:
            failures[atom_id] = f"Batch error: {resp.error}"
            continue

        try:
            data = json.loads(resp.text)
            raw_slots = data.get("plan", [])
            if not raw_slots:
                failures[atom_id] = "Empty plan from LLM"
                continue
            plans[atom_id] = [
                PlanSlot.model_validate(s) for s in raw_slots
            ]
        except (json.JSONDecodeError, ValueError) as exc:
            failures[atom_id] = f"Parse error: {exc}"

    return plans, failures


# ------------------------------------------------------------------
# Phase 4 — Generation response processing + XSD retry
# ------------------------------------------------------------------


def process_generation_responses(
    responses: list[BatchResponse],
    slot_maps: dict[str, dict[int, PlanSlot]],
) -> tuple[dict[str, list[GeneratedItem]], dict[str, list[PlanSlot]]]:
    """Parse generation responses and XSD-validate each item.

    Returns:
        succeeded: atom_id -> list of valid GeneratedItems
        xsd_failed: atom_id -> list of PlanSlots that need retry
    """
    succeeded: dict[str, list[GeneratedItem]] = {}
    xsd_failed: dict[str, list[PlanSlot]] = {}
    xsd_errors_map: dict[str, dict[int, tuple[str, str]]] = {}

    for resp in responses:
        parsed = parse_custom_id(resp.custom_id)
        atom_id = parsed["atom_id"]
        slot_idx = int(parsed.get("slot_index", "0"))
        slots = slot_maps.get(atom_id, {})
        slot = slots.get(slot_idx)

        if not slot:
            logger.warning(
                "No slot found for %s", resp.custom_id,
            )
            continue

        if resp.error:
            xsd_failed.setdefault(atom_id, []).append(slot)
            xsd_errors_map.setdefault(atom_id, {})[slot_idx] = (
                "", f"Batch error: {resp.error}",
            )
            continue

        try:
            item = _parse_generation_response(
                resp.text, atom_id, slot,
            )
            xsd_result = validate_qti_xml(item.qti_xml)
            if xsd_result.get("valid"):
                succeeded.setdefault(atom_id, []).append(item)
            else:
                xsd_errors = str(
                    xsd_result.get("validation_errors", ""),
                )
                xsd_failed.setdefault(atom_id, []).append(slot)
                xsd_errors_map.setdefault(
                    atom_id, {},
                )[slot_idx] = (item.qti_xml, xsd_errors)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                "Parse error for %s: %s", resp.custom_id, exc,
            )
            xsd_failed.setdefault(atom_id, []).append(slot)

    return succeeded, xsd_failed


def build_xsd_retry_requests(
    xsd_failed: dict[str, list[PlanSlot]],
    context_sections: dict[str, str],
    xsd_errors_map: dict[str, dict[int, tuple[str, str]]],
    attempt: int,
    model: str = "gpt-5.1",
) -> list[Any]:
    """Build retry requests for slots that failed XSD validation."""
    from app.question_generation.batch_api import BatchRequest

    requests: list[BatchRequest] = []
    for atom_id, slots in xsd_failed.items():
        ctx_section = context_sections.get(atom_id, "")
        errors_for_atom = xsd_errors_map.get(atom_id, {})
        for slot in slots:
            failed_xml, xsd_errs = errors_for_atom.get(
                slot.slot_index, ("", "XSD validation failed"),
            )
            requests.append(build_xsd_retry_request(
                slot, ctx_section, atom_id,
                failed_xml, xsd_errs, attempt, model,
            ))
    return requests


# ------------------------------------------------------------------
# Phase 6 — Solvability response processing
# ------------------------------------------------------------------


def process_solvability_responses(
    responses: list[BatchResponse],
    items_by_id: dict[str, GeneratedItem],
) -> tuple[list[GeneratedItem], list[str]]:
    """Parse solvability check responses.

    Returns (passed_items, error_messages).
    """
    passed: list[GeneratedItem] = []
    errors: list[str] = []

    for resp in responses:
        parsed = parse_custom_id(resp.custom_id)
        item_id = parsed.get("item_id", "")
        item = items_by_id.get(item_id)

        if not item:
            errors.append(f"Unknown item_id in {resp.custom_id}")
            continue

        if resp.error:
            errors.append(
                f"{item_id}: Batch error: {resp.error}",
            )
            continue

        error = _check_solvability_result(resp.text, item)
        if error:
            errors.append(f"{item_id}: {error}")
        else:
            passed.append(item)

    return passed, errors


def _check_solvability_result(
    text: str,
    item: GeneratedItem,
) -> str | None:
    """Check solvability result against declared answer."""
    try:
        result = json.loads(text)
        raw_answer = result.get("answer", "").strip()
    except (json.JSONDecodeError, ValueError) as exc:
        return f"Solvability parse error: {exc}"

    model_letter = normalize_option_letter(raw_answer)
    if not model_letter:
        return (
            f"Could not parse model answer "
            f"'{raw_answer}' into A-D"
        )

    declared = extract_correct_option(item.qti_xml)
    if not declared:
        return "Could not extract declared correct option"

    if model_letter != declared:
        steps = result.get("steps", "no steps provided")
        return (
            f"Solvability mismatch: model={model_letter}, "
            f"declared={declared} — {steps}"
        )
    return None


# ------------------------------------------------------------------
# Phase 7-8 — Enhancement + Review response processing
# ------------------------------------------------------------------


def process_enhancement_responses(
    responses: list[BatchResponse],
    items_by_id: dict[str, GeneratedItem],
) -> tuple[dict[str, GeneratedItem], dict[str, str]]:
    """Parse enhancement responses, XSD-validate each.

    Returns (item_id -> updated GeneratedItem, item_id -> error).
    """
    succeeded: dict[str, GeneratedItem] = {}
    failures: dict[str, str] = {}

    for resp in responses:
        parsed = parse_custom_id(resp.custom_id)
        item_id = parsed.get("item_id", "")
        item = items_by_id.get(item_id)

        if not item:
            failures[item_id] = f"Unknown item: {resp.custom_id}"
            continue

        if resp.error:
            failures[item_id] = f"Batch error: {resp.error}"
            continue

        try:
            xml = _extract_qti_xml(resp.text)
            xsd_result = validate_qti_xml(xml)
            if xsd_result.get("valid"):
                item.qti_xml = xml
                succeeded[item_id] = item
            else:
                xsd_err = xsd_result.get(
                    "validation_errors", "XSD failed",
                )
                failures[item_id] = f"XSD: {xsd_err}"
        except Exception as exc:
            failures[item_id] = f"Parse error: {exc}"

    return succeeded, failures


def process_review_responses(
    responses: list[BatchResponse],
) -> tuple[dict[str, str], dict[str, str]]:
    """Parse review responses.

    Returns:
        passed: item_id -> "pass"
        failed_with_issues: item_id -> issues_string
    """
    passed: dict[str, str] = {}
    failed_with_issues: dict[str, str] = {}

    for resp in responses:
        parsed = parse_custom_id(resp.custom_id)
        item_id = parsed.get("item_id", "")

        if resp.error:
            failed_with_issues[item_id] = resp.error
            continue

        try:
            result = json.loads(resp.text)
            verdict = result.get("review_result", "fail")
            if verdict == "pass":
                passed[item_id] = "pass"
            else:
                issues = _extract_review_issues(result)
                failed_with_issues[item_id] = issues
        except (json.JSONDecodeError, ValueError) as exc:
            failed_with_issues[item_id] = str(exc)

    return passed, failed_with_issues


def _extract_review_issues(result: dict[str, Any]) -> str:
    """Extract human-readable issues string from review result."""
    issues: list[str] = []
    for key in (
        "feedback_accuracy", "feedback_clarity", "formatting_check",
    ):
        section = result.get(key, {})
        section_issues = section.get("issues", [])
        if section_issues:
            issues.extend(section_issues)
    if not issues:
        issues.append(
            result.get("overall_reasoning", "Review failed"),
        )
    return "; ".join(issues)


# ------------------------------------------------------------------
# Phase 9 — Final validation response processing
# ------------------------------------------------------------------


def process_final_validation_responses(
    responses: list[BatchResponse],
    items_by_id: dict[str, GeneratedItem],
) -> tuple[list[GeneratedItem], list[str]]:
    """Parse final validation responses.

    Returns (passed_items, error_messages).
    """
    passed: list[GeneratedItem] = []
    errors: list[str] = []

    for resp in responses:
        parsed = parse_custom_id(resp.custom_id)
        item_id = parsed.get("item_id", "")
        item = items_by_id.get(item_id)

        if not item:
            errors.append(f"Unknown item: {resp.custom_id}")
            continue

        if resp.error:
            errors.append(f"{item_id}: {resp.error}")
            continue

        try:
            result = json.loads(resp.text)
            verdict = result.get("validation_result", "fail")
            if verdict == "pass":
                passed.append(item)
            else:
                reason = result.get(
                    "overall_reasoning", "Validation failed",
                )
                errors.append(f"{item_id}: {reason}")
        except (json.JSONDecodeError, ValueError) as exc:
            errors.append(f"{item_id}: Parse error: {exc}")

    return passed, errors


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _parse_generation_response(
    text: str,
    atom_id: str,
    slot: PlanSlot,
) -> GeneratedItem:
    """Parse a generation response into a GeneratedItem.

    Replicates generator._parse_single_response logic.
    """
    data: dict[str, Any] = json.loads(text)

    if "items" in data and isinstance(data["items"], list):
        if not data["items"]:
            raise ValueError("Empty items array")
        data = data["items"][0]

    qti_xml = data.get("qti_xml", "")
    if not qti_xml:
        raise ValueError(f"Slot {slot.slot_index}: empty qti_xml")

    qti_xml = _extract_qti_xml(qti_xml)
    slot_idx = data.get("slot_index", slot.slot_index)
    image_desc = data.get("image_description", "")

    return GeneratedItem(
        item_id=f"{atom_id}_Q{slot_idx}",
        qti_xml=qti_xml,
        slot_index=slot_idx,
        image_description=image_desc,
    )


def _extract_qti_xml(text: str) -> str:
    """Extract QTI XML from potentially wrapped text."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)
    if "<qti-assessment-item" in cleaned:
        start = cleaned.index("<qti-assessment-item")
        end_tag = "</qti-assessment-item>"
        end = cleaned.rindex(end_tag) + len(end_tag)
        cleaned = cleaned[start:end]
    return cleaned.strip()
