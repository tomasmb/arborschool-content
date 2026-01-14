"""Extract data from content repo JSON/XML files.

This module reads the canonical data files and returns structured data ready
for transformation to DB schema.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# -----------------------------------------------------------------------------
# Path constants
# -----------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = REPO_ROOT / "app" / "data"
ATOMS_DIR = DATA_DIR / "atoms"
STANDARDS_DIR = DATA_DIR / "standards"
PRUEBAS_FINALIZADAS_DIR = DATA_DIR / "pruebas" / "finalizadas"


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
    """Raw question data extracted from QTI XML and metadata JSON."""

    id: str
    test_id: str
    question_number: int
    qti_xml: str
    correct_answer: str
    title: str | None
    # From metadata_tags.json
    atoms: list[dict[str, Any]]  # List of {atom_id, relevance, reasoning}
    difficulty_level: str | None
    difficulty_score: float | None
    difficulty_analysis: str | None
    general_analysis: str | None
    feedback_general: str | None
    feedback_per_option: dict[str, str] | None
    # Image paths found in QTI
    image_paths: list[str]


@dataclass
class ExtractedTest:
    """Raw test data extracted from pruebas/finalizadas."""

    id: str
    name: str
    admission_year: int | None
    application_type: str | None
    question_ids: list[str]  # Ordered by position


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


def _parse_correct_answer_from_qti(qti_xml: str) -> str:
    """Extract correct answer identifier from QTI XML.

    Looks for <qti-correct-response><qti-value>ChoiceX</qti-value></qti-correct-response>
    """
    pattern = re.compile(
        r"<qti-correct-response>\s*<qti-value>([^<]+)</qti-value>\s*</qti-correct-response>",
        re.IGNORECASE,
    )
    match = pattern.search(qti_xml)
    if match:
        return match.group(1).strip()
    return ""


def _parse_title_from_qti(qti_xml: str) -> str | None:
    """Extract title from QTI XML."""
    pattern = re.compile(r'title=["\']([^"\']+)["\']', re.IGNORECASE)
    match = pattern.search(qti_xml)
    if match:
        return match.group(1).strip()
    return None


def extract_test_questions(test_dir: Path) -> tuple[ExtractedTest, list[ExtractedQuestion]]:
    """Extract a test and its questions from a finalizadas test directory.

    Args:
        test_dir: Path to the test directory (e.g., pruebas/finalizadas/prueba-invierno-2026)

    Returns:
        Tuple of (ExtractedTest, list of ExtractedQuestion)
    """
    test_name = test_dir.name
    test_id = test_name.lower()

    # Parse admission year and application type from test name
    admission_year = None
    application_type = None
    year_match = re.search(r"(\d{4})", test_name)
    if year_match:
        admission_year = int(year_match.group(1))

    if "invierno" in test_name.lower():
        application_type = "invierno"
    elif "regular" in test_name.lower():
        application_type = "regular"
    elif "seleccion" in test_name.lower():
        application_type = "seleccion"

    # Find all question directories
    qti_dir = test_dir / "qti"
    if not qti_dir.exists():
        return ExtractedTest(
            id=test_id,
            name=test_name,
            admission_year=admission_year,
            application_type=application_type,
            question_ids=[],
        ), []

    questions: list[ExtractedQuestion] = []
    question_ids: list[str] = []

    # Sort question directories by number
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

        # Read QTI XML
        qti_file = q_dir / "question.xml"
        if not qti_file.exists():
            continue

        with open(qti_file, encoding="utf-8") as f:
            qti_xml = f.read()

        # Read metadata
        metadata_file = q_dir / "metadata_tags.json"
        metadata: dict[str, Any] = {}
        if metadata_file.exists():
            with open(metadata_file, encoding="utf-8") as f:
                metadata = json.load(f)

        # Extract atoms info
        atoms_data: list[dict[str, Any]] = []
        for atom_info in metadata.get("selected_atoms", []):
            atoms_data.append({
                "atom_id": atom_info.get("atom_id"),
                "relevance": atom_info.get("relevance", "primary").lower(),
                "reasoning": atom_info.get("reasoning"),
            })

        # Extract difficulty
        difficulty = metadata.get("difficulty", {})
        difficulty_level = difficulty.get("level", "medium").lower() if difficulty else "medium"
        # Normalize difficulty level
        if difficulty_level not in ("low", "medium", "high"):
            difficulty_level = "medium"

        # Extract feedback
        feedback = metadata.get("feedback", {})

        questions.append(
            ExtractedQuestion(
                id=question_id,
                test_id=test_id,
                question_number=q_num,
                qti_xml=qti_xml,
                correct_answer=_parse_correct_answer_from_qti(qti_xml),
                title=_parse_title_from_qti(qti_xml),
                atoms=atoms_data,
                difficulty_level=difficulty_level,
                difficulty_score=difficulty.get("score") if difficulty else None,
                difficulty_analysis=difficulty.get("analysis") if difficulty else None,
                general_analysis=metadata.get("general_analysis"),
                feedback_general=feedback.get("general_guidance") if feedback else None,
                feedback_per_option=feedback.get("per_option_feedback") if feedback else None,
                image_paths=_find_images_in_qti(qti_xml),
            )
        )
        question_ids.append(question_id)

    test = ExtractedTest(
        id=test_id,
        name=test_name,
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
