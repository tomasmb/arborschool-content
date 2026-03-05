"""Batch-run Phase 9 final validation over generated questions.

Uses the exact same request builder as the generation pipeline:
`build_final_validation_request`, which already embeds the shared
FINAL_VALIDATION_PROMPT + FINAL_VALIDATION_SCHEMA.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.question_feedback.final_validation_parser import (
    parse_final_validation_payload,
)
from app.question_generation.batch_api import (
    BatchRequest,
    BatchResponse,
    OpenAIBatchSubmitter,
)
from app.question_generation.batch_request_builders import (
    build_final_validation_request,
    parse_custom_id,
)
from app.question_generation.helpers import (
    deserialize_items,
    load_checkpoint,
)
from app.question_generation.models import GeneratedItem
from app.utils.logging_config import setup_logging
from app.utils.paths import QUESTION_GENERATION_DIR


@dataclass
class ItemRef:
    atom_id: str
    item: GeneratedItem


def main() -> None:
    args = _parse_args()
    setup_logging(verbose=args.verbose)

    refs = _load_question_items(
        max_items=args.max_items,
    )
    if not refs:
        print("No phase_8 feedback items found to validate.")
        return

    requests = [
        build_final_validation_request(
            ref.item, ref.atom_id, model=args.model,
        )
        for ref in refs
    ]
    print(f"Prepared {len(requests)} final-validation requests.")

    if args.dry_run:
        out = Path(args.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        run_id = _run_id()
        jsonl_path = out / f"{run_id}_requests.jsonl"
        submitter = _get_submitter(args, require_api_key=False)
        submitter.write_jsonl(requests, jsonl_path)
        print(f"Dry run complete: {jsonl_path}")
        return

    submitter = _get_submitter(args)
    responses, files = _submit_and_collect(submitter, requests, args)
    report = _build_report(refs, responses, args, files)
    report_path = _write_report(report, args.output_dir)
    _print_summary(report, report_path)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run Phase-9 final validation in Batch API mode over "
            "question-generation phase_8 items."
        ),
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=None,
        help="Optional cap on number of questions to validate.",
    )
    parser.add_argument(
        "--model",
        default="gpt-5.1",
        help="Model for validation requests (default: gpt-5.1).",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=30,
        help="Seconds between batch polls (default: 30).",
    )
    parser.add_argument(
        "--max-wait",
        type=int,
        default=86400,
        help="Max seconds to wait for completion (default: 86400).",
    )
    parser.add_argument(
        "--output-dir",
        default="app/data/.final-validation-batch",
        help="Directory for JSONL/results/report files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only write request JSONL; do not submit batch.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    return parser.parse_args()


def _load_question_items(
    max_items: int | None = None,
) -> list[ItemRef]:
    refs: list[ItemRef] = []
    for atom_dir in sorted(QUESTION_GENERATION_DIR.iterdir()):
        if not atom_dir.is_dir() or atom_dir.name.startswith("."):
            continue
        atom_id = atom_dir.name

        ckpt = load_checkpoint(atom_dir, 8, "feedback")
        if not ckpt or not ckpt.get("items"):
            continue

        items = deserialize_items(ckpt["items"])
        for item in items:
            if not item.item_id or not item.qti_xml:
                continue
            refs.append(ItemRef(atom_id=atom_id, item=item))
            if max_items and len(refs) >= max_items:
                return refs
    return refs


def _get_submitter(
    args: argparse.Namespace,
    *,
    require_api_key: bool = True,
) -> OpenAIBatchSubmitter:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key and require_api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    if not api_key:
        api_key = "dry-run"
    return OpenAIBatchSubmitter(
        api_key=api_key,
        poll_interval=args.poll_interval,
        max_wait=args.max_wait,
    )


def _submit_and_collect(
    submitter: OpenAIBatchSubmitter,
    requests: list[BatchRequest],
    args: argparse.Namespace,
) -> tuple[list[BatchResponse], dict[str, str]]:
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    run_id = _run_id()
    req_path = out / f"{run_id}_requests.jsonl"
    res_path = out / f"{run_id}_results.jsonl"

    print(f"Writing JSONL: {req_path.name}")
    submitter.write_jsonl(requests, req_path)

    print("Uploading JSONL file...")
    file_id = submitter.upload_file(req_path)

    print("Creating batch job...")
    batch_id = submitter.create_batch(
        file_id,
        metadata={
            "pipeline": "final_validation_qa",
            "run_id": run_id,
        },
    )
    print(f"Batch created: {batch_id}. Polling...")

    batch = submitter.poll_until_done(batch_id)
    status = batch.get("status")
    counts = batch.get("request_counts", {})
    print(
        "Batch finished: "
        f"status={status} "
        f"completed={counts.get('completed', 0)} "
        f"failed={counts.get('failed', 0)}",
    )

    if status != "completed":
        raise RuntimeError(
            f"Batch ended with status={status}. "
            "Inspect dashboard for details.",
        )

    output_file_id = batch.get("output_file_id")
    if not output_file_id:
        raise RuntimeError("Batch has no output_file_id.")

    print(f"Downloading results: {res_path.name}")
    submitter.download_file(output_file_id, res_path)
    responses = submitter.parse_results_file(res_path)
    return responses, {
        "run_id": run_id,
        "batch_id": batch_id,
        "request_jsonl": str(req_path),
        "result_jsonl": str(res_path),
    }


def _build_report(
    refs: list[ItemRef],
    responses: list[BatchResponse],
    args: argparse.Namespace,
    files: dict[str, str],
) -> dict[str, Any]:
    refs_by_item_id = {ref.item.item_id: ref for ref in refs}
    seen_item_ids: set[str] = set()
    failures: list[dict[str, str]] = []
    passed = 0

    for resp in responses:
        try:
            parsed = parse_custom_id(resp.custom_id)
        except ValueError:
            failures.append({
                "atom_id": "",
                "item_id": "",
                "reason": f"Malformed custom_id: {resp.custom_id}",
            })
            continue
        item_id = parsed.get("item_id", "")
        atom_id = parsed.get("atom_id", "")
        if not item_id:
            failures.append({
                "atom_id": atom_id,
                "item_id": "",
                "reason": f"Malformed custom_id: {resp.custom_id}",
            })
            continue

        seen_item_ids.add(item_id)
        ref = refs_by_item_id.get(item_id)
        if ref is None:
            failures.append({
                "atom_id": atom_id,
                "item_id": item_id,
                "reason": "Unknown item_id in response",
            })
            continue

        if resp.error:
            failures.append({
                "atom_id": ref.atom_id,
                "item_id": item_id,
                "reason": f"Batch error: {resp.error}",
            })
            continue

        try:
            parsed_payload = parse_final_validation_payload(
                json.loads(resp.text),
            )
        except (json.JSONDecodeError, ValueError) as exc:
            failures.append({
                "atom_id": ref.atom_id,
                "item_id": item_id,
                "reason": f"Parse error: {exc}",
            })
            continue

        if parsed_payload.validation_result == "pass":
            passed += 1
        else:
            failures.append({
                "atom_id": ref.atom_id,
                "item_id": item_id,
                "reason": (
                    parsed_payload.overall_reasoning
                    or "Validation failed"
                ),
            })

    missing = [
        ref for ref in refs
        if ref.item.item_id not in seen_item_ids
    ]
    for ref in missing:
        failures.append({
            "atom_id": ref.atom_id,
            "item_id": ref.item.item_id,
            "reason": "No API response returned for item",
        })

    total = len(refs)
    failed = len(failures)

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "total_items": total,
        "passed_items": passed,
        "failed_items": failed,
        "pass_rate": (passed / total) if total else 0.0,
        "batch": files,
        "failures": failures,
    }


def _write_report(report: dict[str, Any], output_dir: str) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{report['batch']['run_id']}_report.json"
    path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def _print_summary(report: dict[str, Any], report_path: Path) -> None:
    print("\nFinal Validation Batch Summary")
    print("=" * 40)
    print(f"Total items : {report['total_items']}")
    print(f"Passed      : {report['passed_items']}")
    print(f"Failed      : {report['failed_items']}")
    print(f"Pass rate   : {report['pass_rate']:.2%}")
    print(f"Report      : {report_path}")


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime(
        "final_validation_%Y%m%d_%H%M%S",
    )


if __name__ == "__main__":
    main()
