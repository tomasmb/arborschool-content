"""Atom question generation pipeline orchestrator (v3.1 spec, phases 0-9)."""

from __future__ import annotations

import logging
from pathlib import Path

from app.llm_clients import (
    OpenAIClient,
    clear_cost_accumulator,
    load_default_openai_client,
    set_cost_accumulator,
)
from app.question_feedback.pipeline import QuestionPipeline
from app.question_generation.artifacts import clean_stale_artifacts
from app.question_generation.enricher import AtomEnricher
from app.question_generation.exemplars import load_exemplars_for_atom
from app.question_generation.generator import BaseQtiGenerator
from app.question_generation.helpers import (
    check_prerequisites,
    deserialize_items,
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
from app.question_generation.phase8_runner import run_feedback
from app.question_generation.planner import PlanGenerator, validate_plan
from app.question_generation.progress import CostAccumulator
from app.question_generation.syncer import persist_enrichment
from app.question_generation.validators import (
    BaseValidator,
    DuplicateGate,
    FinalValidator,
)
from app.utils.paths import QUESTION_GENERATION_DIR

logger = logging.getLogger(__name__)


def _split_carried(
    incoming: list[GeneratedItem],
    output_dir: Path,
    phase_num: int,
    phase_name: str,
    label: str,
) -> tuple[list[GeneratedItem], list[GeneratedItem]]:
    """Split items into carried (from checkpoint) vs to-process.

    Uses the checkpoint version of carried items so that validator
    statuses from the completed phase are preserved.
    """
    ckpt = load_checkpoint(output_dir, phase_num, phase_name)
    if not ckpt or not ckpt.get("items"):
        return [], incoming

    prev_map = {
        it.item_id: it
        for it in deserialize_items(ckpt["items"])
    }
    incoming_ids = {it.item_id for it in incoming}
    carried = [
        prev_map[iid]
        for iid in incoming_ids
        if iid in prev_map
    ]
    carried_ids = {it.item_id for it in carried}
    to_process = [
        it for it in incoming
        if it.item_id not in carried_ids
    ]
    if carried:
        logger.info(
            "%s resume: %d carried, %d new",
            label, len(carried), len(to_process),
        )
    return carried, to_process


class AtomQuestionPipeline:
    """Orchestrates phases 0-9 of the per-atom question pipeline.

    DB sync is handled separately via the sync API, not inline.
    """

    def __init__(
        self,
        config: PipelineConfig | None = None,
        client: OpenAIClient | None = None,
    ) -> None:
        self._config = config or PipelineConfig(atom_id="")
        self._client = client or load_default_openai_client()
        retries = self._config.max_retries
        self._enricher = AtomEnricher(self._client, retries)
        self._planner = PlanGenerator(self._client, retries)
        self._generator = BaseQtiGenerator(self._client, retries)
        self._image_generator = ImageGenerator(self._client)
        self._dedupe_gate = DuplicateGate()
        self._base_validator = BaseValidator(self._client)
        self._final_validator = FinalValidator(self._client)
        self._feedback_pipeline = QuestionPipeline()

    def run(self, atom_id: str) -> PipelineResult:
        """Run the pipeline for a single atom."""
        self._config.atom_id = atom_id
        result = PipelineResult(atom_id=atom_id)
        self._cost_acc = CostAccumulator()
        set_cost_accumulator(self._cost_acc)
        output_dir = self._get_output_dir(atom_id)
        start, end = PHASE_GROUPS.get(self._config.phase, (0, 9))

        eff_phase = self._config.phase
        if self._config.resume and start == 0:
            rg = find_resume_phase_group(output_dir)
            if rg:
                eff_phase, start = rg, PHASE_GROUPS[rg][0]
                logger.info("Resuming: '%s' (phase %d)", rg, start)

        print_pipeline_header(atom_id)
        if not self._config.resume:
            clean_stale_artifacts(atom_id, eff_phase)

        ctx = self._phase_0_inputs(atom_id, result)
        if ctx is None:
            return result

        enrichment: AtomEnrichment | None = None
        plan_slots: list[PlanSlot] | None = None
        base_items: list[GeneratedItem] | None = None
        if start > 0:
            ok, missing = check_prerequisites(eff_phase, output_dir)
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

        if (
            not self._config.skip_images
            and enrichment
            and enrichment.required_image_types
        ):
            if not can_generate_all(enrichment.required_image_types):
                unsup = get_unsupported_types(
                    enrichment.required_image_types,
                )
                result.phase_results.append(PhaseResult(
                    phase_name="image_generatability_gate",
                    success=False,
                    errors=[f"Unsupported: {unsup}"],
                ))
                return self._finalize(result, output_dir)

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
                skip_images=self._config.skip_images,
            )
            if base_items is None:
                return result

        if end <= 4:
            return self._finalize(result, output_dir)

        if self._config.resume and base_items and plan_slots:
            base_items = self._retry_failed_images(
                base_items, plan_slots, ctx, result, output_dir,
            )

        validated: list[GeneratedItem] | None = None
        if start <= 6:
            items = base_items or []
            existing_fps = load_existing_fingerprints(atom_id)
            deduped = self._phase_5_dedupe(
                items, result, existing_fingerprints=existing_fps,
            )
            if deduped is None:
                return result
            result.total_passed_dedupe = len(deduped)

            carried: list[GeneratedItem] = []
            to_validate = deduped
            if self._config.resume:
                carried, to_validate = _split_carried(
                    deduped, output_dir, 6,
                    "base_validation", "Phase 6",
                )
            if to_validate:
                newly_valid = self._phase_6_base_validation(
                    to_validate, ctx, result,
                )
                validated = carried + (newly_valid or [])
            elif carried:
                logger.info(
                    "Phase 6: all %d items already validated",
                    len(carried),
                )
                result.phase_results.append(PhaseResult(
                    phase_name="base_validation", success=True,
                    data={"valid_items": carried},
                ))
                validated = carried

            if not validated:
                return result
            result.total_passed_base_validation = len(validated)
            save_checkpoint(output_dir, 6, "base_validation", {
                "valid_count": len(validated),
                "items": serialize_items(validated),
            })
        else:
            validated = base_items

        if end <= 6:
            return self._finalize(result, output_dir)

        enriched: list[GeneratedItem] | None = None
        if start <= 8:
            if not validated:
                return result
            enriched = run_feedback(
                validated, result, self._feedback_pipeline,
                resume=self._config.resume,
                output_dir=output_dir,
            )
            if enriched is None:
                return result
            result.total_passed_feedback = len(enriched)
        else:
            enriched = base_items

        if end <= 8:
            return self._finalize(result, output_dir)

        if not enriched:
            return result

        carried_final: list[GeneratedItem] = []
        to_final_validate = enriched
        if self._config.resume:
            carried_final, to_final_validate = _split_carried(
                enriched, output_dir, 9,
                "final_validation", "Phase 9",
            )

        if to_final_validate:
            newly_final = self._phase_9_final_validation(
                to_final_validate, ctx, result,
            )
            final = carried_final + (newly_final or [])
        elif carried_final:
            logger.info(
                "Phase 9: all %d items already validated",
                len(carried_final),
            )
            result.phase_results.append(PhaseResult(
                phase_name="final_validation", success=True,
                data={"final_items": carried_final},
            ))
            final = carried_final
        else:
            final = None

        if final is None:
            return result
        result.total_final = len(final)
        result.final_items = final
        save_checkpoint(output_dir, 9, "final_validation", {
            "final_count": len(final),
            "items": serialize_items(final),
        })

        return self._finalize(result, output_dir)

    def _finalize(
        self,
        result: PipelineResult,
        output_dir: Path,
    ) -> PipelineResult:
        """Compute success, save results, report cost, print summary."""
        result.success = result.total_final > 0 or any(
            p.success for p in result.phase_results
        )
        save_pipeline_results(output_dir, result)
        print_pipeline_summary(result)

        if hasattr(self, "_cost_acc"):
            self._cost_acc.report()
            clear_cost_accumulator()

        return result

    def _phase_0_inputs(
        self, atom_id: str, result: PipelineResult,
    ) -> AtomContext | None:
        """Phase 0: Load atom definition and exemplars."""
        logger.info("Phase 0: Loading inputs for %s", atom_id)
        atom = load_atom(atom_id)
        if atom is None:
            result.phase_results.append(PhaseResult(
                phase_name="inputs", success=False,
                errors=[f"Atom {atom_id} not found"],
            ))
            return None
        exs = load_exemplars_for_atom(atom_id)
        ctx = AtomContext(
            atom_id=atom.id, atom_title=atom.titulo,
            atom_description=atom.descripcion, eje=atom.eje,
            standard_ids=atom.standard_ids, tipo_atomico=atom.tipo_atomico,
            criterios_atomicos=atom.criterios_atomicos,
            ejemplos_conceptuales=atom.ejemplos_conceptuales,
            notas_alcance=atom.notas_alcance, exemplars=exs,
        )
        result.phase_results.append(PhaseResult(
            phase_name="inputs", success=True,
            data={"exemplar_count": len(exs)},
        ))
        return ctx

    def _phase_1_enrichment(
        self, ctx: AtomContext, result: PipelineResult,
    ) -> AtomEnrichment | None:
        """Phase 1: Atom enrichment (non-blocking)."""
        if self._config.skip_enrichment:
            result.phase_results.append(PhaseResult(
                phase_name="atom_enrichment", success=True,
                data={"enrichment_status": EnrichmentStatus.MISSING},
                warnings=["Enrichment skipped by config"],
            ))
            return None
        phase = self._enricher.enrich(ctx, ctx.exemplars)
        result.phase_results.append(phase)
        if phase.data and phase.data.get("enrichment"):
            return phase.data["enrichment"]
        return None

    def _phase_2_3_plan(
        self, ctx: AtomContext,
        enrichment: AtomEnrichment | None,
        result: PipelineResult,
    ) -> list[PlanSlot] | None:
        """Phases 2-3: Plan generation + validation."""
        gen_phase = self._planner.generate_plan(
            ctx, enrichment, self._config.planned_distribution,
        )
        result.phase_results.append(gen_phase)
        if not gen_phase.success:
            return None
        plan_slots: list[PlanSlot] = gen_phase.data
        val_phase = validate_plan(
            plan_slots, ctx, self._config.planned_distribution,
        )
        result.phase_results.append(val_phase)
        return plan_slots if val_phase.success else None

    def _retry_failed_images(
        self,
        items: list[GeneratedItem],
        plan_slots: list[PlanSlot],
        ctx: AtomContext,
        result: PipelineResult,
        output_dir: Path,
    ) -> list[GeneratedItem]:
        """Re-run Phase 4b for items with image_failed + placeholder."""
        retryable = [
            it for it in items
            if it.image_failed
            and "IMAGE_PLACEHOLDER" in it.qti_xml
        ]
        if not retryable:
            return [it for it in items if not it.image_failed]

        logger.info(
            "Retrying %d failed images from prior run",
            len(retryable),
        )
        slot_map = {s.slot_index: s for s in plan_slots}
        phase = self._image_generator.generate_images(
            retryable, slot_map, ctx.atom_id,
        )
        result.phase_results.append(phase)

        # Mark any items still with placeholder as failed
        for it in items:
            if (
                "IMAGE_PLACEHOLDER" in it.qti_xml
                and not it.image_failed
            ):
                it.image_failed = True

        save_checkpoint(output_dir, 4, "generation", {
            "item_count": len(items),
            "items": serialize_items(items),
        })
        active = [it for it in items if not it.image_failed]
        recovered = sum(1 for it in retryable if not it.image_failed)
        logger.info(
            "Image retry: %d/%d recovered, %d active total",
            recovered, len(retryable), len(active),
        )
        return active

    def _phase_5_dedupe(
        self, items: list[GeneratedItem], result: PipelineResult,
        existing_fingerprints: set[str] | None = None,
    ) -> list[GeneratedItem] | None:
        """Phase 5: Deterministic duplicate gate."""
        phase = self._dedupe_gate.run(
            items, existing_fingerprints=existing_fingerprints,
            pool_total=result.total_planned or len(items),
        )
        result.phase_results.append(phase)
        return phase.data["filtered_items"] if phase.success else None

    def _phase_6_base_validation(
        self, items: list[GeneratedItem],
        ctx: AtomContext, result: PipelineResult,
    ) -> list[GeneratedItem] | None:
        """Phase 6: Base validation."""
        phase = self._base_validator.validate(items, ctx.exemplars)
        result.phase_results.append(phase)
        return phase.data["valid_items"] if phase.success else None

    def _phase_9_final_validation(
        self, items: list[GeneratedItem],
        ctx: AtomContext, result: PipelineResult,
    ) -> list[GeneratedItem] | None:
        """Phase 9: Final validation."""
        phase = self._final_validator.validate(items, ctx.exemplars)
        result.phase_results.append(phase)
        return phase.data["final_items"] if phase.success else None

    def _get_output_dir(self, atom_id: str) -> Path:
        """Get output directory for this atom's generation run."""
        if self._config.output_dir:
            return Path(self._config.output_dir)
        return QUESTION_GENERATION_DIR / atom_id
