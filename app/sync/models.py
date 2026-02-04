"""Database-compatible output models matching the Drizzle schema.

These models represent the final shape of data for DB insertion, aligned with
docs/data-model-specification.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

# -----------------------------------------------------------------------------
# Enums matching DB schema
# -----------------------------------------------------------------------------


class AtomType(str, Enum):
    """Matches atom_type enum in DB."""

    CONCEPTO = "concepto"
    PROCEDIMIENTO = "procedimiento"
    REPRESENTACION = "representacion"
    CONCEPTO_PROCEDIMENTAL = "concepto_procedimental"
    MODELIZACION = "modelizacion"
    ARGUMENTACION = "argumentacion"


class SkillType(str, Enum):
    """Matches skill_type enum in DB."""

    REPRESENTAR = "representar"
    RESOLVER_PROBLEMAS = "resolver_problemas"
    MODELAR = "modelar"
    ARGUMENTAR = "argumentar"


class QuestionSource(str, Enum):
    """Matches question_source enum in DB."""

    OFFICIAL = "official"
    ALTERNATE = "alternate"
    QUESTION_SET = "question_set"


class DifficultyLevel(str, Enum):
    """Matches difficulty_level enum in DB."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AtomRelevance(str, Enum):
    """Matches atom_relevance enum in DB."""

    PRIMARY = "primary"
    SECONDARY = "secondary"


class TestType(str, Enum):
    """Matches test_type enum in DB."""

    OFFICIAL = "official"
    DIAGNOSTIC = "diagnostic"
    PRACTICE = "practice"


# -----------------------------------------------------------------------------
# Data classes for DB rows
# -----------------------------------------------------------------------------


@dataclass
class StandardRow:
    """Represents a row in the standards table."""

    id: str
    subject_id: str
    axis: str
    unit: str | None
    title: str
    description: str | None = None
    includes: list[str] | None = None
    excludes: list[str] | None = None


@dataclass
class AtomRow:
    """Represents a row in the atoms table."""

    id: str
    subject_id: str
    axis: str
    standard_ids: list[str]
    atom_type: AtomType
    primary_skill: SkillType
    secondary_skills: list[SkillType]
    title: str
    description: str
    mastery_criteria: list[str]
    conceptual_examples: list[str] | None = None
    scope_notes: list[str] | None = None
    prerequisite_ids: list[str] | None = None


@dataclass
class QuestionRow:
    """Represents a row in the questions table.

    Note: correct_answer, title, and feedback are parsed directly from qti_xml
    rather than stored as separate fields.
    """

    id: str
    source: QuestionSource
    qti_xml: str
    difficulty_level: DifficultyLevel
    parent_question_id: str | None = None
    question_set_id: str | None = None
    difficulty_score: float | None = None
    source_test_id: str | None = None
    source_question_number: int | None = None


@dataclass
class QuestionAtomRow:
    """Represents a row in the question_atoms junction table."""

    question_id: str
    atom_id: str
    relevance: AtomRelevance
    reasoning: str | None = None


@dataclass
class TestRow:
    """Represents a row in the tests table."""

    id: str
    subject_id: str
    test_type: TestType
    name: str
    question_count: int
    description: str | None = None
    admission_year: int | None = None
    application_type: str | None = None
    time_limit_minutes: int | None = None
    is_adaptive: bool = False
    stages: int | None = None


@dataclass
class TestQuestionRow:
    """Represents a row in the test_questions junction table."""

    test_id: str
    question_id: str
    position: int
    stage: int = 1


# -----------------------------------------------------------------------------
# Aggregate container for full sync payload
# -----------------------------------------------------------------------------


@dataclass
class SyncPayload:
    """Container for all data to be synced to the database.

    Note: Subjects are master data managed separately and not synced from the content repo.
    """

    standards: list[StandardRow] = field(default_factory=list)
    atoms: list[AtomRow] = field(default_factory=list)
    questions: list[QuestionRow] = field(default_factory=list)
    question_atoms: list[QuestionAtomRow] = field(default_factory=list)
    tests: list[TestRow] = field(default_factory=list)
    test_questions: list[TestQuestionRow] = field(default_factory=list)

    def summary(self) -> dict[str, int]:
        """Return counts of each entity type."""
        return {
            "standards": len(self.standards),
            "atoms": len(self.atoms),
            "questions": len(self.questions),
            "question_atoms": len(self.question_atoms),
            "tests": len(self.tests),
            "test_questions": len(self.test_questions),
        }
