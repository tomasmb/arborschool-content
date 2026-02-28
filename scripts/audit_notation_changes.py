"""Independent audit of notation changes before committing.

Uses git diff to find exactly which questions/lessons changed,
then runs an independent LLM check on each changed item to verify
nothing was broken. The audit prompt is deliberately different from
the fix/validate prompts — it has no knowledge of notation rules
and just checks whether the two versions are equivalent in meaning.

Usage:
    python scripts/audit_notation_changes.py
    python scripts/audit_notation_changes.py --workers 4
    python scripts/audit_notation_changes.py --model gpt-4o
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.llm_clients import load_default_openai_client
from app.prompts.notation_check import build_revalidation_prompt

logger = logging.getLogger(__name__)

_QG_ROOT = Path("app/data/question-generation")
_ML_ROOT = Path("app/data/mini-lessons")
_PRUEBAS_ROOT = Path("app/data/pruebas")
_PRINT_LOCK = threading.Lock()

# -- Git helpers ---------------------------------------------------


def _git_show(ref_path: str) -> str | None:
    """Return file contents at a given git ref, or None."""
    try:
        result = subprocess.run(
            ["git", "show", ref_path],
            capture_output=True, text=True, check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return None


def _git_changed_files() -> list[str]:
    """Return list of files with uncommitted changes (staged + unstaged)."""
    result = subprocess.run(
        ["git", "diff", "HEAD", "--name-only"],
        capture_output=True, text=True, check=True,
    )
    return [
        f.strip() for f in result.stdout.splitlines()
        if f.strip()
    ]


# ------------------------------------------------------------------
# Extract changed items
# ------------------------------------------------------------------


def _extract_question_changes(
    changed_files: list[str],
) -> list[dict]:
    """Find individual questions that changed in phase_9 JSONs."""
    items: list[dict] = []
    p9_files = [
        f for f in changed_files
        if f.endswith("phase_9_final_validation.json")
        and f.startswith("app/data/question-generation/")
    ]
    for rel_path in p9_files:
        old_raw = _git_show(f"HEAD:{rel_path}")
        if old_raw is None:
            continue
        new_path = Path(rel_path)
        if not new_path.exists():
            continue
        try:
            old_data = json.loads(old_raw)
            new_data = json.loads(
                new_path.read_text(encoding="utf-8"),
            )
        except (json.JSONDecodeError, OSError):
            continue

        old_map = {
            it["item_id"]: it.get("qti_xml", "")
            for it in old_data.get("items", [])
        }
        for new_item in new_data.get("items", []):
            iid = new_item.get("item_id", "")
            new_xml = new_item.get("qti_xml", "")
            old_xml = old_map.get(iid, "")
            if old_xml and new_xml and old_xml != new_xml:
                items.append({
                    "item_id": iid,
                    "source": "question",
                    "file": rel_path,
                    "before": old_xml,
                    "after": new_xml,
                })
    return items


def _extract_mini_class_changes(
    changed_files: list[str],
) -> list[dict]:
    """Find mini-class HTML files that changed."""
    items: list[dict] = []
    html_files = [
        f for f in changed_files
        if f.endswith("mini-class.html")
        and f.startswith("app/data/mini-lessons/")
    ]
    for rel_path in html_files:
        old_html = _git_show(f"HEAD:{rel_path}")
        new_path = Path(rel_path)
        if old_html is None or not new_path.exists():
            continue
        new_html = new_path.read_text(encoding="utf-8")
        if old_html != new_html:
            atom_id = Path(rel_path).parent.name
            items.append({
                "item_id": atom_id,
                "source": "mini-class",
                "file": rel_path,
                "before": old_html,
                "after": new_html,
            })
    return items


def _extract_xml_changes(
    changed_files: list[str],
) -> list[dict]:
    """Find exemplar/variant question.xml files that changed."""
    items: list[dict] = []
    xml_files = [
        f for f in changed_files
        if f.endswith("question.xml")
        and f.startswith("app/data/pruebas/")
    ]
    for rel_path in xml_files:
        old_xml = _git_show(f"HEAD:{rel_path}")
        new_path = Path(rel_path)
        if old_xml is None or not new_path.exists():
            continue
        new_xml = new_path.read_text(encoding="utf-8")
        if old_xml != new_xml:
            label = "/".join(Path(rel_path).parts[-3:-1])
            items.append({
                "item_id": label,
                "source": "exemplar",
                "file": rel_path,
                "before": old_xml,
                "after": new_xml,
            })
    return items


# ------------------------------------------------------------------
# LLM audit
# ------------------------------------------------------------------


def _audit_one(
    client: object,
    item: dict,
) -> dict:
    """Run the independent audit on a single changed item."""
    prompt = build_revalidation_prompt(
        original=item["before"],
        corrected=item["after"],
    )
    try:
        resp = client.call(
            prompt,
            response_format={"type": "json_object"},
            reasoning_effort="medium",
        )
        data = json.loads(resp.text)
        return {
            "item_id": item["item_id"],
            "source": item["source"],
            "pass": data.get("pass", False),
            "issues": data.get("issues", []),
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
        }
    except Exception as exc:
        logger.warning(
            "Audit error for %s: %s", item["item_id"], exc,
        )
        return {
            "item_id": item["item_id"],
            "source": item["source"],
            "pass": False,
            "issues": [f"Audit error: {exc}"],
            "input_tokens": 0,
            "output_tokens": 0,
        }


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------


def main() -> None:
    """CLI entry point."""
    args = _parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not set.")
        sys.exit(1)

    print("Finding changed files via git diff...")
    changed_files = _git_changed_files()
    if not changed_files:
        print("No uncommitted changes found. Nothing to audit.")
        sys.exit(0)

    items = (
        _extract_question_changes(changed_files)
        + _extract_mini_class_changes(changed_files)
        + _extract_xml_changes(changed_files)
    )

    if not items:
        print(
            f"Found {len(changed_files)} changed files but "
            "no question/lesson content changes to audit.",
        )
        sys.exit(0)

    total = len(items)
    workers = min(args.workers, total)
    print(
        f"Auditing {total} changed items with {workers} "
        f"workers (model: {args.model})...",
    )

    client = load_default_openai_client(model=args.model)
    results: list[dict] = []
    done = 0
    total_in = total_out = 0

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {
            pool.submit(_audit_one, client, item): item
            for item in items
        }
        for fut in as_completed(futs):
            r = fut.result()
            results.append(r)
            done += 1
            total_in += r.get("input_tokens", 0)
            total_out += r.get("output_tokens", 0)
            tag = "PASS" if r["pass"] else "FAIL"
            with _PRINT_LOCK:
                print(
                    f"[{done}/{total}] [{tag}] "
                    f"{r['source']}: {r['item_id']}",
                )
                if not r["pass"]:
                    for issue in r["issues"]:
                        print(f"  -> {issue}")

    _print_summary(results, total_in, total_out)


def _print_summary(
    results: list[dict],
    total_in: int,
    total_out: int,
) -> None:
    """Print final audit summary."""
    passed = [r for r in results if r["pass"]]
    failed = [r for r in results if not r["pass"]]

    print(f"\n{'=' * 50}")
    print(f"AUDIT COMPLETE: {len(passed)} passed, {len(failed)} failed")
    print(f"Tokens: {total_in:,} in / {total_out:,} out")

    if failed:
        print(f"\nFAILED ITEMS ({len(failed)}):")
        for r in failed:
            print(f"  [{r['source']}] {r['item_id']}")
            for issue in r["issues"]:
                print(f"    - {issue}")
        print(
            "\nDo NOT commit until failures are resolved.",
        )
    else:
        print("\nAll items passed. Safe to commit.")
    print("=" * 50)


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Independent audit of notation changes "
            "before committing."
        ),
    )
    parser.add_argument(
        "--workers", type=int, default=8,
        help="Concurrent workers (default: 8)",
    )
    parser.add_argument(
        "--model", type=str, default="gpt-5.1",
        help="OpenAI model for audit (default: gpt-5.1)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
