#!/usr/bin/env python3
"""Aggregate controlled benchmark metrics from persisted variant outputs."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _has_image_variant(metadata_path: Path, question_xml_path: Path) -> bool:
    metadata = _load_json(metadata_path)
    blueprint = metadata.get("planning_blueprint", {})
    if blueprint.get("requires_image") is True:
        return True
    xml = question_xml_path.read_text(encoding="utf-8")
    return "<img" in xml or "<qti-object" in xml or "<object" in xml


def build_report(output_dir: Path, test_id: str) -> dict[str, Any]:
    report: dict[str, Any] = {
        "output_dir": str(output_dir),
        "test_id": test_id,
        "variants_seen": 0,
        "approved": 0,
        "rejected": 0,
        "pipeline_failures": 0,
        "rejection_reasons": Counter(),
        "gates": {
            "constructo": Counter(),
            "dificultad": Counter(),
            "answer_correct": Counter(),
            "non_mechanizable": Counter(),
            "imagen": Counter(),
        },
        "questions": defaultdict(lambda: {"variants_seen": 0, "approved": 0, "rejected": 0}),
        "contracts": {
            "task_form": defaultdict(lambda: {"variants_seen": 0, "approved": 0, "rejected": 0}),
            "evidence_mode": defaultdict(lambda: {"variants_seen": 0, "approved": 0, "rejected": 0}),
            "cognitive_action": defaultdict(lambda: {"variants_seen": 0, "approved": 0, "rejected": 0}),
            "solution_structure": defaultdict(lambda: {"variants_seen": 0, "approved": 0, "rejected": 0}),
        },
    }

    for validation_path in sorted(output_dir.glob(f"{test_id}/Q*/**/validation_result.json")):
        variant_dir = validation_path.parent
        question_id = _question_id_from_variant_dir(variant_dir)
        payload = _load_json(validation_path)
        report["variants_seen"] += 1
        report["questions"][question_id]["variants_seen"] += 1

        if payload.get("pipeline_success") is False:
            report["pipeline_failures"] += 1

        semantic = payload.get("semantic_validation") or {}
        is_approved = bool(payload.get("is_approved"))
        if is_approved:
            report["approved"] += 1
            report["questions"][question_id]["approved"] += 1
        else:
            report["rejected"] += 1
            report["questions"][question_id]["rejected"] += 1
            reason = str((semantic or {}).get("rejection_reason") or "").strip()
            if reason:
                report["rejection_reasons"][reason] += 1

        report["gates"]["constructo"]["pass" if semantic.get("concept_aligned") else "fail"] += 1
        report["gates"]["dificultad"]["pass" if semantic.get("difficulty_equal") else "fail"] += 1
        report["gates"]["answer_correct"]["pass" if semantic.get("answer_correct") else "fail"] += 1
        report["gates"]["non_mechanizable"]["pass" if semantic.get("non_mechanizable") else "fail"] += 1

        metadata_path = variant_dir / "metadata_tags.json"
        question_xml_path = variant_dir / "question.xml"
        if metadata_path.exists() and question_xml_path.exists():
            metadata = _load_json(metadata_path)
            contract = metadata.get("construct_contract", {})
            _bump_contract_bucket(report["contracts"]["task_form"], str(contract.get("task_form") or "unknown"), is_approved)
            _bump_contract_bucket(report["contracts"]["evidence_mode"], str(contract.get("evidence_mode") or "unknown"), is_approved)
            _bump_contract_bucket(report["contracts"]["cognitive_action"], str(contract.get("cognitive_action") or "unknown"), is_approved)
            _bump_contract_bucket(report["contracts"]["solution_structure"], str(contract.get("solution_structure") or "unknown"), is_approved)
            if _has_image_variant(metadata_path, question_xml_path):
                report["gates"]["imagen"]["not_implemented"] += 1
            else:
                report["gates"]["imagen"]["not_applicable"] += 1
        else:
            report["gates"]["imagen"]["unknown"] += 1

    report["questions"] = dict(sorted(report["questions"].items()))
    report["rejection_reasons"] = dict(report["rejection_reasons"])
    report["gates"] = {name: dict(counter) for name, counter in report["gates"].items()}
    report["contracts"] = {
        name: dict(sorted(bucket.items()))
        for name, bucket in report["contracts"].items()
    }
    return report


def _question_id_from_variant_dir(variant_dir: Path) -> str:
    if variant_dir.parent.name in {"approved", "rejected"}:
        variants_dir = variant_dir.parent.parent
        if variants_dir.name == "variants":
            return variants_dir.parent.name
        return variants_dir.name
    if variant_dir.parent.parent.name in {"approved", "rejected"}:
        question_dir = variant_dir.parent.parent.parent
        if question_dir.name == "variants":
            return question_dir.parent.name
        return question_dir.name
    return variant_dir.parent.parent.name


def _bump_contract_bucket(bucket: defaultdict[str, dict[str, int]], key: str, is_approved: bool) -> None:
    bucket[key]["variants_seen"] += 1
    bucket[key]["approved" if is_approved else "rejected"] += 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarise variant benchmark results by gate.")
    parser.add_argument("--output-dir", required=True, help="Benchmark output directory root")
    parser.add_argument("--source-test", required=True, help="Test ID used in the run")
    args = parser.parse_args()

    report = build_report(Path(args.output_dir), args.source_test)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
