"""Pipeline phases: sanity + XSD -> LLM validate -> apply -> retry -> verify."""
from __future__ import annotations

import json
import logging
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from app.llm_clients import OpenAIClient
from app.prompts.notation_check import (
    build_mini_class_prompt,
    build_retry_prompt,
    build_validation_prompt,
    build_xml_file_prompt,
)
from scripts.notation_sanity import run_sanity_checks, run_xsd_validation
from scripts.notation_state import PipelineState

logger = logging.getLogger(__name__)

_QG_ROOT = Path("app/data/question-generation")
_ML_ROOT = Path("app/data/mini-lessons")
_PRUEBAS_ROOT = Path("app/data/pruebas")
_BACKUP_QG = _QG_ROOT / ".notation_fix_backups"
_BACKUP_ML = _ML_ROOT / ".notation_fix_backups"
_BACKUP_PRUEBAS = _PRUEBAS_ROOT / ".notation_fix_backups"
_LOCK = threading.Lock()


def _content_type(source: str) -> str:
    return "HTML" if source == "mini-class" else "QTI XML"


def _parse_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"parse_error": True, "raw": raw[:200]}

# -- LLM calls (one item at a time) --

def validate_one(
    client: OpenAIClient,
    original: str,
    corrected: str,
    issues: list[str],
    content_type: str,
    *,
    validation_client: OpenAIClient | None = None,
) -> dict:
    """LLM validation: verify corrected version didn't break anything."""
    llm = validation_client or client
    prompt = build_validation_prompt(
        original, corrected, issues, content_type,
    )
    try:
        resp = llm.call(
            prompt,
            response_format={"type": "json_object"},
            reasoning_effort="medium",
        )
        data = _parse_json(resp.text)
        return {
            "verdict": data.get("verdict", "UNKNOWN"),
            "reasons": data.get("reasons", []),
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
        }
    except Exception as exc:
        logger.warning("Validation error: %s", exc)
        return {
            "verdict": "ERROR", "reasons": [str(exc)],
            "input_tokens": 0, "output_tokens": 0,
        }


def retry_one(
    client: OpenAIClient,
    original: str,
    rejection_reasons: list[str],
) -> dict:
    """Re-scan a single item with feedback from failed validation."""
    prompt = build_retry_prompt(original, rejection_reasons)
    try:
        resp = client.call(
            prompt,
            response_format={"type": "json_object"},
            reasoning_effort="medium",
        )
        data = _parse_json(resp.text)
        return {
            "status": data.get("status", "ERROR"),
            "issues": data.get("issues", []),
            "corrected": data.get("corrected_content"),
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
        }
    except Exception as exc:
        logger.warning("Retry error: %s", exc)
        return {
            "status": "ERROR", "issues": [str(exc)],
            "corrected": None,
            "input_tokens": 0, "output_tokens": 0,
        }


def verify_one(
    client: OpenAIClient,
    content: str,
    label: str,
    source: str,
) -> dict:
    """Re-scan applied content to confirm it's clean."""
    if source == "mini-class":
        prompt = build_mini_class_prompt(label, content)
    else:
        prompt = build_xml_file_prompt(label, content)
    try:
        resp = client.call(
            prompt,
            response_format={"type": "json_object"},
            reasoning_effort="low",
        )
        data = _parse_json(resp.text)
        return {
            "clean": data.get("status") == "OK",
            "issues": data.get("issues", []),
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
        }
    except Exception as exc:
        logger.warning("Verify error for %s: %s", label, exc)
        return {
            "clean": False, "issues": [str(exc)],
            "input_tokens": 0, "output_tokens": 0,
        }


# -- Write-back with backups --

def _backup_and_write(
    file_path: Path, new_content: str,
    backup_root: Path, base_root: Path, ts: str,
) -> None:
    """Create a timestamped backup then overwrite the file."""
    rel = file_path.relative_to(base_root)
    bak = backup_root / ts / rel
    bak.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(file_path, bak)
    file_path.write_text(new_content, encoding="utf-8")


def _apply_single_item(item: dict, ts: str) -> None:
    """Write corrected content for a mini-class or XML file."""
    fp = Path(item["file_path"])
    src = item["source"]
    if src == "mini-class":
        _backup_and_write(fp, item["corrected"], _BACKUP_ML, _ML_ROOT, ts)
    else:
        _backup_and_write(
            fp, item["corrected"], _BACKUP_PRUEBAS, _PRUEBAS_ROOT, ts,
        )


def _apply_question_group(
    p9_path: Path,
    items: list[dict],
    ts: str,
) -> int:
    """Replace corrected question XMLs in a phase_9 JSON file."""
    bak = _BACKUP_QG / ts / p9_path.relative_to(_QG_ROOT)
    bak.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p9_path, bak)

    data = json.loads(p9_path.read_text(encoding="utf-8"))
    by_qid = {it["question_id"]: it["corrected"] for it in items}
    changed = 0
    for entry in data.get("items", []):
        iid = entry.get("item_id", "")
        if iid in by_qid and by_qid[iid]:
            entry["qti_xml"] = by_qid[iid]
            changed += 1
    p9_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return changed


