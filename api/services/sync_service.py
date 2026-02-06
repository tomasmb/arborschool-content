"""Sync service for test-level question synchronization.

Handles preview (diff) and execution of syncing questions from local
file system to the database, including variants.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from api.config import PRUEBAS_ALTERNATIVAS_DIR, PRUEBAS_FINALIZADAS_DIR
from api.services.sync_db import (
    batch_fetch_from_db,
    fetch_test_question_ids,
    fetch_test_variant_ids,
    get_db_connection,
    upsert_question_qti,
)
from app.question_feedback.utils.qti_parser import has_feedback
from app.sync.config import SyncEnvironment

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Shared file-system helpers
# -----------------------------------------------------------------------------


def _normalize_xml(xml: str) -> str:
    """Normalize XML for comparison (remove whitespace variations)."""
    normalized = re.sub(r">\s+<", "><", xml)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.strip()


def _check_validation(folder: Path) -> str | None:
    """Check if a question/variant folder passes validation.

    Returns None if valid, or a reason string if invalid.
    """
    validation_path = folder / "validation_result.json"
    if not validation_path.exists():
        return "not_enriched"
    try:
        with open(validation_path, encoding="utf-8") as f:
            validation = json.load(f)
    except (json.JSONDecodeError, OSError):
        return "validation_unreadable"
    if not validation.get("can_sync"):
        return "validation_failed"
    return None


def _read_validated_xml(folder: Path) -> tuple[str | None, str | None]:
    """Read question_validated.xml. Returns (content, error)."""
    path = folder / "question_validated.xml"
    if not path.exists():
        return None, "no_validated_xml"
    try:
        return path.read_text(encoding="utf-8"), None
    except OSError:
        return None, "xml_unreadable"


def _iter_variant_dirs(
    test_id: str,
) -> list[tuple[str, int, int, Path]]:
    """Walk alternativas/{test_id}/Q*/approved/* and yield variant info.

    Returns list of (variant_id, q_num, variant_seq, variant_dir).
    """
    alt_dir = PRUEBAS_ALTERNATIVAS_DIR / test_id
    results: list[tuple[str, int, int, Path]] = []
    if not alt_dir.exists():
        return results

    for q_dir in sorted(alt_dir.iterdir()):
        if not q_dir.is_dir() or not q_dir.name.startswith("Q"):
            continue
        q_num_match = re.search(r"(\d+)", q_dir.name)
        if not q_num_match:
            continue
        q_num = int(q_num_match.group(1))

        approved_dir = q_dir / "approved"
        if not approved_dir.exists():
            continue

        variant_seq = 0
        for v_dir in sorted(approved_dir.iterdir()):
            if not v_dir.is_dir():
                continue
            v_match = re.search(r"_v(\d+)$", v_dir.name)
            variant_seq = int(v_match.group(1)) if v_match else variant_seq + 1
            v_id = f"alt-{test_id}-Q{q_num}-{variant_seq:03d}"
            results.append((v_id, q_num, variant_seq, v_dir))

    return results


# -----------------------------------------------------------------------------
# Test-scoped diff (DB status)
# -----------------------------------------------------------------------------


def get_test_sync_diff(test_id: str, environment: SyncEnvironment) -> dict:
    """Compute diff between local files and DB for a specific test."""
    result: dict = {
        "environment": environment, "has_changes": False,
        "questions": _empty_diff(), "variants": _empty_diff(), "error": None,
    }

    local_q = _local_syncable_question_ids(test_id)
    local_v = _local_syncable_variant_ids(test_id)
    result["questions"]["local_count"] = len(local_q)
    result["variants"]["local_count"] = len(local_v)

    conn = get_db_connection(environment)
    if conn is None:
        result["error"] = f"Database not configured for {environment}"
        return result

    try:
        db_q = fetch_test_question_ids(conn, test_id)
        db_v = fetch_test_variant_ids(conn, test_id)
        result["questions"] = _id_diff(local_q, db_q)
        result["variants"] = _id_diff(local_v, db_v)
        result["has_changes"] = (
            result["questions"]["has_changes"]
            or result["variants"]["has_changes"]
        )
    except Exception as e:
        logger.exception("Error computing test sync diff")
        result["error"] = str(e)
    finally:
        conn.close()

    return result


def _empty_diff() -> dict:
    return {
        "local_count": 0, "db_count": 0, "new_count": 0,
        "deleted_count": 0, "unchanged_count": 0, "has_changes": False,
    }


def _id_diff(local_ids: set[str], db_ids: dict[str, str]) -> dict:
    db_set = set(db_ids)
    new = local_ids - db_set
    deleted = db_set - local_ids
    unchanged = local_ids & db_set
    return {
        "local_count": len(local_ids), "db_count": len(db_set),
        "new_count": len(new), "deleted_count": len(deleted),
        "unchanged_count": len(unchanged),
        "has_changes": bool(new or deleted),
    }


def _local_syncable_question_ids(test_id: str) -> set[str]:
    base = PRUEBAS_FINALIZADAS_DIR / test_id / "qti"
    ids: set[str] = set()
    if not base.exists():
        return ids
    for q_folder in base.iterdir():
        if not q_folder.is_dir() or not q_folder.name.startswith("Q"):
            continue
        if _check_validation(q_folder) is not None:
            continue
        if _read_validated_xml(q_folder)[1] is not None:
            continue
        ids.add(f"{test_id}-{q_folder.name}")
    return ids


def _local_syncable_variant_ids(test_id: str) -> set[str]:
    ids: set[str] = set()
    for v_id, _, _, v_dir in _iter_variant_dirs(test_id):
        if _check_validation(v_dir) is not None:
            continue
        if _read_validated_xml(v_dir)[1] is not None:
            continue
        ids.add(v_id)
    return ids


# -----------------------------------------------------------------------------
# Sync preview
# -----------------------------------------------------------------------------


def get_sync_preview(
    test_id: str,
    environment: SyncEnvironment = "local",
    include_variants: bool = True,
) -> dict:
    """Generate sync preview for questions and variants."""
    q_result = _preview_questions(test_id, environment)
    v_result = (
        _preview_variants(test_id, environment) if include_variants
        else _empty_preview()
    )
    q_sum = _sum_preview(q_result)
    v_sum = _sum_preview(v_result)
    return {
        "questions": q_result, "variants": v_result,
        "summary": {
            "create": q_sum["create"] + v_sum["create"],
            "update": q_sum["update"] + v_sum["update"],
            "unchanged": q_sum["unchanged"] + v_sum["unchanged"],
            "skipped": q_sum["skipped"] + v_sum["skipped"],
        },
        "question_summary": q_sum, "variant_summary": v_sum,
    }


def _empty_preview() -> dict:
    return {"to_create": [], "to_update": [], "unchanged": [], "skipped": []}


def _sum_preview(r: dict) -> dict:
    return {
        "create": len(r["to_create"]), "update": len(r["to_update"]),
        "unchanged": len(r["unchanged"]), "skipped": len(r["skipped"]),
    }


def _categorize_item(
    item_id: str, item_num: int, local_qti: str,
    db_questions: dict[str, dict],
) -> dict:
    """Categorize a syncable item as create/update/unchanged."""
    db_q = db_questions.get(item_id)
    if db_q is None:
        return {"question_id": item_id, "question_number": item_num, "status": "create"}

    db_qti = db_q.get("qti_xml", "")
    if _normalize_xml(local_qti) == _normalize_xml(db_qti):
        return {"question_id": item_id, "question_number": item_num, "status": "unchanged"}

    return {
        "question_id": item_id, "question_number": item_num, "status": "update",
        "changes": {
            "qti_xml_changed": True,
            "feedback_added": has_feedback(local_qti) and not has_feedback(db_qti),
            "feedback_changed": has_feedback(local_qti) and has_feedback(db_qti),
        },
    }


def _classify_syncable(
    syncable: list[tuple[str, int, str]],
    db_data: dict[str, dict], result: dict,
) -> None:
    for item_id, item_num, xml in syncable:
        item = _categorize_item(item_id, item_num, xml, db_data)
        bucket = {
            "create": "to_create", "update": "to_update",
        }.get(item["status"], "unchanged")
        result[bucket].append(item)


def _preview_questions(test_id: str, environment: SyncEnvironment) -> dict:
    base = PRUEBAS_FINALIZADAS_DIR / test_id / "qti"
    result = _empty_preview()
    if not base.exists():
        return result

    q_folders = sorted(
        [f for f in base.iterdir() if f.is_dir() and f.name.startswith("Q")],
        key=lambda p: int(p.name[1:]) if p.name[1:].isdigit() else 0,
    )

    syncable: list[tuple[str, int, str]] = []
    for q_folder in q_folders:
        q_id = f"{test_id}-{q_folder.name}"
        try:
            q_num = int(q_folder.name[1:])
        except ValueError:
            q_num = 0

        reason = _check_validation(q_folder)
        if reason:
            result["skipped"].append({
                "question_id": q_id, "question_number": q_num,
                "status": "skipped", "reason": reason,
            })
            continue
        xml, err = _read_validated_xml(q_folder)
        if err:
            result["skipped"].append({
                "question_id": q_id, "question_number": q_num,
                "status": "skipped", "reason": err,
            })
            continue
        syncable.append((q_id, q_num, xml))

    db_qs = batch_fetch_from_db(environment, [s[0] for s in syncable])
    _classify_syncable(syncable, db_qs, result)
    return result


def _preview_variants(test_id: str, environment: SyncEnvironment) -> dict:
    result = _empty_preview()
    syncable: list[tuple[str, int, str]] = []

    for v_id, q_num, _, v_dir in _iter_variant_dirs(test_id):
        reason = _check_validation(v_dir)
        if reason:
            result["skipped"].append({
                "question_id": v_id, "question_number": q_num,
                "status": "skipped", "reason": reason,
            })
            continue
        xml, err = _read_validated_xml(v_dir)
        if err:
            result["skipped"].append({
                "question_id": v_id, "question_number": q_num,
                "status": "skipped", "reason": err,
            })
            continue
        syncable.append((v_id, q_num, xml))

    db_vs = batch_fetch_from_db(environment, [s[0] for s in syncable])
    _classify_syncable(syncable, db_vs, result)
    return result


# -----------------------------------------------------------------------------
# Sync execution
# -----------------------------------------------------------------------------


def execute_sync(
    test_id: str,
    environment: SyncEnvironment = "local",
    include_variants: bool = True,
    upload_images: bool = True,
) -> dict:
    """Execute sync to database."""
    preview = get_sync_preview(test_id, environment, include_variants)
    created = 0
    updated = 0
    details: list[dict] = []
    base = PRUEBAS_FINALIZADAS_DIR / test_id / "qti"

    to_sync = preview["questions"]["to_create"] + preview["questions"]["to_update"]
    for q in to_sync:
        q_id = q["question_id"]
        q_folder = base / f"Q{q['question_number']}"
        xml, err = _read_validated_xml(q_folder)
        if err:
            details.append({"question_id": q_id, "action": "skipped", "reason": err})
            continue
        if upsert_question_qti(q_id, xml, environment):
            is_new = q["status"] == "create"
            created += 1 if is_new else 0
            updated += 0 if is_new else 1
            details.append({"question_id": q_id, "action": "created" if is_new else "updated"})
        else:
            details.append({"question_id": q_id, "action": "failed", "reason": "db_error"})

    for q in preview["questions"]["skipped"]:
        details.append({"question_id": q["question_id"], "action": "skipped", "reason": q["reason"]})

    return {"created": created, "updated": updated, "skipped": len(preview["questions"]["skipped"]), "details": details}


# -----------------------------------------------------------------------------
# Single-question status
# -----------------------------------------------------------------------------


def get_question_sync_status(
    test_id: str, question_num: int,
    environment: SyncEnvironment = "local",
) -> str:
    """Get sync status for a single question.

    Returns: not_in_db | in_sync | local_changed | not_validated
    """
    q_folder = PRUEBAS_FINALIZADAS_DIR / test_id / "qti" / f"Q{question_num}"
    if not q_folder.exists():
        return "not_validated"
    if _check_validation(q_folder):
        return "not_validated"
    xml, err = _read_validated_xml(q_folder)
    if err:
        return "not_validated"

    q_id = f"{test_id}-Q{question_num}"
    db_qs = batch_fetch_from_db(environment, [q_id])
    db_q = db_qs.get(q_id)
    if db_q is None:
        return "not_in_db"
    if _normalize_xml(xml) == _normalize_xml(db_q.get("qti_xml", "")):
        return "in_sync"
    return "local_changed"
