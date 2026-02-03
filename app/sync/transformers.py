"""Transform extracted data to database-compatible format.

This module maps the content repo's Spanish-named schema to the database's
English-named schema as defined in docs/data-model-specification.md.
"""

from __future__ import annotations

from .extractors import (
    ExtractedAtom,
    ExtractedQuestion,
    ExtractedStandard,
    ExtractedTest,
)
from .variant_extractors import ExtractedVariant
from .models import (
    AtomRelevance,
    AtomRow,
    AtomType,
    DifficultyLevel,
    QuestionAtomRow,
    QuestionRow,
    QuestionSource,
    SkillType,
    StandardRow,
    SyncPayload,
    TestQuestionRow,
    TestRow,
    TestType,
)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# Map Spanish eje names to English axis names (kept as-is per schema)
EJE_TO_AXIS = {
    "numeros": "numeros",
    "algebra_y_funciones": "algebra_y_funciones",
    "geometria": "geometria",
    "probabilidad_y_estadistica": "probabilidad_y_estadistica",
}

# Map Spanish habilidad to English skill
HABILIDAD_TO_SKILL: dict[str, SkillType] = {
    "representar": SkillType.REPRESENTAR,
    "resolver_problemas": SkillType.RESOLVER_PROBLEMAS,
    "modelar": SkillType.MODELAR,
    "argumentar": SkillType.ARGUMENTAR,
}

# Map Spanish tipo_atomico to AtomType enum
TIPO_TO_ATOM_TYPE: dict[str, AtomType] = {
    "concepto": AtomType.CONCEPTO,
    "procedimiento": AtomType.PROCEDIMIENTO,
    "representacion": AtomType.REPRESENTACION,
    "concepto_procedimental": AtomType.CONCEPTO_PROCEDIMENTAL,
    "modelizacion": AtomType.MODELIZACION,
    "argumentacion": AtomType.ARGUMENTACION,
}

# Map difficulty level strings to enum
DIFFICULTY_MAP: dict[str, DifficultyLevel] = {
    "low": DifficultyLevel.LOW,
    "medium": DifficultyLevel.MEDIUM,
    "high": DifficultyLevel.HIGH,
}

# -----------------------------------------------------------------------------
# Transform functions
# -----------------------------------------------------------------------------


def transform_standard(extracted: ExtractedStandard, subject_id: str = "paes_m1") -> StandardRow:
    """Transform an extracted standard to a database row.

    Args:
        extracted: ExtractedStandard from JSON
        subject_id: Subject identifier

    Returns:
        StandardRow ready for DB insertion
    """
    return StandardRow(
        id=extracted.id,
        subject_id=subject_id,
        axis=EJE_TO_AXIS.get(extracted.eje, extracted.eje),
        unit=extracted.unidad_temario,
        title=extracted.titulo,
        description=extracted.descripcion_general,
        includes=extracted.incluye if extracted.incluye else None,
        excludes=extracted.no_incluye if extracted.no_incluye else None,
    )


def transform_atom(extracted: ExtractedAtom, subject_id: str = "paes_m1") -> AtomRow:
    """Transform an extracted atom to a database row.

    Args:
        extracted: ExtractedAtom from JSON
        subject_id: Subject identifier

    Returns:
        AtomRow ready for DB insertion
    """
    # Transform habilidades
    primary_skill = HABILIDAD_TO_SKILL.get(extracted.habilidad_principal, SkillType.RESOLVER_PROBLEMAS)
    secondary_skills = [HABILIDAD_TO_SKILL[h] for h in extracted.habilidades_secundarias if h in HABILIDAD_TO_SKILL]

    # Transform tipo_atomico
    atom_type = TIPO_TO_ATOM_TYPE.get(extracted.tipo_atomico, AtomType.CONCEPTO)

    return AtomRow(
        id=extracted.id,
        subject_id=subject_id,
        axis=EJE_TO_AXIS.get(extracted.eje, extracted.eje),
        standard_ids=extracted.standard_ids,
        atom_type=atom_type,
        primary_skill=primary_skill,
        secondary_skills=secondary_skills,
        title=extracted.titulo,
        description=extracted.descripcion,
        mastery_criteria=extracted.criterios_atomicos,
        conceptual_examples=extracted.ejemplos_conceptuales if extracted.ejemplos_conceptuales else None,
        scope_notes=extracted.notas_alcance if extracted.notas_alcance else None,
        prerequisite_ids=extracted.prerrequisitos if extracted.prerrequisitos else None,
    )


