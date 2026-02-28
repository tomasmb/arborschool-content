"""Pipeline phases: fix -> sanity -> validate -> revalidate -> apply.

Pass 2: LLM fix (flagged -> pending_validate)
Pass 3: sanity checks + LLM validate (-> pending_revalidate)
Pass 4: LLM revalidate with semantic equivalence prompt
Apply: write passing fixes to disk with backups
Retry: re-fix failed items with rejection feedback
Verify: post-apply re-scan to confirm cleanliness
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from app.llm_clients import OpenAIClient
from scripts.notation_fix_io import (
    apply_question_group,
    apply_single_item,
    revert_question_item,
    revert_single_item,
)
from scripts.notation_fix_llm import (
    fix_one,
    revalidate_one,
    retry_one,
    validate_one,
    verify_one,
)
from scripts.notation_sanity import run_sanity_checks, run_xsd_validation
from scripts.notation_state import PipelineState

logger = logging.getLogger(__name__)
_LOCK = threading.Lock()


def _content_type(source: str) -> str:
    return "HTML" if source == "mini-class" else "QTI XML"


# -- Pass 2: fix flagged items --

def _phase_fix(
    client: OpenAIClient, state: PipelineState, workers: int,
) -> None:
    """Fix all flagged items via LLM (medium reasoning)."""
    flagged = state.items_by_status("flagged")
    if not flagged:
        return
    print(f"  Fixing {len(flagged)} flagged items...")
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {
            pool.submit(fix_one, client, item): key
            for key, item in flagged
        }
        for fut in as_completed(futs):
            key = futs[fut]
            result = fut.result()
            item = state.get_item(key)
            state.add_tokens(
                result.get("input_tokens", 0),
                result.get("output_tokens", 0),
            )
            if result["status"] == "FIXED" and result["corrected"]:
                item["corrected"] = result["corrected"]
                item["issues"] = result["issues"]
                item["status"] = "pending_validate"
            elif result["status"] == "OK":
                item["status"] = "ok"
            else:
                item["status"] = "fail"
                item["validation_result"] = {
                    "verdict": "FIX_ERROR",
                    "reasons": result["issues"],
                }
            done += 1
            with _LOCK:
                tag = result["status"]
                print(f"  [{done}/{len(futs)}] [FIX:{tag}] {key}")


# -- Pass 3: sanity check + LLM validation --

def _run_xsd_checks(state: PipelineState) -> None:
    """Run XSD validation on QTI XML items still pending."""
    pending_xml = [
        (k, it) for k, it in state.items_by_status("pending_validate")
        if it["source"] != "mini-class"
    ]
    if not pending_xml:
        return
    print(f"  XSD-validating {len(pending_xml)} QTI items...")
    for key, item in pending_xml:
        passed, reasons = run_xsd_validation(item["corrected"])
        if not passed:
            sr = item.get("sanity_result") or {
                "pass": True, "reasons": [],
            }
            sr["pass"] = False
            sr["reasons"].extend(reasons)
            item["sanity_result"] = sr
            item["status"] = "sanity_fail"
            with _LOCK:
                print(f"  [XSD_FAIL] {key}: {reasons}")


def _phase_sanity_validate(
    client: OpenAIClient, state: PipelineState, workers: int,
) -> None:
    """Sanity checks + LLM validation. Pass -> pending_revalidate."""
    pending = state.items_by_status("pending_validate")
    if not pending:
        return
    for key, item in pending:
        ctype = _content_type(item["source"])
        passed, reasons = run_sanity_checks(
            item["original"], item["corrected"], ctype,
        )
        item["sanity_result"] = {"pass": passed, "reasons": reasons}
        if not passed:
            item["status"] = "sanity_fail"
            with _LOCK:
                print(f"  [SANITY_FAIL] {key}: {reasons}")

    _run_xsd_checks(state)

    to_validate = state.items_by_status("pending_validate")
    if not to_validate:
        return
    print(f"  LLM-validating {len(to_validate)} items...")
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs: dict = {}
        for key, item in to_validate:
            ctype = _content_type(item["source"])
            futs[pool.submit(
                validate_one, client,
                item["original"], item["corrected"],
                item["issues"], ctype,
            )] = key
        for fut in as_completed(futs):
            key = futs[fut]
            vr = fut.result()
            item = state.get_item(key)
            item["validation_result"] = vr
            state.add_tokens(
                vr.get("input_tokens", 0),
                vr.get("output_tokens", 0),
            )
            if vr["verdict"] == "PASS":
                item["status"] = "pending_revalidate"
            else:
                item["status"] = "fail"
            done += 1
            with _LOCK:
                print(
                    f"  [{done}/{len(futs)}] "
                    f"[{vr['verdict']}] {key}",
                )


# -- Pass 4: independent revalidation --

def _phase_revalidate(
    client: OpenAIClient, state: PipelineState, workers: int,
) -> None:
    """Independent semantic equivalence check (different prompt)."""
    pending = state.items_by_status("pending_revalidate")
    if not pending:
        return
    print(f"  Revalidating {len(pending)} items...")
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {
            pool.submit(
                revalidate_one, client,
                item["original"], item["corrected"],
            ): key
            for key, item in pending
        }
        for fut in as_completed(futs):
            key = futs[fut]
            rr = fut.result()
            item = state.get_item(key)
            state.add_tokens(
                rr.get("input_tokens", 0),
                rr.get("output_tokens", 0),
            )
            item["revalidation_result"] = rr
            if rr["pass"]:
                item["status"] = "pass"
            else:
                item["status"] = "fail"
                item["validation_result"] = {
                    "verdict": "REVALIDATE_FAIL",
                    "reasons": rr.get("issues", []),
                }
            done += 1
            with _LOCK:
                tag = "PASS" if rr["pass"] else "FAIL"
                print(f"  [{done}/{len(futs)}] [REVAL:{tag}] {key}")


# -- Apply passing fixes --

def _phase_apply(state: PipelineState, ts: str) -> int:
    """Write back all ``pass`` items with backups. Returns count."""
    passing = state.items_by_status("pass")
    if not passing:
        return 0
    q_groups: dict[str, list[dict]] = {}
    total = 0
    for _key, item in passing:
        if item["source"] == "question":
            q_groups.setdefault(item["file_path"], []).append(item)
        else:
            apply_single_item(item, ts)
            item["status"] = "applied"
            total += 1
    for fp, items in q_groups.items():
        total += apply_question_group(Path(fp), items, ts)
        for it in items:
            it["status"] = "applied"
    print(f"  Applied {total} fixes (backup ts={ts})")
    return total


# -- Retry with feedback --

def _collect_rejection_reasons(item: dict) -> list[str]:
    sr = (item.get("sanity_result") or {}).get("reasons", [])
    vr = (item.get("validation_result") or {}).get("reasons", [])
    return sr + vr


def _phase_retry(
    client: OpenAIClient, state: PipelineState,
    attempt: int, workers: int,
) -> None:
    """Re-fix failed items with rejection feedback."""
    retryable = state.items_by_status("fail", "sanity_fail")
    if not retryable:
        return
    print(f"  Retry round {attempt}: {len(retryable)} items...")
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs: dict = {}
        for key, item in retryable:
            reasons = _collect_rejection_reasons(item)
            futs[pool.submit(
                retry_one, client, item["original"], reasons,
            )] = key
        for fut in as_completed(futs):
            key = futs[fut]
            result = fut.result()
            item = state.get_item(key)
            item["retries"] = item.get("retries", 0) + 1
            item["retry_feedback"].append({
                "attempt": attempt,
                "reasons": _collect_rejection_reasons(item),
            })
            state.add_tokens(
                result.get("input_tokens", 0),
                result.get("output_tokens", 0),
            )
            if result["status"] == "FIXED" and result["corrected"]:
                item["corrected"] = result["corrected"]
                item["issues"] = result["issues"]
                item["status"] = "pending_validate"
                item["sanity_result"] = None
                item["validation_result"] = None
            elif result["status"] == "OK":
                item["status"] = "ok"
                item["corrected"] = None
                item["issues"] = []
            done += 1
            with _LOCK:
                print(
                    f"  [{done}/{len(futs)}] "
                    f"[RETRY->{result['status']}] {key}",
                )


# -- Verify applied items --

def _phase_verify(
    client: OpenAIClient, state: PipelineState, workers: int,
) -> None:
    """Re-scan applied items; revert + review if new issues found."""
    applied = state.items_by_status("applied")
    if not applied:
        return
    print(f"  Verifying {len(applied)} applied items...")
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {
            pool.submit(
                verify_one, client,
                item["corrected"], item["item_key"], item["source"],
            ): key
            for key, item in applied
        }
        for fut in as_completed(futs):
            key = futs[fut]
            result = fut.result()
            item = state.get_item(key)
            state.add_tokens(
                result.get("input_tokens", 0),
                result.get("output_tokens", 0),
            )
            if result["clean"]:
                item["status"] = "verified"
            else:
                logger.warning(
                    "Verify failed for %s: %s",
                    key, result["issues"],
                )
                if item["source"] == "question":
                    revert_question_item(item)
                else:
                    revert_single_item(item)
                item["status"] = "review"
                item["validation_result"] = {
                    "verdict": "VERIFY_FAIL",
                    "reasons": result["issues"],
                }
            done += 1
            with _LOCK:
                tag = "OK" if result["clean"] else "REVERT"
                print(f"  [{done}/{len(futs)}] [VERIFY:{tag}] {key}")


# -- Main pipeline orchestrator --

def run_pipeline(
    client: OpenAIClient,
    state: PipelineState,
    workers: int = 8,
    max_retries: int = 2,
) -> None:
    """Run Passes 2-4: fix -> sanity -> validate -> revalidate -> apply.

    Mutates ``state`` in place and saves to disk after each phase.
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    state.meta["apply_ts"] = ts

    print("\nPass 2: fixing flagged items...")
    _phase_fix(client, state, workers)
    state.save()

    print("\nPass 3: sanity check + LLM validation...")
    _phase_sanity_validate(client, state, workers)
    state.save()

    print("\nPass 4: independent revalidation...")
    _phase_revalidate(client, state, workers)
    state.save()

    print("\nApplying validated fixes...")
    _phase_apply(state, ts)
    state.save()

    for attempt in range(1, max_retries + 1):
        retryable = state.items_by_status("fail", "sanity_fail")
        if not retryable:
            break
        print(f"\nRetry round {attempt}/{max_retries}...")
        _phase_retry(client, state, attempt, workers)
        state.save()
        _phase_sanity_validate(client, state, workers)
        state.save()
        _phase_revalidate(client, state, workers)
        state.save()
        _phase_apply(state, ts)
        state.save()

    exhausted = state.items_by_status("fail", "sanity_fail")
    if exhausted:
        print(
            f"\n{len(exhausted)} items exhausted retries "
            "-> review queue",
        )
        for _, item in exhausted:
            item["status"] = "review"
        state.save()

    print("\nVerifying applied items...")
    _phase_verify(client, state, workers)
    state.save()
    state.print_summary()
