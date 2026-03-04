"""Write validated notation fixes to disk.

Handles these source types:
- generated-question: update qti_xml inside phase_9 checkpoint JSON.
- official-question / variant: overwrite question_validated.xml.
- lesson: overwrite mini-class.html.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from scripts.notation_state import PipelineState

logger = logging.getLogger(__name__)


def write_fixes_to_disk(state: PipelineState) -> int:
    """Write all fix_ok items to their source files.

    Returns the number of items written.
    """
    fix_ok = state.items_by_status("fix_ok")
    if not fix_ok:
        print("No fix_ok items to write.")
        return 0

    q_updates: dict[str, list[tuple[str, str]]] = {}
    file_updates: dict[str, str] = {}

    for key, item in fix_ok:
        fixed = item.get("fixed_content", "")
        if not fixed:
            continue
        source = item.get("source", "")
        fp = item.get("file_path", "")

        if source == "generated-question":
            qid = item.get("item_key", key)
            q_updates.setdefault(fp, []).append((qid, fixed))
        else:
            file_updates[fp] = fixed

    written = 0
    for fp, updates in q_updates.items():
        written += _write_question_fixes(
            Path(fp), updates,
        )
    for fp, fixed in file_updates.items():
        _write_file_fix(Path(fp), fixed)
        written += 1

    print(f"Wrote {written} fixes.")
    return written


def _write_question_fixes(
    p9_path: Path,
    updates: list[tuple[str, str]],
) -> int:
    """Update qti_xml fields in a phase_9 JSON file."""
    if not p9_path.exists():
        logger.warning("File not found: %s", p9_path)
        return 0

    data = json.loads(p9_path.read_text("utf-8"))
    update_map = dict(updates)
    count = 0
    for item in data.get("items", []):
        iid = item.get("item_id", "")
        if iid in update_map:
            item["qti_xml"] = update_map[iid]
            count += 1

    p9_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return count


def _write_file_fix(
    file_path: Path,
    fixed: str,
) -> None:
    """Write a fixed mini-class HTML or question XML file."""
    if not file_path.exists():
        logger.warning("File not found: %s", file_path)
        return
    file_path.write_text(fixed, encoding="utf-8")
