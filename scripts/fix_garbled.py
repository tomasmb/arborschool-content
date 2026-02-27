"""Fix garbled Spanish characters in generated questions.

Deterministically repairs corrupted accented characters, then optionally
verifies each fix with GPT 5.1 low reasoning before writing back.

Usage:
    python scripts/fix_garbled.py                    # dry-run
    python scripts/fix_garbled.py --verify           # dry-run + GPT check
    python scripts/fix_garbled.py --verify --apply   # verify + write
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import sys
import textwrap
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.garbled_mappings import (
    HEX_TO_CORRECT,
    INTERROGATIVE_FIXES,
    NULL_BYTE_FIXES,
    POST_FIX_CORRECTIONS,
    POST_FIX_WORD_CORRECTIONS,
    TILDE_FIXES,
    WORD_ACCENT_FIXES,
)

_log = logging.getLogger(__name__)

QG_ROOT = Path("app/data/question-generation")
BACKUP_DIR = QG_ROOT / ".fix_backups"
MANUAL_REVIEW_PATH = Path("scripts/fix_garbled_manual_review.txt")

# ── Safety zones: regions we must never modify ───────────────
_MATH_RE = re.compile(r"<math[^>]*>.*?</math>", re.DOTALL)
_SRC_RE = re.compile(r'src="[^"]*"')
_ID_RE = re.compile(
    r'(?:identifier|xsi:schemaLocation|xmlns(?::\w+)?)'
    r'="[^"]*"'
)
_SHA_RE = re.compile(r"sha256:[0-9a-f]{64}")
_URL_RE = re.compile(r"https?://\S+")

_PLACEHOLDER = "\x00SAFE{}\x00"


def _protect_zones(text: str) -> tuple[str, list[str]]:
    """Replace safety zones with placeholders, return (text, stash)."""
    stash: list[str] = []
    for pattern in (_MATH_RE, _SRC_RE, _ID_RE, _SHA_RE, _URL_RE):
        for m in pattern.finditer(text):
            placeholder = _PLACEHOLDER.format(len(stash))
            stash.append(m.group())
            text = text.replace(m.group(), placeholder, 1)
    return text, stash


def _restore_zones(text: str, stash: list[str]) -> str:
    """Put stashed zones back into the text."""
    for i, original in enumerate(stash):
        text = text.replace(_PLACEHOLDER.format(i), original, 1)
    return text


# ── Fix engine ───────────────────────────────────────────────


def _case_preserving_replace(match: re.Match[str], good: str) -> str:
    """Return `good` with capitalization matching the match."""
    word = match.group()
    if word[0].isupper():
        return good[0].upper() + good[1:]
    return good


def _apply_hex_fixes(text: str) -> str:
    """Class 1: replace hex-substitution patterns."""
    for garbled, correct in sorted(
        HEX_TO_CORRECT.items(), key=lambda x: -len(x[0]),
    ):
        text = text.replace(garbled, correct)
    return text


def _apply_post_fix_corrections(text: str) -> str:
    """Fix words where earlier steps produce wrong Spanish."""
    for bad, good in POST_FIX_CORRECTIONS.items():
        text = text.replace(bad, good)
    for bad, good in POST_FIX_WORD_CORRECTIONS:
        text = re.sub(rf"\b{re.escape(bad)}\b", good, text)
    return text


def _apply_word_accent_fixes(text: str) -> str:
    """Classes 2 + 4b: word-boundary accent restoration."""
    for bad, good in WORD_ACCENT_FIXES:
        text = re.sub(
            rf"\b{re.escape(bad)}\b",
            lambda m, g=good: _case_preserving_replace(m, g),
            text,
            flags=re.IGNORECASE,
        )
    return text


def _apply_tilde_fixes(text: str) -> str:
    """Class 3: ñ restoration."""
    for bad, good in TILDE_FIXES:
        text = re.sub(
            rf"\b{re.escape(bad)}\b",
            lambda m, g=good: _case_preserving_replace(m, g),
            text,
            flags=re.IGNORECASE,
        )
    return text


def _apply_interrogative_fixes(text: str) -> str:
    """Class 6: interrogative accent restoration."""
    for pattern, replacement in INTERROGATIVE_FIXES:
        text = re.sub(pattern, replacement, text)
    return text


def _apply_double_encoded_fixes(text: str) -> str:
    """Class 5: fix double-encoded HTML entities."""
    text = re.sub(
        r"&amp;((?:aacute|eacute|iacute|oacute|uacute|ntilde"
        r"|Aacute|iquest|iexcl|#x[0-9a-fA-F]+|#\d+);?)",
        r"&\1",
        text,
    )
    return text


def _apply_null_byte_fixes(text: str) -> str:
    """Fix null-byte split characters in image_description."""
    for bad, good in NULL_BYTE_FIXES.items():
        text = text.replace(bad, good)
    return text


_LITERAL_ESCAPE_RE = re.compile(r"\\u([0-9a-fA-F]{4})")


def _apply_literal_escape_fixes(text: str) -> str:
    r"""Decode literal \uXXXX sequences the LLM wrote as text."""
    return _LITERAL_ESCAPE_RE.sub(
        lambda m: chr(int(m.group(1), 16)), text,
    )


def fix_xml(xml: str) -> str:
    """Apply all deterministic fixes to a QTI XML string."""
    protected, stash = _protect_zones(xml)
    protected = _apply_literal_escape_fixes(protected)
    protected = _apply_hex_fixes(protected)
    protected = _apply_word_accent_fixes(protected)
    protected = _apply_tilde_fixes(protected)
    protected = _apply_interrogative_fixes(protected)
    protected = _apply_double_encoded_fixes(protected)
    protected = _apply_post_fix_corrections(protected)
    return _restore_zones(protected, stash)


def fix_image_description(desc: str) -> str:
    """Apply fixes to an image_description string."""
    desc = _apply_null_byte_fixes(desc)
    desc = _apply_literal_escape_fixes(desc)
    desc = _apply_hex_fixes(desc)
    desc = _apply_word_accent_fixes(desc)
    desc = _apply_tilde_fixes(desc)
    desc = _apply_interrogative_fixes(desc)
    desc = _apply_post_fix_corrections(desc)
    return desc


# ── Diff generation ──────────────────────────────────────────

def _build_diff(
    item_id: str, field: str, old: str, new: str,
) -> str | None:
    """Build a human-readable diff of changes. None if identical."""
    if old == new:
        return None
    old_lines = old.splitlines()
    new_lines = new.splitlines()
    chunks: list[str] = []
    for i, (ol, nl) in enumerate(
        zip(old_lines, new_lines), start=1,
    ):
        if ol != nl:
            chunks.append(f"  L{i}:")
            chunks.append(f"    - {ol.strip()}")
            chunks.append(f"    + {nl.strip()}")
    if len(new_lines) != len(old_lines):
        chunks.append(
            f"  (line count changed: {len(old_lines)}"
            f" → {len(new_lines)})"
        )
    if not chunks:
        chunks.append("  (binary/whitespace-only diff)")
    header = f"[{item_id}] {field}"
    return header + "\n" + "\n".join(chunks)


# ── GPT verification ────────────────────────────────────────

_VERIFY_PROMPT = textwrap.dedent("""\
    You are a QA checker for Spanish math questions in QTI XML.

    Below is a diff showing ONLY the lines that changed. Each
    changed line is shown in full (old line with "-", new line
    with "+"). The diff is produced by fixing garbled accented
    characters (e.g. "funcif3n" → "función", "bfCue1l" → "¿Cuál").

    Check ONLY for these real problems:
    1. A replacement produced WRONG Spanish (e.g. "tampocó"
       instead of "tampoco", or "ccómo" instead of "cómo").
    2. A replacement ALTERED math expressions, MathML tags,
       URLs, or XML attributes (not just the text around them).

    Do NOT flag:
    - Garbled text that was NOT changed (pre-existing corruption
      that the fix didn't address is fine — ignore it).
    - Changes where only accents/tildes were added to text
      content — these are the intended fixes.

    Respond with ONLY a JSON object:
    {{"verdict": "PASS"}} or {{"verdict": "FAIL", "issues": ["..."]}}

    Diff:
    {diff_text}
""")


def _verify_with_gpt(
    diff_text: str,
    client: object,
) -> tuple[bool, str]:
    """Send diff to GPT 5.1 low for verification.

    Returns (passed: bool, raw_response: str).
    """
    prompt = _VERIFY_PROMPT.format(diff_text=diff_text)
    resp = client.generate_text(  # type: ignore[union-attr]
        prompt,
        reasoning_effort="low",
        response_mime_type="application/json",
    )
    raw = resp.text.strip()
    try:
        parsed = json.loads(raw)
        verdict = parsed.get("verdict", "").upper()
        return verdict == "PASS", raw
    except json.JSONDecodeError:
        return "PASS" in raw.upper(), raw


# ── Scanning + orchestration ─────────────────────────────────

def _load_affected_ids() -> set[str]:
    """Parse the garbled report for affected item IDs."""
    report = QG_ROOT / "garbled_questions_report.txt"
    ids: set[str] = set()
    for line in report.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("#") or line.startswith("##") or not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            ids.add(parts[0].strip())
    return ids


def _iter_phase9_files() -> list[Path]:
    """Return all phase_9_final_validation.json paths, sorted."""
    return sorted(
        QG_ROOT.glob("*/checkpoints/phase_9_final_validation.json")
    )


def _post_fix_is_clean(xml: str, desc: str) -> bool:
    """Return True if the garbled detector finds no issues."""
    from scripts.garbled_report import _check_item
    problems = _check_item(xml)
    if desc:
        problems += _check_item(desc)
    return len(problems) == 0


def run(
    *,
    verify: bool = False,
    apply: bool = False,
    force_clean: bool = False,
) -> None:
    """Main entry point for the fix pipeline."""
    affected_ids = _load_affected_ids()
    print(f"Loaded {len(affected_ids)} affected item IDs from report")

    gpt_client = None
    if verify:
        from app.llm_clients import load_default_openai_client
        gpt_client = load_default_openai_client(model="gpt-5.1")
        print("GPT 5.1 client loaded for verification")

    total_fixed = 0
    total_verified = 0
    total_failed = 0
    total_force_applied = 0
    all_diffs: list[str] = []
    manual_review: list[str] = []
    files_to_write: dict[Path, dict] = {}

    for p9_path in _iter_phase9_files():
        data = json.loads(p9_path.read_text(encoding="utf-8"))
        items = data.get("items", [])
        file_changed = False

        for item in items:
            item_id = item.get("item_id", "")
            if item_id not in affected_ids:
                continue

            xml_old = item.get("qti_xml", "")
            desc_old = item.get("image_description", "")

            xml_new = fix_xml(xml_old) if xml_old else xml_old
            desc_new = (
                fix_image_description(desc_old) if desc_old
                else desc_old
            )

            xml_diff = _build_diff(item_id, "qti_xml", xml_old, xml_new)
            desc_diff = _build_diff(
                item_id, "image_description", desc_old, desc_new,
            )

            if not xml_diff and not desc_diff:
                continue

            combined_diff = "\n".join(
                d for d in (xml_diff, desc_diff) if d
            )
            all_diffs.append(combined_diff)
            total_fixed += 1

            should_apply = True
            if verify and gpt_client is not None:
                passed, raw_resp = _verify_with_gpt(
                    combined_diff, gpt_client,
                )
                if passed:
                    total_verified += 1
                    print(f"  PASS: {item_id}")
                elif force_clean and _post_fix_is_clean(
                    xml_new, desc_new,
                ):
                    total_force_applied += 1
                    print(
                        f"  FORCE: {item_id}"
                        " (GPT FAIL but detector clean)"
                    )
                else:
                    total_failed += 1
                    manual_review.append(
                        f"{item_id}\n  GPT said: {raw_resp}\n"
                        f"  Diff:\n{combined_diff}\n"
                    )
                    print(f"  FAIL: {item_id} → {raw_resp[:80]}")
                    should_apply = False

            if should_apply:
                item["qti_xml"] = xml_new
                if desc_old:
                    item["image_description"] = desc_new
                file_changed = True

        if file_changed:
            files_to_write[p9_path] = data

    # Print summary
    print(f"\n{'='*60}")
    print(f"Questions with fixes: {total_fixed}")
    if verify:
        print(f"GPT verified PASS:    {total_verified}")
        if force_clean:
            print(f"Force-applied (clean):{total_force_applied}")
        print(f"GPT verified FAIL:    {total_failed}")
    print(f"Files to update:      {len(files_to_write)}")

    if not apply:
        print("\n[DRY RUN] No files modified. Showing diffs:\n")
        for d in all_diffs[:10]:
            print(d)
            print()
        if len(all_diffs) > 10:
            print(f"  ... and {len(all_diffs) - 10} more diffs")
        print(
            "\nRe-run with --apply to write changes"
            " (add --verify for GPT check)."
        )
        return

    # Write backups + apply
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = BACKUP_DIR / f"fix_{ts}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    for p9_path, data in files_to_write.items():
        rel = p9_path.relative_to(QG_ROOT)
        bak = backup_dir / rel
        bak.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p9_path, bak)
        p9_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"  Updated: {p9_path}")

    print(f"\nBackups saved to: {backup_dir}")

    if manual_review:
        MANUAL_REVIEW_PATH.write_text(
            "\n".join(manual_review), encoding="utf-8",
        )
        print(
            f"Manual review needed for {len(manual_review)} items:"
            f" {MANUAL_REVIEW_PATH}"
        )

    print(f"\nDone. Run 'python scripts/garbled_report.py' to verify.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(
        description="Fix garbled Spanish characters in questions",
    )
    parser.add_argument(
        "--verify", action="store_true",
        help="Verify each fix with GPT 5.1 low reasoning",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Write fixes back to phase_9 JSON files",
    )
    parser.add_argument(
        "--force-clean", action="store_true",
        help="Apply even if GPT rejects, when garbled detector "
        "confirms post-fix text is clean",
    )
    args = parser.parse_args()

    if args.apply and not args.verify:
        print(
            "ERROR: --apply requires --verify for safety. "
            "Use: --verify --apply"
        )
        sys.exit(1)

    run(
        verify=args.verify,
        apply=args.apply,
        force_clean=args.force_clean,
    )
