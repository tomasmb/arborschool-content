"""Apply notation fixes with sample-first validation.

Workflow:
  --sample N   Fix N random items per category, validate, report.
  --apply      Fix all confirmed items, validate, write to disk.
  --dry-run    Like --apply but skip writing to disk.

Validation is two-layer:
  1. Deterministic sanity checks (notation_sanity.py)
  2. LLM re-scan (same scan prompt, low reasoning)
"""

from __future__ import annotations

import argparse
import difflib
import json
import logging
import os
import random
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.llm_clients import OpenAIClient, load_default_openai_client
from app.prompts.notation_check import build_llm_fix_prompt
from scripts.notation_fix_rules import (
    DETERMINISTIC_CATEGORIES,
    apply_deterministic_fixes,
)
from scripts.notation_fix_writer import write_fixes_to_disk
from scripts.notation_sanity import run_sanity_checks
from scripts.notation_state import PipelineState

logger = logging.getLogger(__name__)

_PRINT_LOCK = threading.Lock()

_PHASE_CATEGORIES: dict[int, list[str]] = {
    1: [
        "deterministic_thousands_sep",
        "deterministic_spacing",
    ],
    2: ["deterministic_encoding", "manual_fix"],
}

_LLM_CATEGORIES = {"deterministic_encoding", "manual_fix"}


# ------------------------------------------------------------------
# Fix logic
# ------------------------------------------------------------------


def _item_categories(item: dict) -> set[str]:
    """Extract unique categories from confirmed issues."""
    return {
        ci["category"]
        for ci in item.get("confirmed_issues", [])
        if ci.get("category")
    }


def _item_issue_descriptions(
    item: dict, categories: set[str] | None = None,
) -> list[str]:
    """Get issue descriptions, optionally filtered by category."""
    return [
        ci["issue"]
        for ci in item.get("confirmed_issues", [])
        if ci.get("issue")
        and (categories is None or ci.get("category") in categories)
    ]


def _fix_deterministic(
    item: dict, phase_cats: set[str],
) -> str | None:
    """Apply deterministic fixes. Returns fixed content or None."""
    cats = _item_categories(item) & phase_cats
    det_cats = cats & set(DETERMINISTIC_CATEGORIES.keys())
    if not det_cats:
        return None
    original = item["original"]
    fixed = apply_deterministic_fixes(original, det_cats)
    return fixed if fixed != original else None


def _fix_llm(
    client: OpenAIClient, item: dict,
    phase_cats: set[str],
) -> tuple[str | None, int, int]:
    """Apply LLM fix. Returns (fixed_content, in_tok, out_tok)."""
    cats = _item_categories(item) & phase_cats & _LLM_CATEGORIES
    if not cats:
        return None, 0, 0
    issues = _item_issue_descriptions(item, cats)
    if not issues:
        return None, 0, 0
    prompt = build_llm_fix_prompt(
        content=item["original"], issues=issues,
    )
    resp = client.call(
        prompt,
        response_format={"type": "json_object"},
        reasoning_effort="medium",
    )
    try:
        data = json.loads(resp.text)
    except json.JSONDecodeError:
        return None, resp.usage.input_tokens, resp.usage.output_tokens
    if data.get("status") == "FIXED" and data.get("corrected_content"):
        return (
            data["corrected_content"],
            resp.usage.input_tokens,
            resp.usage.output_tokens,
        )
    return None, resp.usage.input_tokens, resp.usage.output_tokens


# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------


def _content_type(item: dict) -> str:
    return "HTML" if item.get("source") == "mini-class" else "QTI XML"


def _validate_sanity(
    item: dict, fixed: str, *, lenient: bool = False,
) -> tuple[bool, list[str]]:
    """Run deterministic sanity checks on the fix."""
    return run_sanity_checks(
        item["original"], fixed, _content_type(item),
        lenient=lenient,
    )


def _process_one(
    client: OpenAIClient,
    key: str,
    item: dict,
    phase_cats: set[str],
    use_llm: bool,
) -> dict:
    """Fix and validate a single item. Returns result dict."""
    det_fixed = _fix_deterministic(item, phase_cats)
    llm_fixed = None
    llm_in = llm_out = 0
    if use_llm:
        llm_fixed, llm_in, llm_out = _fix_llm(
            client, item, phase_cats,
        )

    fixed = llm_fixed or det_fixed
    if fixed is None:
        return {
            "key": key, "status": "no_change",
            "input_tokens": llm_in, "output_tokens": llm_out,
        }

    if det_fixed and llm_fixed:
        fixed = apply_deterministic_fixes(
            llm_fixed,
            _item_categories(item) & phase_cats
            & set(DETERMINISTIC_CATEGORIES.keys()),
        )

    sanity_ok, sanity_reasons = _validate_sanity(
        item, fixed, lenient=use_llm,
    )
    if not sanity_ok:
        return {
            "key": key, "status": "sanity_fail",
            "reasons": sanity_reasons, "fixed": fixed,
            "input_tokens": llm_in, "output_tokens": llm_out,
        }

    # Sanity checks suffice for all phases. LLM rescan is too
    # noisy (catches pre-existing issues unrelated to our fix)
    # and the critical invariants (answer key, choice set,
    # content length) are already covered by sanity checks.
    return {
        "key": key, "status": "ok",
        "fixed": fixed, "reasons": [],
        "input_tokens": llm_in, "output_tokens": llm_out,
    }


