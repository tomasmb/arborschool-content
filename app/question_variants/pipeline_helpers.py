"""Shared helpers for pipeline.py -- postprocessing, dedup, checkpointing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.question_generation.validation_checks import (
    check_feedback_completeness,
    check_paes_structure,
    validate_qti_xml,
)
from app.question_variants.contracts.structural_profile import (
    build_construct_contract,
)
from app.question_variants.models import (
    GenerationReport,
    SourceQuestion,
    VariantBlueprint,
    VariantQuestion,
)
from app.question_variants.postprocess.family_repairs import (
    repair_family_specific_qti,
)
from app.question_variants.postprocess.repair_utils import (
    apply_declared_correct_choice,
    canonicalize_qti_markup,
    normalize_named_entities,
    strip_choice_identifier_mentions,
    strip_xml_comments,
)
from app.question_variants.postprocess.presentation_transformer import (
    normalize_variant_presentation,
)
from app.question_variants.qti_validation_utils import (
    extract_question_text,
    surface_similarity,
    validate_choice_interaction_integrity,
)
from app.question_variants.variant_validator import (
    validate_visual_completeness,
    validate_xml,
)


# ------------------------------------------------------------------
# Shared postprocessing
# ------------------------------------------------------------------


def postprocess_variant(
    variant: VariantQuestion,
    source_contract: dict[str, Any],
) -> None:
    """Apply the full postprocess chain to a variant (mutates in place)."""
    original_qti = variant.qti_xml

    variant.qti_xml = normalize_variant_presentation(
        variant.qti_xml,
        str(source_contract.get("operation_signature") or ""),
        str(source_contract.get("task_form") or ""),
        str(source_contract.get("selection_load") or "not_applicable"),
    )
    normalized_qti = variant.qti_xml

    variant.qti_xml = repair_family_specific_qti(
        variant.qti_xml, source_contract, variant.metadata,
    )
    repaired_qti = variant.qti_xml

    variant.qti_xml = normalize_named_entities(variant.qti_xml)
    entity_qti = variant.qti_xml

    variant.qti_xml = apply_declared_correct_choice(
        variant.qti_xml,
        str(variant.metadata.get(
            "generator_declared_correct_identifier", "",
        )),
    )
    decl_qti = variant.qti_xml

    variant.qti_xml = canonicalize_qti_markup(variant.qti_xml)
    canon_qti = variant.qti_xml

    variant.qti_xml = strip_choice_identifier_mentions(variant.qti_xml)
    id_qti = variant.qti_xml

    variant.qti_xml = strip_xml_comments(variant.qti_xml)
    stripped_qti = variant.qti_xml

    variant.metadata["postprocess_summary"] = {
        "presentation_normalized": normalized_qti != original_qti,
        "family_repaired": repaired_qti != normalized_qti,
        "entities_normalized": entity_qti != repaired_qti,
        "correct_declaration_synced": decl_qti != entity_qti,
        "qti_canonicalized": canon_qti != decl_qti,
        "choice_identifiers_stripped": id_qti != canon_qti,
        "comments_stripped": stripped_qti != id_qti,
    }


def run_deterministic_checks(
    variant: VariantQuestion,
    source: SourceQuestion,
    *,
    check_feedback: bool = False,
) -> tuple[bool, str]:
    """Run deterministic pre-checks on a variant. Returns (ok, error).

    Checks (in order): XML parse, XSD schema, PAES structure,
    choice-interaction integrity, visual completeness.
    When *check_feedback* is True, also verifies feedback elements.
    """
    xml_ok, xml_err = validate_xml(variant.qti_xml)
    if not xml_ok:
        return False, f"XML inválido: {xml_err}"

    xsd_result = validate_qti_xml(variant.qti_xml)
    if not xsd_result.get("valid", False):
        xsd_err = xsd_result.get("validation_errors", "unknown")
        return False, f"XSD inválido: {xsd_err}"

    paes_errors = check_paes_structure(variant.qti_xml)
    if paes_errors:
        return False, "; ".join(paes_errors)

    wire_ok, wire_err = validate_choice_interaction_integrity(variant.qti_xml)
    if not wire_ok:
        return False, wire_err

    vis_ok, vis_err = validate_visual_completeness(variant.qti_xml, source)
    if not vis_ok:
        return False, vis_err

    if check_feedback:
        fb_errors = check_feedback_completeness(variant.qti_xml)
        if fb_errors:
            return False, "; ".join(fb_errors)

    return True, ""


def dedup_variant(
    variant: VariantQuestion,
    approved: list[VariantQuestion],
) -> tuple[bool, str]:
    """Check if a variant is too similar to already-approved ones."""
    variant_text = extract_question_text(variant.qti_xml)
    for existing in approved:
        existing_text = extract_question_text(existing.qti_xml)
        sim = surface_similarity(variant_text, existing_text)
        if sim > 0.85:
            return False, (
                f"Demasiado similar a {existing.variant_id} "
                f"(similitud={sim:.2f})"
            )
    return True, ""


def build_source_contract(source: SourceQuestion) -> dict[str, Any]:
    """Build the construct contract for a source question."""
    return build_construct_contract(
        source.question_text,
        source.qti_xml,
        bool(source.image_urls),
        source.primary_atoms,
        source.metadata,
        source.choices,
        source.correct_answer,
    )


def source_key(source: SourceQuestion) -> str:
    """Build a unique key for a source question."""
    return f"{source.test_id}__{source.question_id}"


def print_summary(
    reports: list[GenerationReport], output_dir: str,
) -> None:
    """Print a summary of the pipeline run."""
    total_gen = sum(r.total_generated for r in reports)
    total_app = sum(r.total_approved for r in reports)
    total_rej = sum(r.total_rejected for r in reports)

    print(f"\n{'=' * 60}")
    print("RESUMEN")
    print(f"{'=' * 60}")
    print(f"Preguntas procesadas: {len(reports)}")
    print(f"Variantes generadas:  {total_gen}")
    if total_gen > 0:
        pct = 100 * total_app / total_gen
        print(f"Variantes aprobadas:  {total_app} ({pct:.1f}%)")
    print(f"Variantes rechazadas: {total_rej}")
    print(f"\nOutput: {output_dir}")
    print(f"{'=' * 60}\n")


# ------------------------------------------------------------------
# Checkpoint / serialization helpers
# ------------------------------------------------------------------


def load_state(job_dir: Path) -> dict[str, Any]:
    """Load the checkpoint state from disk."""
    state_path = job_dir / "batch_state.json"
    if state_path.exists():
        with open(state_path) as f:
            return json.load(f)
    return {}


def save_state(job_dir: Path, state: dict[str, Any]) -> None:
    """Persist the checkpoint state to disk."""
    job_dir.mkdir(parents=True, exist_ok=True)
    with open(job_dir / "batch_state.json", "w") as f:
        json.dump(state, f, indent=2)


def get_phase_state(
    state: dict[str, Any], phase_name: str,
) -> dict[str, Any]:
    """Return the sub-state dict for a batch phase, creating if absent."""
    phases = state.setdefault("phases", {})
    return phases.setdefault(phase_name, {"status": "pending"})


def update_phase_state(
    state: dict[str, Any],
    job_dir: Path,
    phase_name: str,
    **updates: Any,
) -> None:
    """Merge *updates* into the phase sub-state and persist."""
    ps = get_phase_state(state, phase_name)
    ps.update(updates)
    save_state(job_dir, state)


def save_json(path: Path, data: Any) -> None:
    """Write any JSON-serializable data to a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(path: Path) -> Any:
    """Read a JSON file."""
    with open(path) as f:
        return json.load(f)


