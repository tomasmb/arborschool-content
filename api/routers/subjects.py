"""Subjects router - subject detail, standards, atoms, tests.

Endpoints:
    GET /api/subjects/{subject_id} - Subject detail with pipeline status
    GET /api/subjects/{subject_id}/standards - Standards list
    GET /api/subjects/{subject_id}/atoms - Atoms list with filters
    GET /api/subjects/{subject_id}/atoms/{atom_id} - Single atom detail
    GET /api/subjects/{subject_id}/atoms/graph - Knowledge graph data
    GET /api/subjects/{subject_id}/atoms/unlock-status - Unlock status for Q Sets/Lessons
    GET /api/subjects/{subject_id}/temario - Temario JSON content
    GET /api/subjects/{subject_id}/tests - Tests list
    GET /api/subjects/{subject_id}/tests/{test_id} - Test detail with questions

Note: Question detail endpoint is in questions.py
"""

from __future__ import annotations

import json
import re

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from api.config import PRUEBAS_RAW_DIR, SUBJECTS_CONFIG, TEMARIOS_PDF_DIR
from api.schemas.api_models import (
    AtomBrief,
    AtomDetail,
    GraphData,
    GraphEdge,
    GraphNode,
    QuestionBrief,
    StandardBrief,
    SubjectDetail,
    TestBrief,
    TestDetail,
    UnlockStatus,
)
from api.services.status_tracker import StatusTracker
from app.question_generation.helpers import get_last_completed_phase
from app.utils.paths import TEMARIOS_JSON_DIR

router = APIRouter()


def _get_tracker(subject_id: str) -> StatusTracker:
    """Get tracker for subject, raising 404 if not found."""
    if subject_id not in SUBJECTS_CONFIG:
        raise HTTPException(status_code=404, detail=f"Subject '{subject_id}' not found")
    return StatusTracker(subject_id)


def _build_test_brief(test_id: str, status: dict) -> TestBrief:
    """Build a TestBrief from status_tracker output.

    Single source of truth for constructing TestBrief across all endpoints.
    """
    # Parse year and type from test name
    admission_year = None
    application_type = None
    year_match = re.search(r"(\d{4})", test_id)
    if year_match:
        admission_year = int(year_match.group(1))
    if "invierno" in test_id.lower():
        application_type = "invierno"
    elif "regular" in test_id.lower():
        application_type = "regular"
    elif "seleccion" in test_id.lower():
        application_type = "seleccion"

    return TestBrief(
        id=test_id,
        name=test_id,
        admission_year=admission_year,
        application_type=application_type,
        raw_pdf_exists=status["raw_pdf_exists"],
        split_count=status["split_count"],
        qti_count=status["qti_count"],
        finalized_count=status["finalized_count"],
        tagged_count=status["tagged_count"],
        enriched_count=status["enriched_count"],
        validated_count=status["validated_count"],
        variants_count=status["variants_count"],
        enriched_variants_count=status["enriched_variants_count"],
        validated_variants_count=status["validated_variants_count"],
    )


@router.get("/{subject_id}", response_model=SubjectDetail)
async def get_subject(subject_id: str) -> SubjectDetail:
    """Get full subject detail including standards, atoms count, and tests."""
    tracker = _get_tracker(subject_id)
    config = SUBJECTS_CONFIG[subject_id]

    # Get standards with atom counts
    standards_data = tracker.get_standards()
    standards = [
        StandardBrief(
            id=std["id"],
            eje=std["eje"],
            title=std["titulo"],
            atoms_count=len(tracker.get_atoms_by_standard(std["id"])),
        )
        for std in standards_data
    ]

    # Get test briefs using shared helper
    tests = []
    for test_dir in tracker.get_test_dirs():
        test_id = test_dir.name
        status = tracker.get_test_status(test_id)
        tests.append(_build_test_brief(test_id, status))

    return SubjectDetail(
        id=subject_id,
        name=config["name"],
        full_name=config["full_name"],
        year=config["year"],
        temario_exists=tracker.temario_exists(),
        temario_file=config.get("temario_file"),
        standards=standards,
        atoms_count=tracker.atoms_count(),
        tests=tests,
    )