def transform_question(
    extracted: ExtractedQuestion,
    source: QuestionSource = QuestionSource.OFFICIAL,
) -> tuple[QuestionRow, list[QuestionAtomRow]]:
    """Transform an extracted question to database rows.

    Args:
        extracted: ExtractedQuestion from QTI/JSON
        source: Question source type

    Returns:
        Tuple of (QuestionRow, list of QuestionAtomRow)
    """
    # Parse difficulty level
    difficulty = DIFFICULTY_MAP.get(extracted.difficulty_level or "medium", DifficultyLevel.MEDIUM)

    question_row = QuestionRow(
        id=extracted.id,
        source=source,
        qti_xml=extracted.qti_xml,
        correct_answer=extracted.correct_answer,
        difficulty_level=difficulty,
        title=extracted.title,
        difficulty_score=extracted.difficulty_score,
        difficulty_analysis=extracted.difficulty_analysis,
        general_analysis=extracted.general_analysis,
        feedback_general=extracted.feedback_general,
        feedback_per_option=extracted.feedback_per_option,
        source_test_id=extracted.test_id,
        source_question_number=extracted.question_number,
    )

    # Create question-atom relationships
    question_atoms: list[QuestionAtomRow] = []
    for atom_data in extracted.atoms:
        if not atom_data.get("atom_id"):
            continue

        relevance_str = atom_data.get("relevance", "primary").lower()
        relevance = AtomRelevance.PRIMARY if relevance_str == "primary" else AtomRelevance.SECONDARY

        question_atoms.append(
            QuestionAtomRow(
                question_id=extracted.id,
                atom_id=atom_data["atom_id"],
                relevance=relevance,
                reasoning=atom_data.get("reasoning"),
            )
        )

    return question_row, question_atoms


def transform_test(
    extracted: ExtractedTest,
    subject_id: str = "paes_m1",
) -> tuple[TestRow, list[TestQuestionRow]]:
    """Transform an extracted test to database rows.

    Args:
        extracted: ExtractedTest from pruebas/finalizadas
        subject_id: Subject identifier

    Returns:
        Tuple of (TestRow, list of TestQuestionRow)
    """
    test_row = TestRow(
        id=extracted.id,
        subject_id=subject_id,
        test_type=TestType.OFFICIAL,
        name=extracted.name,
        question_count=len(extracted.question_ids),
        admission_year=extracted.admission_year,
        application_type=extracted.application_type,
        time_limit_minutes=150,  # Standard PAES time
    )

    # Create test-question relationships with positions
    test_questions: list[TestQuestionRow] = []
    for position, question_id in enumerate(extracted.question_ids, start=1):
        test_questions.append(
            TestQuestionRow(
                test_id=extracted.id,
                question_id=question_id,
                position=position,
            )
        )

    return test_row, test_questions


def transform_variant(extracted: ExtractedVariant) -> QuestionRow:
    """Transform an extracted variant to a database row.

    Variants are stored as questions with source=ALTERNATE and parent_question_id set.
    They inherit atom associations from their parent question via parent_question_id,
    so no separate question_atoms rows are created for variants.

    Args:
        extracted: ExtractedVariant from alternativas/

    Returns:
        QuestionRow ready for DB insertion (no question_atoms - inherited from parent)
    """
    difficulty = DIFFICULTY_MAP.get(
        extracted.difficulty_level or "medium", DifficultyLevel.MEDIUM
    )

    return QuestionRow(
        id=extracted.id,
        source=QuestionSource.ALTERNATE,
        parent_question_id=extracted.parent_question_id,
        qti_xml=extracted.qti_xml,
        correct_answer=extracted.correct_answer,
        difficulty_level=difficulty,
        title=f"Variant of Q{extracted.source_question_number}",
        difficulty_score=extracted.difficulty_score,
        difficulty_analysis=extracted.difficulty_analysis,
        general_analysis=extracted.general_analysis,
        feedback_general=extracted.feedback_general,
        feedback_per_option=extracted.feedback_per_option,
        source_test_id=extracted.source_test_id,
        source_question_number=extracted.source_question_number,
    )


def build_sync_payload(
    standards: list[ExtractedStandard],
    atoms: list[ExtractedAtom],
    tests: list[ExtractedTest],
    questions: list[ExtractedQuestion],
    variants: list[ExtractedVariant] | None = None,
    subject_id: str = "paes_m1",
) -> SyncPayload:
    """Build a complete sync payload from all extracted data.

    Args:
        standards: List of extracted standards
        atoms: List of extracted atoms
        tests: List of extracted tests
        questions: List of extracted questions
        variants: List of extracted variants (optional)
        subject_id: Subject identifier

    Returns:
        SyncPayload containing all transformed data
    """
    payload = SyncPayload()

    # Note: Subjects are master data managed separately - not synced from content repo.
    # The subject (e.g., "paes_m1") must already exist in the database.

    # Transform standards
    for std in standards:
        payload.standards.append(transform_standard(std, subject_id))

    # Transform atoms
    for atom in atoms:
        payload.atoms.append(transform_atom(atom, subject_id))

    # Transform questions and their atom relationships
    for q in questions:
        q_row, q_atoms = transform_question(q)
        payload.questions.append(q_row)
        payload.question_atoms.extend(q_atoms)

    # Transform variants (alternate questions)
    # Note: Variants inherit atom associations from their parent via parent_question_id,
    # so no question_atoms rows are created for them.
    if variants:
        for v in variants:
            payload.questions.append(transform_variant(v))

    # Transform tests and their question relationships
    for test in tests:
        t_row, t_questions = transform_test(test, subject_id)
        payload.tests.append(t_row)
        payload.test_questions.extend(t_questions)

    return payload
