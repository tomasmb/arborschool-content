"""Fix garbled text in published mini-lessons using LLM.

Reads the scan report (or re-scans), fixes each lesson with an LLM call,
then validates via three independent gates before writing.

Usage:
    python -m app.mini_lessons.scripts.fix_garbled_lessons
    python -m app.mini_lessons.scripts.fix_garbled_lessons --apply
    python -m app.mini_lessons.scripts.fix_garbled_lessons --workers 4
"""

from __future__ import annotations

import argparse
import difflib
import json
import logging
import os
import re
import shutil
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from app.llm_clients import OpenAIClient
from app.mini_lessons.html_validator import check_full_lesson_structure
from app.mini_lessons.prompts.validation import (
    build_garbled_fix_prompt,
    build_garbled_fix_verify_prompt,
    build_garbled_text_prompt,
)

logger = logging.getLogger(__name__)

_MINI_LESSONS_DIR = Path("app/data/mini-lessons")
_REPORT_PATH = _MINI_LESSONS_DIR / "garbled_lessons_report.txt"
_BACKUP_DIR = _MINI_LESSONS_DIR / ".fix_backups"
_PRINT_LOCK = threading.Lock()

_ATOM_ID_RE = re.compile(r"^# (A-M\d+-[A-Z]{3,4}-\d{2}-\d{2}):$")
_ISSUE_RE = re.compile(r"^#   - (.+)$")
_HTML_WRAPPER_RE = re.compile(
    r"^\s*<html[^>]*>\s*", re.IGNORECASE,
)
_HTML_CLOSE_RE = re.compile(
    r"\s*</html>\s*$", re.IGNORECASE,
)


# ------------------------------------------------------------------
# Load garbled atoms from report
# ------------------------------------------------------------------


def _load_garbled_atoms() -> dict[str, list[str]]:
    """Parse the scan report and return {atom_id: [issue_strings]}.

    Each issue is a single human-readable line from the report.
    """
    if not _REPORT_PATH.exists():
        logger.error("Report not found: %s", _REPORT_PATH)
        return {}

    atoms: dict[str, list[str]] = {}
    current_atom: str | None = None
    for raw_line in _REPORT_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        atom_match = _ATOM_ID_RE.match(line)
        if atom_match:
            current_atom = atom_match.group(1)
            atoms[current_atom] = []
            continue
        if current_atom is not None:
            issue_match = _ISSUE_RE.match(line)
            if issue_match:
                atoms[current_atom].append(issue_match.group(1))
            elif line == "#":
                current_atom = None
    return atoms


# ------------------------------------------------------------------
# Diff helper
# ------------------------------------------------------------------


def _strip_html_wrapper(html: str) -> str:
    """Remove spurious <html>...</html> wrapper the LLM may add."""
    html = _HTML_WRAPPER_RE.sub("", html)
    html = _HTML_CLOSE_RE.sub("", html)
    return html.strip() + "\n"


def _ensure_trailing_newline(text: str) -> str:
    """Ensure text ends with exactly one newline."""
    return text.rstrip("\n") + "\n"


def _build_diff(old: str, new: str) -> str:
    """Build a unified diff between old and new HTML."""
    old_norm = _ensure_trailing_newline(old)
    new_norm = _ensure_trailing_newline(new)
    diff = difflib.unified_diff(
        old_norm.splitlines(keepends=True),
        new_norm.splitlines(keepends=True),
        fromfile="original", tofile="fixed", n=2,
    )
    return "".join(diff)


# ------------------------------------------------------------------
# Three-stage validation
# ------------------------------------------------------------------


def _validate_fix(
    client: OpenAIClient,
    original_html: str,
    fixed_html: str,
) -> tuple[bool, list[str]]:
    """Run 3-stage validation on the proposed fix.

    Returns (passed, list_of_reasons_if_failed).
    """
    reasons: list[str] = []
    diff_text = _build_diff(original_html, fixed_html)

    if not diff_text.strip():
        return False, ["No changes were made by the fix"]

    # Stage 1: LLM verify the diff
    verify_prompt = build_garbled_fix_verify_prompt(diff_text)
    try:
        resp = client.call(
            verify_prompt,
            response_format={"type": "json_object"},
            reasoning_effort="low",
        )
        verdict = json.loads(resp.text)
        if verdict.get("verdict") != "PASS":
            issues = verdict.get("issues", ["Unknown"])
            reasons.append(
                f"Stage 1 (LLM verify) FAIL: {issues}"
            )
    except Exception as exc:
        reasons.append(f"Stage 1 (LLM verify) error: {exc}")

    # Stage 2: Re-scan with garbled text check
    scan_prompt = build_garbled_text_prompt(fixed_html)
    try:
        resp = client.call(
            scan_prompt,
            response_format={"type": "json_object"},
            reasoning_effort="low",
        )
        scan_result = json.loads(resp.text)
        if not scan_result.get("text_clean", False):
            remaining = scan_result.get("issues", [])
            reasons.append(
                f"Stage 2 (re-scan) still garbled: {remaining}"
            )
    except Exception as exc:
        reasons.append(f"Stage 2 (re-scan) error: {exc}")

    # Stage 3: Structural HTML check
    structural_errors = check_full_lesson_structure(fixed_html)
    if structural_errors:
        reasons.append(
            f"Stage 3 (structure) errors: {structural_errors}"
        )

    return len(reasons) == 0, reasons


# ------------------------------------------------------------------
# Fix one lesson
# ------------------------------------------------------------------


