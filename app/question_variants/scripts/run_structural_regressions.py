#!/usr/bin/env python3
"""Run deterministic structural regressions over curated variant artifacts."""

from __future__ import annotations

from pathlib import Path

from app.question_variants.io.source_loader import load_source_questions
from app.question_variants.models import PipelineConfig, SourceQuestion, VariantQuestion
from app.question_variants.postprocess.family_repairs import repair_family_specific_qti
from app.question_variants.postprocess.presentation_transformer import normalize_variant_presentation
from app.question_variants.scripts.regression_cases import STRUCTURAL_REGRESSION_CASES
from app.question_variants.variant_validator import VariantValidator


def load_source_map() -> dict[tuple[str, str], SourceQuestion]:
    """Load all finalized source questions keyed by (test_id, question_id)."""
    source_map: dict[tuple[str, str], SourceQuestion] = {}
    finalized_root = Path("app/data/pruebas/finalizadas")
    for test_dir in finalized_root.iterdir():
        if not test_dir.is_dir():
            continue
        test_id = test_dir.name
        for source in load_source_questions(test_id):
            source_map[(test_id, source.question_id)] = source
    return source_map


def main() -> None:
    validator = VariantValidator(PipelineConfig(validate_variants=True))
    source_map = load_source_map()
    failures: list[str] = []

    for case in STRUCTURAL_REGRESSION_CASES:
        source_key = (case["test_id"], case["question_id"])
        source = source_map.get(source_key)
        if source is None:
            failures.append(f"{case['name']}: source not found for {source_key}")
            continue

        variant_xml = Path(case["variant_xml_path"]).read_text(encoding="utf-8")
        contract = source.metadata.get("construct_contract") or {}
        if not contract:
            from app.question_variants.contracts.structural_profile import build_construct_contract

            contract = build_construct_contract(
                source.question_text,
                source.qti_xml,
                bool(source.image_urls),
                source.primary_atoms,
                source.metadata,
                source.choices,
                source.correct_answer,
            )

        normalized_xml = normalize_variant_presentation(
            variant_xml,
            str(contract.get("operation_signature") or ""),
            str(contract.get("task_form") or ""),
            str(contract.get("selection_load") or "not_applicable"),
        )
        repaired_xml = repair_family_specific_qti(normalized_xml, contract)

        ok, reason = validator._validate_structural_alignment(repaired_xml, source)
        expected_ok = bool(case["expected_ok"])
        if ok != expected_ok:
            failures.append(
                f"{case['name']}: expected_ok={expected_ok}, got_ok={ok}, reason={reason!r}"
            )
            continue

        expected_reason = str(case.get("reason_contains") or "")
        if expected_reason and expected_reason not in reason:
            failures.append(
                f"{case['name']}: expected reason containing {expected_reason!r}, got {reason!r}"
            )

    if failures:
        print("STRUCTURAL_REGRESSIONS_FAILED")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)

    print("STRUCTURAL_REGRESSIONS_PASSED")
    print(f"cases\t{len(STRUCTURAL_REGRESSION_CASES)}")


if __name__ == "__main__":
    main()
