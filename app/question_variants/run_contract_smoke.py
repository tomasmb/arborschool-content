#!/usr/bin/env python3
"""Run representative smoke checks for construct-contract inference."""

from __future__ import annotations

from app.question_variants.contract_smoke_cases import CONTRACT_SMOKE_CASES
from app.question_variants.contracts.structural_profile import build_construct_contract
from app.question_variants.io.source_loader import load_source_questions


def main() -> None:
    source_map = {}
    tests = sorted({case["test_id"] for case in CONTRACT_SMOKE_CASES})
    for test_id in tests:
        for source in load_source_questions(test_id):
            source_map[(test_id, source.question_id)] = source

    failures: list[str] = []
    for case in CONTRACT_SMOKE_CASES:
        key = (case["test_id"], case["question_id"])
        source = source_map.get(key)
        if source is None:
            failures.append(f"{key}: source not found")
            continue

        contract = build_construct_contract(
            source.question_text,
            source.qti_xml,
            bool(source.image_urls),
            source.primary_atoms,
            source.metadata,
            source.choices,
            source.correct_answer,
        )
        for field, expected_value in case["expected"].items():
            actual_value = contract.get(field)
            if actual_value != expected_value:
                failures.append(
                    f"{key} field={field}: expected {expected_value!r}, got {actual_value!r}"
                )

    if failures:
        print("CONTRACT_SMOKE_FAILED")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)

    print("CONTRACT_SMOKE_PASSED")
    print(f"cases\t{len(CONTRACT_SMOKE_CASES)}")


if __name__ == "__main__":
    main()
