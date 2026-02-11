"""Phase 1 — Atom Enrichment.

Generates pedagogical enrichment data for an atom using an LLM.
The enrichment phase is MANDATORY to run but its output is NON-BLOCKING:
the pipeline proceeds even if enrichment fails (spec section 5).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.llm_clients import OpenAIClient
from app.question_generation.models import (
    AtomContext,
    AtomEnrichment,
    EnrichmentStatus,
    Exemplar,
    PhaseResult,
)
from app.question_generation.image_types import (
    NOT_IMAGES_DESCRIPTION,
    build_image_type_catalog,
    filter_valid_types,
)
from app.question_generation.prompts.enrichment import (
    ATOM_ENRICHMENT_PROMPT,
    build_exemplars_section,
)

logger = logging.getLogger(__name__)


_ENRICHMENT_REASONING = "low"


class AtomEnricher:
    """Generates atom enrichment via LLM (Phase 1).

    The enrichment provides scope guardrails, difficulty rubrics,
    and pedagogical guidance for downstream plan generation.
    """

    def __init__(
        self,
        client: OpenAIClient,
        max_retries: int = 2,
    ) -> None:
        """Initialize the enricher.

        Args:
            client: OpenAI client for LLM calls.
            max_retries: Maximum retry attempts on failure.
        """
        self._client = client
        self._max_retries = max_retries

    def enrich(
        self,
        atom_context: AtomContext,
        exemplars: list[Exemplar] | None = None,
    ) -> PhaseResult:
        """Generate enrichment for an atom.

        This phase is mandatory to run but non-blocking:
        - On success: returns enrichment + status "present"
        - On failure: returns status "failed" with warnings (not errors)

        Args:
            atom_context: Atom data from Phase 0.
            exemplars: Optional exemplars for context.

        Returns:
            PhaseResult with AtomEnrichment data or failure info.
        """
        logger.info("Phase 1: Enriching atom %s", atom_context.atom_id)

        prompt = self._build_prompt(atom_context, exemplars or [])

        for attempt in range(self._max_retries + 1):
            logger.info(
                "Enrichment attempt %d/%d",
                attempt + 1, self._max_retries + 1,
            )

            try:
                response = self._client.generate_text(
                    prompt,
                    response_mime_type="application/json",
                    reasoning_effort=_ENRICHMENT_REASONING,
                )
                enrichment = self._parse_response(response)

                logger.info(
                    "Enrichment succeeded for atom %s",
                    atom_context.atom_id,
                )
                return PhaseResult(
                    phase_name="atom_enrichment",
                    success=True,
                    data={
                        "enrichment": enrichment,
                        "enrichment_status": EnrichmentStatus.PRESENT,
                    },
                )

            except (json.JSONDecodeError, ValueError, KeyError) as exc:
                logger.warning(
                    "Enrichment attempt %d parse error: %s",
                    attempt + 1, exc,
                )
                if attempt == self._max_retries:
                    return self._failure_result(
                        f"Parse error after {attempt + 1} attempts: {exc}",
                    )

            except Exception as exc:
                logger.warning(
                    "Enrichment attempt %d failed: %s",
                    attempt + 1, exc,
                )
                if attempt == self._max_retries:
                    return self._failure_result(
                        f"LLM error after {attempt + 1} attempts: {exc}",
                    )

        return self._failure_result("Max retries exceeded")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        ctx: AtomContext,
        exemplars: list[Exemplar],
    ) -> str:
        """Build the enrichment prompt from atom context.

        Args:
            ctx: Atom context data.
            exemplars: Exemplar questions for reference.

        Returns:
            Formatted prompt string.
        """
        return ATOM_ENRICHMENT_PROMPT.format(
            atom_id=ctx.atom_id,
            atom_title=ctx.atom_title,
            atom_description=ctx.atom_description,
            eje=ctx.eje,
            tipo_atomico=ctx.tipo_atomico,
            criterios_atomicos=", ".join(ctx.criterios_atomicos),
            ejemplos_conceptuales=", ".join(ctx.ejemplos_conceptuales),
            notas_alcance=", ".join(ctx.notas_alcance) or "N/A",
            standard_ids=", ".join(ctx.standard_ids),
            exemplars_section=build_exemplars_section(exemplars),
            image_type_catalog=build_image_type_catalog(),
            not_images_description=NOT_IMAGES_DESCRIPTION,
        )

    def _parse_response(self, response: str) -> AtomEnrichment:
        """Parse and validate the LLM enrichment response.

        Validates required_image_types against the known taxonomy,
        stripping any unrecognized values.

        Args:
            response: Raw JSON string from LLM.

        Returns:
            Validated AtomEnrichment object.

        Raises:
            json.JSONDecodeError: If response is not valid JSON.
            ValueError: If JSON doesn't match expected schema.
        """
        data: dict[str, Any] = json.loads(response)
        enrichment = AtomEnrichment.model_validate(data)

        # Filter image types to only recognized values
        raw_types = enrichment.required_image_types
        enrichment.required_image_types = filter_valid_types(raw_types)
        if len(raw_types) != len(enrichment.required_image_types):
            stripped = set(raw_types) - set(enrichment.required_image_types)
            logger.warning(
                "Stripped unrecognized image types: %s", stripped,
            )

        return enrichment

    def _failure_result(self, warning_msg: str) -> PhaseResult:
        """Build a non-blocking failure result.

        Enrichment failures are warnings, not errors, because
        the phase output is non-blocking (spec section 5.2).

        Args:
            warning_msg: Description of the failure.

        Returns:
            PhaseResult with success=True (non-blocking) but no data.
        """
        logger.warning("Enrichment failed (non-blocking): %s", warning_msg)
        return PhaseResult(
            phase_name="atom_enrichment",
            success=True,  # Non-blocking: pipeline continues
            data={
                "enrichment": None,
                "enrichment_status": EnrichmentStatus.FAILED,
            },
            warnings=[warning_msg],
        )