def blueprint_to_dict(bp: VariantBlueprint) -> dict[str, Any]:
    """Serialize a blueprint to a plain dict."""
    return {
        "variant_id": bp.variant_id,
        "scenario_description": bp.scenario_description,
        "non_mechanizable_axes": bp.non_mechanizable_axes,
        "required_reasoning": bp.required_reasoning,
        "difficulty_target": bp.difficulty_target,
        "requires_image": bp.requires_image,
        "image_description": bp.image_description,
        "selected_shape_id": bp.selected_shape_id,
    }


def variant_to_dict(v: VariantQuestion) -> dict[str, Any]:
    """Serialize a VariantQuestion to a plain dict."""
    return {
        "variant_id": v.variant_id,
        "source_question_id": v.source_question_id,
        "source_test_id": v.source_test_id,
        "qti_xml": v.qti_xml,
        "metadata": v.metadata,
    }


def load_variants_json(
    path: Path,
    sources_by_key: dict[str, SourceQuestion] | None = None,
) -> list[VariantQuestion]:
    """Deserialize a list of VariantQuestion from JSON."""
    data = load_json(path)
    return [
        VariantQuestion(
            variant_id=d["variant_id"],
            source_question_id=d["source_question_id"],
            source_test_id=d["source_test_id"],
            qti_xml=d.get("qti_xml", ""),
            metadata=d.get("metadata", {}),
        )
        for d in data
    ]


