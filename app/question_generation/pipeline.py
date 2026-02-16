"""Atom question generation pipeline orchestrator (v3.1 spec, phases 0-10)."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from app.llm_clients import OpenAIClient, load_default_openai_client
from app.question_feedback.models import (
    PipelineResult as FeedbackResult,
)
from app.question_feedback.pipeline import QuestionPipeline
from app.question_generation.artifacts import clean_stale_artifacts
from app.question_generation.enricher import AtomEnricher
from app.question_generation.exemplars import load_exemplars_for_atom
from app.question_generation.generator import BaseQtiGenerator
from app.question_generation.helpers import (
    check_prerequisites,
    find_resume_phase_group,
    load_atom,
    load_checkpoint,
    load_existing_fingerprints,
    load_phase_state,
    print_pipeline_header,
    print_pipeline_summary,
    save_checkpoint,
    save_pipeline_results,
    serialize_items,
)
from app.question_generation.image_generator import ImageGenerator
from app.question_generation.image_types import (
    can_generate_all,
    get_unsupported_types,
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
from app.question_generation.phase4_runner import run_phase_4
from app.question_generation.planner import PlanGenerator, validate_plan
from app.question_generation.syncer import (
    QuestionSyncer,
    persist_enrichment,
)
from app.question_generation.validators import (
    BaseValidator,
    DuplicateGate,
    FinalValidator,
)
from app.utils.paths import QUESTION_GENERATION_DIR

logger = logging.getLogger(__name__)

# Max parallel feedback enrichment calls (Phase 7-8)
_MAX_PARALLEL_FEEDBACK = 5


class AtomQuestionPipeline:
    """Orchestrates phases 0-10 of the per-atom question pipeline.

    Gate phases short-circuit on failure. Prerequisites are enforced
    when running individual phase groups.
    """

    def __init__(
        self,
        config: PipelineConfig | None = None,
        client: OpenAIClient | None = None,
    ) -> None:
        """Initialize with config and LLM client (defaults from env)."""
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
        self._image_generator = ImageGenerator(self._client)
        self._dedupe_gate = DuplicateGate()
        self._base_validator = BaseValidator(self._client)
        self._final_validator = FinalValidator(self._client)
        self._feedback_pipeline = QuestionPipeline()
        self._syncer = QuestionSyncer()

    def run(self, atom_id: str) -> PipelineResult:
        """Run the pipeline for a single atom.

        Supports phase groups via config.phase. Prerequisites are
        enforced: a phase group cannot run unless prior phases
        completed (checkpoint exists on disk).
        """
        self._config.atom_id = atom_id
        result = PipelineResult(atom_id=atom_id)
        output_dir = self._get_output_dir(atom_id)
        start, end = PHASE_GROUPS.get(
            self._config.phase, (0, 10),
        )

        # Resume: detect completed phases and skip ahead
        eff_phase = self._config.phase
        if self._config.resume and start == 0:
            rg = find_resume_phase_group(output_dir)
            if rg:
                eff_phase, start = rg, PHASE_GROUPS[rg][0]
                logger.info(
                    "Resuming: '%s' (phase %d)", rg, start,
                )

        print_pipeline_header(atom_id)

        # Clean downstream artifacts only for full reruns (not resume).
        # In resume mode, downstream checkpoints are preserved so
        # phases like validation can carry over already-passed items.
        if not self._config.resume:
            clean_stale_artifacts(atom_id, eff_phase)

        # Phase 0 — Inputs (always runs, no LLM)
        ctx = self._phase_0_inputs(atom_id, result)
        if ctx is None:
            return result

        # Prerequisite check + state loading when starting late
        enrichment: AtomEnrichment | None = None
        plan_slots: list[PlanSlot] | None = None
        base_items: list[GeneratedItem] | None = None

        if start > 0:
            ok, missing = check_prerequisites(
                eff_phase, output_dir,
            )
            if not ok:
                result.phase_results.append(PhaseResult(
                    phase_name="prerequisite_check",
                    success=False, errors=missing,
                ))
                return self._finalize(result, output_dir)
            state = load_phase_state(eff_phase, output_dir)
            enrichment = state.get("enrichment")
            plan_slots = state.get("plan_slots")
            base_items = state.get("items")

        # Phase 1 — Enrichment
        if start <= 1 and end >= 1:
            enrichment = self._phase_1_enrichment(ctx, result)
            if enrichment is not None:
                persist_enrichment(atom_id, enrichment)
            save_checkpoint(output_dir, 1, "enrichment", {
                "has_enrichment": enrichment is not None,
                "enrichment_data": enrichment.model_dump() if enrichment else None,
            })

        if end <= 1:
            return self._finalize(result, output_dir)

        # Generatability gate — block on unsupported image types
        if enrichment and enrichment.required_image_types:
            if not can_generate_all(enrichment.required_image_types):
                unsup = get_unsupported_types(enrichment.required_image_types)
                result.phase_results.append(PhaseResult(
                    phase_name="image_generatability_gate",
                    success=False, errors=[f"Unsupported: {unsup}"],
                ))
                return self._finalize(result, output_dir)

        # Phases 2-3 — Plan Generation + Validation
        if start <= 3 and plan_slots is None:
            plan_slots = self._phase_2_3_plan(
                ctx, enrichment, result,
            )
            if plan_slots is None:
                return result
            result.total_planned = len(plan_slots)
            save_checkpoint(output_dir, 3, "plan", {
                "slots": [s.model_dump() for s in plan_slots],
            })

        if end <= 3:
            return self._finalize(result, output_dir)

        # Phase 4 + 4b — Base QTI Generation + Images
        if start <= 4:
            base_items = run_phase_4(
                plan_slots=plan_slots,
                ctx=ctx,
                enrichment=enrichment,
                result=result,
                generator=self._generator,
                image_generator=self._image_generator,
                output_dir=output_dir,
                resume=self._config.resume,
                base_items=base_items,
            )
            if base_items is None:
                return result

        if end <= 4:
            return self._finalize(result, output_dir)

        # Phases 5-6 — Dedupe + Base Validation
        items = base_items or []
        existing_fps = load_existing_fingerprints(atom_id)
        deduped = self._phase_5_dedupe(
            items, result, existing_fingerprints=existing_fps,
        )
        if deduped is None:
            return result
        result.total_passed_dedupe = len(deduped)

        # Resume: carry over items already in phase 6 checkpoint
        carried: list[GeneratedItem] = []
        to_validate = deduped
        if self._config.resume:
            ckpt = load_checkpoint(output_dir, 6, "base_validation")
            if ckpt and ckpt.get("items"):
                prev = {it["item_id"] for it in ckpt["items"]
                        if isinstance(it, dict) and it.get("item_id")}
                carried = [it for it in deduped if it.item_id in prev]
                to_validate = [
                    it for it in deduped if it.item_id not in prev
                ]
                if carried:
                    logger.info("Phase 6 resume: %d carried, %d new",
                                len(carried), len(to_validate))
        if to_validate:
            newly_valid = self._phase_6_base_validation(
                to_validate, ctx, result,
            )
            validated = carried + (newly_valid or [])
        elif carried:
            logger.info("Phase 6: all %d items already validated",
                        len(carried))
            result.phase_results.append(PhaseResult(
                phase_name="base_validation", success=True,
                data={"valid_items": carried},
            ))
            validated = carried
        else:
            validated = None

        if not validated:
            return result
        result.total_passed_base_validation = len(validated)
        save_checkpoint(output_dir, 6, "base_validation", {
            "valid_count": len(validated),
            "items": serialize_items(validated),
        })

        if end <= 6:
            return self._finalize(result, output_dir)

        # Phases 7-8 — Feedback Enrichment
        enriched = self._phase_7_8_feedback(validated, result)
        if enriched is None:
            return result
        result.total_passed_feedback = len(enriched)
        save_checkpoint(output_dir, 8, "feedback", {
            "enriched_count": len(enriched),
            "items": serialize_items(enriched),
        })

        if end <= 8:
            return self._finalize(result, output_dir)

        # Phases 9-10 — Final Validation + Sync
        final = self._phase_9_final_validation(
            enriched, ctx, result,
        )
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
        dist = self._config.planned_distribution

        # Phase 2: Generate plan
        gen_phase = self._planner.generate_plan(
            ctx, enrichment, dist,
        )
        result.phase_results.append(gen_phase)
        if not gen_phase.success:
            return None

        plan_slots: list[PlanSlot] = gen_phase.data

        # Phase 3: Validate plan
        val_phase = validate_plan(plan_slots, ctx, dist)
        result.phase_results.append(val_phase)
        if not val_phase.success:
            return None

        return plan_slots

    def _phase_5_dedupe(
        self,
        items: list[GeneratedItem],
        result: PipelineResult,
        existing_fingerprints: set[str] | None = None,
    ) -> list[GeneratedItem] | None:
        """Phase 5: Deterministic duplicate gate."""
        phase = self._dedupe_gate.run(
            items,
            existing_fingerprints=existing_fingerprints,
            pool_total=result.total_planned or len(items),
        )
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
        self, items: list[GeneratedItem], result: PipelineResult,
    ) -> list[GeneratedItem] | None:
        """Phases 7-8: Feedback enrichment (parallel)."""
        logger.info("Phases 7-8: Feedback for %d items (parallel=%d)",
                     len(items), _MAX_PARALLEL_FEEDBACK)
        enriched: list[GeneratedItem] = []
        errors: list[str] = []
        with ThreadPoolExecutor(max_workers=_MAX_PARALLEL_FEEDBACK) as pool:
            futures = {
                pool.submit(self._enrich_single_item, item): item
                for item in items
            }
            for future in as_completed(futures):
                item = futures[future]
                fb = future.result()
                if fb.success and fb.qti_xml_final:
                    item.qti_xml = fb.qti_xml_final
                    enriched.append(item)
                else:
                    errors.append(
                        f"{item.item_id}: {fb.stage_failed}: {fb.error}",
                    )
        phase = PhaseResult(
            phase_name="feedback_enrichment",
            success=len(enriched) > 0,
            data={"enriched_items": enriched}, errors=errors,
        )
        result.phase_results.append(phase)
        return enriched if enriched else None

    def _enrich_single_item(self, item: GeneratedItem) -> FeedbackResult:
        """Run feedback enrichment on a single item."""
        return self._feedback_pipeline.process(
            question_id=item.item_id,
            qti_xml=item.qti_xml,
            output_dir=None,
        )

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

    def _get_output_dir(self, atom_id: str) -> Path:
        """Get the output directory for this atom's generation run."""
        if self._config.output_dir:
            return Path(self._config.output_dir)
        return QUESTION_GENERATION_DIR / atom_id
