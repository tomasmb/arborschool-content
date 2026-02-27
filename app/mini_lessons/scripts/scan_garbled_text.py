"""Scan all published mini-lessons for garbled / corrupted text.

Usage:
    python -m app.mini_lessons.scripts.scan_garbled_text
    python -m app.mini_lessons.scripts.scan_garbled_text --include-rejected
    python -m app.mini_lessons.scripts.scan_garbled_text --workers 8
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from app.llm_clients import OpenAIClient
from app.mini_lessons.prompts.validation import build_garbled_text_prompt

logger = logging.getLogger(__name__)

_MINI_LESSONS_DIR = Path("app/data/mini-lessons")
_REPORT_PATH = Path("app/data/mini-lessons/garbled_lessons_report.txt")
_PRINT_LOCK = threading.Lock()


def _find_lessons(include_rejected: bool = False) -> list[tuple[str, Path]]:
    """Find all mini-lesson HTML files. Returns (atom_id, path) pairs."""
    lessons: list[tuple[str, Path]] = []
    if not _MINI_LESSONS_DIR.exists():
        return lessons
    for atom_dir in sorted(_MINI_LESSONS_DIR.iterdir()):
        if not atom_dir.is_dir() or atom_dir.name.startswith("."):
            continue
        published = atom_dir / "mini-class.html"
        rejected = atom_dir / "mini-class.rejected.html"
        if published.exists():
            lessons.append((atom_dir.name, published))
        elif include_rejected and rejected.exists():
            lessons.append((atom_dir.name, rejected))
    return lessons


def _check_one(
    client: OpenAIClient, atom_id: str, html_path: Path,
) -> dict:
    """Check a single lesson for garbled text via LLM."""
    html = html_path.read_text(encoding="utf-8")
    prompt = build_garbled_text_prompt(html)
    try:
        resp = client.call(
            prompt,
            response_format={"type": "json_object"},
            reasoning_effort="low",
        )
        data = json.loads(resp.text)
        return {
            "atom_id": atom_id,
            "text_clean": data.get("text_clean", True),
            "issues": data.get("issues", []),
            "error": None,
        }
    except Exception as exc:
        logger.warning("Check failed for %s: %s", atom_id, exc)
        return {
            "atom_id": atom_id,
            "text_clean": None,
            "issues": [],
            "error": str(exc),
        }


def _write_report(
    results: list[dict], total: int, include_rejected: bool,
) -> Path:
    """Write the garbled text scan report."""
    clean = sum(1 for r in results if r["text_clean"] is True)
    garbled = [r for r in results if r["text_clean"] is False]
    errors = [r for r in results if r["error"] is not None]
    affected_atoms = len(garbled)

    lines = [
        "# Garbled Text Report — Mini-Lessons",
        f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"# Scope: {'published + rejected' if include_rejected else 'published only'}",
        f"# Total lessons scanned: {total}",
        f"# Clean lessons: {clean}",
        f"# Garbled lessons: {affected_atoms}",
        f"# Scan errors: {len(errors)}",
        f"# Percentage garbled: {affected_atoms / total * 100:.1f}%"
        if total > 0 else "# Percentage garbled: 0.0%",
        "#",
    ]

    if garbled:
        lines.append("# === GARBLED LESSONS ===")
        lines.append("#")
        for r in sorted(garbled, key=lambda x: x["atom_id"]):
            lines.append(f"# {r['atom_id']}:")
            for issue in r["issues"]:
                if isinstance(issue, str):
                    lines.append(f"#   - {issue}")
                elif isinstance(issue, dict):
                    cat = issue.get("category", "?")
                    desc = issue.get("description", issue.get("issue", str(issue)))
                    frag = issue.get("fragment", "")
                    line = f"#   - [{cat}] {desc}"
                    if frag:
                        line += f" → «{frag[:80]}»"
                    lines.append(line)
            lines.append("#")

    if errors:
        lines.append("# === SCAN ERRORS ===")
        for r in errors:
            lines.append(f"# {r['atom_id']}: {r['error']}")
        lines.append("#")

    if not garbled and not errors:
        lines.append("# All lessons passed garbled text check.")
        lines.append("#")

    report_text = "\n".join(lines) + "\n"
    _REPORT_PATH.write_text(report_text, encoding="utf-8")
    return _REPORT_PATH


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

    lessons = _find_lessons(include_rejected=args.include_rejected)
    if not lessons:
        print("No lessons found to scan.")
        sys.exit(0)

    total = len(lessons)
    workers = min(args.workers, total)
    print(f"Scanning {total} lessons with {workers} workers...")

    client = OpenAIClient(api_key=api_key)
    results: list[dict] = []
    done = 0

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_check_one, client, aid, path): aid
            for aid, path in lessons
        }
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            done += 1
            status = "CLEAN" if result["text_clean"] else "GARBLED"
            if result["error"]:
                status = "ERROR"
            with _PRINT_LOCK:
                print(f"[{done}/{total}] [{status}] {result['atom_id']}")

    report_path = _write_report(results, total, args.include_rejected)

    garbled = sum(1 for r in results if r["text_clean"] is False)
    clean = sum(1 for r in results if r["text_clean"] is True)
    print(f"\n=== Scan complete: {clean} clean, {garbled} garbled ===")
    print(f"Report: {report_path}")


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Scan mini-lessons for garbled text.",
    )
    parser.add_argument(
        "--include-rejected", action="store_true",
        help="Also scan rejected lessons",
    )
    parser.add_argument(
        "--workers", type=int, default=8,
        help="Concurrent workers (default: 8)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