@router.get("/{subject_id}/standards", response_model=list[StandardBrief])
async def get_standards(subject_id: str) -> list[StandardBrief]:
    """Get all standards for a subject."""
    tracker = _get_tracker(subject_id)
    standards_data = tracker.get_standards()

    return [
        StandardBrief(
            id=std["id"],
            eje=std["eje"],
            title=std["titulo"],
            atoms_count=len(tracker.get_atoms_by_standard(std["id"])),
        )
        for std in standards_data
    ]


@router.get("/{subject_id}/atoms", response_model=list[AtomBrief])
async def get_atoms(
    subject_id: str,
    eje: str | None = Query(None, description="Filter by eje"),
    standard_id: str | None = Query(None, description="Filter by standard"),
) -> list[AtomBrief]:
    """Get atoms list with optional filters."""
    tracker = _get_tracker(subject_id)
    atoms_data = tracker.get_atoms()

    # Apply filters
    if eje:
        atoms_data = [a for a in atoms_data if a.get("eje") == eje]
    if standard_id:
        atoms_data = [a for a in atoms_data if standard_id in a.get("standard_ids", [])]

    return [
        AtomBrief(
            id=atom["id"],
            eje=atom["eje"],
            standard_ids=atom.get("standard_ids", []),
            tipo_atomico=atom["tipo_atomico"],
            titulo=atom["titulo"],
            question_set_count=0,  # TODO: implement
            has_lesson=False,  # TODO: implement
            last_completed_phase=get_last_completed_phase(atom["id"]),
        )
        for atom in atoms_data
    ]


@router.get("/{subject_id}/atoms/graph", response_model=GraphData)
async def get_atoms_graph(subject_id: str) -> GraphData:
    """Get knowledge graph data for React Flow visualization."""
    tracker = _get_tracker(subject_id)
    atoms_data = tracker.get_atoms()

    # Build nodes
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []

    # Create a lookup for positioning by eje
    eje_columns = {
        "numeros": 0,
        "algebra_y_funciones": 1,
        "geometria": 2,
        "probabilidad_y_estadistica": 3,
    }

    # Group atoms by eje for layout
    atoms_by_eje: dict[str, list[dict]] = {}
    for atom in atoms_data:
        eje = atom.get("eje", "unknown")
        if eje not in atoms_by_eje:
            atoms_by_eje[eje] = []
        atoms_by_eje[eje].append(atom)

    # Create nodes with positions
    atom_ids = {a["id"] for a in atoms_data}
    for eje, eje_atoms in atoms_by_eje.items():
        col = eje_columns.get(eje, 0)
        for row, atom in enumerate(eje_atoms):
            nodes.append(
                GraphNode(
                    id=atom["id"],
                    type="atom",
                    position={"x": col * 300, "y": row * 100},
                    data={
                        "label": atom["titulo"],
                        "eje": atom["eje"],
                        "tipo": atom["tipo_atomico"],
                    },
                )
            )

    # Create edges from prerequisites
    for atom in atoms_data:
        for prereq_id in atom.get("prerrequisitos", []):
            if prereq_id in atom_ids:  # Only create edge if prereq exists
                edges.append(
                    GraphEdge(
                        id=f"{prereq_id}->{atom['id']}",
                        source=prereq_id,
                        target=atom["id"],
                    )
                )

    # Calculate stats
    stats = {
        "total_atoms": len(atoms_data),
        "atoms_by_eje": {eje: len(atoms) for eje, atoms in atoms_by_eje.items()},
        "total_edges": len(edges),
        "orphan_atoms": len([
            a for a in atoms_data
            if not a.get("prerrequisitos")
            and not any(a["id"] in other.get("prerrequisitos", []) for other in atoms_data)
        ]),
    }

    return GraphData(nodes=nodes, edges=edges, stats=stats)


