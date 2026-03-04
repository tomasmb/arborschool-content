"""Sync-scoped QA scan and confirm pipeline."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.llm_clients import OpenAIClient, load_default_openai_client
from app.prompts.qa_check import (
    build_confirm_prompt,
    build_scan_prompt,
)
from scripts.qa_batch import run_batch_confirm, run_batch_scan
from scripts.qa_shared import (
    normalize_confirmed_issues,
    normalize_rejected_issues,
)
from scripts.qa_state import PipelineState, ScanItem, populate_from_scan
from scripts.qa_preflight import (
    GATE_PATH,
    ensure_gate,
    run_dry_run,
    source_counts,
)
from scripts.qa_sources import (
    POOL_ALIASES,
    POOL_CHOICES,
    load_items,
    pool_name,
)

logger = logging.getLogger(__name__)
_PRINT_LOCK = threading.Lock()


def _parse_response(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Bad JSON: %s", raw[:200])
        return {"parse_error": True}


def _normalize_issues(raw_issues: Any) -> list[dict | str]:
    if not isinstance(raw_issues, list):
        return []
    return [issue for issue in raw_issues if isinstance(issue, (dict, str))]


def _scan_one(client: OpenAIClient, item: ScanItem) -> dict:
    key, source, _fp, content, label = item
    prompt = build_scan_prompt(source, label, content)
    try:
        resp = client.call(
            prompt,
            response_format={"type": "json_object"},
            reasoning_effort="low",
        )
        data = _parse_response(resp.text)
        issues = _normalize_issues(data.get("issues", []))
        has = data.get("status") == "HAS_ISSUES" and bool(issues)
        return {
            "key": key,
            "has_issues": has,
            "issues": issues,
            "error": None,
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
        }
    except Exception as exc:
        logger.warning("Scan failed %s: %s", key, exc)
        return {
            "key": key,
            "has_issues": None,
            "issues": [],
            "error": str(exc),
            "input_tokens": 0,
            "output_tokens": 0,
        }


def _run_scan(
    client: OpenAIClient,
    items: list[ScanItem],
    workers: int,
) -> list[dict]:
    results: list[dict] = []
    total = len(items)
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(_scan_one, client, it): it for it in items}
        for fut in as_completed(futs):
            r = fut.result()
            results.append(r)
            done += 1
            source = futs[fut][1]
            tag = {
                "official-question": "OFF",
                "variant": "VAR",
                "generated-question": "GEN",
                "lesson": "LES",
            }.get(source, "?")
            if r["error"]:
                s = "ERROR"
            elif r["has_issues"]:
                s = f"FLAG({len(r['issues'])})"
            else:
                s = "OK"
            with _PRINT_LOCK:
                print(f"[{done}/{total}] [{tag}] [{s}] {r['key']}")
    return results


def _confirm_one(client: OpenAIClient, key: str, item: dict) -> dict:
    prompt = build_confirm_prompt(
        content=item["original"],
        issues=item.get("issues", []),
        source=item.get("source", ""),
    )
    resp = client.call(
        prompt,
        response_format={"type": "json_object"},
        reasoning_effort="medium",
    )
    data = _parse_response(resp.text)
    return {
        "key": key,
        "confirmed": normalize_confirmed_issues(
            data.get("confirmed", []),
        ),
        "rejected": normalize_rejected_issues(
            data.get("rejected", []),
        ),
        "input_tokens": resp.usage.input_tokens,
        "output_tokens": resp.usage.output_tokens,
    }


def _run_confirm(
    client: OpenAIClient,
    state: PipelineState,
    workers: int,
) -> None:
    flagged = state.items_by_status("flagged")
    if not flagged:
        print("No flagged items to confirm.")
        return
    total = len(flagged)
    done = 0
    print(f"Confirming {total} flagged items (medium reasoning)...")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {
            pool.submit(_confirm_one, client, key, item): key
            for key, item in flagged
        }
        for fut in as_completed(futs):
            key = futs[fut]
            done += 1
            try:
                r = fut.result()
            except Exception as exc:
                logger.warning("Confirm failed for %s: %s", key, exc)
                with _PRINT_LOCK:
                    print(f"  [{done}/{total}] [ERROR] {key}")
                continue
            item = state.get_item(key)
            if item is None:
                continue
            state.add_tokens(r["input_tokens"], r["output_tokens"])
            item["confirmed_issues"] = r["confirmed"]
            item["rejected_issues"] = r["rejected"]
            if r["confirmed"]:
                item["status"] = "confirmed"
                tag = "CONFIRMED"
            else:
                item["status"] = "false_positive"
                tag = "FP"
            with _PRINT_LOCK:
                print(
                    f"  [{done}/{total}] [{tag}] {key}"
                    f" ({len(r['confirmed'])} conf, {len(r['rejected'])} rej)",
                )
    state.save()


def _require_api_key() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not set.")
        sys.exit(1)


def _load_state(args: argparse.Namespace) -> PipelineState | None:
    if args.state:
        return PipelineState.load(Path(args.state))
    return PipelineState.load_latest(pool_name(args.only))


def _print_items_summary(items: list[ScanItem]) -> None:
    counts = source_counts(items)
    parts = [f"{n} {s}" for s, n in sorted(counts.items())]
    print(f"Loaded {len(items)} items: {', '.join(parts)}")


def _cmd_dry_run(args: argparse.Namespace) -> None:
    items = load_items(args.only, args.limit)
    report_path = (
        Path(args.report)
        if args.report
        else Path("app/data/.notation_pipeline/preflight")
        / f"preflight_{pool_name(args.only)}.json"
    )
    emit_dir = Path(args.emit_jsonl) if args.emit_jsonl else None
    report = run_dry_run(
        items=items,
        pool=pool_name(args.only),
        limit=args.limit,
        report_path=report_path,
        emit_jsonl_dir=emit_dir,
    )
    print("Dry-run complete (no LLM calls).")
    print(f"Pool: {report['pool']}  Total: {report['total_items']}")
    for source, n in sorted(report["counts_by_source"].items()):
        print(f"  {source:20s}: {n}")
    c = report["cost_estimate"]
    print(
        "Estimated cost range: "
        f"${c['cost_usd_min']:.2f} - ${c['cost_usd_max']:.2f}",
    )
    print(f"Report: {report_path}")
    if emit_dir:
        print(f"JSONL dir: {emit_dir}")
    print(f"Gate file: {GATE_PATH}")


def _cmd_scan(args: argparse.Namespace) -> None:
    try:
        ensure_gate(
            force_run=args.force_run,
            expected_pool=pool_name(args.only),
        )
    except RuntimeError as exc:
        print(str(exc))
        sys.exit(2)
    _require_api_key()
    items = load_items(args.only, args.limit)
    _print_items_summary(items)
    if not items:
        print("Nothing to scan.")
        return
    if args.batch:
        print(f"Scanning {len(items)} items via Batch API (50% cost)...")
        results = run_batch_scan(items)
    else:
        workers = min(args.workers, len(items))
        client = load_default_openai_client(model="gpt-5.1")
        print(
            f"Scanning {len(items)} items with {workers} workers "
            "(low reasoning, 1 item per call)...",
        )
        results = _run_scan(client, items, workers)
    state = PipelineState(pool=pool_name(args.only))
    populate_from_scan(state, items, results)
    state.save()
    state.print_summary()


def _cmd_confirm(args: argparse.Namespace) -> None:
    try:
        ensure_gate(
            force_run=args.force_run,
            expected_pool=pool_name(args.only),
        )
    except RuntimeError as exc:
        print(str(exc))
        sys.exit(2)
    _require_api_key()
    state = _load_state(args)
    if not state:
        print("No saved state. Run a scan first.")
        return
    flagged = state.items_by_status("flagged")
    if not flagged:
        print("No flagged items to confirm.")
        state.print_summary()
        return
    print(f"Found {len(flagged)} flagged items to confirm.")
    if args.batch:
        run_batch_confirm(state)
    else:
        client = load_default_openai_client(model="gpt-5.1")
        _run_confirm(client, state, args.workers)
    state.print_summary()


def _cmd_status(args: argparse.Namespace) -> None:
    state = _load_state(args)
    if not state:
        print(f"No saved state for pool '{pool_name(args.only)}'.")
        return
    state.print_summary()


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Sync-scoped QA scanner for questions/variants/"
            "generated-questions/lessons.",
        ),
    )
    p.add_argument(
        "--only",
        choices=list(POOL_CHOICES) + list(POOL_ALIASES),
        default=None,
    )
    p.add_argument("--workers", type=int, default=8)
    p.add_argument(
        "--confirm",
        action="store_true",
        help="Pass 2: confirm flagged findings (medium reasoning).",
    )
    p.add_argument(
        "--state",
        type=str,
        default=None,
        help="Path to a specific state JSON file to use.",
    )
    p.add_argument(
        "--status",
        action="store_true",
        help="Show pipeline state for the selected pool.",
    )
    p.add_argument(
        "--batch",
        action="store_true",
        help="Use OpenAI Batch API for live calls.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Build preflight report and optional JSONL only (no LLM calls).",
    )
    p.add_argument(
        "--report",
        type=str,
        default=None,
        help="Output path for preflight report JSON.",
    )
    p.add_argument(
        "--emit-jsonl",
        type=str,
        default=None,
        help="Directory to emit scan/confirm request JSONL files.",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on candidates (applies to dry-run and live scan).",
    )
    p.add_argument(
        "--force-run",
        action="store_true",
        help="Bypass dry-run gate and run live calls directly.",
    )
    p.add_argument("--verbose", "-v", action="store_true")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    if args.dry_run:
        _cmd_dry_run(args)
    elif args.status:
        _cmd_status(args)
    elif args.confirm:
        _cmd_confirm(args)
    else:
        _cmd_scan(args)


if __name__ == "__main__":
    main()
