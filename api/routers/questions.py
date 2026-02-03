"""Questions router - question detail endpoints.

Endpoints:
    GET /api/subjects/{subject_id}/tests/{test_id}/questions/{question_num}
    GET /api/subjects/{subject_id}/tests/{test_id}/questions/{question_num}/pdf
"""

from __future__ import annotations

import json as json_module
import xml.etree.ElementTree as ET

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from api.config import (
    PRUEBAS_ALTERNATIVAS_DIR,
    PRUEBAS_FINALIZADAS_DIR,
    PRUEBAS_PROCESADAS_DIR,
    SUBJECTS_CONFIG,
)
from api.schemas.api_models import (
    AtomTag,
    QuestionDetail,
    VariantBrief,
)


router = APIRouter()


def _parse_qti_xml(xml_content: str) -> dict:
    """Parse QTI XML to extract question stem and options.

    Returns dict with keys: stem, options (list of {id, text}), correct_answer
    """
    result = {"stem": None, "options": [], "correct_answer": None}

    try:
        root = ET.fromstring(xml_content)
        ns = {"qti": "http://www.imsglobal.org/xsd/imsqtiasi_v3p0"}

        # Try to find itemBody
        item_body = root.find(".//qti:itemBody", ns) or root.find(".//itemBody")

        if item_body is not None:
            # Extract stem from prompt or first p/div
            prompt = item_body.find(".//qti:prompt", ns) or item_body.find(".//prompt")
            if prompt is not None:
                result["stem"] = "".join(prompt.itertext()).strip()
            else:
                for elem in item_body:
                    text = "".join(elem.itertext()).strip()
                    if text:
                        result["stem"] = text
                        break

        # Find choice interaction
        choice_interaction = (
            root.find(".//qti:choiceInteraction", ns)
            or root.find(".//choiceInteraction")
        )
        if choice_interaction is not None:
            for choice in choice_interaction.findall(".//*"):
                if "simpleChoice" in choice.tag or choice.tag.endswith("simpleChoice"):
                    choice_id = choice.get("identifier", "")
                    choice_text = "".join(choice.itertext()).strip()
                    if choice_id and choice_text:
                        result["options"].append({"id": choice_id, "text": choice_text})

        # Find correct answer
        response_decl = (
            root.find(".//qti:responseDeclaration", ns)
            or root.find(".//responseDeclaration")
        )
        if response_decl is not None:
            correct = (
                response_decl.find(".//qti:correctResponse/qti:value", ns)
                or response_decl.find(".//correctResponse/value")
            )
            if correct is not None and correct.text:
                result["correct_answer"] = correct.text.strip()

    except ET.ParseError:
        pass

    return result


@router.get(
    "/{subject_id}/tests/{test_id}/questions/{question_num}",
    response_model=QuestionDetail
)
async def get_question_detail(
    subject_id: str,
    test_id: str,
    question_num: int
) -> QuestionDetail:
    """Get full question detail including QTI content, atoms, and variants."""
    if subject_id not in SUBJECTS_CONFIG:
        raise HTTPException(status_code=404, detail=f"Subject '{subject_id}' not found")

    test_dir = PRUEBAS_FINALIZADAS_DIR / test_id
    q_dir = test_dir / "qti" / f"Q{question_num}"

    if not q_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Question Q{question_num} not found in test '{test_id}'"
        )

    question_id = f"{test_id}-Q{question_num}"
    qti_file = q_dir / "question.xml"
    metadata_file = q_dir / "metadata_tags.json"
    pdf_dir = PRUEBAS_PROCESADAS_DIR / test_id / "pdf"
    pdf_file = pdf_dir / f"Q{question_num}.pdf"
    alternativas_dir = PRUEBAS_ALTERNATIVAS_DIR / test_id / f"Q{question_num}" / "approved"

    # Read QTI content
    qti_xml = None
    qti_stem = None
    qti_options = None
    correct_answer = None

    if qti_file.exists():
        qti_xml = qti_file.read_text(encoding="utf-8")
        parsed = _parse_qti_xml(qti_xml)
        qti_stem = parsed["stem"]
        qti_options = parsed["options"] if parsed["options"] else None
        correct_answer = parsed["correct_answer"]

    # Read metadata/tags
    atom_tags: list[AtomTag] = []
    difficulty = None
    feedback: dict[str, str] = {}
    source_info: dict = {}

    if metadata_file.exists():
        try:
            with open(metadata_file, encoding="utf-8") as f:
                metadata = json_module.load(f)

            for atom_data in metadata.get("selected_atoms", []):
                if isinstance(atom_data, str):
                    atom_tags.append(AtomTag(
                        atom_id=atom_data, titulo=atom_data,
                        eje="unknown", relevance=1.0
                    ))
                elif isinstance(atom_data, dict):
                    atom_tags.append(AtomTag(
                        atom_id=atom_data.get("atom_id", ""),
                        titulo=atom_data.get("titulo", atom_data.get("atom_id", "")),
                        eje=atom_data.get("eje", "unknown"),
                        relevance=atom_data.get("relevance", 1.0)
                    ))

            difficulty = metadata.get("difficulty")
            feedback = metadata.get("feedback", {})
            source_info = metadata.get("source_info", {})
        except (json_module.JSONDecodeError, OSError):
            pass

    # List variants
    variants: list[VariantBrief] = []
    if alternativas_dir.exists():
        for idx, variant_dir in enumerate(sorted(alternativas_dir.iterdir()), 1):
            if variant_dir.is_dir():
                variants.append(VariantBrief(
                    id=f"{question_id}-v{idx}",
                    variant_number=idx,
                    folder_name=variant_dir.name,
                    has_qti=(variant_dir / "question.xml").exists(),
                    has_metadata=(variant_dir / "metadata_tags.json").exists(),
                ))

    return QuestionDetail(
        id=question_id,
        test_id=test_id,
        question_number=question_num,
        has_split_pdf=pdf_file.exists(),
        has_qti=qti_file.exists(),
        is_finalized=qti_file.exists(),
        is_tagged=metadata_file.exists(),
        qti_xml=qti_xml,
        qti_stem=qti_stem,
        qti_options=qti_options,
        correct_answer=correct_answer,
        difficulty=difficulty,
        source_info=source_info,
        atom_tags=atom_tags,
        feedback=feedback,
        variants=variants,
        qti_path=str(qti_file) if qti_file.exists() else None,
        pdf_path=str(pdf_file) if pdf_file.exists() else None,
    )


@router.get("/{subject_id}/tests/{test_id}/questions/{question_num}/pdf")
async def get_question_pdf(
    subject_id: str,
    test_id: str,
    question_num: int
) -> FileResponse:
    """Serve the split PDF file for a specific question.

    Returns the PDF file for viewing/downloading in the browser.
    """
    if subject_id not in SUBJECTS_CONFIG:
        raise HTTPException(status_code=404, detail=f"Subject '{subject_id}' not found")

    pdf_dir = PRUEBAS_PROCESADAS_DIR / test_id / "pdf"
    pdf_file = pdf_dir / f"Q{question_num}.pdf"

    if not pdf_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"PDF for Q{question_num} not found in test '{test_id}'"
        )

    return FileResponse(
        path=pdf_file,
        media_type="application/pdf",
        filename=f"{test_id}-Q{question_num}.pdf",
    )