@router.get("/{subject_id}/atoms/{atom_id}", response_model=AtomDetail)
async def get_atom_detail(subject_id: str, atom_id: str) -> AtomDetail:
    """Get full detail for a single atom."""
    tracker = _get_tracker(subject_id)
    atoms_data = tracker.get_atoms()

    # Find the atom
    atom = next((a for a in atoms_data if a["id"] == atom_id), None)
    if not atom:
        raise HTTPException(status_code=404, detail=f"Atom '{atom_id}' not found")

    # Find dependent atoms (atoms that have this as prerequisite)
    dependent_atoms = [
        a["id"] for a in atoms_data
        if atom_id in a.get("prerrequisitos", [])
    ]

    # TODO: Find linked questions (requires scanning all metadata_tags.json)
    linked_questions: list[str] = []

    return AtomDetail(
        id=atom["id"],
        eje=atom["eje"],
        standard_ids=atom.get("standard_ids", []),
        habilidad_principal=atom["habilidad_principal"],
        habilidades_secundarias=atom.get("habilidades_secundarias", []),
        tipo_atomico=atom["tipo_atomico"],
        titulo=atom["titulo"],
        descripcion=atom["descripcion"],
        criterios_atomicos=atom.get("criterios_atomicos", []),
        ejemplos_conceptuales=atom.get("ejemplos_conceptuales", []),
        prerrequisitos=atom.get("prerrequisitos", []),
        notas_alcance=atom.get("notas_alcance", []),
        dependent_atoms=dependent_atoms,
        linked_questions=linked_questions,
        question_set_count=0,  # TODO: implement
        has_lesson=False,  # TODO: implement
    )


@router.get("/{subject_id}/tests", response_model=list[TestBrief])
async def get_tests(subject_id: str) -> list[TestBrief]:
    """Get all tests for a subject."""
    tracker = _get_tracker(subject_id)
    tests = []

    for test_dir in tracker.get_test_dirs():
        test_id = test_dir.name
        status = tracker.get_test_status(test_id)
        tests.append(_build_test_brief(test_id, status))

    return tests


@router.get("/{subject_id}/tests/{test_id}", response_model=TestDetail)
async def get_test_detail(subject_id: str, test_id: str) -> TestDetail:
    """Get full test detail including all questions."""
    tracker = _get_tracker(subject_id)
    status = tracker.get_test_status(test_id)

    if not status["questions"]:
        raise HTTPException(status_code=404, detail=f"Test '{test_id}' not found")

    # Parse year and type
    admission_year = None
    application_type = None
    year_match = re.search(r"(\d{4})", test_id)
    if year_match:
        admission_year = int(year_match.group(1))
    if "invierno" in test_id.lower():
        application_type = "invierno"
    elif "regular" in test_id.lower():
        application_type = "regular"
    elif "seleccion" in test_id.lower():
        application_type = "seleccion"

    questions = [
        QuestionBrief(**q) for q in status["questions"]
    ]

    return TestDetail(
        id=test_id,
        name=test_id,
        admission_year=admission_year,
        application_type=application_type,
        raw_pdf_exists=status["raw_pdf_exists"],
        split_count=status["split_count"],
        qti_count=status["qti_count"],
        finalized_count=status["finalized_count"],
        tagged_count=status["tagged_count"],
        enriched_count=status["enriched_count"],
        validated_count=status["validated_count"],
        variants_count=status["variants_count"],
        enriched_variants_count=status["enriched_variants_count"],
        validated_variants_count=status["validated_variants_count"],
        failed_validation_variants_count=status["failed_validation_variants_count"],
        questions=questions,
    )