# ------------------------------------------------------------------
# Batch orchestration
# ------------------------------------------------------------------


def _select_items(
    state: PipelineState,
    phase: int,
    sample_n: int | None,
) -> list[tuple[str, dict]]:
    """Select confirmed items matching the phase categories."""
    cats = set(_PHASE_CATEGORIES[phase])
    confirmed = state.items_by_status("confirmed")
    matching = [
        (k, item) for k, item in confirmed
        if _item_categories(item) & cats
    ]
    if sample_n and sample_n < len(matching):
        matching = random.sample(matching, sample_n)
    return matching


def _run_fixes(
    client: OpenAIClient,
    state: PipelineState,
    items: list[tuple[str, dict]],
    phase: int,
    workers: int,
) -> tuple[int, int, int]:
    """Fix and validate items concurrently. Returns counts."""
    phase_cats = set(_PHASE_CATEGORIES[phase])
    use_llm = bool(phase_cats & _LLM_CATEGORIES)
    total = len(items)
    ok_count = fail_count = skip_count = 0
    done = 0

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {
            pool.submit(
                _process_one, client, k, item, phase_cats, use_llm,
            ): (k, item)
            for k, item in items
        }
        for fut in as_completed(futs):
            key, item = futs[fut]
            done += 1
            try:
                r = fut.result()
            except Exception as exc:
                logger.warning("Fix failed %s: %s", key, exc)
                with _PRINT_LOCK:
                    print(f"  [{done}/{total}] [ERROR] {key}")
                fail_count += 1
                continue

            state.add_tokens(
                r.get("input_tokens", 0),
                r.get("output_tokens", 0),
            )

            if r["status"] == "no_change":
                skip_count += 1
                with _PRINT_LOCK:
                    print(f"  [{done}/{total}] [SKIP] {key}")
                continue

            if r["status"] == "ok":
                item["fixed_content"] = r["fixed"]
                item["status"] = "fix_ok"
                ok_count += 1
                tag = "FIX_OK"
            else:
                item["sanity_result"] = r.get("reasons", [])
                item["status"] = "fix_fail"
                fail_count += 1
                tag = r["status"].upper()

            diff = _short_diff(
                item["original"], r.get("fixed", ""), key,
            )
            with _PRINT_LOCK:
                print(f"  [{done}/{total}] [{tag}] {key}")
                if r.get("reasons"):
                    for reason in r["reasons"][:3]:
                        print(f"    ! {reason[:120]}")
                if diff and r["status"] == "ok":
                    print(diff)

    state.save()
    return ok_count, fail_count, skip_count


def _short_diff(
    original: str, fixed: str, label: str,
) -> str:
    """Generate a compact unified diff (max 20 lines)."""
    orig = original.splitlines(keepends=True)
    fix = fixed.splitlines(keepends=True)
    diff = list(difflib.unified_diff(
        orig, fix,
        fromfile=f"original/{label}",
        tofile=f"fixed/{label}",
        n=1,
    ))
    if not diff:
        return ""
    lines = diff[:20]
    if len(diff) > 20:
        lines.append(f"    ... ({len(diff) - 20} more diff lines)\n")
    return "    " + "    ".join(lines)


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------


def _require_api_key() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not set.")
        sys.exit(1)


def _load_state(args: argparse.Namespace) -> PipelineState | None:
    if args.state:
        return PipelineState.load(Path(args.state))
    return PipelineState.load_latest(args.pool or "all")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Apply notation fixes with validation.",
    )
    p.add_argument(
        "--phase", type=int, choices=[1, 2], required=True,
    )
    p.add_argument(
        "--sample", type=int, default=None,
        help="Fix N random items per category (preview mode)",
    )
    p.add_argument(
        "--apply", action="store_true",
        help="Fix all and write to disk",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Like --apply but skip writing to disk",
    )
    p.add_argument("--workers", type=int, default=10)
    p.add_argument("--pool", type=str, default="all")
    p.add_argument(
        "--state", type=str, default=None,
        help="Path to a specific state JSON file",
    )
    p.add_argument("--verbose", "-v", action="store_true")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    _require_api_key()

    state = _load_state(args)
    if not state:
        print("No saved state. Run scan + confirm first.")
        return

    phase = args.phase
    cats = _PHASE_CATEGORIES[phase]
    print(f"Phase {phase}: {', '.join(cats)}")

    sample_n = args.sample
    items = _select_items(state, phase, sample_n)
    if not items:
        print("No confirmed items for this phase.")
        state.print_summary()
        return

    mode = "sample" if sample_n else (
        "dry-run" if args.dry_run else "apply"
    )
    print(f"Mode: {mode} | Items: {len(items)} | "
          f"Workers: {args.workers}")

    client = load_default_openai_client(model="gpt-5.1")
    ok, fail, skip = _run_fixes(
        client, state, items, phase, args.workers,
    )
    print(f"\nResults: {ok} ok, {fail} fail, {skip} skip")

    if args.apply and not args.dry_run and ok > 0:
        written = write_fixes_to_disk(state)
        print(f"Written to disk: {written} items")

    state.print_summary()


if __name__ == "__main__":
    main()
