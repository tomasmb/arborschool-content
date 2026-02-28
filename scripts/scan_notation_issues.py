"""Scan, fix, and validate notation / text quality issues.

Pass 1 (default): scan-only, detect issues with low reasoning.
Pass 2-4 (--fix): fix -> validate -> revalidate -> apply.
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
    build_scan_batch_prompt,
    build_scan_mini_class_prompt,
    build_scan_xml_file_prompt,
)
from scripts.notation_fix_apply import run_pipeline
from scripts.notation_state import (
    PipelineState,
    export_review_queue,
    populate_from_scan,
)

logger = logging.getLogger(__name__)

_QG_ROOT = Path("app/data/question-generation")
_ML_ROOT = Path("app/data/mini-lessons")
_PRUEBAS_ROOT = Path("app/data/pruebas")
_PRINT_LOCK = threading.Lock()

_MAX_BATCH_CHARS = 600_000
_POOL_CHOICES = ("questions", "mini-classes", "exemplars", "variants")


# ------------------------------------------------------------------
# Data iterators
# ------------------------------------------------------------------


def _iter_atoms(
    atom_filter: set[str] | None = None,
) -> list[tuple[str, Path, list[dict]]]:
    """Return (atom_id, json_path, items) for phase_9 files."""
    atoms: list[tuple[str, Path, list[dict]]] = []
    for p9 in sorted(
        _QG_ROOT.glob("*/checkpoints/phase_9_final_validation.json"),
    ):
        atom_id = p9.parent.parent.name
        if atom_filter and atom_id not in atom_filter:
            continue
        data = json.loads(p9.read_text(encoding="utf-8"))
        items = data.get("items", [])
        if items:
            atoms.append((atom_id, p9, items))
    return atoms


def _iter_mini_classes(
    atom_filter: set[str] | None = None,
) -> list[tuple[str, Path, str]]:
    """Return (atom_id, html_path, html) for published mini-classes."""
    lessons: list[tuple[str, Path, str]] = []
    if not _ML_ROOT.exists():
        return lessons
    for atom_dir in sorted(_ML_ROOT.iterdir()):
        if not atom_dir.is_dir() or atom_dir.name.startswith("."):
            continue
        if atom_filter and atom_dir.name not in atom_filter:
            continue
        html_path = atom_dir / "mini-class.html"
        if html_path.exists():
            html = html_path.read_text(encoding="utf-8")
            lessons.append((atom_dir.name, html_path, html))
    return lessons


def _iter_exemplars() -> list[tuple[str, Path, str]]:
    """Return (label, xml_path, xml) for exemplar questions."""
    root = _PRUEBAS_ROOT / "finalizadas"
    if not root.exists():
        return []
    items: list[tuple[str, Path, str]] = []
    for xml_path in sorted(root.glob("*/qti/*/question.xml")):
        prueba = xml_path.parent.parent.parent.name
        q_id = xml_path.parent.name
        label = f"{prueba}/{q_id}"
        items.append((label, xml_path, xml_path.read_text("utf-8")))
    return items


def _iter_variants() -> list[tuple[str, Path, str]]:
    """Return (label, xml_path, xml) for variant questions."""
    root = _PRUEBAS_ROOT / "alternativas"
    if not root.exists():
        return []
    items: list[tuple[str, Path, str]] = []
    for xml_path in sorted(
        root.glob("*/Q*/approved/*/question.xml"),
    ):
        parts = xml_path.relative_to(root).parts
        prueba, q_id = parts[0], parts[1]
        variant = parts[3]
        label = f"{prueba}/{q_id}/{variant}"
        items.append((label, xml_path, xml_path.read_text("utf-8")))
    return items


# ------------------------------------------------------------------
# Pass 1: Scan-only (detect issues, no corrections)
# ------------------------------------------------------------------


def _parse_response(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Bad JSON: %s", raw[:200])
        return {"parse_error": True}


def _split_batches(qti_xmls: list[str]) -> list[list[str]]:
    """Split XMLs into sub-batches under _MAX_BATCH_CHARS each."""
    batches: list[list[str]] = []
    current: list[str] = []
    current_chars = 0
    for xml in qti_xmls:
        if current and current_chars + len(xml) > _MAX_BATCH_CHARS:
            batches.append(current)
            current, current_chars = [], 0
        current.append(xml)
        current_chars += len(xml)
    if current:
        batches.append(current)
    return batches


def _scan_atom(
    client: OpenAIClient, atom_id: str, items: list[dict],
) -> dict:
    """Scan all questions in an atom (detect only, no fix)."""
    xmls = [
        it.get("qti_xml", "") for it in items if it.get("qti_xml")
    ]
    if not xmls:
        return _result("question", atom_id, 0)

    batches = _split_batches(xmls)
    all_flagged: list[dict] = []
    total_in = total_out = 0

    try:
        for batch in batches:
            prompt = build_scan_batch_prompt(atom_id, batch)
            resp = client.call(
                prompt,
                response_format={"type": "json_object"},
                reasoning_effort="low",
            )
            data = _parse_response(resp.text)
            all_flagged.extend(data.get("items", []))
            total_in += resp.usage.input_tokens
            total_out += resp.usage.output_tokens
        return _result(
            "question", atom_id, len(xmls),
            flagged_items=all_flagged,
            tin=total_in, tout=total_out,
        )
    except Exception as exc:
        logger.warning("Scan failed for %s: %s", atom_id, exc)
        return _result(
            "question", atom_id, len(xmls),
            flagged_items=all_flagged, error=str(exc),
            tin=total_in, tout=total_out,
        )


def _scan_single(
    client: OpenAIClient, label: str, content: str,
    source: str, prompt_fn: callable,
) -> dict:
    """Scan a single content item (detect only, no fix)."""
    prompt = prompt_fn(label, content)
    try:
        resp = client.call(
            prompt,
            response_format={"type": "json_object"},
            reasoning_effort="low",
        )
        data = _parse_response(resp.text)
        status = data.get("status", "OK")
        issues = data.get("issues", [])
        return _result(
            source, label, 1,
            issues=issues if status == "HAS_ISSUES" else None,
            tin=resp.usage.input_tokens,
            tout=resp.usage.output_tokens,
        )
    except Exception as exc:
        logger.warning("Scan failed for %s %s: %s", source, label, exc)
        return _result(source, label, 1, error=str(exc))


def _result(
    source: str, item_id: str, n: int, *,
    flagged_items: list[dict] | None = None,
    issues: list[str] | None = None,
    error: str | None = None,
    tin: int = 0, tout: int = 0,
) -> dict:
    has_issues: bool | None = None
    if error is None:
        if flagged_items is not None:
            has_issues = len(flagged_items) > 0
        else:
            has_issues = issues is not None and len(issues) > 0
    return {
        "source": source, "item_id": item_id,
        "items_checked": n,
        "has_issues": has_issues,
        "flagged_items": flagged_items or [],
        "issues": issues or [],
        "error": error,
        "input_tokens": tin, "output_tokens": tout,
    }


# ------------------------------------------------------------------
# Scan orchestration
# ------------------------------------------------------------------


def _run_scan(
    client: OpenAIClient,
    atoms: list[tuple[str, Path, list[dict]]],
    mcs: list[tuple[str, Path, str]],
    exemplars: list[tuple[str, Path, str]],
    variants: list[tuple[str, Path, str]],
    workers: int,
) -> list[dict]:
    """Pass 1: scan all content concurrently (detect only)."""
    results: list[dict] = []
    total = len(atoms) + len(mcs) + len(exemplars) + len(variants)
    done = 0

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs: dict = {}
        for aid, _, items in atoms:
            futs[pool.submit(
                _scan_atom, client, aid, items,
            )] = ("Q", aid)
        for aid, _, html in mcs:
            futs[pool.submit(
                _scan_single, client, aid, html,
                "mini-class", build_scan_mini_class_prompt,
            )] = ("MC", aid)
        for label, _, xml in exemplars:
            futs[pool.submit(
                _scan_single, client, label, xml,
                "exemplar", build_scan_xml_file_prompt,
            )] = ("EX", label)
        for label, _, xml in variants:
            futs[pool.submit(
                _scan_single, client, label, xml,
                "variant", build_scan_xml_file_prompt,
            )] = ("VA", label)

        for fut in as_completed(futs):
            r = fut.result()
            results.append(r)
            done += 1
            tag, aid = futs[fut]
            if r["error"]:
                s = "ERROR"
            elif r["has_issues"]:
                n_issues = (
                    len(r["flagged_items"])
                    if r["flagged_items"]
                    else len(r["issues"])
                )
                s = f"FLAG({n_issues})"
            else:
                s = "OK"
            with _PRINT_LOCK:
                print(f"[{done}/{total}] [{tag}] [{s}] {aid}")
    return results


# ------------------------------------------------------------------
# CLI commands
# ------------------------------------------------------------------


def _require_api_key() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not set.")
        sys.exit(1)


def _pool_name(args: argparse.Namespace) -> str:
    return args.only or "all"


def _load_data(
    args: argparse.Namespace,
) -> tuple[list, list, list, list]:
    """Load data iterators based on --only and --atoms flags."""
    af: set[str] | None = None
    if args.atoms:
        af = {a.strip() for a in args.atoms.split(",")}
    only = args.only
    atoms = _iter_atoms(af) if only in (None, "questions") else []
    mcs = _iter_mini_classes(af) if only in (None, "mini-classes") else []
    exs = _iter_exemplars() if only in (None, "exemplars") else []
    vas = _iter_variants() if only in (None, "variants") else []
    return atoms, mcs, exs, vas


def _cmd_scan(args: argparse.Namespace) -> None:
    """Pass 1: scan-only (detect issues, no corrections)."""
    _require_api_key()
    atoms, mcs, exs, vas = _load_data(args)

    tq = sum(len(it) for _, _, it in atoms)
    print(
        f"Loaded {len(atoms)} atoms ({tq} Qs), {len(mcs)} MCs, "
        f"{len(exs)} exemplars, {len(vas)} variants",
    )
    pool_size = len(atoms) + len(mcs) + len(exs) + len(vas)
    if pool_size == 0:
        print("Nothing to scan.")
        return

    w = min(args.workers, pool_size)
    client = load_default_openai_client(model="gpt-5.1")

    print(f"Pass 1: scanning with {w} workers (low reasoning)...")
    scan_results = _run_scan(client, atoms, mcs, exs, vas, w)

    state = PipelineState(pool=_pool_name(args))
    populate_from_scan(state, scan_results, atoms, mcs, exs, vas)
    state.save()
    state.print_summary()


def _cmd_fix(args: argparse.Namespace) -> None:
    """Passes 2-4: fix flagged items from the latest scan state."""
    _require_api_key()
    state = PipelineState.load_latest(_pool_name(args))
    if not state:
        print(f"No saved state for pool '{_pool_name(args)}'.")
        print("Run a scan first (without --fix).")
        return
    flagged = state.items_by_status("flagged")
    if not flagged:
        print("No flagged items to fix.")
        state.print_summary()
        return
    print(f"Fixing {len(flagged)} flagged items...")
    client = load_default_openai_client(model="gpt-5.1")
    run_pipeline(
        client, state,
        workers=args.workers,
        max_retries=2,
    )


def _cmd_status(args: argparse.Namespace) -> None:
    """Show pipeline state for a pool."""
    state = PipelineState.load_latest(_pool_name(args))
    if not state:
        print(f"No saved state for pool '{_pool_name(args)}'.")
        return
    state.print_summary()


def _cmd_retry(args: argparse.Namespace) -> None:
    """Retry failed items from the latest state."""
    _require_api_key()
    state = PipelineState.load_latest(_pool_name(args))
    if not state:
        print(f"No saved state for pool '{_pool_name(args)}'.")
        return
    retryable = state.items_by_status("fail", "sanity_fail", "review")
    if not retryable:
        print("No failed items to retry.")
        state.print_summary()
        return
    print(f"Retrying {len(retryable)} failed items...")
    for _, item in retryable:
        if item["status"] == "review":
            item["status"] = "fail"
    client = load_default_openai_client(model="gpt-5.1")
    run_pipeline(client, state, workers=args.workers, max_retries=2)


def _cmd_verify(args: argparse.Namespace) -> None:
    """Re-verify applied items from the latest state."""
    _require_api_key()
    from scripts.notation_fix_apply import _phase_verify
    state = PipelineState.load_latest(_pool_name(args))
    if not state:
        print(f"No saved state for pool '{_pool_name(args)}'.")
        return
    applied = state.items_by_status("applied")
    if not applied:
        print("No applied items to verify.")
        state.print_summary()
        return
    print(f"Verifying {len(applied)} applied items...")
    client = load_default_openai_client(model="gpt-5.1")
    _phase_verify(client, state, args.workers)
    state.save()
    state.print_summary()


def _cmd_review(args: argparse.Namespace) -> None:
    """Export review queue for manual fixing."""
    state = PipelineState.load_latest(_pool_name(args))
    if not state:
        print(f"No saved state for pool '{_pool_name(args)}'.")
        return
    export_review_queue(state)


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Notation & text quality scanner with pipeline.",
    )
    p.add_argument(
        "--only", choices=list(_POOL_CHOICES), default=None,
    )
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--atoms", type=str, default=None)
    p.add_argument(
        "--fix", action="store_true",
        help="Run Passes 2-4: fix + validate + revalidate + apply",
    )
    p.add_argument(
        "--status", action="store_true",
        help="Show pipeline state for the specified pool",
    )
    p.add_argument(
        "--retry", action="store_true",
        help="Retry failed items from the latest saved state",
    )
    p.add_argument(
        "--verify", action="store_true",
        help="Re-verify applied items from the latest saved state",
    )
    p.add_argument(
        "--review", action="store_true",
        help="Export review queue for items needing manual fixing",
    )
    p.add_argument("--verbose", "-v", action="store_true")
    return p.parse_args()


def main() -> None:
    """CLI entry point — dispatches to the appropriate command."""
    args = _parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    if args.status:
        _cmd_status(args)
    elif args.review:
        _cmd_review(args)
    elif args.retry:
        _cmd_retry(args)
    elif args.verify:
        _cmd_verify(args)
    elif args.fix:
        _cmd_fix(args)
    else:
        _cmd_scan(args)


if __name__ == "__main__":
    main()
