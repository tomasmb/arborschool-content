"""Database client for upserting content to Postgres.

Uses psycopg3 for modern, type-safe database operations with proper
connection pooling and transaction management.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import asdict
from enum import Enum
from typing import Any, Generator

import psycopg
from psycopg.rows import dict_row

from .config import DBConfig, SyncEnvironment
from .models import (
    AtomRow,
    QuestionAtomRow,
    QuestionRow,
    StandardRow,
    SyncPayload,
    TestQuestionRow,
    TestRow,
)

# Re-export for backwards compatibility
__all__ = ["DBClient", "DBConfig", "SyncEnvironment"]


# -----------------------------------------------------------------------------
# Database Client
# -----------------------------------------------------------------------------


class DBClient:
    """Database client for syncing content to Postgres."""

    def __init__(self, config: DBConfig):
        """Initialize with database configuration.

        Args:
            config: Database connection configuration
        """
        self.config = config
        self._conn: psycopg.Connection | None = None

    @contextmanager
    def connection(self) -> Generator[psycopg.Connection, None, None]:
        """Get a database connection with automatic cleanup.

        Yields:
            Active database connection
        """
        # Timeout is configured in the connection string (see config.py)
        conn = psycopg.connect(self.config.connection_string, row_factory=dict_row)
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaction(self, conn: psycopg.Connection) -> Generator[psycopg.Cursor, None, None]:
        """Execute operations within a transaction.

        Args:
            conn: Database connection

        Yields:
            Database cursor
        """
        with conn.transaction():
            with conn.cursor() as cur:
                yield cur

    # -------------------------------------------------------------------------
    # Schema management
    # -------------------------------------------------------------------------

    def ensure_schema(self, conn: psycopg.Connection) -> None:
        """Ensure all required columns exist on synced tables.

        Uses ADD COLUMN IF NOT EXISTS so this is safe to call repeatedly.
        Runs outside the main transaction so schema changes are committed
        before the data upsert transaction begins.
        """
        with conn.cursor() as cur:
            # Columns added after the initial questions table was created.
            # All nullable since they are populated by enrichment pipeline.
            for col, col_type in (
                ("title", "VARCHAR(255)"),
                ("correct_answer", "VARCHAR(50)"),
                ("difficulty_analysis", "TEXT"),
                ("general_analysis", "TEXT"),
                ("feedback_general", "TEXT"),
                ("feedback_per_option", "JSONB"),
            ):
                cur.execute(
                    "ALTER TABLE questions "
                    f"ADD COLUMN IF NOT EXISTS {col} {col_type}"
                )
            conn.commit()

    # -------------------------------------------------------------------------
    # Helper methods
    # -------------------------------------------------------------------------

    def _serialize_value(self, value: Any) -> Any:
        """Serialize Python values for Postgres insertion."""
        if value is None:
            return None
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, list):
            # For arrays of enums or strings
            return [v.value if isinstance(v, Enum) else v for v in value]
        if isinstance(value, dict):
            return json.dumps(value)
        return value

    def _row_to_dict(self, row: Any) -> dict[str, Any]:
        """Convert a dataclass row to a dict with serialized values."""
        if hasattr(row, "__dataclass_fields__"):
            return {k: self._serialize_value(v) for k, v in asdict(row).items()}
        return dict(row)

    # -------------------------------------------------------------------------
    # Upsert operations
    # -------------------------------------------------------------------------

    def upsert_standards(self, cur: psycopg.Cursor, standards: list[StandardRow]) -> int:
        """Upsert standards to the database.

        Args:
            cur: Database cursor
            standards: List of StandardRow to upsert

        Returns:
            Number of rows affected
        """
        if not standards:
            return 0

        affected = 0
        for std in standards:
            data = self._row_to_dict(std)
            # Convert lists to JSONB for includes/excludes
            if data.get("includes"):
                data["includes"] = json.dumps(data["includes"])
            if data.get("excludes"):
                data["excludes"] = json.dumps(data["excludes"])

            cur.execute(
                """
                INSERT INTO standards (id, subject_id, axis, unit, title, description, includes, excludes)
                VALUES (%(id)s, %(subject_id)s, %(axis)s, %(unit)s, %(title)s, %(description)s,
                        %(includes)s::jsonb, %(excludes)s::jsonb)
                ON CONFLICT (id) DO UPDATE SET
                    subject_id = EXCLUDED.subject_id,
                    axis = EXCLUDED.axis,
                    unit = EXCLUDED.unit,
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    includes = EXCLUDED.includes,
                    excludes = EXCLUDED.excludes
                """,
                data,
            )
            affected += cur.rowcount

        return affected

    def upsert_atoms(self, cur: psycopg.Cursor, atoms: list[AtomRow]) -> int:
        """Upsert atoms to the database.

        Args:
            cur: Database cursor
            atoms: List of AtomRow to upsert

        Returns:
            Number of rows affected
        """
        if not atoms:
            return 0

        affected = 0
        for atom in atoms:
            data = self._row_to_dict(atom)
            # Convert to JSONB where needed
            data["mastery_criteria"] = json.dumps(data["mastery_criteria"])
            if data.get("conceptual_examples"):
                data["conceptual_examples"] = json.dumps(data["conceptual_examples"])
            if data.get("scope_notes"):
                data["scope_notes"] = json.dumps(data["scope_notes"])

            cur.execute(
                """
                INSERT INTO atoms (
                    id, subject_id, axis, standard_ids, atom_type, primary_skill,
                    secondary_skills, title, description, mastery_criteria,
                    conceptual_examples, scope_notes, prerequisite_ids
                )
                VALUES (
                    %(id)s, %(subject_id)s, %(axis)s, %(standard_ids)s, %(atom_type)s, %(primary_skill)s,
                    %(secondary_skills)s::skill_type[], %(title)s, %(description)s, %(mastery_criteria)s::jsonb,
                    %(conceptual_examples)s::jsonb, %(scope_notes)s::jsonb, %(prerequisite_ids)s
                )
                ON CONFLICT (id) DO UPDATE SET
                    subject_id = EXCLUDED.subject_id,
                    axis = EXCLUDED.axis,
                    standard_ids = EXCLUDED.standard_ids,
                    atom_type = EXCLUDED.atom_type,
                    primary_skill = EXCLUDED.primary_skill,
                    secondary_skills = EXCLUDED.secondary_skills,
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    mastery_criteria = EXCLUDED.mastery_criteria,
                    conceptual_examples = EXCLUDED.conceptual_examples,
                    scope_notes = EXCLUDED.scope_notes,
                    prerequisite_ids = EXCLUDED.prerequisite_ids
                """,
                data,
            )
            affected += cur.rowcount

        return affected

    def upsert_questions(self, cur: psycopg.Cursor, questions: list[QuestionRow]) -> int:
        """Upsert questions to the database.

        Args:
            cur: Database cursor
            questions: List of QuestionRow to upsert

        Returns:
            Number of rows affected
        """
        if not questions:
            return 0

        affected = 0
        for q in questions:
            data = self._row_to_dict(q)
            # Convert feedback_per_option to JSONB
            if data.get("feedback_per_option"):
                data["feedback_per_option"] = json.dumps(data["feedback_per_option"])

            cur.execute(
                """
                INSERT INTO questions (
                    id, source, parent_question_id, question_set_id, qti_xml, title,
                    correct_answer, difficulty_level, difficulty_score, difficulty_analysis,
                    general_analysis, feedback_general, feedback_per_option,
                    source_test_id, source_question_number
                )
                VALUES (
                    %(id)s, %(source)s, %(parent_question_id)s, %(question_set_id)s, %(qti_xml)s, %(title)s,
                    %(correct_answer)s, %(difficulty_level)s, %(difficulty_score)s, %(difficulty_analysis)s,
                    %(general_analysis)s, %(feedback_general)s, %(feedback_per_option)s::jsonb,
                    %(source_test_id)s, %(source_question_number)s
                )
                ON CONFLICT (id) DO UPDATE SET
                    source = EXCLUDED.source,
                    parent_question_id = EXCLUDED.parent_question_id,
                    question_set_id = EXCLUDED.question_set_id,
                    qti_xml = EXCLUDED.qti_xml,
                    title = EXCLUDED.title,
                    correct_answer = EXCLUDED.correct_answer,
                    difficulty_level = EXCLUDED.difficulty_level,
                    difficulty_score = EXCLUDED.difficulty_score,
                    difficulty_analysis = EXCLUDED.difficulty_analysis,
                    general_analysis = EXCLUDED.general_analysis,
                    feedback_general = EXCLUDED.feedback_general,
                    feedback_per_option = EXCLUDED.feedback_per_option,
                    source_test_id = EXCLUDED.source_test_id,
                    source_question_number = EXCLUDED.source_question_number
                """,
                data,
            )
            affected += cur.rowcount

        return affected

    def upsert_question_atoms(self, cur: psycopg.Cursor, question_atoms: list[QuestionAtomRow]) -> int:
        """Upsert question-atom relationships to the database.

        Args:
            cur: Database cursor
            question_atoms: List of QuestionAtomRow to upsert

        Returns:
            Number of rows affected
        """
        if not question_atoms:
            return 0

        affected = 0
        for qa in question_atoms:
            data = self._row_to_dict(qa)
            cur.execute(
                """
                INSERT INTO question_atoms (question_id, atom_id, relevance, reasoning)
                VALUES (%(question_id)s, %(atom_id)s, %(relevance)s, %(reasoning)s)
                ON CONFLICT (question_id, atom_id) DO UPDATE SET
                    relevance = EXCLUDED.relevance,
                    reasoning = EXCLUDED.reasoning
                """,
                data,
            )
            affected += cur.rowcount

        return affected

    def upsert_tests(self, cur: psycopg.Cursor, tests: list[TestRow]) -> int:
        """Upsert tests to the database.

        Args:
            cur: Database cursor
            tests: List of TestRow to upsert

        Returns:
            Number of rows affected
        """
        if not tests:
            return 0

        affected = 0
        for test in tests:
            data = self._row_to_dict(test)
            cur.execute(
                """
                INSERT INTO tests (
                    id, subject_id, test_type, name, description, admission_year,
                    application_type, question_count, time_limit_minutes, is_adaptive, stages
                )
                VALUES (
                    %(id)s, %(subject_id)s, %(test_type)s, %(name)s, %(description)s, %(admission_year)s,
                    %(application_type)s, %(question_count)s, %(time_limit_minutes)s, %(is_adaptive)s, %(stages)s
                )
                ON CONFLICT (id) DO UPDATE SET
                    subject_id = EXCLUDED.subject_id,
                    test_type = EXCLUDED.test_type,
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    admission_year = EXCLUDED.admission_year,
                    application_type = EXCLUDED.application_type,
                    question_count = EXCLUDED.question_count,
                    time_limit_minutes = EXCLUDED.time_limit_minutes,
                    is_adaptive = EXCLUDED.is_adaptive,
                    stages = EXCLUDED.stages
                """,
                data,
            )
            affected += cur.rowcount

        return affected

    def upsert_test_questions(self, cur: psycopg.Cursor, test_questions: list[TestQuestionRow]) -> int:
        """Upsert test-question relationships to the database.

        Args:
            cur: Database cursor
            test_questions: List of TestQuestionRow to upsert

        Returns:
            Number of rows affected
        """
        if not test_questions:
            return 0

        affected = 0
        for tq in test_questions:
            data = self._row_to_dict(tq)
            cur.execute(
                """
                INSERT INTO test_questions (test_id, question_id, position, stage)
                VALUES (%(test_id)s, %(question_id)s, %(position)s, %(stage)s)
                ON CONFLICT (test_id, question_id) DO UPDATE SET
                    position = EXCLUDED.position,
                    stage = EXCLUDED.stage
                """,
                data,
            )
            affected += cur.rowcount

        return affected

    # -------------------------------------------------------------------------
    # Deletion operations
    # -------------------------------------------------------------------------

    def delete_atoms(
        self, cur: psycopg.Cursor, atom_ids: list[str],
    ) -> int:
        """Delete atoms by ID, cascading to all referencing tables first."""
        if not atom_ids:
            return 0
        # Delete from all tables that reference atoms via FK
        for fk_table in (
            "question_atoms", "atom_mastery", "lessons", "question_sets",
        ):
            cur.execute(
                f"DELETE FROM {fk_table} WHERE atom_id = ANY(%s)",  # noqa: S608
                (atom_ids,),
            )
        cur.execute("DELETE FROM atoms WHERE id = ANY(%s)", (atom_ids,))
        return cur.rowcount

    def delete_question_atoms(
        self, cur: psycopg.Cursor, composite_ids: list[str],
    ) -> int:
        """Delete question_atom rows by 'question_id:atom_id' keys."""
        if not composite_ids:
            return 0
        pairs = [cid.split(":", 1) for cid in composite_ids]
        affected = 0
        for qid, aid in pairs:
            cur.execute(
                "DELETE FROM question_atoms "
                "WHERE question_id = %s AND atom_id = %s",
                (qid, aid),
            )
            affected += cur.rowcount
        return affected

    # -------------------------------------------------------------------------
    # Sync operations
    # -------------------------------------------------------------------------

    def sync_all(
        self,
        payload: SyncPayload,
        dry_run: bool = False,
        deletions: dict[str, list[str]] | None = None,
    ) -> dict[str, int]:
        """Sync all data: upserts in dependency order, then deletes stale rows.

        Args:
            payload: Data to upsert
            dry_run: If True, rollback instead of committing
            deletions: Table name → list of IDs to delete
                (supports 'atoms', 'question_atoms')
        """
        results: dict[str, int] = {}
        deletions = deletions or {}

        with self.connection() as conn:
            self.ensure_schema(conn)
            try:
                with self.transaction(conn) as cur:
                    results["standards"] = self.upsert_standards(cur, payload.standards)
                    results["atoms"] = self.upsert_atoms(cur, payload.atoms)
                    results["tests"] = self.upsert_tests(cur, payload.tests)
                    results["questions"] = self.upsert_questions(cur, payload.questions)
                    results["question_atoms"] = self.upsert_question_atoms(cur, payload.question_atoms)
                    results["test_questions"] = self.upsert_test_questions(cur, payload.test_questions)
                    # Delete stale rows (reverse dependency order)
                    results["deleted_question_atoms"] = self.delete_question_atoms(
                        cur, deletions.get("question_atoms", []),
                    )
                    results["deleted_atoms"] = self.delete_atoms(
                        cur, deletions.get("atoms", []),
                    )
                    if dry_run:
                        raise psycopg.Rollback()
            except psycopg.Rollback:
                pass

        return results
