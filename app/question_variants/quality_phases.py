"""Phases 5-7 quality runners for the variant pipeline.

Extracted from ``pipeline.py`` to keep each file under 500 lines.

- Phase 5: XSD + Solvability gate (batch or sync)
- Phase 6: Feedback enrichment (sync with parallelism)
- Phase 7: Final validation (batch or sync)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.question_variants.models import (
    GenerationReport,
    PipelineConfig,
    SourceQuestion,
    VariantQuestion,
)
from app.question_variants.pipeline_helpers import (
    load_json,
    save_json,
    save_state,
)

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Sync quality phases (used by SyncVariantPipeline)
# ------------------------------------------------------------------


def run_sync_quality_phases(
    approved: list[VariantQuestion],
    rejected: list[VariantQuestion],
    sources_map: dict[str, SourceQuestion],
    report: GenerationReport,
    config: PipelineConfig,
) -> tuple[list[VariantQuestion], list[VariantQuestion]]:
    """Run phases 5-7 sequentially using sync LLM calls."""
    from app.question_feedback.validator import (
        FinalValidator as LlmFinalValidator,
    )
    from app.question_variants.variant_enrichment import run_enrichment
    from app.question_variants.variant_solvability import (
        check_solvability_sync,
    )

    client = _build_sync_client(config.model)

    # Phase 5: solvability
    print("  🔷 Phase 5: Solvability gate...")
    solvable: list[VariantQuestion] = []
    for v in approved:
        ok, reason = check_solvability_sync(v, client)
        if ok:
            solvable.append(v)
        else:
            report.total_solvability_failed += 1
            report.rejection_reasons.append(reason)
            rejected.append(v)
    print(
        f"  ✅ Phase 5: {len(solvable)} passed, "
        f"{report.total_solvability_failed} failed",
    )

    if not solvable:
        return solvable, rejected

    # Phase 6: feedback enrichment
    print("  🔷 Phase 6: Feedback enrichment...")
    enriched, enrich_failed = run_enrichment(
        solvable,
        sources_map,
        max_workers=config.enrichment_max_workers,
        enrichment_model=config.enrichment_model,
        max_correction_retries=config.enrichment_max_correction_retries,
    )
    report.total_enrichment_failed = len(enrich_failed)
    rejected.extend(enrich_failed)
    print(
        f"  ✅ Phase 6: {len(enriched)} enriched, "
        f"{len(enrich_failed)} failed",
    )

    if not enriched:
        return enriched, rejected

    # Phase 7: final validation
    print("  🔷 Phase 7: Final validation...")
    final_validator = LlmFinalValidator(model=config.model)
    final_approved: list[VariantQuestion] = []
    for v in enriched:
        sk = f"{v.source_test_id}__{v.source_question_id}"
        src = sources_map.get(sk)
        image_urls = src.image_urls if src else None
        result = final_validator.validate(
            v.qti_xml, image_urls=image_urls or None,
        )
        if result.validation_result == "pass":
            v.metadata["final_validation"] = "pass"
            final_approved.append(v)
        else:
            report.total_final_validation_failed += 1
            v.metadata["final_validation"] = "fail"
            v.metadata["final_validation_reason"] = (
                result.overall_reasoning
            )
            rejected.append(v)
    print(
        f"  ✅ Phase 7: {len(final_approved)} approved, "
        f"{report.total_final_validation_failed} failed",
    )
    return final_approved, rejected


# ------------------------------------------------------------------
# Batch quality phases (used by BatchVariantPipeline)
# ------------------------------------------------------------------


def batch_phase_solvability(
    state: dict[str, Any],
    submitter: Any,
    variants: list[VariantQuestion],
    model: str,
    job_dir: Path,
    submit_and_wait: Any,
) -> tuple[list[VariantQuestion], list[VariantQuestion]]:
    """Phase 5 (batch): solvability gate."""
    from app.question_variants.batch_request_builders import (
        build_solvability_request,
    )
    from app.question_variants.batch_response_processors import (
        process_solvability_responses,
    )

    if state.get("phase_5_solvability") == "completed":
        print("✅ Phase 5 (Solvability) -- resuming from checkpoint")
        verdicts = load_json(job_dir / "solvability_results.json")
        return _apply_solvability_verdicts(variants, verdicts)

    reqs = [build_solvability_request(v, model) for v in variants]
    print(f"\n🔷 Phase 5: Solvability for {len(reqs)} variants...")
    resps = submit_and_wait(
        submitter, reqs, "solvability", job_dir, state,
    )
    by_id = {v.variant_id: v for v in variants}
    raw_verdicts = process_solvability_responses(resps, by_id)

    serialised = {
        vid: {"passed": ok, "reason": reason}
        for vid, (ok, reason) in raw_verdicts.items()
    }
    save_json(job_dir / "solvability_results.json", serialised)
    state["phase_5_solvability"] = "completed"
    save_state(job_dir, state)

    passed, failed = _apply_solvability_verdicts(variants, serialised)
    print(f"✅ Phase 5: {len(passed)} passed, {len(failed)} failed")
    return passed, failed


def batch_phase_enrichment(
    variants: list[VariantQuestion],
    sources_map: dict[str, SourceQuestion],
    job_dir: Path,
    state: dict[str, Any],
    config: PipelineConfig,
) -> tuple[list[VariantQuestion], list[VariantQuestion]]:
    """Phase 6 (sync with parallelism): feedback enrichment."""
    from app.question_variants.variant_enrichment import run_enrichment

    if state.get("phase_6_enrichment") == "completed":
        print("✅ Phase 6 (Enrichment) -- resuming from checkpoint")
        enriched_data = load_json(
            job_dir / "enriched_variants.json",
        )
        enriched_ids = {
            d["variant_id"]
            for d in enriched_data if d.get("enrichment") == "pass"
        }
        enriched = [
            _apply_enriched_xml(v, enriched_data)
            for v in variants if v.variant_id in enriched_ids
        ]
        failed = [
            v for v in variants if v.variant_id not in enriched_ids
        ]
        return enriched, failed

    print(f"\n🔷 Phase 6: Enriching {len(variants)} variants...")
    enriched, failed = run_enrichment(
        variants,
        sources_map,
        max_workers=config.enrichment_max_workers,
        enrichment_model=config.enrichment_model,
        max_correction_retries=config.enrichment_max_correction_retries,
    )

    save_json(job_dir / "enriched_variants.json", [
        {
            "variant_id": v.variant_id,
            "qti_xml": v.qti_xml,
            "enrichment": v.metadata.get("enrichment", "unknown"),
        }
        for v in enriched + failed
    ])
    state["phase_6_enrichment"] = "completed"
    save_state(job_dir, state)

    print(
        f"✅ Phase 6: {len(enriched)} enriched, "
        f"{len(failed)} failed",
    )
    return enriched, failed


def batch_phase_final_validate(
    state: dict[str, Any],
    submitter: Any,
    variants: list[VariantQuestion],
    sources_map: dict[str, SourceQuestion],
    model: str,
    job_dir: Path,
    submit_and_wait: Any,
) -> tuple[list[VariantQuestion], list[VariantQuestion]]:
    """Phase 7 (batch): comprehensive final validation."""
    from app.question_variants.batch_request_builders import (
        build_final_validation_request,
    )
    from app.question_variants.batch_response_processors import (
        process_final_validation_responses,
    )

    if state.get("phase_7_final_validate") == "completed":
        print(
            "✅ Phase 7 (Final Validation) -- "
            "resuming from checkpoint",
        )
        fv_data = load_json(
            job_dir / "final_validation_results.json",
        )
        return _apply_final_verdicts(variants, fv_data)

    reqs = []
    for v in variants:
        sk = f"{v.source_test_id}__{v.source_question_id}"
        src = sources_map.get(sk)
        image_urls = src.image_urls if src else None
        reqs.append(
            build_final_validation_request(
                v, model, image_urls=image_urls or None,
            ),
        )

    print(
        f"\n🔷 Phase 7: Final validation for "
        f"{len(reqs)} variants...",
    )
    resps = submit_and_wait(
        submitter, reqs, "final_validate", job_dir, state,
    )
    fv_results = process_final_validation_responses(resps)

    fv_serialised: dict[str, Any] = {}
    for vid, res in fv_results.items():
        fv_serialised[vid] = {
            "validation_result": res.validation_result,
            "overall_reasoning": res.overall_reasoning,
        }
    save_json(
        job_dir / "final_validation_results.json", fv_serialised,
    )
    state["phase_7_final_validate"] = "completed"
    save_state(job_dir, state)

    approved, rejected = _apply_final_verdicts(
        variants, fv_serialised,
    )
    print(
        f"✅ Phase 7: {len(approved)} approved, "
        f"{len(rejected)} failed",
    )
    return approved, rejected


# ------------------------------------------------------------------
# Verdict helpers (shared by sync and batch, checkpoint-friendly)
# ------------------------------------------------------------------


def _build_sync_client(model: str) -> Any:
    """Build a sync LLM client for Phase 5/7."""
    from app.llm_clients import load_default_openai_client
    return load_default_openai_client(model=model)


def _apply_solvability_verdicts(
    variants: list[VariantQuestion],
    verdicts: dict[str, Any],
) -> tuple[list[VariantQuestion], list[VariantQuestion]]:
    """Split variants by solvability verdicts."""
    passed: list[VariantQuestion] = []
    failed: list[VariantQuestion] = []
    for v in variants:
        data = verdicts.get(v.variant_id)
        if data and data.get("passed"):
            passed.append(v)
        else:
            v.metadata["solvability_reason"] = (
                data.get("reason", "unknown") if data else "no verdict"
            )
            failed.append(v)
    return passed, failed


def _apply_final_verdicts(
    variants: list[VariantQuestion],
    verdicts: dict[str, Any],
) -> tuple[list[VariantQuestion], list[VariantQuestion]]:
    """Split variants by final-validation verdicts."""
    approved: list[VariantQuestion] = []
    rejected: list[VariantQuestion] = []
    for v in variants:
        data = verdicts.get(v.variant_id)
        if data and data.get("validation_result") == "pass":
            v.metadata["final_validation"] = "pass"
            approved.append(v)
        else:
            v.metadata["final_validation"] = "fail"
            v.metadata["final_validation_reason"] = (
                data.get("overall_reasoning", "unknown")
                if data else "no verdict"
            )
            rejected.append(v)
    return approved, rejected


def _apply_enriched_xml(
    variant: VariantQuestion,
    enriched_data: list[dict[str, Any]],
) -> VariantQuestion:
    """Restore enriched QTI XML from checkpoint onto a variant."""
    for d in enriched_data:
        if d["variant_id"] == variant.variant_id:
            variant.qti_xml = d.get("qti_xml", variant.qti_xml)
            variant.metadata["enrichment"] = "pass"
            break
    return variant


# ------------------------------------------------------------------
# Batch quality phases orchestrator
# ------------------------------------------------------------------


def run_batch_quality_phases(
    state: dict[str, Any],
    submitter: Any,
    approved: list[VariantQuestion],
    sources_map: dict[str, SourceQuestion],
    model: str,
    job_dir: Path,
    config: PipelineConfig,
    submit_and_wait: Any,
) -> tuple[list[VariantQuestion], list[VariantQuestion]]:
    """Run phases 5-7 for the batch pipeline."""
    rejected: list[VariantQuestion] = []

    solvable, solve_rej = batch_phase_solvability(
        state, submitter, approved, model, job_dir, submit_and_wait,
    )
    rejected.extend(solve_rej)
    if not solvable:
        return solvable, rejected

    enriched, enrich_rej = batch_phase_enrichment(
        solvable, sources_map, job_dir, state, config,
    )
    rejected.extend(enrich_rej)
    if not enriched:
        return enriched, rejected

    final, final_rej = batch_phase_final_validate(
        state, submitter, enriched, sources_map,
        model, job_dir, submit_and_wait,
    )
    rejected.extend(final_rej)

    return final, rejected
