"""Variant generation pipeline: Sync and Batch implementations.

Phases 1-4 (plan, generate, postprocess, validate) are the original
generation pipeline.  Phases 5-7 (solvability, enrichment, final
validation) bring quality to parity with the atom question generation
pipeline and are skipped when ``config.skip_enrichment`` is True.
"""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Any

from app.question_variants.io.artifacts import (
    save_report,
    save_source_snapshot,
    save_variant,
    save_variant_plan,
)
from app.question_variants.io.source_loader import load_source_questions
from app.question_variants.models import (
    GenerationReport,
    PipelineConfig,
    SourceQuestion,
    VariantBlueprint,
    VariantQuestion,
)
from app.question_variants.pipeline_helpers import (
    apply_verdicts,
    blueprint_to_dict,
    build_source_contract,
    dedup_variant,
    load_json,
    load_state,
    load_variants_json,
    postprocess_variant,
    print_summary,
    run_deterministic_checks,
    save_batch_results,
    save_json,
    save_state,
    source_key,
    submit_and_wait_batch,
    variant_to_dict,
)

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# SyncVariantPipeline (--no-batch debug / pilot mode)
# ------------------------------------------------------------------


class SyncVariantPipeline:
    """Sequential LLM calls -- useful for debugging and pilot runs."""

    def __init__(self, config: PipelineConfig | None = None):
        self.config = config or PipelineConfig(use_batch_api=False)

    def run(
        self,
        test_id: str,
        question_ids: list[str] | None = None,
        num_variants: int | None = None,
    ) -> list[GenerationReport]:
        from app.question_variants.variant_generator import VariantGenerator
        from app.question_variants.variant_planner import VariantPlanner
        from app.question_variants.variant_validator import VariantValidator

        print(f"\n{'=' * 60}")
        print("PIPELINE SYNC: Generación de Variantes")
        print(f"Test: {test_id} | model: {self.config.model}")
        print(f"{'=' * 60}\n")

        sources = load_source_questions(test_id, question_ids)
        if not sources:
            print("❌ No se encontraron preguntas.")
            return []
        print(f"📋 Cargadas {len(sources)} preguntas fuente\n")

        planner = VariantPlanner(self.config)
        generator = VariantGenerator(self.config)
        validator = VariantValidator(self.config)

        sources_map = {source_key(s): s for s in sources}
        reports: list[GenerationReport] = []
        n = num_variants or self.config.variants_per_question
        for src in sources:
            report = self._process_question(
                src, n, planner, generator, validator, sources_map,
            )
            reports.append(report)

        print_summary(reports, self.config.output_dir)
        return reports

    def _process_question(
        self,
        source: SourceQuestion,
        n: int,
        planner: Any,
        generator: Any,
        validator: Any,
        sources_map: dict[str, SourceQuestion],
    ) -> GenerationReport:
        from app.question_variants.quality_phases import (
            run_sync_quality_phases,
        )

        print(f"\n{'─' * 40}")
        print(f"Procesando: {source.question_id}")
        print(f"{'─' * 40}")

        report = GenerationReport(
            source_question_id=source.question_id,
            source_test_id=source.test_id,
        )
        save_source_snapshot(self.config.output_dir, source)
        contract = build_source_contract(source)

        blueprints = planner.plan_variants(source, n)
        save_variant_plan(self.config.output_dir, source, blueprints)

        variants = generator.generate_variants(
            source, n, blueprints=blueprints,
        )
        report.total_generated = len(variants)
        if not variants:
            report.errors.append("No se pudieron generar variantes")
            save_report(self.config.output_dir, report)
            return report

        # -- Phases 3-4: postprocess, validate, dedup --------------------
        approved: list[VariantQuestion] = []
        rejected: list[VariantQuestion] = []
        for variant in variants:
            postprocess_variant(variant, contract)

            if self.config.validate_variants:
                result = validator.validate(variant, source)
                variant.validation_result = result
                if not result.is_approved:
                    report.total_rejected += 1
                    if result.rejection_reason:
                        report.rejection_reasons.append(
                            result.rejection_reason,
                        )
                    rejected.append(variant)
                    continue

            dup_ok, dup_reason = dedup_variant(variant, approved)
            if not dup_ok:
                report.total_rejected += 1
                report.rejection_reasons.append(dup_reason)
                rejected.append(variant)
                continue

            approved.append(variant)

        # -- Phases 5-7 --------------------------------------------------
        if not self.config.skip_enrichment and approved:
            approved, rejected = run_sync_quality_phases(
                approved, rejected, sources_map, report, self.config,
            )

        report.total_approved = len(approved)
        for variant in approved:
            save_variant(self.config.output_dir, variant, source, None)
            report.variants.append(variant.variant_id)

        if self.config.save_rejected:
            for v in rejected:
                save_variant(
                    self.config.output_dir, v, source, None,
                    is_rejected=True,
                )

        save_report(self.config.output_dir, report)
        return report


