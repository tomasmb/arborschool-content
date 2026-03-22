#!/usr/bin/env python3
"""Normalize hard-variants output directories to the source/ + variants/ layout."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from app.utils.qti_extractor import parse_qti_xml

FINALIZED_ROOT = Path("app/data/pruebas/finalizadas")


def resolve_finalized_test_dir(test_id: str) -> Path:
    candidates = [FINALIZED_ROOT / test_id]
    normalized = test_id.lower()
    for path in FINALIZED_ROOT.iterdir():
        if path.is_dir() and path.name.lower() == normalized:
            candidates.append(path)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"No finalized test directory found for {test_id}")


def ensure_source_snapshot(question_dir: Path, test_id: str, question_id: str) -> None:
    source_dir = question_dir / "source"
    if source_dir.exists():
        return

    finalized_test_dir = resolve_finalized_test_dir(test_id)
    finalized_question_dir = finalized_test_dir / "qti" / question_id
    xml_path = finalized_question_dir / "question.xml"
    metadata_path = finalized_question_dir / "metadata_tags.json"
    if not xml_path.exists() or not metadata_path.exists():
        raise FileNotFoundError(f"Missing finalized source files for {test_id}/{question_id}")

    source_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(xml_path, source_dir / "question.xml")
    shutil.copy2(metadata_path, source_dir / "metadata_tags.json")

    qti_xml = xml_path.read_text(encoding="utf-8")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    parsed = parse_qti_xml(qti_xml)
    source_info = {
        "source_question_id": question_id,
        "source_test_id": test_id,
        "question_text": parsed.text,
        "choices": parsed.choices,
        "correct_answer": parsed.correct_answer_text or "",
        "image_urls": parsed.image_urls,
        "metadata_summary_keys": sorted(metadata.keys()),
    }
    with (source_dir / "source_info.json").open("w", encoding="utf-8") as handle:
        json.dump(source_info, handle, ensure_ascii=False, indent=2)


def move_loose_variant_artifacts(question_dir: Path) -> None:
    variants_dir = question_dir / "variants"
    variants_dir.mkdir(exist_ok=True)

    for name in ("approved", "rejected", "generation_report.json", "variant_plan.json"):
        old_path = question_dir / name
        if old_path.exists():
            shutil.move(str(old_path), str(variants_dir / name))


def migrate_question_dir(question_dir: Path, test_id: str) -> None:
    ensure_source_snapshot(question_dir, test_id, question_dir.name)
    move_loose_variant_artifacts(question_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize hard_variants directories to source/ + variants/")
    parser.add_argument("--root", default="app/data/pruebas/hard_variants", help="Root hard_variants directory")
    args = parser.parse_args()

    root = Path(args.root)
    for run_dir in sorted([p for p in root.iterdir() if p.is_dir()]):
        if run_dir.name == "benchmarks":
            for benchmark_dir in sorted([p for p in run_dir.iterdir() if p.is_dir()]):
                for test_dir in sorted([p for p in benchmark_dir.iterdir() if p.is_dir()]):
                    for question_dir in sorted([p for p in test_dir.iterdir() if p.is_dir()]):
                        migrate_question_dir(question_dir, test_dir.name)
            continue

        for test_dir in sorted([p for p in run_dir.iterdir() if p.is_dir()]):
            for question_dir in sorted([p for p in test_dir.iterdir() if p.is_dir()]):
                migrate_question_dir(question_dir, test_dir.name)


if __name__ == "__main__":
    main()
