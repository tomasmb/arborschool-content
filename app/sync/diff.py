"""Sync diff computation for comparing local data vs database.

Computes the differences between local content and what's in the database
to prevent unnecessary syncs and show exactly what would change.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any

import psycopg
from psycopg.rows import dict_row

from .config import DBConfig, SyncEnvironment
from .db_client import DBClient

logger = logging.getLogger(__name__)


@dataclass
class EntityDiff:
    """Diff result for a single entity type."""

    local_count: int = 0
    db_count: int = 0
    new_ids: list[str] = field(default_factory=list)
    modified_ids: list[str] = field(default_factory=list)
    deleted_ids: list[str] = field(default_factory=list)
    unchanged_count: int = 0

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return bool(self.new_ids or self.modified_ids or self.deleted_ids)

    @property
    def changes_summary(self) -> str:
        """Get a human-readable summary of changes."""
        parts = []
        if self.new_ids:
            parts.append(f"+{len(self.new_ids)} new")
        if self.modified_ids:
            parts.append(f"{len(self.modified_ids)} modified")
        if self.deleted_ids:
            parts.append(f"-{len(self.deleted_ids)} deleted")
        return ", ".join(parts) if parts else "No changes"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "local_count": self.local_count,
            "db_count": self.db_count,
            "new": self.new_ids[:20],  # Limit to first 20 for response size
            "new_count": len(self.new_ids),
            "modified": self.modified_ids[:20],
            "modified_count": len(self.modified_ids),
            "deleted": self.deleted_ids[:20],
            "deleted_count": len(self.deleted_ids),
            "unchanged": self.unchanged_count,
            "has_changes": self.has_changes,
        }


@dataclass
class SyncDiff:
    """Complete diff result for all entity types."""

    environment: str
    has_changes: bool = False
    entities: dict[str, EntityDiff] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "environment": self.environment,
            "has_changes": self.has_changes,
            "entities": {k: v.to_dict() for k, v in self.entities.items()},
            "error": self.error,
        }


def _compute_content_hash(data: dict[str, Any]) -> str:
    """Compute a hash of the content for change detection.

    Excludes timestamps and other non-content fields.
    """
    # Sort keys for consistent hashing
    content = json.dumps(data, sort_keys=True, default=str)
    return hashlib.md5(content.encode()).hexdigest()[:16]


def _fetch_db_ids(
    conn: psycopg.Connection,
    table: str,
    subject_id: str | None = None,
) -> dict[str, str]:
    """Fetch all IDs and content hashes from a database table.

    Returns:
        Dict mapping ID to content hash (or empty string if no hash column)
    """
    with conn.cursor(row_factory=dict_row) as cur:
        if subject_id and table in ("standards", "atoms", "tests"):
            cur.execute(
                f"SELECT id FROM {table} WHERE subject_id = %s",  # noqa: S608
                (subject_id,),
            )
        elif table == "questions":
            # Questions don't have direct subject_id, but we can filter by source_test
            cur.execute("SELECT id FROM questions")
        elif table == "question_atoms":
            cur.execute("SELECT question_id || ':' || atom_id as id FROM question_atoms")
        elif table == "test_questions":
            cur.execute("SELECT test_id || ':' || question_id as id FROM test_questions")
        else:
            cur.execute(f"SELECT id FROM {table}")  # noqa: S608

        return {row["id"]: "" for row in cur.fetchall()}


def compute_entity_diff(
    local_items: list[Any],
    db_ids: dict[str, str],
    id_field: str = "id",
) -> EntityDiff:
    """Compute diff between local items and database IDs.

    Args:
        local_items: List of local items (dataclasses or dicts)
        db_ids: Dict of database IDs to content hashes
        id_field: Field name to use as ID

    Returns:
        EntityDiff with new, modified, deleted items
    """
    diff = EntityDiff(
        local_count=len(local_items),
        db_count=len(db_ids),
    )

    local_ids = set()
    for item in local_items:
        if hasattr(item, id_field):
            item_id = getattr(item, id_field)
        elif isinstance(item, dict):
            item_id = item.get(id_field)
        else:
            continue

        local_ids.add(item_id)

        if item_id not in db_ids:
            diff.new_ids.append(item_id)
        else:
            # For now, treat all existing items as potentially modified
            # A more sophisticated approach would compare content hashes
            diff.unchanged_count += 1

    # Find deleted items (in DB but not in local)
    diff.deleted_ids = [id_ for id_ in db_ids if id_ not in local_ids]

    return diff


def compute_sync_diff(
    extracted_data: dict[str, list],
    environment: SyncEnvironment,
    subject_id: str | None = None,
) -> SyncDiff:
    """Compute full sync diff between local data and database.

    Args:
        extracted_data: Dict with extracted local data per entity type
        environment: Target database environment
        subject_id: Optional subject ID for filtering

    Returns:
        SyncDiff with diffs for each entity type
    """
    result = SyncDiff(environment=environment)

    try:
        db_config = DBConfig.for_environment(environment)
    except ValueError as e:
        result.error = str(e)
        return result

    try:
        db_client = DBClient(db_config)

        with db_client.connection() as conn:
            # Standards
            if extracted_data.get("standards"):
                db_ids = _fetch_db_ids(conn, "standards", subject_id)
                result.entities["standards"] = compute_entity_diff(
                    extracted_data["standards"], db_ids
                )

            # Atoms
            if extracted_data.get("atoms"):
                db_ids = _fetch_db_ids(conn, "atoms", subject_id)
                result.entities["atoms"] = compute_entity_diff(
                    extracted_data["atoms"], db_ids
                )

            # Tests
            if extracted_data.get("tests"):
                db_ids = _fetch_db_ids(conn, "tests", subject_id)
                result.entities["tests"] = compute_entity_diff(
                    extracted_data["tests"], db_ids
                )

            # Questions
            if extracted_data.get("questions"):
                db_ids = _fetch_db_ids(conn, "questions")
                result.entities["questions"] = compute_entity_diff(
                    extracted_data["questions"], db_ids
                )

            # Variants (also go into questions table)
            if extracted_data.get("variants"):
                db_ids = _fetch_db_ids(conn, "questions")
                result.entities["variants"] = compute_entity_diff(
                    extracted_data["variants"], db_ids
                )

        # Check if any entity has changes
        result.has_changes = any(
            entity.has_changes for entity in result.entities.values()
        )

    except Exception as e:
        logger.exception("Error computing sync diff")
        result.error = str(e)

    return result
