"""Phase 4 — Base QTI Generation (parallel, per-slot).

Generates one QTI 3.0 XML item per plan slot using parallel LLM
calls (ThreadPoolExecutor). Each slot is independent: generate,
validate XSD immediately, and retry with error feedback on failure.

Emits ``[PROGRESS] n/total`` markers to stdout so that the API
pipeline runner can update job progress in real time.

This phase is MANDATORY and BLOCKING (spec section 8, Phase 4).
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from app.llm_clients import OpenAIClient
from app.question_generation.models import (
    AtomContext,
    AtomEnrichment,
    GeneratedItem,
    PhaseResult,
    PlanSlot,
)
from app.question_generation.progress import report_progress
from app.question_generation.prompts.generation import (
    build_context_section,
    build_single_generation_prompt,
    build_xsd_retry_prompt,
)
from app.question_generation.validation_checks import validate_qti_xml

logger = logging.getLogger(__name__)

# LLM reasoning depth for generation (medium = structured output)
_GENERATION_REASONING = "medium"

# Max parallel LLM calls (bounded by OpenAI TPM/RPM limits)
_MAX_PARALLEL = 15


class BaseQtiGenerator:
    """Generates base QTI 3.0 XML items from plan slots (Phase 4).

    Each slot is processed independently in a thread pool:
    1. Build a single-slot prompt.
    2. Call the LLM.
    3. Validate XSD immediately.
    4. On XSD failure, retry with the specific errors (up to max_retries).

    Items are generated WITHOUT feedback or worked solutions.
    Those are added later in Phase 7 via QuestionPipeline.
    """

    def __init__(
        self,
        client: OpenAIClient,
        max_retries: int = 2,
    ) -> None:
        """Initialize the generator.

        Args:
            client: OpenAI client for LLM calls.
            max_retries: Max retry attempts per slot on XSD failure.
        """
        self._client = client
        self._max_retries = max_retries

    def generate(
        self,
        plan_slots: list[PlanSlot],
        atom_context: AtomContext,
        enrichment: AtomEnrichment | None = None,
        *,
        progress_offset: int = 0,
        total_override: int | None = None,
        on_item_complete: Callable[[GeneratedItem], None] | None = None,
    ) -> PhaseResult:
        """Generate base QTI XML items from plan slots in parallel.

        Args:
            plan_slots: Validated plan from Phase 3 (may be a
                subset when resuming a partial run).
            atom_context: Atom data for context.
            enrichment: Optional enrichment from Phase 1.
            progress_offset: Items already completed in a prior run.
                Progress reports start from this value so the
                runner sees e.g. ``[PROGRESS] 26/62``.
            total_override: Original total slot count. When set,
                progress denominator uses this instead of
                ``len(plan_slots)`` (useful on resume).
            on_item_complete: Optional callback invoked (under lock)
                after each successful item. Used by the pipeline to
                save incremental checkpoints so progress survives
                interruptions.

        Returns:
            PhaseResult with list[GeneratedItem] data.
        """
        batch_size = len(plan_slots)
        report_total = total_override or batch_size
        logger.info(
            "Phase 4: Generating %d base QTI items for atom %s "
            "(parallel=%d, offset=%d, total=%d)",
            batch_size, atom_context.atom_id, _MAX_PARALLEL,
            progress_offset, report_total,
        )

        # Build shared context once (reused by every slot call)
        context_section = build_context_section(
            atom_context, enrichment,
        )

        items: list[GeneratedItem] = []
        errors: list[str] = []
        completed = 0

        with ThreadPoolExecutor(max_workers=_MAX_PARALLEL) as pool:
            futures = {
                pool.submit(
                    self._generate_single_with_xsd,
                    slot,
                    context_section,
                    atom_context.atom_id,
                ): slot
                for slot in plan_slots
            }

            for future in as_completed(futures):
                slot = futures[future]
                completed += 1
                try:
                    item = future.result()
                    items.append(item)
                    if on_item_complete:
                        on_item_complete(item)
                    logger.info(
                        "Slot %d OK (%d/%d)",
                        slot.slot_index,
                        progress_offset + completed,
                        report_total,
                    )
                except Exception as exc:
                    errors.append(
                        f"Slot {slot.slot_index}: {exc}",
                    )
                    logger.warning(
                        "Slot %d FAILED (%d/%d): %s",
                        slot.slot_index,
                        progress_offset + completed,
                        report_total, exc,
                    )
                _report_progress(
                    progress_offset + completed, report_total,
                )

        logger.info(
            "Generation complete: %d succeeded, %d failed",
            len(items), len(errors),
        )

        return PhaseResult(
            phase_name="base_qti_generation",
            success=len(items) > 0,
            data=items,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Per-slot generation with immediate XSD validation
    # ------------------------------------------------------------------

    def _generate_single_with_xsd(
        self,
        slot: PlanSlot,
        context_section: str,
        atom_id: str,
    ) -> GeneratedItem:
        """Generate one QTI item, validate XSD, retry on failure.

        Args:
            slot: Plan slot specification.
            context_section: Shared atom+enrichment context text.
            atom_id: Atom identifier for item IDs.

        Returns:
            GeneratedItem with valid QTI XML.

        Raises:
            ValueError: If XSD validation fails after all retries.
        """
        prompt = build_single_generation_prompt(
            context_section, slot, atom_id,
        )

        for attempt in range(self._max_retries + 1):
            llm_resp = self._client.generate_text(
                prompt,
                response_mime_type="application/json",
                reasoning_effort=_GENERATION_REASONING,
            )
            item = _parse_single_response(
                llm_resp.text, atom_id, slot,
            )

            # Immediate XSD validation
            xsd_result = validate_qti_xml(item.qti_xml)
            if xsd_result.get("valid"):
                return item

            # XSD failed — build retry prompt with specific errors
            xsd_errors = xsd_result.get(
                "validation_errors", "unknown XSD error",
            )
            logger.warning(
                "Slot %d: XSD invalid (attempt %d/%d): %s",
                slot.slot_index,
                attempt + 1,
                self._max_retries + 1,
                xsd_errors[:200],
            )
            prompt = build_xsd_retry_prompt(
                context_section, slot, item.qti_xml,
                xsd_errors, atom_id,
            )

        msg = (
            f"Slot {slot.slot_index}: XSD invalid after "
            f"{self._max_retries + 1} attempts"
        )
        raise ValueError(msg)


# ------------------------------------------------------------------
# Response parsing helpers
# ------------------------------------------------------------------


def _parse_single_response(
    response: str,
    atom_id: str,
    slot: PlanSlot,
) -> GeneratedItem:
    """Parse a single-item LLM JSON response into a GeneratedItem.

    Expected format:
      {"slot_index": N, "qti_xml": "..."}
    For image slots also includes:
      {"slot_index": N, "qti_xml": "...", "image_description": "..."}

    Args:
        response: Raw JSON string from LLM.
        atom_id: Atom identifier for item IDs.
        slot: Original PlanSlot for fallback slot_index.

    Returns:
        GeneratedItem with cleaned QTI XML and optional
        image_description.

    Raises:
        json.JSONDecodeError: If response is not valid JSON.
        ValueError: If qti_xml is empty.
    """
    data: dict[str, Any] = json.loads(response)

    # Support both flat format and wrapped {"items": [...]} format
    if "items" in data and isinstance(data["items"], list):
        if not data["items"]:
            msg = "LLM returned empty items array"
            raise ValueError(msg)
        data = data["items"][0]

    qti_xml = data.get("qti_xml", "")
    if not qti_xml:
        msg = f"Slot {slot.slot_index}: LLM returned empty qti_xml"
        raise ValueError(msg)

    qti_xml = _extract_qti_xml(qti_xml)
    slot_idx = data.get("slot_index", slot.slot_index)
    item_id = f"{atom_id}_Q{slot_idx}"

    image_desc = data.get("image_description", "")

    return GeneratedItem(
        item_id=item_id,
        qti_xml=qti_xml,
        slot_index=slot_idx,
        image_description=image_desc,
    )


def _extract_qti_xml(text: str) -> str:
    """Extract QTI XML from potentially wrapped text.

    Handles markdown code blocks and extraneous content.

    Args:
        text: Raw text that may contain QTI XML.

    Returns:
        Clean QTI XML string.
    """
    cleaned = text.strip()

    # Remove markdown code blocks if present
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)

    # Extract QTI element if embedded in other text
    match = re.search(
        r"(<qti-assessment-item\b.*?</qti-assessment-item>)",
        cleaned,
        re.DOTALL,
    )
    if match:
        return match.group(1).strip()

    return cleaned.strip()


# ------------------------------------------------------------------
# Progress reporting
# ------------------------------------------------------------------


def _report_progress(completed: int, total: int) -> None:
    """Thin wrapper around shared report_progress (keeps local API)."""
    report_progress(completed, total)
