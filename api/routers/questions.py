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

    Note: correct_answer and feedback are now embedded in qti_xml and parsed
    by the frontend when displaying questions.

    Returns dict with keys: stem, options (list of {id, text})
    """
    result = {"stem": None, "options": []}

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
    validated_qti_file = q_dir / "question_validated.xml"
    original_qti_file = q_dir / "question.xml"
    validation_result_file = q_dir / "validation_result.json"
    metadata_file = q_dir / "metadata_tags.json"
    pdf_dir = PRUEBAS_PROCESADAS_DIR / test_id / "pdf"
    pdf_file = pdf_dir / f"Q{question_num}.pdf"
    alternativas_dir = PRUEBAS_ALTERNATIVAS_DIR / test_id / f"Q{question_num}" / "approved"

    # Show enriched XML if it exists (for review), regardless of validation status
    # Sync is gated on can_sync=true, not display
    if validated_qti_file.exists():
        qti_file = validated_qti_file
    else:
        qti_file = original_qti_file

    # Read QTI content
    qti_xml = None
    qti_stem = None
    qti_options = None

    if qti_file.exists():
        qti_xml = qti_file.read_text(encoding="utf-8")
        parsed = _parse_qti_xml(qti_xml)
        qti_stem = parsed["stem"]
        qti_options = parsed["options"] if parsed["options"] else None

    # Read metadata/tags
    atom_tags: list[AtomTag] = []
    difficulty = None
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
                    # Convert string relevance values to float
                    raw_relevance = atom_data.get("relevance", 1.0)
                    if isinstance(raw_relevance, str):
                        relevance_map = {"primary": 1.0, "secondary": 0.5, "tertiary": 0.25}
                        relevance = relevance_map.get(raw_relevance.lower(), 1.0)
                    else:
                        relevance = float(raw_relevance) if raw_relevance else 1.0
                    atom_tags.append(AtomTag(
                        atom_id=atom_data.get("atom_id", ""),
                        titulo=atom_data.get("titulo", atom_data.get("atom_id", "")),
                        eje=atom_data.get("eje", "unknown"),
                        relevance=relevance
                    ))

            raw_difficulty = metadata.get("difficulty")
            # Handle difficulty as dict or string
            if isinstance(raw_difficulty, dict):
                difficulty = raw_difficulty.get("level")
            else:
                difficulty = raw_difficulty
            source_info = metadata.get("source_info", {})
        except (json_module.JSONDecodeError, OSError):
            pass

    # List variants with enrichment/validation status
    variants: list[VariantBrief] = []
    if alternativas_dir.exists():
        for idx, variant_dir in enumerate(sorted(alternativas_dir.iterdir()), 1):
            if variant_dir.is_dir():
                # Check variant-level enrichment (question_validated.xml)
                variant_enriched = (variant_dir / "question_validated.xml").exists()
                # Check variant-level validation (validation_result.json with success)
                variant_validated = False
                variant_validation_file = variant_dir / "validation_result.json"
                if variant_validation_file.exists():
                    try:
                        with open(variant_validation_file, encoding="utf-8") as f:
                            vdata = json_module.load(f)
                        variant_validated = vdata.get("can_sync", False) or vdata.get("success", False)
                    except (json_module.JSONDecodeError, OSError):
                        pass

                variants.append(VariantBrief(
                    id=f"{question_id}-v{idx}",
                    variant_number=idx,
                    folder_name=variant_dir.name,
                    has_qti=(variant_dir / "question.xml").exists(),
                    has_metadata=(variant_dir / "metadata_tags.json").exists(),
                    is_enriched=variant_enriched,
                    is_validated=variant_validated,
                ))

    # Check enrichment/validation status (reuse validation data read earlier)
    is_enriched = validated_qti_file.exists()
    is_validated = False
    can_sync = False
    validation_result: dict | None = None

    if validation_result_file.exists():
        try:
            with open(validation_result_file, encoding="utf-8") as f:
                validation_data = json_module.load(f)
            can_sync = validation_data.get("can_sync", False)
            is_validated = can_sync or validation_data.get("success", False)
            # Extract validation details for display
            if "stages" in validation_data and "final_validation" in validation_data["stages"]:
                validation_result = validation_data["stages"]["final_validation"]
            elif "validation_details" in validation_data:
                validation_result = validation_data["validation_details"]
        except (json_module.JSONDecodeError, OSError):
            pass

    # Get sync status
    from api.services.sync_service import get_question_sync_status

    sync_status = get_question_sync_status(test_id, question_num)

    return QuestionDetail(
        id=question_id,
        test_id=test_id,
        question_number=question_num,
        has_split_pdf=pdf_file.exists(),
        has_qti=original_qti_file.exists(),
        is_finalized=original_qti_file.exists(),
        is_tagged=metadata_file.exists(),
        qti_xml=qti_xml,
        qti_stem=qti_stem,
        qti_options=qti_options,
        difficulty=difficulty,
        source_info=source_info,
        atom_tags=atom_tags,
        variants=variants,
        qti_path=str(qti_file) if qti_file.exists() else None,
        pdf_path=str(pdf_file) if pdf_file.exists() else None,
        is_enriched=is_enriched,
        is_validated=is_validated,
        can_sync=can_sync,
        sync_status=sync_status,
        validation_result=validation_result,
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
        # Use inline to display in browser instead of downloading
        content_disposition_type="inline",
    )