def apply_verdicts(
    variants: list[VariantQuestion],
    verdicts: dict[str, Any],
) -> tuple[list[VariantQuestion], list[VariantQuestion]]:
    """Split variants into approved and rejected based on verdicts."""
    approved: list[VariantQuestion] = []
    rejected: list[VariantQuestion] = []
    for v in variants:
        verdict_data = verdicts.get(v.variant_id)
        if verdict_data is None:
            rejected.append(v)
            continue
        if hasattr(verdict_data, "is_approved"):
            is_ok = verdict_data.is_approved
        else:
            is_ok = verdict_data.get("verdict") == "APROBADA"
        if is_ok:
            approved.append(v)
        else:
            rejected.append(v)
    return approved, rejected


def submit_and_wait_batch(
    submitter: Any,
    requests: list[Any],
    phase_name: str,
    job_dir: Path,
    state: dict[str, Any],
    job_id: str,
) -> list[Any]:
    """5-state batch lifecycle with crash-safe checkpointing.

    States: pending → file_uploaded → submitted → results_downloaded
    → parsed.  Each transition is checkpointed so any crash is fully
    recoverable without re-submitting or losing API spend.
    """
    import logging as _log
    _logger = _log.getLogger(__name__)

    ps = get_phase_state(state, phase_name)
    st = ps.get("status", "pending")
    meta = {
        "pipeline": "variant", "phase": phase_name,
        "job_id": job_id,
    }

    if st == "pending":
        jsonl_path = job_dir / f"{phase_name}.jsonl"
        submitter.write_jsonl(requests, jsonl_path)
        fid = submitter.upload_file(jsonl_path)
        update_phase_state(
            state, job_dir, phase_name,
            status="file_uploaded", file_id=fid,
            request_count=len(requests),
        )
        ps = get_phase_state(state, phase_name)
        st = "file_uploaded"

    if st == "file_uploaded":
        fid = ps.get("file_id", "")
        orphan = submitter.find_orphan_batch(
            file_id=fid, metadata_match=meta,
        )
        bid = (
            orphan["id"] if orphan
            else submitter.create_batch(fid, meta)
        )
        if orphan:
            _logger.info("Re-attached orphan batch %s", bid)
        update_phase_state(
            state, job_dir, phase_name,
            status="submitted", batch_id=bid,
        )
        ps = get_phase_state(state, phase_name)
        st = "submitted"

    if st == "submitted":
        bid = ps.get("batch_id", "")
        print(f"  Batch {bid} polling ({phase_name})...")
        batch_obj = submitter.poll_until_done(bid)
        if batch_obj.get("status") != "completed":
            raise RuntimeError(
                f"Batch {bid} ended: {batch_obj.get('status')}",
            )
        out_fid = batch_obj.get("output_file_id", "")
        results_path = job_dir / f"{phase_name}_results.jsonl"
        submitter.download_file(out_fid, results_path)
        update_phase_state(
            state, job_dir, phase_name,
            status="results_downloaded",
            results_jsonl=str(results_path),
        )
        ps = get_phase_state(state, phase_name)

    results_path = Path(ps.get(
        "results_jsonl",
        str(job_dir / f"{phase_name}_results.jsonl"),
    ))
    return submitter.parse_results_file(results_path)


def save_batch_results(
    config: Any,
    sources_map: dict[str, SourceQuestion],
    approved: list[VariantQuestion],
    rejected: list[VariantQuestion],
    bps: dict[str, list[VariantBlueprint]],
) -> list[GenerationReport]:
    """Build reports and persist approved/rejected variants to disk."""
    from app.question_variants.io.artifacts import (
        save_report,
        save_variant,
    )

    reports_by_q: dict[str, GenerationReport] = {}
    for src in sources_map.values():
        reports_by_q[src.question_id] = GenerationReport(
            source_question_id=src.question_id,
            source_test_id=src.test_id,
        )

    for v in approved:
        r = reports_by_q.get(v.source_question_id)
        src = sources_map.get(
            f"{v.source_test_id}__{v.source_question_id}",
        )
        if r and src:
            save_variant(config.output_dir, v, src, None)
            r.variants.append(v.variant_id)
            r.total_approved += 1

    if config.save_rejected:
        for v in rejected:
            src = sources_map.get(
                f"{v.source_test_id}__{v.source_question_id}",
            )
            if src:
                save_variant(
                    config.output_dir, v, src, None,
                    is_rejected=True,
                )

    for r in reports_by_q.values():
        k = f"{r.source_test_id}__{r.source_question_id}"
        r.total_generated = len(bps.get(k, []))
        r.total_rejected = r.total_generated - r.total_approved
        save_report(config.output_dir, r)

    return list(reports_by_q.values())