# ------------------------------------------------------------------
# BatchVariantPipeline (Batch API, checkpointed)
# ------------------------------------------------------------------


class BatchVariantPipeline:
    """7-phase pipeline using OpenAI Batch API with checkpointing.

    Phases 1-4 handle generation and 3-gate validation.
    Phases 5-7 (solvability, enrichment, final validation) are
    skipped when ``config.skip_enrichment`` is True.
    """

    def __init__(self, config: PipelineConfig | None = None):
        self.config = config or PipelineConfig()
        self.job_id = config.job_id if config else None
        if not self.job_id:
            self.job_id = uuid.uuid4().hex[:12]

    def run(
        self,
        test_id: str,
        question_ids: list[str] | None = None,
        num_variants: int | None = None,
    ) -> list[GenerationReport]:
        from app.question_generation.batch_api import OpenAIBatchSubmitter

        n = num_variants or self.config.variants_per_question
        model = self.config.model

        print(f"\n{'=' * 60}")
        print("PIPELINE BATCH: Generación de Variantes")
        print(f"Test: {test_id} | model: {model} | job: {self.job_id}")
        print(f"{'=' * 60}\n")

        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")

        submitter = OpenAIBatchSubmitter(
            api_key=api_key,
            poll_interval=self.config.batch_poll_interval,
        )

        sources = load_source_questions(test_id, question_ids)
        if not sources:
            print("❌ No se encontraron preguntas.")
            return []
        print(f"📋 Cargadas {len(sources)} preguntas fuente")

        sources_map = {source_key(s): s for s in sources}
        contracts_map = {
            source_key(s): build_source_contract(s) for s in sources
        }
        job_dir = (
            Path(self.config.output_dir) / ".batch_runs" / self.job_id
        )
        state = load_state(job_dir)

        # -- Phases 1-4 --------------------------------------------------
        bps = self._phase_plan(
            state, submitter, sources, n, model, job_dir,
        )
        raw = self._phase_generate(
            state, submitter, sources_map, bps, model, job_dir,
        )
        valid, inv = self._phase_postprocess(
            raw, sources_map, contracts_map,
        )
        print(f"\n📦 Phase 3: {len(valid)} passed, {inv} filtered")

        if self.config.validate_variants:
            approved, rejected = self._phase_validate(
                state, submitter, valid, sources_map, model, job_dir,
            )
        else:
            approved, rejected = valid, []

        # -- Phases 5-7 --------------------------------------------------
        if not self.config.skip_enrichment and approved:
            from app.question_variants.quality_phases import (
                run_batch_quality_phases,
            )
            approved, phase57_rej = run_batch_quality_phases(
                state, submitter, approved, sources_map,
                model, job_dir, self.config, self._submit_and_wait,
            )
            rejected.extend(phase57_rej)

        reports = self._save_results(
            sources_map, approved, rejected, bps,
        )
        print_summary(reports, self.config.output_dir)
        return reports

    # ---- Phase 1: Plan -----------------------------------------------

    def _phase_plan(
        self, state: dict, submitter: Any,
        sources: list[SourceQuestion], n: int,
        model: str, job_dir: Path,
    ) -> dict[str, list[VariantBlueprint]]:
        from app.question_variants.batch_request_builders import (
            build_plan_request,
        )
        from app.question_variants.batch_response_processors import (
            process_plan_responses,
        )

        if state.get("phase_1_plan") == "completed":
            print("✅ Phase 1 (Plan) -- resuming from checkpoint")
            return load_json(job_dir / "blueprints.json")

        print(f"\n🔷 Phase 1: Planning {len(sources)} questions...")
        reqs = [build_plan_request(s, n, model) for s in sources]
        resps = self._submit_and_wait(
            submitter, reqs, "plan", job_dir, state,
        )

        sm = {source_key(s): s for s in sources}
        bps = process_plan_responses(resps, sm)
        for s in sources:
            k = source_key(s)
            save_source_snapshot(self.config.output_dir, s)
            save_variant_plan(
                self.config.output_dir, s, bps.get(k, []),
            )

        save_json(job_dir / "blueprints.json", {
            k: [blueprint_to_dict(b) for b in v]
            for k, v in bps.items()
        })
        state["phase_1_plan"] = "completed"
        save_state(job_dir, state)
        total = sum(len(v) for v in bps.values())
        print(f"✅ Phase 1 done: {total} blueprints")
        return bps

    # ---- Phase 2: Generate -------------------------------------------

    def _phase_generate(
        self, state: dict, submitter: Any,
        sources_map: dict[str, SourceQuestion],
        bps: dict[str, list[VariantBlueprint]],
        model: str, job_dir: Path,
    ) -> list[VariantQuestion]:
        from app.question_variants.batch_request_builders import (
            build_generation_request,
        )
        from app.question_variants.batch_response_processors import (
            process_generation_responses,
        )

        if state.get("phase_2_generate") == "completed":
            print("✅ Phase 2 (Generate) -- resuming from checkpoint")
            return load_variants_json(job_dir / "raw_variants.json")

        reqs = []
        for key, blueprints in bps.items():
            src = sources_map.get(key)
            if not src:
                continue
            for bp in blueprints:
                reqs.append(build_generation_request(src, bp, model))

        print(f"\n🔷 Phase 2: Generating {len(reqs)} variants...")
        resps = self._submit_and_wait(
            submitter, reqs, "generate", job_dir, state,
        )
        raw = process_generation_responses(resps, sources_map, bps)

        save_json(
            job_dir / "raw_variants.json",
            [variant_to_dict(v) for v in raw],
        )
        state["phase_2_generate"] = "completed"
        save_state(job_dir, state)
        print(f"✅ Phase 2 done: {len(raw)} variants parsed")
        return raw

    # ---- Phase 3: Postprocess + deterministic (local) ----------------

    def _phase_postprocess(
        self, variants: list[VariantQuestion],
        sources_map: dict[str, SourceQuestion],
        contracts_map: dict[str, dict[str, Any]],
    ) -> tuple[list[VariantQuestion], int]:
        valid, inv = [], 0
        for v in variants:
            k = f"{v.source_test_id}__{v.source_question_id}"
            postprocess_variant(v, contracts_map.get(k, {}))
            src = sources_map.get(k)
            if src:
                ok, _ = run_deterministic_checks(v, src)
                if not ok:
                    inv += 1
                    continue
            valid.append(v)
        return valid, inv

    # ---- Phase 4: Validate -------------------------------------------

    def _phase_validate(
        self, state: dict, submitter: Any,
        variants: list[VariantQuestion],
        sources_map: dict[str, SourceQuestion],
        model: str, job_dir: Path,
    ) -> tuple[list[VariantQuestion], list[VariantQuestion]]:
        from app.question_variants.batch_request_builders import (
            build_validation_request,
        )
        from app.question_variants.batch_response_processors import (
            process_validation_responses,
        )

        if state.get("phase_4_validate") == "completed":
            print("✅ Phase 4 (Validate) -- resuming from checkpoint")
            verdicts = load_json(job_dir / "verdicts.json")
            return apply_verdicts(variants, verdicts)

        reqs = []
        for v in variants:
            k = f"{v.source_test_id}__{v.source_question_id}"
            src = sources_map.get(k)
            if src:
                reqs.append(build_validation_request(v, src, model))

        print(f"\n🔷 Phase 4: Validating {len(reqs)} variants...")
        resps = self._submit_and_wait(
            submitter, reqs, "validate", job_dir, state,
        )
        verdicts = process_validation_responses(resps)

        save_json(job_dir / "verdicts.json", {
            k: {
                "verdict": r.verdict.value,
                "answer_correct": r.answer_correct,
                "concept_aligned": r.concept_aligned,
                "rejection_reason": r.rejection_reason,
            }
            for k, r in verdicts.items()
        })
        state["phase_4_validate"] = "completed"
        save_state(job_dir, state)

        approved, rejected = apply_verdicts(variants, verdicts)

        final: list[VariantQuestion] = []
        by_src: dict[str, list[VariantQuestion]] = {}
        for v in approved:
            by_src.setdefault(v.source_question_id, []).append(v)
        for group in by_src.values():
            deduped: list[VariantQuestion] = []
            for v in group:
                ok, _ = dedup_variant(v, deduped)
                if ok:
                    deduped.append(v)
                else:
                    rejected.append(v)
            final.extend(deduped)

        print(
            f"✅ Phase 4: {len(final)} approved, "
            f"{len(rejected)} rejected",
        )
        return final, rejected

    # ---- Batch submission helper ------------------------------------

    def _submit_and_wait(
        self, submitter: Any, requests: list[Any],
        phase_name: str, job_dir: Path, state: dict,
    ) -> list[Any]:
        """Delegate to the shared batch lifecycle function."""
        return submit_and_wait_batch(
            submitter, requests, phase_name,
            job_dir, state, self.job_id or "",
        )

    # ---- Save results ------------------------------------------------

    def _save_results(
        self,
        sources_map: dict[str, SourceQuestion],
        approved: list[VariantQuestion],
        rejected: list[VariantQuestion],
        bps: dict[str, list[VariantBlueprint]],
    ) -> list[GenerationReport]:
        return save_batch_results(
            self.config, sources_map, approved, rejected, bps,
        )
