"""Scan and confirm notation / text quality issues.

Every item (question, mini-class, exemplar, variant) is scanned
individually — one LLM call per item, no batching.

Pass 1 (default): scan-only, low reasoning.
Pass 2 (--confirm): validate flagged issues, medium reasoning.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.llm_clients import OpenAIClient, load_default_openai_client
from app.prompts.notation_check import (
    ISSUE_CATEGORIES,
    build_confirm_prompt,
    build_scan_mini_class_prompt,
    build_scan_xml_file_prompt,
)
from scripts.notation_state import (
    PipelineState,
    ScanItem,
    populate_from_scan,
)

logger = logging.getLogger(__name__)

_QG_ROOT = Path("app/data/question-generation")
_ML_ROOT = Path("app/data/mini-lessons")
_PRUEBAS_ROOT = Path("app/data/pruebas")
_PRINT_LOCK = threading.Lock()

_POOL_CHOICES = (
    "questions", "mini-classes", "exemplars", "variants",
)


# ------------------------------------------------------------------
# Data iterators — each returns list[ScanItem]
# ScanItem = (key, source, file_path, content, label)
# ------------------------------------------------------------------


def _iter_questions(
    atom_filter: set[str] | None = None,
) -> list[ScanItem]:
    """Yield one ScanItem per individual question."""
    items: list[ScanItem] = []
    for p9 in sorted(_QG_ROOT.glob(
        "*/checkpoints/phase_9_final_validation.json",
    )):
        aid = p9.parent.parent.name
        if atom_filter and aid not in atom_filter:
            continue
        data = json.loads(p9.read_text("utf-8"))
        for it in data.get("items", []):
            xml = it.get("qti_xml", "")
            qid = it.get("item_id", "")
            if xml and qid:
                items.append((
                    f"q:{aid}:{qid}", "question",
                    str(p9), xml, f"{aid}/{qid}",
                ))
    return items


def _iter_mini_classes(
    atom_filter: set[str] | None = None,
) -> list[ScanItem]:
    """Yield one ScanItem per mini-class HTML."""
    if not _ML_ROOT.exists():
        return []
    out: list[ScanItem] = []
    for d in sorted(_ML_ROOT.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        if atom_filter and d.name not in atom_filter:
            continue
        hp = d / "mini-class.html"
        if hp.exists():
            out.append((
                f"mini-class:{d.name}", "mini-class",
                str(hp), hp.read_text("utf-8"), d.name,
            ))
    return out


def _iter_exemplars() -> list[ScanItem]:
    """Yield one ScanItem per exemplar question XML."""
    root = _PRUEBAS_ROOT / "finalizadas"
    if not root.exists():
        return []
    out: list[ScanItem] = []
    for xp in sorted(root.glob("*/qti/*/question.xml")):
        prueba = xp.parent.parent.parent.name
        qid = xp.parent.name
        label = f"{prueba}/{qid}"
        out.append((
            f"exemplar:{label}", "exemplar",
            str(xp), xp.read_text("utf-8"), label,
        ))
    return out


def _iter_variants() -> list[ScanItem]:
    """Yield one ScanItem per variant question XML."""
    root = _PRUEBAS_ROOT / "alternativas"
    if not root.exists():
        return []
    out: list[ScanItem] = []
    for xp in sorted(root.glob("*/Q*/approved/*/question.xml")):
        parts = xp.relative_to(root).parts
        label = f"{parts[0]}/{parts[1]}/{parts[3]}"
        out.append((
            f"variant:{label}", "variant",
            str(xp), xp.read_text("utf-8"), label,
        ))
    return out


# ------------------------------------------------------------------
# Pass 1: Scan-only (one LLM call per item)
# ------------------------------------------------------------------


def _parse_response(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Bad JSON: %s", raw[:200])
        return {"parse_error": True}


def _scan_one(
    client: OpenAIClient, item: ScanItem,
) -> dict:
    """Scan a single item (question, mini-class, etc.)."""
    key, source, _fp, content, label = item
    if source == "mini-class":
        prompt = build_scan_mini_class_prompt(label, content)
    else:
        prompt = build_scan_xml_file_prompt(label, content)
    try:
        resp = client.call(
            prompt,
            response_format={"type": "json_object"},
            reasoning_effort="low",
        )
        data = _parse_response(resp.text)
        has = data.get("status") == "HAS_ISSUES"
        issues = data.get("issues", []) if has else []
        return {
            "key": key, "has_issues": has,
            "issues": issues, "error": None,
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
        }
    except Exception as exc:
        logger.warning("Scan failed %s: %s", key, exc)
        return {
            "key": key, "has_issues": None,
            "issues": [], "error": str(exc),
            "input_tokens": 0, "output_tokens": 0,
        }


def _run_scan(
    client: OpenAIClient,
    items: list[ScanItem],
    workers: int,
) -> list[dict]:
    """Pass 1: scan every item individually and concurrently."""
    results: list[dict] = []
    total = len(items)
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {
            pool.submit(_scan_one, client, it): it
            for it in items
        }
        for fut in as_completed(futs):
            r = fut.result()
            results.append(r)
            done += 1
            it = futs[fut]
            source = it[1]
            tag = {
                "question": "Q", "mini-class": "MC",
                "exemplar": "EX", "variant": "VA",
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


# ------------------------------------------------------------------
# Pass 2: Confirm flagged issues (medium reasoning)
# ------------------------------------------------------------------


def _confirm_one(
    client: OpenAIClient, key: str, item: dict,
) -> dict:
    """Confirm or reject flagged issues for a single item."""
    prompt = build_confirm_prompt(
        content=item["original"],
        issues=item.get("issues", []),
    )
    resp = client.call(
        prompt,
        response_format={"type": "json_object"},
        reasoning_effort="medium",
    )
    data = _parse_response(resp.text)
    return {
        "key": key,
        "confirmed": data.get("confirmed", []),
        "rejected": data.get("rejected", []),
        "input_tokens": resp.usage.input_tokens,
        "output_tokens": resp.usage.output_tokens,
    }


def _validate_categories(confirmed: list[dict]) -> list[dict]:
    """Normalise category values, falling back to manual_fix."""
    for ci in confirmed:
        if ci.get("category") not in ISSUE_CATEGORIES:
            ci["category"] = "manual_fix"
    return confirmed


def _run_confirm(
    client: OpenAIClient,
    state: PipelineState,
    workers: int,
) -> None:
    """Pass 2: validate each flagged item concurrently."""
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
                logger.warning(
                    "Confirm failed for %s: %s", key, exc,
                )
                with _PRINT_LOCK:
                    print(f"  [{done}/{total}] [ERROR] {key}")
                continue

            item = state.get_item(key)
            state.add_tokens(
                r["input_tokens"], r["output_tokens"],
            )
            confirmed = _validate_categories(r["confirmed"])
            rejected = r["rejected"]
            item["confirmed_issues"] = confirmed
            item["rejected_issues"] = rejected

            if confirmed:
                item["status"] = "confirmed"
                tag = "CONFIRMED"
            else:
                item["status"] = "false_positive"
                tag = "FP"

            with _PRINT_LOCK:
                print(
                    f"  [{done}/{total}] [{tag}] {key}"
                    f" ({len(confirmed)} conf, "
                    f"{len(rejected)} rej)",
                )

    state.save()


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------


def _require_api_key() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not set.")
        sys.exit(1)


def _pool_name(args: argparse.Namespace) -> str:
    return args.only or "all"


def _load_items(
    args: argparse.Namespace,
) -> list[ScanItem]:
    """Build flat list of items to scan based on CLI flags."""
    af = (
        {a.strip() for a in args.atoms.split(",")}
        if args.atoms else None
    )
    o = args.only
    items: list[ScanItem] = []
    if o in (None, "questions"):
        items.extend(_iter_questions(af))
    if o in (None, "mini-classes"):
        items.extend(_iter_mini_classes(af))
    if o in (None, "exemplars"):
        items.extend(_iter_exemplars())
    if o in (None, "variants"):
        items.extend(_iter_variants())
    return items


def _cmd_scan(args: argparse.Namespace) -> None:
    """Pass 1: scan every item individually (low reasoning)."""
    _require_api_key()
    items = _load_items(args)
    src_counts: dict[str, int] = {}
    for _, source, *_ in items:
        src_counts[source] = src_counts.get(source, 0) + 1
    parts = [f"{n} {s}" for s, n in sorted(src_counts.items())]
    print(f"Loaded {len(items)} items: {', '.join(parts)}")
    if not items:
        print("Nothing to scan.")
        return
    w = min(args.workers, len(items))
    client = load_default_openai_client(model="gpt-5.1")
    print(f"Scanning {len(items)} items with {w} workers "
          f"(low reasoning, 1 item per call)...")
    results = _run_scan(client, items, w)
    state = PipelineState(pool=_pool_name(args))
    populate_from_scan(state, items, results)
    state.save()
    state.print_summary()


def _load_state(
    args: argparse.Namespace,
) -> PipelineState | None:
    """Load state from --state path or latest for the pool."""
    if args.state:
        return PipelineState.load(Path(args.state))
    return PipelineState.load_latest(_pool_name(args))


def _cmd_confirm(args: argparse.Namespace) -> None:
    """Pass 2: confirm flagged issues (medium reasoning)."""
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
    client = load_default_openai_client(model="gpt-5.1")
    _run_confirm(client, state, args.workers)
    state.print_summary()


def _cmd_status(args: argparse.Namespace) -> None:
    """Show pipeline state for a pool."""
    state = _load_state(args)
    if not state:
        print(f"No saved state for pool '{_pool_name(args)}'.")
        return
    state.print_summary()


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Notation & text quality scanner — "
            "individual items, no batching."
        ),
    )
    p.add_argument(
        "--only", choices=list(_POOL_CHOICES), default=None,
    )
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--atoms", type=str, default=None)
    p.add_argument(
        "--confirm", action="store_true",
        help=(
            "Pass 2: confirm flagged issues with medium "
            "reasoning, categorise, eliminate false positives"
        ),
    )
    p.add_argument(
        "--state", type=str, default=None,
        help="Path to a specific state JSON file to use",
    )
    p.add_argument(
        "--status", action="store_true",
        help="Show pipeline state for the specified pool",
    )
    p.add_argument("--verbose", "-v", action="store_true")
    return p.parse_args()


def main() -> None:
    """CLI entry point."""
    args = _parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    if args.status:
        _cmd_status(args)
    elif args.confirm:
        _cmd_confirm(args)
    else:
        _cmd_scan(args)


if __name__ == "__main__":
    main()
