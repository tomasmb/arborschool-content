"""Batch API mode for the notation scan pipeline.

Builds BatchRequest objects for Pass 1 (scan) and Pass 2 (confirm),
submits them via OpenAIBatchSubmitter, and returns results in the same
format as the synchronous pipeline for seamless integration.

Uses the OpenAI Batch API for 50% cost savings.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from app.prompts.notation_check import (
    ISSUE_CATEGORIES,
    build_confirm_prompt,
    build_scan_mini_class_prompt,
    build_scan_xml_file_prompt,
)
from app.question_generation.batch_api import (
    BatchRequest,
    BatchResponse,
    OpenAIBatchSubmitter,
    build_text_messages,
)
from scripts.notation_state import PipelineState, ScanItem

logger = logging.getLogger(__name__)

_MODEL = "gpt-5.1"
_BATCH_DIR = Path("app/data/.notation_pipeline/batch_files")


# ------------------------------------------------------------------
# Batch request builders
# ------------------------------------------------------------------


def _build_scan_request(item: ScanItem) -> BatchRequest:
    """Build a BatchRequest for a single scan-pass item."""
    key, source, _fp, content, label = item
    if source == "mini-class":
        prompt = build_scan_mini_class_prompt(label, content)
    else:
        prompt = build_scan_xml_file_prompt(label, content)
    return BatchRequest(
        custom_id=f"scan:{key}",
        model=_MODEL,
        messages=build_text_messages(prompt),
        response_format={"type": "json_object"},
        reasoning_effort="low",
    )


def _build_confirm_request(
    key: str, item: dict,
) -> BatchRequest:
    """Build a BatchRequest for a single confirm-pass item."""
    prompt = build_confirm_prompt(
        content=item["original"],
        issues=item.get("issues", []),
    )
    return BatchRequest(
        custom_id=f"confirm:{key}",
        model=_MODEL,
        messages=build_text_messages(prompt),
        response_format={"type": "json_object"},
        reasoning_effort="medium",
    )


# ------------------------------------------------------------------
# Parse batch responses
# ------------------------------------------------------------------


def _parse_scan_response(resp: BatchResponse) -> dict:
    """Parse a BatchResponse into the same dict format as _scan_one."""
    key = resp.custom_id.removeprefix("scan:")
    if resp.error:
        return {
            "key": key, "has_issues": None,
            "issues": [], "error": resp.error,
            "input_tokens": resp.input_tokens,
            "output_tokens": resp.output_tokens,
        }
    try:
        data = json.loads(resp.text)
    except json.JSONDecodeError:
        logger.warning("Bad JSON from batch for %s: %s", key, resp.text[:200])
        data = {"parse_error": True}

    has = data.get("status") == "HAS_ISSUES"
    issues = data.get("issues", []) if has else []
    return {
        "key": key, "has_issues": has,
        "issues": issues, "error": None,
        "input_tokens": resp.input_tokens,
        "output_tokens": resp.output_tokens,
    }


def _parse_confirm_response(resp: BatchResponse) -> dict:
    """Parse a BatchResponse into confirm result dict."""
    key = resp.custom_id.removeprefix("confirm:")
    if resp.error:
        return {
            "key": key,
            "confirmed": [], "rejected": [],
            "error": resp.error,
            "input_tokens": resp.input_tokens,
            "output_tokens": resp.output_tokens,
        }
    try:
        data = json.loads(resp.text)
    except json.JSONDecodeError:
        logger.warning("Bad JSON from batch for %s: %s", key, resp.text[:200])
        data = {}
    confirmed = data.get("confirmed", [])
    for ci in confirmed:
        if ci.get("category") not in ISSUE_CATEGORIES:
            ci["category"] = "manual_fix"
    return {
        "key": key,
        "confirmed": confirmed,
        "rejected": data.get("rejected", []),
        "error": None,
        "input_tokens": resp.input_tokens,
        "output_tokens": resp.output_tokens,
    }


# ------------------------------------------------------------------
# Orchestration: submit → poll → download → parse
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
    """Write JSONL, upload, create batch, poll, download, parse."""
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
        metadata={"pipeline": "notation_scan", "phase": phase_label},
    )
    print(f"Batch created: {batch_id}. Polling for completion...")

    batch = submitter.poll_until_done(batch_id, poll_interval=30)
    status = batch["status"]
    counts = batch.get("request_counts", {})
    print(
        f"Batch {batch_id} finished: status={status}  "
        f"completed={counts.get('completed', 0)}  "
        f"failed={counts.get('failed', 0)}"
    )

    if status != "completed":
        raise RuntimeError(
            f"Batch {batch_id} ended with status={status}. "
            f"Check the OpenAI dashboard for details."
        )

    output_file_id = batch.get("output_file_id")
    if not output_file_id:
        raise RuntimeError(f"Batch {batch_id} has no output file.")

    print("Downloading results...")
    submitter.download_file(output_file_id, results_path)
    return submitter.parse_results_file(results_path)


# ------------------------------------------------------------------
# Public API: batch scan + batch confirm
# ------------------------------------------------------------------


def run_batch_scan(items: list[ScanItem]) -> list[dict]:
    """Pass 1 via Batch API: scan every item for notation issues.

    Returns results in the same format as the synchronous _run_scan().
    """
    requests = [_build_scan_request(it) for it in items]
    submitter = _get_submitter()
    responses = _submit_and_collect(submitter, requests, "notation_scan")

    results = [_parse_scan_response(r) for r in responses]

    ok = sum(1 for r in results if r["has_issues"] is False)
    flagged = sum(1 for r in results if r["has_issues"] is True)
    errors = sum(1 for r in results if r["error"])
    print(f"Batch scan done: {ok} OK, {flagged} flagged, {errors} errors")
    return results


def run_batch_confirm(state: PipelineState) -> None:
    """Pass 2 via Batch API: confirm flagged items.

    Updates state in-place with confirmed/rejected issues,
    same as the synchronous _run_confirm().
    """
    flagged = state.items_by_status("flagged")
    if not flagged:
        print("No flagged items to confirm.")
        return

    print(f"Building {len(flagged)} confirm requests...")
    requests = [
        _build_confirm_request(key, item) for key, item in flagged
    ]

    submitter = _get_submitter()
    responses = _submit_and_collect(
        submitter, requests, "notation_confirm",
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
            logger.warning("Batch error for %s: %s", key, resp_dict["error"])
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
        f"{fp_count} false positive"
    )
