#!/usr/bin/env python3
"""Audit non-mechanizability expectations across official source questions."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from app.question_variants.contracts.structural_profile import build_construct_contract
from app.question_variants.io.source_loader import load_source_questions


def main() -> None:
    root = Path("app/data/pruebas/finalizadas")
    by_expectation = Counter()
    by_family = Counter()
    grouped: dict[str, list[tuple[str, str, str]]] = defaultdict(list)

    for test_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        for source in load_source_questions(test_dir.name):
            contract = build_construct_contract(
                source.question_text,
                source.qti_xml,
                bool(source.image_urls),
                source.primary_atoms,
                source.metadata,
                source.choices,
                source.correct_answer,
            )
            expectation = str(contract.get("non_mechanizable_expectation") or "unknown")
            family_id = str(contract.get("family_id") or "unknown")
            by_expectation[expectation] += 1
            by_family[family_id] += 1
            grouped[expectation].append((family_id, test_dir.name, source.question_id))

    print("NON_MECHANIZABLE_EXPECTATIONS")
    for expectation, count in by_expectation.most_common():
        print(f"{expectation}\t{count}")

    print("\nFAMILIES")
    for family_id, count in by_family.most_common():
        print(f"{family_id}\t{count}")

    print("\nSAMPLES")
    for expectation in ("low", "medium", "high"):
        print(f"[{expectation}]")
        for family_id, test_id, question_id in grouped.get(expectation, [])[:10]:
            print(f"{family_id}\t{test_id}\t{question_id}")


if __name__ == "__main__":
    main()
