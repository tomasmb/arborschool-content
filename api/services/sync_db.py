"""Database helpers for test-level sync operations.

Provides environment-aware DB connections and query functions
used by sync_service.py.
"""

from __future__ import annotations

import logging

import psycopg
from psycopg.rows import dict_row

from app.sync.config import DBConfig, SyncEnvironment

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Connection
# -----------------------------------------------------------------------------


def get_db_connection(environment: SyncEnvironment) -> psycopg.Connection | None:
    """Open a DB connection for the given environment.

    Returns None if the environment is not configured or on error.
    """
    if not DBConfig.check_environment_configured(environment):
        return None

    try:
        config = DBConfig.for_environment(environment)
        return psycopg.connect(config.connection_string, row_factory=dict_row)
    except Exception:
        logger.exception("Failed to connect to %s DB", environment)
        return None


# -----------------------------------------------------------------------------
# Query functions
# -----------------------------------------------------------------------------


def fetch_questions_by_ids(
    conn: psycopg.Connection,
    question_ids: list[str],
) -> dict[str, dict]:
    """Fetch multiple questions from DB by their IDs.

    Returns dict mapping question_id -> {id, qti_xml}.
    """
    if not question_ids:
        return {}

    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, qti_xml FROM questions WHERE id = ANY(%s)",
            (question_ids,),
        )
        return {row["id"]: dict(row) for row in cur.fetchall()}


def fetch_test_question_ids(
    conn: psycopg.Connection,
    test_id: str,
) -> dict[str, str]:
    """Fetch original question IDs for a test (no variants).

    Returns dict mapping question_id -> '' (for compatibility with diff).
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM questions "
            "WHERE source_test_id = %s "
            "AND parent_question_id IS NULL",
            (test_id,),
        )
        return {row["id"]: "" for row in cur.fetchall()}


def fetch_test_variant_ids(
    conn: psycopg.Connection,
    test_id: str,
) -> dict[str, str]:
    """Fetch variant IDs for a test's questions.

    Returns dict mapping variant_id -> ''.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM questions "
            "WHERE source_test_id = %s "
            "AND parent_question_id IS NOT NULL",
            (test_id,),
        )
        return {row["id"]: "" for row in cur.fetchall()}


def batch_fetch_from_db(
    environment: SyncEnvironment,
    ids: list[str],
) -> dict[str, dict]:
    """Batch-fetch questions/variants from DB by ID list.

    Returns empty dict if DB is not configured or on error.
    """
    if not ids:
        return {}

    conn = get_db_connection(environment)
    if conn is None:
        return {}

    try:
        return fetch_questions_by_ids(conn, ids)
    except Exception:
        logger.exception("Error batch-fetching from DB")
        return {}
    finally:
        conn.close()


def upsert_question_qti(
    question_id: str,
    qti_xml: str,
    environment: SyncEnvironment = "local",
) -> bool:
    """Upsert a single question's QTI XML to database.

    Returns True on success.
    """
    conn = get_db_connection(environment)
    if conn is None:
        logger.error("Cannot upsert %s: DB not configured", question_id)
        return False

    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE questions SET qti_xml = %s WHERE id = %s",
                (qti_xml, question_id),
            )
            conn.commit()
        return True
    except Exception:
        logger.exception("Error upserting question %s", question_id)
        return False
    finally:
        conn.close()
