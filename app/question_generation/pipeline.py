"""Atom question generation pipeline orchestrator.

Sequences all 11 phases (0-10) from the v3.1 spec, connecting
enrichment, planning, generation, validation, feedback, and sync.

Usage:
    from app.question_generation.pipeline import AtomQuestionPipeline

    pipeline = AtomQuestionPipeline()
    result = pipeline.run("A-M1-ALG-01-02")
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.llm_clients import OpenAIClient, load_default_openai_client
from app.question_feedback.pipeline import QuestionPipeline
from app.question_generation.enricher import AtomEnricher
from app.question_generation.exemplars import load_exemplars_for_atom
from app.question_generation.generator import BaseQtiGenerator
from app.question_generation.helpers import (
    build_pipeline_meta,
    load_atom,
    load_checkpoint,
    print_pipeline_header,
    print_pipeline_summary,
    save_checkpoint,
    save_pipeline_results,
)
from app.question_generation.models import (
    PHASE_GROUPS,
    AtomContext,
    AtomEnrichment,
    EnrichmentStatus,
    GeneratedItem,
    PhaseResult,
    PipelineConfig,
    PipelineResult,
    PlanSlot,
)
from app.question_generation.planner import PlanGenerator, validate_plan
from app.question_generation.syncer import QuestionSyncer
from app.question_generation.validators import (
    BaseValidator,
    DuplicateGate,
    FinalValidator,
)
from app.utils.paths import QUESTION_GENERATION_DIR

logger = logging.getLogger(__name__)


class AtomQuestionPipeline:
    """Orchestrates the full per-atom question generation pipeline.

    Phases 0-10 as defined in the v3.1 spec. Each phase is a
    private method that returns a PhaseResult. Gate phases
    short-circuit the pipeline on failure.
    """

    def __init__(
        self,
        config: PipelineConfig | None = None,
        client: OpenAIClient | None = None,
    ) -> None:
        """Initialize the pipeline with all component classes.

        Args:
            config: Pipeline configuration. Built from defaults if None.
            client: OpenAI client. Loaded from env if None.
        """
        self._config = config or PipelineConfig(atom_id="")
        self._client = client or load_default_openai_client()

        # Component classes (dependency injection)
        self._enricher = AtomEnricher(
            self._client, self._config.max_retries,
        )
        self._planner = PlanGenerator(
            self._client, self._config.max_retries,
        )
        self._generator = BaseQtiGenerator(
            self._client, self._config.max_retries,
        )
        self._dedupe_gate = DuplicateGate()
        self._base_validator = BaseValidator(self._client)
        self._final_validator = FinalValidator(self._client)
        self._feedback_pipeline = QuestionPipeline()
        self._syncer = QuestionSyncer()

    def run(self, atom_id: str) -> PipelineResult:
        """Run the pipeline for a single atom.

        Supports running all phases or a specific phase group
        (set via config.phase). When running a subset, prior
        phase outputs are loaded from checkpoints on disk.

        Args:
            atom_id: Target atom identifier.

        Returns:
            PipelineResult with all phase reports and final items.
        """
        self._config.atom_id = atom_id
        result = PipelineResult(atom_id=atom_id)
        output_dir = self._get_output_dir(atom_id)
        start, end = PHASE_GROUPS.get(
            self._config.phase, (0, 10),
        )

        print_pipeline_header(atom_id)

        # Phase 0-1 — Inputs + Enrichment
        ctx = self._phase_0_inputs(atom_id, result)
        if ctx is None:
            return result
        enrichment: AtomEnrichment | None = None
        if end >= 1:
            enrichment = self._phase_1_enrichment(ctx, result)
        if end <= 1:
            save_checkpoint(output_dir, 1, "enrichment", {
                "has_enrichment": enrichment is not None,
            })
            return self._finalize(result, output_dir)

        # Phases 2-3 — Plan Generation + Validation
        plan_slots = self._phase_2_3_plan(ctx, enrichment, result)
        if plan_slots is None:
            return result
        result.total_planned = len(plan_slots)
        save_checkpoint(output_dir, 3, "plan", {
            "slots": [s.model_dump() for s in plan_slots],
        })
        if end <= 3:
            return self._finalize(result, output_dir)

        # Phase 4 — Base QTI Generation
        base_items = self._phase_4_generation(
            plan_slots, ctx, enrichment, result,
        )
        if base_items is None:
            return result
        result.total_generated = len(base_items)
        save_checkpoint(output_dir, 4, "generation", {
            "item_count": len(base_items),
        })
        if end <= 4:
            return self._finalize(result, output_dir)

        # Phases 5-6 — Dedupe Gate + Base Validation
        deduped = self._phase_5_dedupe(base_items, result)
        if deduped is None:
            return result
        result.total_passed_dedupe = len(deduped)
        validated = self._phase_6_base_validation(deduped, ctx, result)
        if validated is None:
            return result
        result.total_passed_base_validation = len(validated)
        save_checkpoint(output_dir, 6, "base_validation", {
            "valid_count": len(validated),
        })
        if end <= 6:
            return self._finalize(result, output_dir)

        # Phases 7-8 — Feedback Enrichment
        enriched = self._phase_7_8_feedback(
            validated, output_dir, result,
        )
        if enriched is None:
            return result
        result.total_passed_feedback = len(enriched)
        save_checkpoint(output_dir, 8, "feedback", {
            "enriched_count": len(enriched),
        })
        if end <= 8:
            return self._finalize(result, output_dir)

        # Phases 9-10 — Final Validation + Sync
        final = self._phase_9_final_validation(enriched, ctx, result)
        if final is None:
            return result
        result.total_final = len(final)
        result.final_items = final
        self._phase_10_sync(final, atom_id, result)

        return self._finalize(result, output_dir)

    def _finalize(
        self,
        result: PipelineResult,
        output_dir: Path,
    ) -> PipelineResult:
        """Save results and print summary."""
        save_pipeline_results(output_dir, result)
        print_pipeline_summary(result)
        result.success = result.total_final > 0 or any(
            p.success for p in result.phase_results
        )
        return result

    # ------------------------------------------------------------------
    # Phase implementations
    # ------------------------------------------------------------------

    def _phase_0_inputs(
        self, atom_id: str, result: PipelineResult,
    ) -> AtomContext | None:
        """Phase 0: Load atom definition and exemplars."""
        logger.info("Phase 0: Loading inputs for atom %s", atom_id)

        atom = load_atom(atom_id)
        if atom is None:
            phase = PhaseResult(
                phase_name="inputs", success=False,
                errors=[f"Atom {atom_id} not found"],
            )
            result.phase_results.append(phase)
            return None

        exemplars = load_exemplars_for_atom(atom_id)

        ctx = AtomContext(
            atom_id=atom.id,
            atom_title=atom.titulo,
            atom_description=atom.descripcion,
            eje=atom.eje,
            standard_ids=atom.standard_ids,
            tipo_atomico=atom.tipo_atomico,
            criterios_atomicos=atom.criterios_atomicos,
            ejemplos_conceptuales=atom.ejemplos_conceptuales,
            notas_alcance=atom.notas_alcance,
            exemplars=exemplars,
        )

        result.phase_results.append(PhaseResult(
            phase_name="inputs", success=True,
            data={"exemplar_count": len(exemplars)},
        ))
        return ctx

    def _phase_1_enrichment(
        self, ctx: AtomContext, result: PipelineResult,
    ) -> AtomEnrichment | None:
        """Phase 1: Atom enrichment (non-blocking)."""
        if self._config.skip_enrichment:
            phase = PhaseResult(
                phase_name="atom_enrichment", success=True,
                data={"enrichment_status": EnrichmentStatus.MISSING},
                warnings=["Enrichment skipped by config"],
            )
            result.phase_results.append(phase)
            return None

        phase = self._enricher.enrich(ctx, ctx.exemplars)
        result.phase_results.append(phase)

        if phase.data and phase.data.get("enrichment"):
            return phase.data["enrichment"]
        return None

    def _phase_2_3_plan(
        self,
        ctx: AtomContext,
        enrichment: AtomEnrichment | None,
        result: PipelineResult,
    ) -> list[PlanSlot] | None:
        """Phases 2-3: Plan generation + validation."""
        # Phase 2: Generate plan
        gen_phase = self._planner.generate_plan(
            ctx, enrichment, self._config.pool_size,
        )
        result.phase_results.append(gen_phase)
        if not gen_phase.success:
            return None

        plan_slots: list[PlanSlot] = gen_phase.data

        # Phase 3: Validate plan
        val_phase = validate_plan(
            plan_slots, ctx, self._config.pool_size,
        )
        result.phase_results.append(val_phase)
        if not val_phase.success:
            return None

        return plan_slots

    def _phase_4_generation(
        self,
        slots: list[PlanSlot],
        ctx: AtomContext,
        enrichment: AtomEnrichment | None,
        result: PipelineResult,
    ) -> list[GeneratedItem] | None:
        """Phase 4: Base QTI generation."""
        phase = self._generator.generate(slots, ctx, enrichment)
        result.phase_results.append(phase)

        if not phase.success:
            return None

        items: list[GeneratedItem] = phase.data
        # Attach pipeline metadata from plan slots
        slot_map = {s.slot_index: s for s in slots}
        for item in items:
            slot = slot_map.get(item.slot_index)
            if slot:
                item.pipeline_meta = build_pipeline_meta(ctx.atom_id, slot)

        return items

    def _phase_5_dedupe(
        self,
        items: list[GeneratedItem],
        result: PipelineResult,
    ) -> list[GeneratedItem] | None:
        """Phase 5: Deterministic duplicate gate."""
        phase = self._dedupe_gate.run(items)
        result.phase_results.append(phase)

        if not phase.success:
            return None
        return phase.data["filtered_items"]

    def _phase_6_base_validation(
        self,
        items: list[GeneratedItem],
        ctx: AtomContext,
        result: PipelineResult,
    ) -> list[GeneratedItem] | None:
        """Phase 6: Base validation."""
        phase = self._base_validator.validate(items, ctx.exemplars)
        result.phase_results.append(phase)

        if not phase.success:
            return None
        return phase.data["valid_items"]

    def _phase_7_8_feedback(
        self,
        items: list[GeneratedItem],
        output_dir: Path,
        result: PipelineResult,
    ) -> list[GeneratedItem] | None:
        """Phases 7-8: Feedback enrichment via QuestionPipeline."""
        logger.info(
            "Phases 7-8: Feedback enrichment for %d items", len(items),
        )

        enriched: list[GeneratedItem] = []
        errors: list[str] = []

        for item in items:
            fb_result = self._feedback_pipeline.process(
                question_id=item.item_id,
                qti_xml=item.qti_xml,
                output_dir=None,
            )

            if fb_result.success and fb_result.qti_xml_final:
                item.qti_xml = fb_result.qti_xml_final
                enriched.append(item)
            else:
                errors.append(
                    f"{item.item_id}: feedback failed — "
                    f"{fb_result.stage_failed}: {fb_result.error}",
                )

        phase = PhaseResult(
            phase_name="feedback_enrichment",
            success=len(enriched) > 0,
            data={"enriched_items": enriched},
            errors=errors,
        )
        result.phase_results.append(phase)

        return enriched if enriched else None

    def _phase_9_final_validation(
        self,
        items: list[GeneratedItem],
        ctx: AtomContext,
        result: PipelineResult,
    ) -> list[GeneratedItem] | None:
        """Phase 9: Final validation."""
        phase = self._final_validator.validate(items, ctx.exemplars)
        result.phase_results.append(phase)

        if not phase.success:
            return None
        return phase.data["final_items"]

    def _phase_10_sync(
        self,
        items: list[GeneratedItem],
        atom_id: str,
        result: PipelineResult,
    ) -> None:
        """Phase 10: DB sync."""
        if self._config.skip_sync or self._config.dry_run:
            phase = PhaseResult(
                phase_name="db_sync", success=True,
                data={"skipped": True},
                warnings=["DB sync skipped by config"],
            )
            result.phase_results.append(phase)
            return

        phase = self._syncer.sync(
            items, atom_id, dry_run=False,
        )
        result.phase_results.append(phase)

        if phase.success:
            result.total_synced = len(items)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_output_dir(self, atom_id: str) -> Path:
        """Get the output directory for this atom's generation run."""
        if self._config.output_dir:
            return Path(self._config.output_dir)
        return QUESTION_GENERATION_DIR / atom_id
