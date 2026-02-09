"""Extract data from content repo JSON/XML files.

This module reads the canonical data files and returns structured data ready
for transformation to DB schema.

For variant extraction, see variant_extractors.py.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.utils.paths import (
    ATOMS_DIR,
    PRUEBAS_FINALIZADAS_DIR,
    STANDARDS_DIR,
)

# -----------------------------------------------------------------------------
# Extracted data containers (intermediate format before transform)
# -----------------------------------------------------------------------------


@dataclass
class ExtractedAtom:
    """Raw atom data extracted from JSON."""

    id: str
    eje: str
    standard_ids: list[str]
    habilidad_principal: str
    habilidades_secundarias: list[str]
    tipo_atomico: str
    titulo: str
    descripcion: str
    criterios_atomicos: list[str]
    ejemplos_conceptuales: list[str]
    prerrequisitos: list[str]
    notas_alcance: list[str]
    en_alcance_m1: bool


@dataclass
class ExtractedStandard:
    """Raw standard data extracted from JSON."""

    id: str
    eje: str
    unidad_temario: str
    titulo: str
    descripcion_general: str
    incluye: list[str]
    no_incluye: list[str]


@dataclass
class ExtractedQuestion:
    """Raw question data extracted from QTI XML and metadata JSON.

    Fields like title, correct_answer, and feedback are populated by the
    enrichment pipeline. They default to None until enrichment runs.
    """

    id: str
    test_id: str
    question_number: int
    qti_xml: str
    # From metadata_tags.json
    atoms: list[dict[str, Any]]  # List of {atom_id, relevance, reasoning}
    difficulty_level: str | None
    difficulty_score: float | None
    # Image paths found in QTI
    image_paths: list[str]
    # From metadata (analysis fields, populated if present)
    general_analysis: str | None = None
    difficulty_analysis: str | None = None
    # From enrichment (populated later by enrichment pipeline)
    title: str | None = None
    correct_answer: str | None = None
    feedback_general: str | None = None
    feedback_per_option: dict | None = None


@dataclass
class ExtractedTest:
    """Raw test data extracted from pruebas/finalizadas."""

    id: str
    name: str
    admission_year: int | None
    application_type: str | None
    question_ids: list[str]  # Ordered by position


# -----------------------------------------------------------------------------
# Shared helper functions (also used by variant_extractors)
# -----------------------------------------------------------------------------


def _find_images_in_qti(qti_xml: str) -> list[str]:
    """Find all image references in QTI XML content.

    Looks for <img src="..."> and similar patterns.
    """
    # Pattern for img tags with src attribute
    img_pattern = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)
    # Pattern for object/embed tags
    object_pattern = re.compile(r'<object[^>]+data=["\']([^"\']+)["\']', re.IGNORECASE)

    images: list[str] = []
    images.extend(img_pattern.findall(qti_xml))
    images.extend(object_pattern.findall(qti_xml))

    return images


# -----------------------------------------------------------------------------
# Extraction functions
# -----------------------------------------------------------------------------


def extract_atoms(atoms_file: Path | None = None) -> list[ExtractedAtom]:
    """Extract all atoms from the canonical atoms JSON file.

    Args:
        atoms_file: Path to atoms JSON. Defaults to paes_m1_2026_atoms.json.

    Returns:
        List of ExtractedAtom instances.
    """
    if atoms_file is None:
        atoms_file = ATOMS_DIR / "paes_m1_2026_atoms.json"

    with open(atoms_file, encoding="utf-8") as f:
        data = json.load(f)

    atoms: list[ExtractedAtom] = []
    for atom_data in data.get("atoms", []):
        atoms.append(
            ExtractedAtom(
                id=atom_data["id"],
                eje=atom_data["eje"],
                standard_ids=atom_data["standard_ids"],
                habilidad_principal=atom_data["habilidad_principal"],
                habilidades_secundarias=atom_data.get("habilidades_secundarias", []),
                tipo_atomico=atom_data["tipo_atomico"],
                titulo=atom_data["titulo"],
                descripcion=atom_data["descripcion"],
                criterios_atomicos=atom_data["criterios_atomicos"],
                ejemplos_conceptuales=atom_data.get("ejemplos_conceptuales", []),
                prerrequisitos=atom_data.get("prerrequisitos", []),
                notas_alcance=atom_data.get("notas_alcance", []),
                en_alcance_m1=atom_data.get("en_alcance_m1", True),
            )
        )

    return atoms


def extract_standards(standards_file: Path | None = None) -> list[ExtractedStandard]:
    """Extract all standards from the canonical standards JSON file.

    Args:
        standards_file: Path to standards JSON. Defaults to paes_m1_2026.json.

    Returns:
        List of ExtractedStandard instances.
    """
    if standards_file is None:
        standards_file = STANDARDS_DIR / "paes_m1_2026.json"

    with open(standards_file, encoding="utf-8") as f:
        data = json.load(f)

    standards: list[ExtractedStandard] = []
    for std_data in data.get("standards", []):
        standards.append(
            ExtractedStandard(
                id=std_data["id"],
                eje=std_data["eje"],
                unidad_temario=std_data["unidad_temario"],
                titulo=std_data["titulo"],
                descripcion_general=std_data["descripcion_general"],
                incluye=std_data.get("incluye", []),
                no_incluye=std_data.get("no_incluye", []),
            )
        )

    return standards


def _parse_question_metadata(
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """Parse question-level fields from metadata_tags.json.

    Returns a flat dict with atoms, difficulty, analysis, and enrichment
    fields ready for ExtractedQuestion construction.
    """
    # Atoms
    atoms_data: list[dict[str, Any]] = [
        {
            "atom_id": a.get("atom_id"),
            "relevance": a.get("relevance", "primary").lower(),
            "reasoning": a.get("reasoning"),
        }
        for a in metadata.get("selected_atoms", [])
    ]

    # Difficulty
    difficulty = metadata.get("difficulty", {})
    level = (
        difficulty.get("level", "medium").lower()
        if difficulty else "medium"
    )
    if level not in ("low", "medium", "high"):
        level = "medium"

    return {
        "atoms": atoms_data,
        "difficulty_level": level,
        "difficulty_score": difficulty.get("score") if difficulty else None,
        # Analysis (populated after tagging)
        "general_analysis": metadata.get("general_analysis"),
        "difficulty_analysis": (
            difficulty.get("analysis") if difficulty else None
        ),
        # Enrichment (populated by enrichment pipeline)
        "title": metadata.get("title"),
        "correct_answer": metadata.get("correct_answer"),
        "feedback_general": metadata.get("feedback_general"),
        "feedback_per_option": metadata.get("feedback_per_option"),
    }


def _parse_test_name(
    test_name: str,
) -> tuple[int | None, str | None]:
    """Extract admission year and application type from a test name."""
    admission_year = None
    year_match = re.search(r"(\d{4})", test_name)
    if year_match:
        admission_year = int(year_match.group(1))

    lower = test_name.lower()
    if "invierno" in lower:
        application_type = "invierno"
    elif "regular" in lower:
        application_type = "regular"
    elif "seleccion" in lower:
        application_type = "seleccion"
    else:
        application_type = None

    return admission_year, application_type


def extract_test_questions(
    test_dir: Path,
) -> tuple[ExtractedTest, list[ExtractedQuestion]]:
    """Extract a test and its questions from a finalizadas directory.

    Args:
        test_dir: Path to the test directory

    Returns:
        Tuple of (ExtractedTest, list of ExtractedQuestion)
    """
    test_name = test_dir.name
    test_id = test_name.lower()
    admission_year, application_type = _parse_test_name(test_name)

    qti_dir = test_dir / "qti"
    if not qti_dir.exists():
        return ExtractedTest(
            id=test_id, name=test_name,
            admission_year=admission_year,
            application_type=application_type,
            question_ids=[],
        ), []

    questions: list[ExtractedQuestion] = []
    question_ids: list[str] = []

    q_dirs = sorted(
        [d for d in qti_dir.iterdir() if d.is_dir() and d.name.startswith("Q")],
        key=lambda x: int(re.search(r"\d+", x.name).group()) if re.search(r"\d+", x.name) else 0,
    )

    for q_dir in q_dirs:
        q_num_match = re.search(r"(\d+)", q_dir.name)
        if not q_num_match:
            continue
        q_num = int(q_num_match.group(1))
        question_id = f"{test_id}-Q{q_num}"

        qti_file = q_dir / "question.xml"
        if not qti_file.exists():
            continue
        with open(qti_file, encoding="utf-8") as f:
            qti_xml = f.read()

        # Read and parse metadata
        metadata_file = q_dir / "metadata_tags.json"
        metadata: dict[str, Any] = {}
        if metadata_file.exists():
            with open(metadata_file, encoding="utf-8") as f:
                metadata = json.load(f)
        parsed = _parse_question_metadata(metadata)

        questions.append(
            ExtractedQuestion(
                id=question_id,
                test_id=test_id,
                question_number=q_num,
                qti_xml=qti_xml,
                image_paths=_find_images_in_qti(qti_xml),
                **parsed,
            )
        )
        question_ids.append(question_id)

    test = ExtractedTest(
        id=test_id, name=test_name,
        admission_year=admission_year,
        application_type=application_type,
        question_ids=question_ids,
    )
    return test, questions


def extract_all_tests() -> tuple[list[ExtractedTest], list[ExtractedQuestion]]:
    """Extract all tests and questions from pruebas/finalizadas.

    Returns:
        Tuple of (list of ExtractedTest, list of all ExtractedQuestion)
    """
    all_tests: list[ExtractedTest] = []
    all_questions: list[ExtractedQuestion] = []

    if not PRUEBAS_FINALIZADAS_DIR.exists():
        return all_tests, all_questions

    for test_dir in sorted(PRUEBAS_FINALIZADAS_DIR.iterdir()):
        if not test_dir.is_dir():
            continue

        test, questions = extract_test_questions(test_dir)
        if test.question_ids:  # Only include tests with questions
            all_tests.append(test)
            all_questions.extend(questions)

    return all_tests, all_questions
