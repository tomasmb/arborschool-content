"""Sync service for test-level question synchronization.

Handles preview (diff) and execution of syncing questions from local
file system to the database.
"""

from __future__ import annotations

import json
import logging
import re

from api.config import PRUEBAS_FINALIZADAS_DIR
from app.question_feedback.utils.qti_parser import has_feedback

logger = logging.getLogger(__name__)


def get_sync_preview(
    test_id: str,
    include_variants: bool = True,
) -> dict:
    """Generate sync preview showing what will be created/updated/skipped.

    Args:
        test_id: The test ID to preview sync for.
        include_variants: Whether to include variant questions (future use).

    Returns:
        Dict with questions categorized and summary counts.
    """
    base_path = PRUEBAS_FINALIZADAS_DIR / test_id / "qti"

    to_create: list[dict] = []
    to_update: list[dict] = []
    unchanged: list[dict] = []
    skipped: list[dict] = []

    if not base_path.exists():
        logger.warning(f"Test QTI folder not found: {base_path}")
        return {
            "questions": {
                "to_create": to_create,
                "to_update": to_update,
                "unchanged": unchanged,
                "skipped": skipped,
            },
            "summary": {
                "create": 0,
                "update": 0,
                "unchanged": 0,
                "skipped": 0,
            },
        }

    # Get all Q* folders, sorted by question number
    q_folders = sorted(
        [f for f in base_path.iterdir() if f.is_dir() and f.name.startswith("Q")],
        key=lambda p: int(p.name[1:]) if p.name[1:].isdigit() else 0,
    )

    for q_folder in q_folders:
        question_num = q_folder.name
        question_id = f"{test_id}-{question_num}"

        try:
            q_num_int = int(question_num[1:])
        except ValueError:
            q_num_int = 0

        # Check validation status
        validation_path = q_folder / "validation_result.json"
        if not validation_path.exists():
            skipped.append({
                "question_id": question_id,
                "question_number": q_num_int,
                "status": "skipped",
                "reason": "not_enriched",
            })
            continue

        try:
            with open(validation_path, encoding="utf-8") as f:
                validation = json.load(f)
        except (json.JSONDecodeError, OSError):
            skipped.append({
                "question_id": question_id,
                "question_number": q_num_int,
                "status": "skipped",
                "reason": "validation_unreadable",
            })
            continue

        if not validation.get("can_sync"):
            skipped.append({
                "question_id": question_id,
                "question_number": q_num_int,
                "status": "skipped",
                "reason": "validation_failed",
            })
            continue

        # Get local QTI XML
        validated_xml_path = q_folder / "question_validated.xml"
        if not validated_xml_path.exists():
            skipped.append({
                "question_id": question_id,
                "question_number": q_num_int,
                "status": "skipped",
                "reason": "no_validated_xml",
            })
            continue

        try:
            local_qti = validated_xml_path.read_text(encoding="utf-8")
        except OSError:
            skipped.append({
                "question_id": question_id,
                "question_number": q_num_int,
                "status": "skipped",
                "reason": "xml_unreadable",
            })
            continue

        # Check if exists in DB (placeholder - would call actual DB client)
        db_question = _get_question_from_db(question_id)

        if db_question is None:
            to_create.append({
                "question_id": question_id,
                "question_number": q_num_int,
                "status": "create",
            })
        else:
            # Compare QTI XML
            db_qti = db_question.get("qti_xml", "")

            if _normalize_xml(local_qti) == _normalize_xml(db_qti):
                unchanged.append({
                    "question_id": question_id,
                    "question_number": q_num_int,
                    "status": "unchanged",
                })
            else:
                local_has_feedback = has_feedback(local_qti)
                db_has_feedback = has_feedback(db_qti)

                to_update.append({
                    "question_id": question_id,
                    "question_number": q_num_int,
                    "status": "update",
                    "changes": {
                        "qti_xml_changed": True,
                        "feedback_added": local_has_feedback and not db_has_feedback,
                        "feedback_changed": local_has_feedback and db_has_feedback,
                    },
                })

    return {
        "questions": {
            "to_create": to_create,
            "to_update": to_update,
            "unchanged": unchanged,
            "skipped": skipped,
        },
        "summary": {
            "create": len(to_create),
            "update": len(to_update),
            "unchanged": len(unchanged),
            "skipped": len(skipped),
        },
    }