def _fix_one(
    client: OpenAIClient,
    atom_id: str,
    html_path: Path,
    issues: list[str],
) -> dict:
    """Fix a single garbled lesson and validate the result.

    Returns a result dict with keys: atom_id, status, diff,
    validation_reasons, fixed_html.
    """
    original_html = html_path.read_text(encoding="utf-8")

    fix_prompt = build_garbled_fix_prompt(original_html, issues)
    try:
        resp = client.call(
            fix_prompt,
            response_format={"type": "json_object"},
            reasoning_effort="medium",
        )
        fix_data = json.loads(resp.text)
        fixed_html = _strip_html_wrapper(
            fix_data.get("fixed_html", ""),
        )
    except Exception as exc:
        return {
            "atom_id": atom_id,
            "status": "fix_error",
            "diff": "",
            "validation_reasons": [str(exc)],
            "fixed_html": None,
        }

    if not fixed_html.strip():
        return {
            "atom_id": atom_id,
            "status": "empty_fix",
            "diff": "",
            "validation_reasons": ["LLM returned empty HTML"],
            "fixed_html": None,
        }

    diff_text = _build_diff(original_html, fixed_html)
    passed, reasons = _validate_fix(
        client, original_html, fixed_html,
    )

    status = "validated" if passed else "manual_review"
    return {
        "atom_id": atom_id,
        "status": status,
        "diff": diff_text,
        "validation_reasons": reasons,
        "fixed_html": fixed_html if passed else None,
    }


# ------------------------------------------------------------------
# Write fix with backup
# ------------------------------------------------------------------


def _write_fix(
    atom_id: str,
    html_path: Path,
    fixed_html: str,
    backup_dir: Path,
) -> None:
    """Backup original and write the fixed HTML."""
    atom_backup = backup_dir / atom_id
    atom_backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(html_path, atom_backup / html_path.name)
    html_path.write_text(fixed_html, encoding="utf-8")
    logger.info("Applied fix for %s (backup in %s)", atom_id, atom_backup)


# ------------------------------------------------------------------
# CLI + main
# ------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fix garbled text in mini-lessons using LLM.",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Write fixes to disk (default is dry-run)",
    )
    parser.add_argument(
        "--workers", type=int, default=4,
        help="Concurrent workers (default: 4)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""
    args = _parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("Error: OPENAI_API_KEY not set.")
        sys.exit(1)

    garbled = _load_garbled_atoms()
    if not garbled:
        print("No garbled lessons found in report.")
        sys.exit(0)

    total = len(garbled)
    workers = min(args.workers, total)
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[{mode}] Fixing {total} garbled lessons with {workers} workers...")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = _BACKUP_DIR / f"fix_{timestamp}"

    client = OpenAIClient(api_key=api_key)
    results: list[dict] = []
    done = 0

    items = []
    for atom_id, issues in garbled.items():
        html_path = _MINI_LESSONS_DIR / atom_id / "mini-class.html"
        if not html_path.exists():
            print(f"  SKIP {atom_id}: mini-class.html not found")
            continue
        items.append((atom_id, html_path, issues))

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(
                _fix_one, client, atom_id, path, issues,
            ): atom_id
            for atom_id, path, issues in items
        }
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            done += 1
            with _PRINT_LOCK:
                _print_result(result, done, total, args.apply)

    _apply_and_summarize(results, args.apply, backup_dir)


def _print_result(
    result: dict, done: int, total: int, apply: bool,
) -> None:
    """Print progress for one completed fix."""
    status = result["status"].upper()
    atom = result["atom_id"]
    print(f"\n[{done}/{total}] [{status}] {atom}")
    if result["diff"]:
        for line in result["diff"].splitlines()[:30]:
            print(f"  {line}")
        diff_lines = result["diff"].count("\n")
        if diff_lines > 30:
            print(f"  ... ({diff_lines - 30} more lines)")
    if result["validation_reasons"]:
        for reason in result["validation_reasons"]:
            print(f"  ⚠ {reason}")


def _apply_and_summarize(
    results: list[dict], apply: bool, backup_dir: Path,
) -> None:
    """Apply validated fixes (if --apply) and print summary."""
    validated = [r for r in results if r["status"] == "validated"]
    manual = [r for r in results if r["status"] == "manual_review"]
    errors = [
        r for r in results
        if r["status"] in ("fix_error", "empty_fix")
    ]

    if apply and validated:
        backup_dir.mkdir(parents=True, exist_ok=True)
        for r in validated:
            html_path = (
                _MINI_LESSONS_DIR / r["atom_id"] / "mini-class.html"
            )
            _write_fix(
                r["atom_id"], html_path, r["fixed_html"], backup_dir,
            )

    print("\n" + "=" * 50)
    print(f"VALIDATED (auto-fixed): {len(validated)}")
    for r in validated:
        applied = " ✓ APPLIED" if apply else " (dry-run)"
        print(f"  {r['atom_id']}{applied}")

    if manual:
        print(f"\nMANUAL REVIEW NEEDED: {len(manual)}")
        for r in manual:
            print(f"  {r['atom_id']}")
            for reason in r["validation_reasons"]:
                print(f"    ⚠ {reason}")

    if errors:
        print(f"\nERRORS: {len(errors)}")
        for r in errors:
            print(f"  {r['atom_id']}: {r['validation_reasons']}")

    if apply and validated:
        print(f"\nBackups saved to: {backup_dir}")
    elif validated and not apply:
        print("\nRe-run with --apply to write fixes to disk.")


if __name__ == "__main__":
    main()