@router.get("/{subject_id}/temario")
async def get_temario(subject_id: str) -> dict:
    """Get the temario JSON content for a subject.

    Returns the full temario data including ejes, unidades, and contenidos.
    """
    if subject_id not in SUBJECTS_CONFIG:
        raise HTTPException(status_code=404, detail=f"Subject '{subject_id}' not found")

    config = SUBJECTS_CONFIG[subject_id]
    temario_file = config.get("temario_file")

    if not temario_file:
        raise HTTPException(
            status_code=404,
            detail=f"No temario configured for subject '{subject_id}'"
        )

    temario_path = TEMARIOS_JSON_DIR / temario_file
    if not temario_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Temario file not found: {temario_file}"
        )

    with open(temario_path, encoding="utf-8") as f:
        return json.load(f)


@router.get("/{subject_id}/temario/pdf")
async def get_temario_pdf(subject_id: str) -> FileResponse:
    """Serve the temario PDF file for a subject."""
    if subject_id not in SUBJECTS_CONFIG:
        raise HTTPException(status_code=404, detail=f"Subject '{subject_id}' not found")

    config = SUBJECTS_CONFIG[subject_id]
    if not config.get("temario_file"):
        raise HTTPException(status_code=404, detail=f"No temario for '{subject_id}'")

    if not TEMARIOS_PDF_DIR.exists():
        raise HTTPException(status_code=404, detail="Temario PDF directory not found")

    # Return the most recent PDF (by name, which includes date)
    pdf_files = list(TEMARIOS_PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        raise HTTPException(status_code=404, detail="No temario PDFs found")

    pdf_file = sorted(pdf_files, reverse=True)[0]
    return FileResponse(path=pdf_file, media_type="application/pdf", filename=pdf_file.name)


@router.get("/{subject_id}/tests/{test_id}/raw-pdf")
async def get_test_raw_pdf(subject_id: str, test_id: str) -> FileResponse:
    """Serve the raw (original) PDF file for a test."""
    if subject_id not in SUBJECTS_CONFIG:
        raise HTTPException(status_code=404, detail=f"Subject '{subject_id}' not found")

    raw_test_dir = PRUEBAS_RAW_DIR / test_id
    if not raw_test_dir.exists():
        raise HTTPException(status_code=404, detail=f"Raw PDF not found for '{test_id}'")

    pdf_files = list(raw_test_dir.glob("*.pdf"))
    if not pdf_files:
        raise HTTPException(status_code=404, detail=f"No PDFs found for '{test_id}'")

    # Return the largest PDF (usually the official one)
    pdf_file = max(pdf_files, key=lambda f: f.stat().st_size)
    # Use inline to display in browser instead of downloading
    return FileResponse(
        path=pdf_file,
        media_type="application/pdf",
        content_disposition_type="inline",
    )


@router.get("/{subject_id}/atoms/unlock-status", response_model=UnlockStatus)
async def get_atoms_unlock_status(subject_id: str) -> UnlockStatus:
    """Get unlock status for Question Sets and Lessons generation.

    Question Sets and Lessons can only be generated when ALL finalized
    questions across ALL tests have been tagged with atoms.

    Returns status showing tagging progress and whether generation is unlocked.
    """
    tracker = _get_tracker(subject_id)

    # Count tagged vs total across all tests
    total_tagged = 0
    total_finalized = 0
    tests_status: dict[str, dict] = {}

    for test_dir in tracker.get_test_dirs():
        test_id = test_dir.name
        status = tracker.get_test_status(test_id)

        tagged = status["tagged_count"]
        finalized = status["finalized_count"]

        total_tagged += tagged
        total_finalized += finalized

        tests_status[test_id] = {
            "tagged": tagged,
            "total": finalized,
            "complete": tagged == finalized and finalized > 0,
        }

    # Calculate completion
    completion = (total_tagged / total_finalized * 100) if total_finalized > 0 else 0
    all_tagged = total_tagged == total_finalized and total_finalized > 0

    return UnlockStatus(
        all_questions_tagged=all_tagged,
        tagged_count=total_tagged,
        total_count=total_finalized,
        completion_percentage=round(completion, 1),
        tests_status=tests_status,
    )
