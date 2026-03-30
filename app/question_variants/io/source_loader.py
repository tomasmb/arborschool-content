"""Source-question loading helpers for the hard-variants pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from app.question_variants.models import SourceQuestion
from app.utils.qti_extractor import parse_qti_xml

FINALIZED_PATH = Path("app/data/pruebas/finalizadas")


def load_source_questions(test_id: str, question_ids: list[str] | None = None) -> list[SourceQuestion]:
    """Load finalized source questions from disk."""
    test_path = FINALIZED_PATH / test_id / "qti"
    if not test_path.exists():
        return []

    sources: list[SourceQuestion] = []
    for question_dir in sorted(test_path.iterdir()):
        if question_ids and question_dir.name not in question_ids:
            continue
        if not question_dir.is_dir():
            continue

        xml_path = question_dir / "question.xml"
        meta_path = question_dir / "metadata_tags.json"
        if not xml_path.exists() or not meta_path.exists():
            continue

        qti_xml = xml_path.read_text(encoding="utf-8")
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        parsed = parse_qti_xml(qti_xml)
        sources.append(
            SourceQuestion(
                question_id=question_dir.name,
                test_id=test_id,
                qti_xml=qti_xml,
                metadata=metadata,
                question_text=parsed.text,
                choices=parsed.choices,
                correct_answer=parsed.correct_answer_text or "",
                image_urls=parsed.image_urls,
            )
        )
    return sources
