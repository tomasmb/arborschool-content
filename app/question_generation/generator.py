"""Phase 4 — Base QTI Generation.

Materializes plan slots into base QTI 3.0 XML items (stem + options +
correct response). Does NOT add feedback or worked solutions.
This phase is MANDATORY and BLOCKING (spec section 8, Phase 4).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.llm_clients import GeminiService
from app.question_generation.models import (
    AtomContext,
    AtomEnrichment,
    GeneratedItem,
    PhaseResult,
    PlanSlot,
)
from app.question_generation.prompts.generation import (
    BASE_QTI_GENERATION_PROMPT,
    build_slots_section,
)
from app.question_generation.prompts.planning import (
    build_enrichment_section,
)

logger = logging.getLogger(__name__)


class BaseQtiGenerator:
    """Generates base QTI 3.0 XML items from plan slots (Phase 4).

    Items are generated WITHOUT feedback or worked solutions.
    Those are added later in Phase 7 via QuestionPipeline.
    """

    def __init__(
        self,
        gemini: GeminiService,
        max_retries: int = 2,
    ) -> None:
        """Initialize the generator.

        Args:
            gemini: Gemini service for LLM calls.
            max_retries: Max retry attempts on failure.
        """
        self._gemini = gemini
        self._max_retries = max_retries

    def generate(
        self,
        plan_slots: list[PlanSlot],
        atom_context: AtomContext,
        enrichment: AtomEnrichment | None = None,
    ) -> PhaseResult:
        """Generate base QTI XML items from plan slots.

        Args:
            plan_slots: Validated plan from Phase 3.
            atom_context: Atom data for context.
            enrichment: Optional enrichment from Phase 1.

        Returns:
            PhaseResult with list[GeneratedItem] data.
        """
        logger.info(
            "Phase 4: Generating %d base QTI items for atom %s",
            len(plan_slots), atom_context.atom_id,
        )

        prompt = self._build_prompt(
            plan_slots, atom_context, enrichment,
        )

        for attempt in range(self._max_retries + 1):
            try:
                response = self._gemini.generate_text(
                    prompt,
                    response_mime_type="application/json",
                    temperature=0.0,
                )
                items = self._parse_response(
                    response, atom_context.atom_id, plan_slots,
                )

                logger.info("Generated %d base items", len(items))
                return PhaseResult(
                    phase_name="base_qti_generation",
                    success=True,
                    data=items,
                )

            except (json.JSONDecodeError, ValueError) as exc:
                logger.warning(
                    "Generation attempt %d failed: %s",
                    attempt + 1, exc,
                )
                if attempt == self._max_retries:
                    return PhaseResult(
                        phase_name="base_qti_generation",
                        success=False,
                        errors=[
                            f"Base QTI generation failed after "
                            f"{attempt + 1} attempts: {exc}",
                        ],
                    )

        return PhaseResult(
            phase_name="base_qti_generation",
            success=False,
            errors=["Max retries exceeded"],
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        slots: list[PlanSlot],
        ctx: AtomContext,
        enrichment: AtomEnrichment | None,
    ) -> str:
        """Build the QTI generation prompt."""
        return BASE_QTI_GENERATION_PROMPT.format(
            atom_id=ctx.atom_id,
            atom_title=ctx.atom_title,
            atom_description=ctx.atom_description,
            eje=ctx.eje,
            criterios_atomicos=", ".join(ctx.criterios_atomicos),
            enrichment_section=build_enrichment_section(enrichment),
            num_items=len(slots),
            slots_section=build_slots_section(slots),
        )

    def _parse_response(
        self,
        response: str,
        atom_id: str,
        plan_slots: list[PlanSlot],
    ) -> list[GeneratedItem]:
        """Parse the LLM response into GeneratedItem objects.

        Args:
            response: Raw JSON from LLM.
            atom_id: Atom identifier for item IDs.
            plan_slots: Original plan for metadata.

        Returns:
            List of GeneratedItem with QTI XML.

        Raises:
            json.JSONDecodeError: Invalid JSON.
            ValueError: Missing items or XML.
        """
        data: dict[str, Any] = json.loads(response)
        raw_items = data.get("items", [])

        if not raw_items:
            msg = "LLM returned no items"
            raise ValueError(msg)

        items: list[GeneratedItem] = []

        for raw in raw_items:
            slot_idx = raw.get("slot_index", 0)
            qti_xml = raw.get("qti_xml", "")

            if not qti_xml:
                logger.warning("Slot %d: empty QTI XML, skipping", slot_idx)
                continue

            # Clean XML from any markdown wrapping
            qti_xml = _extract_qti_xml(qti_xml)

            item_id = f"{atom_id}_Q{slot_idx}"
            items.append(
                GeneratedItem(
                    item_id=item_id,
                    qti_xml=qti_xml,
                    slot_index=slot_idx,
                ),
            )

        return items


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