def _revert_single_item(item: dict) -> None:
    """Revert a file to its original content (from state)."""
    fp = Path(item["file_path"])
    fp.write_text(item["original"], encoding="utf-8")


def _revert_question_item(item: dict) -> None:
    """Revert one question inside its phase_9 JSON to original."""
    fp = Path(item["file_path"])
    data = json.loads(fp.read_text(encoding="utf-8"))
    qid = item["question_id"]
    for entry in data.get("items", []):
        if entry.get("item_id") == qid:
            entry["qti_xml"] = item["original"]
            break
    fp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


# -- Phase 2+3: sanity check + XSD + LLM validation --

def _run_xsd_checks(state: PipelineState) -> None:
    """Run XSD validation on QTI XML items still pending validate."""
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
            sr = item.get("sanity_result") or {"pass": True, "reasons": []}
            sr["pass"] = False
            sr["reasons"].extend(reasons)
            item["sanity_result"] = sr
            item["status"] = "sanity_fail"
            with _LOCK:
                print(f"  [XSD_FAIL] {key}: {reasons}")


def _phase_sanity_validate(
    client: OpenAIClient,
    state: PipelineState,
    workers: int,
    *,
    validation_client: OpenAIClient | None = None,
) -> None:
    """Run deterministic sanity checks, then LLM validation."""
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

    # XSD validation for QTI XML items that passed sanity
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
                validation_client=validation_client,
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
            item["status"] = "pass" if vr["verdict"] == "PASS" else "fail"
            done += 1
            with _LOCK:
                print(
                    f"  [{done}/{len(futs)}] "
                    f"[{vr['verdict']}] {key}",
                )


# -- Phase 4: apply passing fixes --

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
            _apply_single_item(item, ts)
            item["status"] = "applied"
            total += 1

    for fp, items in q_groups.items():
        total += _apply_question_group(Path(fp), items, ts)
        for it in items:
            it["status"] = "applied"

    print(f"  Applied {total} fixes (backup ts={ts})")
    return total


# -- Phase 5: retry with feedback --

def _collect_rejection_reasons(item: dict) -> list[str]:
    """Gather all rejection reasons from sanity and LLM validation."""
    sr = (item.get("sanity_result") or {}).get("reasons", [])
    vr = (item.get("validation_result") or {}).get("reasons", [])
    return sr + vr


def _phase_retry(
    client: OpenAIClient,
    state: PipelineState,
    attempt: int,
    workers: int,
) -> None:
    """Re-scan failed items with rejection feedback."""
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


# -- Phase 4b: verify applied items --

def _phase_verify(
    client: OpenAIClient,
    state: PipelineState,
    workers: int,
) -> None:
    """Re-scan applied items; revert + review if new issues found."""
    applied = state.items_by_status("applied")
    if not applied:
        return
    print(f"  Verifying {len(applied)} applied items...")
    done = 0

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs: dict = {}
        for key, item in applied:
            futs[pool.submit(
                verify_one, client,
                item["corrected"], item["item_key"],
                item["source"],
            )] = key
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
                    "Verify failed for %s: %s", key, result["issues"],
                )
                if item["source"] == "question":
                    _revert_question_item(item)
                else:
                    _revert_single_item(item)
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
    validation_client: OpenAIClient | None = None,
) -> None:
    """Run the full pipeline: sanity -> validate -> apply -> retry -> verify.

    Mutates ``state`` in place and saves to disk after each phase.
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    state.meta["apply_ts"] = ts

    print("\nPhase 2+3: sanity check + LLM validation...")
    _phase_sanity_validate(
        client, state, workers,
        validation_client=validation_client,
    )
    state.save()

    print("\nPhase 4: applying validated fixes...")
    _phase_apply(state, ts)
    state.save()

    for attempt in range(1, max_retries + 1):
        retryable = state.items_by_status("fail", "sanity_fail")
        if not retryable:
            break
        print(f"\nPhase 5: retry round {attempt}/{max_retries}...")
        _phase_retry(client, state, attempt, workers)
        state.save()
        _phase_sanity_validate(
            client, state, workers,
            validation_client=validation_client,
        )
        state.save()
        _phase_apply(state, ts)
        state.save()

    exhausted = state.items_by_status("fail", "sanity_fail")
    if exhausted:
        print(f"\n{len(exhausted)} items exhausted retries -> review queue")
        for _, item in exhausted:
            item["status"] = "review"
        state.save()

    print("\nPhase 4b: verifying applied items...")
    _phase_verify(client, state, workers)
    state.save()

    state.print_summary()