def execute_sync(
    test_id: str,
    include_variants: bool = True,
    upload_images: bool = True,
) -> dict:
    """Execute sync to database.

    Args:
        test_id: The test ID to sync.
        include_variants: Whether to include variant questions (future use).
        upload_images: Whether to upload images to S3 (future use).

    Returns:
        Dict with counts and details of sync operations.
    """
    preview = get_sync_preview(test_id, include_variants)

    created = 0
    updated = 0
    details: list[dict] = []

    base_path = PRUEBAS_FINALIZADAS_DIR / test_id / "qti"

    # Process creates and updates
    questions_to_sync = (
        preview["questions"]["to_create"] + preview["questions"]["to_update"]
    )

    for q in questions_to_sync:
        question_id = q["question_id"]
        q_folder = base_path / f"Q{q['question_number']}"

        validated_xml_path = q_folder / "question_validated.xml"
        if not validated_xml_path.exists():
            details.append({
                "question_id": question_id,
                "action": "skipped",
                "reason": "xml_missing",
            })
            continue

        try:
            qti_xml = validated_xml_path.read_text(encoding="utf-8")
        except OSError:
            details.append({
                "question_id": question_id,
                "action": "skipped",
                "reason": "xml_unreadable",
            })
            continue

        # TODO: Upload images to S3 if upload_images=True

        # Upsert to database
        success = _upsert_question_to_db(question_id, qti_xml)

        if success:
            if q["status"] == "create":
                created += 1
                details.append({"question_id": question_id, "action": "created"})
            else:
                updated += 1
                details.append({"question_id": question_id, "action": "updated"})
        else:
            details.append({
                "question_id": question_id,
                "action": "failed",
                "reason": "db_error",
            })

    # Add skipped to details
    for q in preview["questions"]["skipped"]:
        details.append({
            "question_id": q["question_id"],
            "action": "skipped",
            "reason": q["reason"],
        })

    return {
        "created": created,
        "updated": updated,
        "skipped": len(preview["questions"]["skipped"]),
        "details": details,
    }


def _normalize_xml(xml: str) -> str:
    """Normalize XML for comparison (remove whitespace variations)."""
    # Remove extra whitespace between tags
    normalized = re.sub(r">\s+<", "><", xml)
    # Normalize line endings
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    # Strip
    return normalized.strip()


def _get_question_from_db(question_id: str) -> dict | None:
    """Get question from database by ID.

    Placeholder - would call actual DB client.
    Returns None if not found.
    """
    # TODO: Implement actual DB lookup
    # from app.sync.db_client import get_question_by_id
    # return get_question_by_id(question_id)
    logger.debug(f"DB lookup for {question_id} (placeholder - returning None)")
    return None


def _upsert_question_to_db(question_id: str, qti_xml: str) -> bool:
    """Upsert question to database.

    Placeholder - would call actual DB client.
    Returns True on success.
    """
    # TODO: Implement actual DB upsert
    # from app.sync.db_client import upsert_question
    # return upsert_question(question_id, qti_xml)
    logger.info(f"DB upsert for {question_id} (placeholder - returning True)")
    return True


def get_question_sync_status(
    test_id: str,
    question_num: int,
) -> str:
    """Get sync status for a single question.

    Returns one of:
    - "not_in_db": Question not yet in database
    - "in_sync": Local and DB versions match
    - "local_changed": Local version has changes
    - "not_validated": Cannot sync because validation failed/missing
    """
    q_folder = PRUEBAS_FINALIZADAS_DIR / test_id / "qti" / f"Q{question_num}"

    if not q_folder.exists():
        return "not_validated"

    # Check validation status
    validation_path = q_folder / "validation_result.json"
    if not validation_path.exists():
        return "not_validated"

    try:
        with open(validation_path, encoding="utf-8") as f:
            validation = json.load(f)
    except (json.JSONDecodeError, OSError):
        return "not_validated"

    if not validation.get("can_sync"):
        return "not_validated"

    # Get local QTI XML
    validated_xml_path = q_folder / "question_validated.xml"
    if not validated_xml_path.exists():
        return "not_validated"

    try:
        local_qti = validated_xml_path.read_text(encoding="utf-8")
    except OSError:
        return "not_validated"

    question_id = f"{test_id}-Q{question_num}"
    db_question = _get_question_from_db(question_id)

    if db_question is None:
        return "not_in_db"

    db_qti = db_question.get("qti_xml", "")
    if _normalize_xml(local_qti) == _normalize_xml(db_qti):
        return "in_sync"

    return "local_changed"
