"""Subjects router - subject detail, standards, atoms, tests.

Endpoints:
    GET /api/subjects/{subject_id} - Subject detail with pipeline status
    GET /api/subjects/{subject_id}/standards - Standards list
    GET /api/subjects/{subject_id}/atoms - Atoms list with filters
    GET /api/subjects/{subject_id}/atoms/{atom_id} - Single atom detail
    GET /api/subjects/{subject_id}/atoms/graph - Knowledge graph data
    GET /api/subjects/{subject_id}/tests - Tests list
    GET /api/subjects/{subject_id}/tests/{test_id} - Test detail with questions

Note: Question detail endpoint is in questions.py
"""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Query

from api.config import SUBJECTS_CONFIG
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
)
from api.services.status_tracker import StatusTracker

router = APIRouter()


def _get_tracker(subject_id: str) -> StatusTracker:
    """Get tracker for subject, raising 404 if not found."""
    if subject_id not in SUBJECTS_CONFIG:
        raise HTTPException(status_code=404, detail=f"Subject '{subject_id}' not found")
    return StatusTracker(subject_id)


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

    # Get test briefs
    tests = []
    for test_dir in tracker.get_test_dirs():
        test_id = test_dir.name
        status = tracker.get_test_status(test_id)

        # Parse year and type from test name
        admission_year = None
        application_type = None
        import re
        year_match = re.search(r"(\d{4})", test_id)
        if year_match:
            admission_year = int(year_match.group(1))
        if "invierno" in test_id.lower():
            application_type = "invierno"
        elif "regular" in test_id.lower():
            application_type = "regular"
        elif "seleccion" in test_id.lower():
            application_type = "seleccion"

        tests.append(
            TestBrief(
                id=test_id,
                name=test_id,
                admission_year=admission_year,
                application_type=application_type,
                raw_pdf_exists=status["raw_pdf_exists"],
                split_count=status["split_count"],
                qti_count=status["qti_count"],
                finalized_count=status["finalized_count"],
                tagged_count=status["tagged_count"],
                variants_count=status["variants_count"],
            )
        )

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
            question_set_count=0,  # TODO: implement when question sets exist
            has_lesson=False,  # TODO: implement when lessons exist
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

        # Parse year and type
        import re
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

        tests.append(
            TestBrief(
                id=test_id,
                name=test_id,
                admission_year=admission_year,
                application_type=application_type,
                raw_pdf_exists=status["raw_pdf_exists"],
                split_count=status["split_count"],
                qti_count=status["qti_count"],
                finalized_count=status["finalized_count"],
                tagged_count=status["tagged_count"],
                variants_count=status["variants_count"],
            )
        )

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
        variants_count=status["variants_count"],
        questions=questions,
    )
