"""Batch API helpers for sync-scoped QA scan/confirm pipeline.

Supports two modes:
- prepare-only: build JSONL requests without submitting (dry run)
- execute: submit → poll → download → parse
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from app.prompts.qa_check import (
    build_confirm_prompt,
    build_scan_prompt,
)
from app.question_generation.batch_api import (
    BatchRequest,
    BatchResponse,
    OpenAIBatchSubmitter,
    build_text_messages,
)
from scripts.qa_state import PipelineState, ScanItem
from scripts.qa_shared import (
    is_lesson_source,
    normalize_confirmed_issues,
    normalize_rejected_issues,
)

logger = logging.getLogger(__name__)

_MODEL = "gpt-5.1"
# Keep legacy on-disk path for compatibility with existing tooling.
_BATCH_DIR = Path("app/data/.notation_pipeline/batch_files")
_CONFIRM_PLACEHOLDER_ISSUE = "DRY_RUN_PLACEHOLDER_ISSUE"


# ------------------------------------------------------------------
# Request builders
# ------------------------------------------------------------------


def _build_scan_request(item: ScanItem) -> BatchRequest:
    key, source, _fp, content, label = item
    prompt = build_scan_prompt(source, label, content)
    return BatchRequest(
        custom_id=f"scan:{key}",
        model=_MODEL,
        messages=build_text_messages(prompt),
        response_format={"type": "json_object"},
        reasoning_effort="low",
    )


def _build_confirm_request(key: str, item: dict) -> BatchRequest:
    source = str(item.get("source", ""))
    issues = item.get("issues", [])
    prompt = build_confirm_prompt(
        content=item["original"],
        issues=issues,
        source=source,
    )
    return BatchRequest(
        custom_id=f"confirm:{key}",
        model=_MODEL,
        messages=build_text_messages(prompt),
        response_format={"type": "json_object"},
        reasoning_effort="medium",
    )


def build_scan_requests(items: list[ScanItem]) -> list[BatchRequest]:
    """Build scan requests for a set of items."""
    return [_build_scan_request(it) for it in items]


def build_confirm_template_requests(
    items: list[ScanItem],
) -> list[BatchRequest]:
    """Build confirm-request templates for dry-run schema validation."""
    requests: list[BatchRequest] = []
    for key, source, fp, content, _label in items:
        pseudo_item = {
            "source": source,
            "file_path": fp,
            "original": content,
            "issues": [{
                "issue": _CONFIRM_PLACEHOLDER_ISSUE,
                "check_name": (
                    "lesson_content_quality_check"
                    if is_lesson_source(source)
                    else "content_quality_check"
                ),
                "severity": "blocking",
                "evidence": "dry-run placeholder",
            }],
        }
        requests.append(_build_confirm_request(key, pseudo_item))
    return requests


def write_jsonl(requests: list[BatchRequest], output_path: Path) -> Path:
    """Write batch JSONL without calling OpenAI."""
    submitter = OpenAIBatchSubmitter(api_key="dry-run")
    submitter.write_jsonl(requests, output_path)
    return output_path


# ------------------------------------------------------------------
# Response parsing
# ------------------------------------------------------------------


def _parse_scan_response(resp: BatchResponse) -> dict:
    key = resp.custom_id.removeprefix("scan:")
    if resp.error:
        return {
            "key": key,
            "has_issues": None,
            "issues": [],
            "error": resp.error,
            "input_tokens": resp.input_tokens,
            "output_tokens": resp.output_tokens,
        }
    try:
        data = json.loads(resp.text)
    except json.JSONDecodeError:
        logger.warning(
            "Bad JSON from batch for %s: %s", key, resp.text[:200],
        )
        data = {"parse_error": True}
    raw_issues = data.get("issues", [])
    issues = raw_issues if isinstance(raw_issues, list) else []
    has = data.get("status") == "HAS_ISSUES" and bool(issues)
    return {
        "key": key,
        "has_issues": has,
        "issues": issues,
        "error": None,
        "input_tokens": resp.input_tokens,
        "output_tokens": resp.output_tokens,
    }


def _parse_confirm_response(resp: BatchResponse) -> dict:
    key = resp.custom_id.removeprefix("confirm:")
    if resp.error:
        return {
            "key": key,
            "confirmed": [],
            "rejected": [],
            "error": resp.error,
            "input_tokens": resp.input_tokens,
            "output_tokens": resp.output_tokens,
        }
    try:
        data = json.loads(resp.text)
    except json.JSONDecodeError:
        logger.warning(
            "Bad JSON from batch for %s: %s", key, resp.text[:200],
        )
        data = {}

    confirmed = normalize_confirmed_issues(
        data.get("confirmed", []),
    )
    rejected = normalize_rejected_issues(
        data.get("rejected", []),
    )

    return {
        "key": key,
        "confirmed": confirmed,
        "rejected": rejected,
        "error": None,
        "input_tokens": resp.input_tokens,
        "output_tokens": resp.output_tokens,
    }


# ------------------------------------------------------------------
# Orchestration
# ------------------------------------------------------------------


def _get_submitter() -> OpenAIBatchSubmitter:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    return OpenAIBatchSubmitter(api_key=api_key)


def _submit_and_collect(
    submitter: OpenAIBatchSubmitter,
    requests: list[BatchRequest],
    phase_label: str,
) -> list[BatchResponse]:
    _BATCH_DIR.mkdir(parents=True, exist_ok=True)
    jsonl_path = _BATCH_DIR / f"{phase_label}.jsonl"
    results_path = _BATCH_DIR / f"{phase_label}_results.jsonl"

    print(f"Writing {len(requests)} requests to {jsonl_path.name}...")
    submitter.write_jsonl(requests, jsonl_path)

    print("Uploading JSONL file...")
    file_id = submitter.upload_file(jsonl_path)

    print("Creating batch job...")
    batch_id = submitter.create_batch(
        file_id,
        metadata={"pipeline": "sync_scoped_qa_scan", "phase": phase_label},
    )
    print(f"Batch created: {batch_id}. Polling for completion...")

    batch = submitter.poll_until_done(batch_id, poll_interval=30)
    status = batch["status"]
    counts = batch.get("request_counts", {})
    print(
        f"Batch {batch_id} finished: status={status}  "
        f"completed={counts.get('completed', 0)}  "
        f"failed={counts.get('failed', 0)}",
    )

    if status != "completed":
        raise RuntimeError(
            f"Batch {batch_id} ended with status={status}. "
            f"Check the OpenAI dashboard for details.",
        )

    output_file_id = batch.get("output_file_id")
    if not output_file_id:
        raise RuntimeError(f"Batch {batch_id} has no output file.")

    print("Downloading results...")
    submitter.download_file(output_file_id, results_path)
    return submitter.parse_results_file(results_path)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


def run_batch_scan(items: list[ScanItem]) -> list[dict]:
    """Pass 1 via Batch API."""
    requests = build_scan_requests(items)
    submitter = _get_submitter()
    responses = _submit_and_collect(submitter, requests, "sync_qa_scan")
    results = [_parse_scan_response(r) for r in responses]

    ok = sum(1 for r in results if r["has_issues"] is False)
    flagged = sum(1 for r in results if r["has_issues"] is True)
    errors = sum(1 for r in results if r["error"])
    print(f"Batch scan done: {ok} OK, {flagged} flagged, {errors} errors")
    return results


def run_batch_confirm(state: PipelineState) -> None:
    """Pass 2 via Batch API."""
    flagged = state.items_by_status("flagged")
    if not flagged:
        print("No flagged items to confirm.")
        return

    print(f"Building {len(flagged)} confirm requests...")
    requests = [_build_confirm_request(key, item) for key, item in flagged]

    submitter = _get_submitter()
    responses = _submit_and_collect(
        submitter, requests, "sync_qa_confirm",
    )

    confirmed_count = 0
    fp_count = 0
    for resp_dict in (_parse_confirm_response(r) for r in responses):
        key = resp_dict["key"]
        item = state.get_item(key)
        if not item:
            logger.warning("No state item for key %s", key)
            continue
        state.add_tokens(
            resp_dict["input_tokens"], resp_dict["output_tokens"],
        )
        if resp_dict.get("error"):
            logger.warning(
                "Batch error for %s: %s", key, resp_dict["error"],
            )
            continue
        item["confirmed_issues"] = resp_dict["confirmed"]
        item["rejected_issues"] = resp_dict["rejected"]
        if resp_dict["confirmed"]:
            item["status"] = "confirmed"
            confirmed_count += 1
        else:
            item["status"] = "false_positive"
            fp_count += 1

    state.save()
    print(
        f"Batch confirm done: {confirmed_count} confirmed, "
        f"{fp_count} false positive",
    )
