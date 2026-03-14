#!/usr/bin/env python3
"""Run semantic validation benchmarks on an existing variant corpus."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from app.question_variants.models import PipelineConfig, SourceQuestion, VariantQuestion
from app.question_variants.variant_validator import VariantValidator
from app.utils.qti_extractor import parse_qti_xml

FINALIZED_PATH = Path("app/data/pruebas/finalizadas")


def load_source_questions(test_id: str, question_ids: list[str] | None) -> dict[str, SourceQuestion]:
    test_path = FINALIZED_PATH / test_id / "qti"
    sources: dict[str, SourceQuestion] = {}

    for question_dir in sorted(test_path.iterdir()):
        if question_ids and question_dir.name not in question_ids:
            continue
        if not question_dir.is_dir():
            continue

        xml_path = question_dir / "question.xml"
        metadata_path = question_dir / "metadata_tags.json"
        if not xml_path.exists() or not metadata_path.exists():
            continue

        qti_xml = xml_path.read_text(encoding="utf-8")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        parsed = parse_qti_xml(qti_xml)
        sources[question_dir.name] = SourceQuestion(
            question_id=question_dir.name,
            test_id=test_id,
            qti_xml=qti_xml,
            metadata=metadata,
            question_text=parsed.text,
            choices=parsed.choices,
            correct_answer=parsed.correct_answer_text or "",
            image_urls=parsed.image_urls,
        )

    return sources


def iter_variant_dirs(input_dir: Path, test_id: str, question_ids: list[str] | None) -> list[Path]:
    base = input_dir / test_id
    variant_dirs: list[Path] = []
    for question_dir in sorted(base.glob("Q*")):
        if question_ids and question_dir.name not in question_ids:
            continue
        for status in ("approved", "rejected"):
            status_dir = question_dir / status
            if not status_dir.exists():
                continue
            for variant_dir in sorted(status_dir.iterdir()):
                if (variant_dir / "question.xml").exists():
                    variant_dirs.append(variant_dir)
    return variant_dirs


def run_benchmark(
    input_dir: Path,
    test_id: str,
    question_ids: list[str] | None,
    provider: str,
    model: str | None,
    max_variants: int | None,
    max_variants_per_question: int | None,
) -> dict[str, Any]:
    sources = load_source_questions(test_id, question_ids)
    validator = VariantValidator(
        PipelineConfig(
            validator_provider=provider,
            validator_model=model,
        )
    )

    summary: dict[str, Any] = {
        "input_dir": str(input_dir),
        "test_id": test_id,
        "validator_provider": provider,
        "validator_model": model,
        "variants_seen": 0,
        "approved": 0,
        "rejected": 0,
        "original_approved": 0,
        "original_rejected": 0,
        "agreement_with_original": Counter(),
        "gates": {
            "constructo": Counter(),
            "dificultad": Counter(),
            "answer_correct": Counter(),
            "non_mechanizable": Counter(),
            "imagen": Counter(),
        },
        "questions": defaultdict(lambda: {"approved": 0, "rejected": 0}),
    }

    variant_dirs = iter_variant_dirs(input_dir, test_id, question_ids)
    if max_variants_per_question is not None:
        per_question_counts: dict[str, int] = {}
        filtered_dirs: list[Path] = []
        for variant_dir in variant_dirs:
            question_id = variant_dir.parent.parent.name
            used = per_question_counts.get(question_id, 0)
            if used >= max_variants_per_question:
                continue
            filtered_dirs.append(variant_dir)
            per_question_counts[question_id] = used + 1
        variant_dirs = filtered_dirs
    if max_variants is not None:
        variant_dirs = variant_dirs[:max_variants]

    for index, variant_dir in enumerate(variant_dirs, start=1):
        question_id = variant_dir.parent.parent.name
        source = sources.get(question_id)
        if source is None:
            continue

        metadata = json.loads((variant_dir / "metadata_tags.json").read_text(encoding="utf-8"))
        qti_xml = (variant_dir / "question.xml").read_text(encoding="utf-8")
        variant = VariantQuestion(
            variant_id=variant_dir.name,
            source_question_id=question_id,
            source_test_id=test_id,
            qti_xml=qti_xml,
            metadata=metadata,
        )

        original_validation_path = variant_dir / "validation_result.json"
        original_payload = json.loads(original_validation_path.read_text(encoding="utf-8"))
        original_approved = bool(original_payload.get("is_approved"))

        print(f"[{index}/{len(variant_dirs)}] Revalidating {variant_dir.name} ({question_id}) with {provider}...")
        result = validator.validate(variant, source)

        summary["variants_seen"] += 1
        summary["original_approved" if original_approved else "original_rejected"] += 1

        revalidated_approved = result.is_approved
        summary["approved" if revalidated_approved else "rejected"] += 1
        summary["questions"][question_id]["approved" if revalidated_approved else "rejected"] += 1
        summary["agreement_with_original"]["match" if revalidated_approved == original_approved else "mismatch"] += 1

        summary["gates"]["constructo"]["pass" if result.concept_aligned else "fail"] += 1
        summary["gates"]["dificultad"]["pass" if result.difficulty_equal else "fail"] += 1
        summary["gates"]["answer_correct"]["pass" if result.answer_correct else "fail"] += 1
        summary["gates"]["non_mechanizable"]["pass" if result.non_mechanizable else "fail"] += 1
        if source.image_urls:
            summary["gates"]["imagen"]["not_implemented"] += 1
        else:
            summary["gates"]["imagen"]["not_applicable"] += 1

    summary["agreement_with_original"] = dict(summary["agreement_with_original"])
    summary["gates"] = {name: dict(counter) for name, counter in summary["gates"].items()}
    summary["questions"] = dict(sorted(summary["questions"].items()))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Revalidate an existing variant corpus with a chosen semantic validator stack.")
    parser.add_argument("--input-dir", required=True, help="Root directory containing variant outputs")
    parser.add_argument("--source-test", required=True, help="Source test ID")
    parser.add_argument("--questions", default=None, help="Comma-separated question IDs to include")
    parser.add_argument("--validator-provider", default="openai", choices=["gemini", "openai"], help="Semantic validator provider")
    parser.add_argument("--validator-model", default=None, help="Optional semantic validator model")
    parser.add_argument("--max-variants", type=int, default=None, help="Optional cap on the number of variants to revalidate")
    parser.add_argument("--max-variants-per-question", type=int, default=None, help="Optional per-question cap applied before the global cap")
    args = parser.parse_args()

    question_ids = None
    if args.questions:
        question_ids = [item.strip() for item in args.questions.split(",") if item.strip()]

    summary = run_benchmark(
        input_dir=Path(args.input_dir),
        test_id=args.source_test,
        question_ids=question_ids,
        provider=args.validator_provider,
        model=args.validator_model,
        max_variants=args.max_variants,
        max_variants_per_question=args.max_variants_per_question,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
