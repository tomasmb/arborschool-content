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
    SubjectRow,
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

    def upsert_subjects(self, cur: psycopg.Cursor, subjects: list[SubjectRow]) -> int:
        """Upsert subjects to the database.

        Args:
            cur: Database cursor
            subjects: List of SubjectRow to upsert

        Returns:
            Number of rows affected
        """
        if not subjects:
            return 0

        affected = 0
        for subject in subjects:
            data = self._row_to_dict(subject)
            cur.execute(
                """
                INSERT INTO subjects (id, name, short_name, description, admission_year, application_types)
                VALUES (%(id)s, %(name)s, %(short_name)s, %(description)s, %(admission_year)s, %(application_types)s)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    short_name = EXCLUDED.short_name,
                    description = EXCLUDED.description,
                    admission_year = EXCLUDED.admission_year,
                    application_types = EXCLUDED.application_types
                """,
                data,
            )
            affected += cur.rowcount

        return affected

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
    # Sync operations
    # -------------------------------------------------------------------------

    def sync_all(self, payload: SyncPayload, dry_run: bool = False) -> dict[str, int]:
        """Sync all data in the payload to the database.

        Executes upserts in dependency order within a single transaction.

        Args:
            payload: SyncPayload containing all data to sync
            dry_run: If True, rollback transaction instead of committing

        Returns:
            Dict mapping table name to number of rows affected
        """
        results: dict[str, int] = {}

        with self.connection() as conn:
            try:
                with self.transaction(conn) as cur:
                    # Upsert in dependency order
                    results["subjects"] = self.upsert_subjects(cur, payload.subjects)
                    results["standards"] = self.upsert_standards(cur, payload.standards)
                    results["atoms"] = self.upsert_atoms(cur, payload.atoms)
                    results["tests"] = self.upsert_tests(cur, payload.tests)
                    results["questions"] = self.upsert_questions(cur, payload.questions)
                    results["question_atoms"] = self.upsert_question_atoms(cur, payload.question_atoms)
                    results["test_questions"] = self.upsert_test_questions(cur, payload.test_questions)

                    if dry_run:
                        # Raise Rollback to abort the transaction cleanly
                        raise psycopg.Rollback()
            except psycopg.Rollback:
                # Expected in dry-run mode
                pass

        return results
