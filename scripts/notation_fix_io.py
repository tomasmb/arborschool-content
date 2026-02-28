"""File I/O helpers for the notation fix pipeline.

Backup, write-back, and revert operations for questions,
mini-classes, and exemplar/variant XML files.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

_QG_ROOT = Path("app/data/question-generation")
_ML_ROOT = Path("app/data/mini-lessons")
_PRUEBAS_ROOT = Path("app/data/pruebas")
_BACKUP_QG = _QG_ROOT / ".notation_fix_backups"
_BACKUP_ML = _ML_ROOT / ".notation_fix_backups"
_BACKUP_PRUEBAS = _PRUEBAS_ROOT / ".notation_fix_backups"


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


def apply_single_item(item: dict, ts: str) -> None:
    """Write corrected content for a mini-class or XML file."""
    fp = Path(item["file_path"])
    src = item["source"]
    if src == "mini-class":
        _backup_and_write(fp, item["corrected"], _BACKUP_ML, _ML_ROOT, ts)
    else:
        _backup_and_write(
            fp, item["corrected"], _BACKUP_PRUEBAS, _PRUEBAS_ROOT, ts,
        )


def apply_question_group(
    p9_path: Path, items: list[dict], ts: str,
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


def revert_single_item(item: dict) -> None:
    """Revert a file to its original content (from state)."""
    fp = Path(item["file_path"])
    fp.write_text(item["original"], encoding="utf-8")


def revert_question_item(item: dict) -> None:
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
