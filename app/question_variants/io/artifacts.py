"""Artifact persistence helpers for the hard-variants pipeline."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from app.question_variants.models import GenerationReport, SourceQuestion, VariantBlueprint, VariantQuestion, VariantResult
from app.question_variants.contracts.structural_profile import build_construct_contract


def load_existing_approved(
    output_dir: str, test_id: str, question_id: str,
) -> list[VariantQuestion]:
    """Load previously approved variants for a question from disk.

    Scans ``{output_dir}/{test_id}/{question_id}/variants/approved/*/
    question.xml`` and returns lightweight ``VariantQuestion`` objects
    suitable for cross-run deduplication.
    """
    approved_dir = (
        Path(output_dir) / test_id / question_id
        / "variants" / "approved"
    )
    if not approved_dir.is_dir():
        return []

    results: list[VariantQuestion] = []
    for variant_dir in sorted(approved_dir.iterdir()):
        xml_path = variant_dir / "question.xml"
        if not xml_path.is_file():
            continue
        results.append(VariantQuestion(
            variant_id=variant_dir.name,
            source_question_id=question_id,
            source_test_id=test_id,
            qti_xml=xml_path.read_text(encoding="utf-8"),
        ))
    return results


def save_variant_plan(output_dir: str, source: SourceQuestion, blueprints: list[VariantBlueprint]) -> None:
    """Persist planner output per source question."""
    plan_path = Path(output_dir) / source.test_id / source.question_id / "variants" / "variant_plan.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_question_id": source.question_id,
        "source_test_id": source.test_id,
        "variants_planned": len(blueprints),
        "blueprints": [
            {
                "variant_id": bp.variant_id,
                "scenario_description": bp.scenario_description,
                "non_mechanizable_axes": bp.non_mechanizable_axes,
                "required_reasoning": bp.required_reasoning,
                "difficulty_target": bp.difficulty_target,
                "requires_image": bp.requires_image,
                "image_description": bp.image_description,
                "selected_shape_id": bp.selected_shape_id,
            }
            for bp in blueprints
        ],
    }
    plan_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def save_report(output_dir: str, report: GenerationReport) -> None:
    """Persist a generation report."""
    report_path = Path(output_dir) / report.source_test_id / report.source_question_id / "variants" / "generation_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")


def save_source_snapshot(output_dir: str, source: SourceQuestion) -> None:
    """Persist original source XML, metadata, and contract."""
    source_path = Path(output_dir) / source.test_id / source.question_id / "source"
    source_path.mkdir(parents=True, exist_ok=True)
    (source_path / "question.xml").write_text(source.qti_xml, encoding="utf-8")
    (source_path / "metadata_tags.json").write_text(
        json.dumps(source.metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    source_contract = build_construct_contract(
        source.question_text,
        source.qti_xml,
        bool(source.image_urls),
        source.primary_atoms,
        source.metadata,
        source.choices,
        source.correct_answer,
    )
    source_info = {
        "source_question_id": source.question_id,
        "source_test_id": source.test_id,
        "question_text": source.question_text,
        "choices": source.choices,
        "correct_answer": source.correct_answer,
        "image_urls": source.image_urls,
        "construct_contract": source_contract,
    }
    (source_path / "source_info.json").write_text(json.dumps(source_info, ensure_ascii=False, indent=2), encoding="utf-8")
    (source_path / "construct_contract.json").write_text(
        json.dumps(source_contract, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_variant(
    output_dir: str,
    variant: VariantQuestion,
    source: SourceQuestion,
    pipeline_result: VariantResult | None = None,
    *,
    is_rejected: bool = False,
    postprocess_summary: dict[str, object] | None = None,
) -> None:
    """Persist variant XML, metadata, validation, and post-process trace."""
    status = "rejected" if is_rejected else "approved"
    variant_path = Path(output_dir) / source.test_id / source.question_id / "variants" / status / variant.variant_id
    variant_path.mkdir(parents=True, exist_ok=True)

    if variant.validation_result:
        variant.metadata["semantic_validation"] = {
            "verdict": variant.validation_result.verdict.value,
            "concept_aligned": variant.validation_result.concept_aligned,
            "difficulty_equal": variant.validation_result.difficulty_equal,
            "difficulty_acceptable": variant.validation_result.difficulty_acceptable,
            "answer_correct": variant.validation_result.answer_correct,
            "non_mechanizable": variant.validation_result.non_mechanizable,
            "calculation_steps": variant.validation_result.calculation_steps,
            "rejection_reason": variant.validation_result.rejection_reason,
        }

    variant_info = {
        "variant_id": variant.variant_id,
        "source_question_id": variant.source_question_id,
        "source_test_id": variant.source_test_id,
        "is_rejected": is_rejected,
        "planning_blueprint": variant.metadata.get("planning_blueprint"),
        "generator_self_check": variant.metadata.get("generator_self_check"),
        "generator_declared_correct_identifier": variant.metadata.get("generator_declared_correct_identifier"),
        "construct_contract": variant.metadata.get("construct_contract"),
        "postprocess_summary": postprocess_summary or {},
    }
    validation_data = {
        "variant_id": variant.variant_id,
        "pipeline_version": "3.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pipeline_success": pipeline_result.success if pipeline_result else None,
        "pipeline_stage_failed": pipeline_result.stage_failed if pipeline_result else None,
        "pipeline_error": pipeline_result.error if pipeline_result else None,
        "pipeline_validation_details": pipeline_result.validation_details if pipeline_result else None,
        "semantic_validation": variant.metadata.get("semantic_validation"),
        "is_approved": not is_rejected,
    }

    (variant_path / "question.xml").write_text(variant.qti_xml, encoding="utf-8")
    (variant_path / "metadata_tags.json").write_text(json.dumps(variant.metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    (variant_path / "variant_info.json").write_text(json.dumps(variant_info, ensure_ascii=False, indent=2), encoding="utf-8")
    (variant_path / "validation_result.json").write_text(json.dumps(validation_data, ensure_ascii=False, indent=2), encoding="utf-8")
