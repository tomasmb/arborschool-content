"""ARCHIVED 2026-03-02: One-off script, work completed. The permanent
notation fix pipeline lives in scripts/apply_notation_fixes.py.

Original description:
One-off: LLM-fix remaining confirmed+fix_fail notation items.

The deterministic regex couldn't handle these edge cases (minus
signs, entity-encoded operators, decimals in <mn>). Sends each
item to gpt-5.1 with the full notation standard, validates with
the same sanity checks, and writes to disk.
"""

from __future__ import annotations

import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.llm_clients import load_default_openai_client
from app.prompts.notation_check import build_llm_fix_prompt
from scripts.notation_fix_writer import write_fixes_to_disk
from scripts.notation_sanity import run_sanity_checks
from scripts.notation_state import PipelineState

_LOCK = threading.Lock()


def _process_one(
    client: object,
    key: str,
    item: dict,
) -> dict:
    """Send one item to the LLM fixer and validate the result."""
    issues = [
        ci["issue"]
        for ci in item.get("confirmed_issues", [])
        if ci.get("issue")
    ]
    if not issues:
        return {"key": key, "status": "no_issues", "in": 0, "out": 0}

    prompt = build_llm_fix_prompt(
        content=item["original"], issues=issues,
    )
    resp = client.call(
        prompt,
        response_format={"type": "json_object"},
        reasoning_effort="medium",
    )
    in_tok = resp.usage.input_tokens
    out_tok = resp.usage.output_tokens

    try:
        data = json.loads(resp.text)
    except json.JSONDecodeError:
        return {
            "key": key, "status": "json_error",
            "in": in_tok, "out": out_tok,
        }

    if data.get("status") != "FIXED" or not data.get("corrected_content"):
        return {
            "key": key, "status": "unchanged",
            "in": in_tok, "out": out_tok,
        }

    fixed = data["corrected_content"]
    ctype = "HTML" if item.get("source") == "mini-class" else "QTI XML"
    ok, reasons = run_sanity_checks(
        item["original"], fixed, ctype, lenient=True,
    )
    if not ok:
        return {
            "key": key, "status": "sanity_fail",
            "reasons": reasons, "in": in_tok, "out": out_tok,
        }
    return {
        "key": key, "status": "ok", "fixed": fixed,
        "in": in_tok, "out": out_tok,
    }


def main() -> None:
    state = PipelineState.load_latest("all")
    if not state:
        print("No saved state found.")
        return

    for _k, item in state.items.items():
        if item.get("status") == "fix_fail":
            item["status"] = "confirmed"
            item.pop("sanity_result", None)
            print(f"Reset {_k} → confirmed (was fix_fail)")

    targets = [
        (k, item) for k, item in state.items.items()
        if item.get("status") == "confirmed"
    ]
    print(f"\nTargets: {len(targets)} items")
    if not targets:
        print("Nothing to fix.")
        return

    state.save()
    client = load_default_openai_client(model="gpt-5.1")

    ok_count = fail_count = skip_count = 0
    done = 0
    total = len(targets)

    with ThreadPoolExecutor(max_workers=10) as pool:
        futs = {
            pool.submit(_process_one, client, k, item): (k, item)
            for k, item in targets
        }
        for fut in as_completed(futs):
            key, item = futs[fut]
            done += 1
            try:
                r = fut.result()
            except Exception as exc:
                with _LOCK:
                    print(f"  [{done}/{total}] [ERROR] {key}: {exc}")
                fail_count += 1
                continue

            state.add_tokens(r.get("in", 0), r.get("out", 0))

            if r["status"] == "ok":
                item["fixed_content"] = r["fixed"]
                item["status"] = "fix_ok"
                ok_count += 1
                with _LOCK:
                    print(f"  [{done}/{total}] [FIX_OK] {key}")
            elif r["status"] == "sanity_fail":
                item["status"] = "fix_fail"
                item["sanity_result"] = r.get("reasons", [])
                fail_count += 1
                with _LOCK:
                    print(f"  [{done}/{total}] [SANITY_FAIL] {key}")
                    for reason in r.get("reasons", [])[:3]:
                        print(f"    ! {reason[:120]}")
            else:
                skip_count += 1
                with _LOCK:
                    print(
                        f"  [{done}/{total}] "
                        f"[{r['status'].upper()}] {key}"
                    )

    state.save()
    print(f"\nResults: {ok_count} ok, {fail_count} fail, {skip_count} skip")

    if ok_count > 0:
        written = write_fixes_to_disk(state)
        print(f"Written to disk: {written} items")

    state.print_summary()


if __name__ == "__main__":
    main()
