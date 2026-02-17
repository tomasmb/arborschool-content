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

    Fields like title, correct_answer, and feedback are populated by the
    enrichment pipeline. They default to None until enrichment runs.
    """

    id: str
    source: QuestionSource
    qti_xml: str
    difficulty_level: DifficultyLevel
    parent_question_id: str | None = None
    difficulty_score: float | None = None
    source_test_id: str | None = None
    source_question_number: int | None = None
    # Fields populated by enrichment / metadata extraction
    title: str | None = None
    correct_answer: str | None = None
    difficulty_analysis: str | None = None
    general_analysis: str | None = None
    feedback_general: str | None = None
    feedback_per_option: dict | None = None


@dataclass
class QuestionAtomRow:
    """Represents a row in the question_atoms junction table."""

    question_id: str
    atom_id: str
    relevance: AtomRelevance
    reasoning: str | None = None


@dataclass
class GeneratedQuestionRow:
    """Represents a row in the generated_questions table.

    Pipeline-generated questions live in a separate table from
    official/alternate questions. Linked to atoms directly via
    atom_id (no junction table needed).
    """

    id: str
    atom_id: str
    qti_xml: str
    difficulty_level: str  # "low", "medium", "high"
    component_tag: str
    operation_skeleton_ast: str
    surface_context: str = "pure_math"
    numbers_profile: str = "small_integers"
    fingerprint: str = ""
    validators: str = "{}"  # JSON string of validator reports
    target_exemplar_id: str | None = None
    distance_level: str | None = None


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

    Note: Subjects are master data managed separately and not synced
    from the content repo.
    """

    standards: list[StandardRow] = field(default_factory=list)
    atoms: list[AtomRow] = field(default_factory=list)
    questions: list[QuestionRow] = field(default_factory=list)
    question_atoms: list[QuestionAtomRow] = field(default_factory=list)
    generated_questions: list[GeneratedQuestionRow] = field(
        default_factory=list,
    )
    tests: list[TestRow] = field(default_factory=list)
    test_questions: list[TestQuestionRow] = field(default_factory=list)

    def summary(self) -> dict[str, int]:
        """Return counts of each entity type."""
        return {
            "standards": len(self.standards),
            "atoms": len(self.atoms),
            "questions": len(self.questions),
            "question_atoms": len(self.question_atoms),
            "generated_questions": len(self.generated_questions),
            "tests": len(self.tests),
            "test_questions": len(self.test_questions),
        }

    def filter_for_entities(self, entities: list[str]) -> None:
        """Remove data for entity types not in the requested list.

        This allows extracting all data (e.g. questions for deriving
        question_atoms) but only syncing the requested tables.

        Mapping from entity request → tables kept:
          "standards"             → standards
          "atoms"                 → atoms
          "questions"             → questions (content)
          "question_atoms"        → question_atoms (links only)
          "generated_questions"   → generated_questions
          "tests"                 → tests, test_questions
          "variants"              → (already in questions list)
        """
        if "standards" not in entities:
            self.standards = []
        if "atoms" not in entities:
            self.atoms = []
        if "questions" not in entities and "variants" not in entities:
            self.questions = []
        if "question_atoms" not in entities and "questions" not in entities:
            self.question_atoms = []
        if "generated_questions" not in entities:
            self.generated_questions = []
        if "tests" not in entities:
            self.tests = []
            self.test_questions = []
