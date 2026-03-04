"""Sync-aligned candidate loaders for the QA scan pipeline."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from api.utils.validation_io import is_can_sync, read_validation_data
from app.sync.extractors import extract_lessons
from app.sync.generated_question_extractor import (
    extract_generated_questions,
)
from app.utils.paths import (
    PRUEBAS_ALTERNATIVAS_DIR,
    PRUEBAS_FINALIZADAS_DIR,
)
from scripts.notation_state import ScanItem

POOL_CHOICES = (
    "official-questions",
    "variants",
    "generated-questions",
    "lessons",
)
POOL_ALIASES = {
    "questions": "official-questions",
    "mini-classes": "lessons",
}


def canonical_pool(raw: str | None) -> str | None:
    if raw is None:
        return None
    return POOL_ALIASES.get(raw, raw)


def pool_name(only: str | None) -> str:
    return canonical_pool(only) or "all-sync"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _check_syncable_folder(folder: Path) -> bool:
    if not (folder / "question_validated.xml").exists():
        return False
    vdata = read_validation_data(folder)
    return is_can_sync(vdata)


def _iter_official_questions() -> list[ScanItem]:
    items: list[ScanItem] = []
    if not PRUEBAS_FINALIZADAS_DIR.exists():
        return items
    for test_dir in sorted(PRUEBAS_FINALIZADAS_DIR.iterdir()):
        qti_dir = test_dir / "qti"
        if not qti_dir.exists():
            continue
        for q_folder in sorted(qti_dir.iterdir()):
            if not q_folder.is_dir() or not q_folder.name.startswith("Q"):
                continue
            if not _check_syncable_folder(q_folder):
                continue
            xml_path = q_folder / "question_validated.xml"
            if not xml_path.exists():
                continue
            item_id = f"{test_dir.name}-{q_folder.name}"
            items.append((
                item_id,
                "official-question",
                str(xml_path),
                _read_text(xml_path),
                item_id,
            ))
    return items


def _iter_variants() -> list[ScanItem]:
    items: list[ScanItem] = []
    if not PRUEBAS_ALTERNATIVAS_DIR.exists():
        return items
    for test_dir in sorted(PRUEBAS_ALTERNATIVAS_DIR.iterdir()):
        for q_dir in sorted(test_dir.iterdir()):
            if not q_dir.is_dir() or not q_dir.name.startswith("Q"):
                continue
            approved_dir = q_dir / "approved"
            if not approved_dir.exists():
                continue
            qnum_m = re.search(r"(\d+)", q_dir.name)
            if not qnum_m:
                continue
            q_num = int(qnum_m.group(1))
            seq = 0
            for v_dir in sorted(approved_dir.iterdir()):
                if not v_dir.is_dir():
                    continue
                m = re.search(r"_v(\d+)$", v_dir.name)
                seq = int(m.group(1)) if m else seq + 1
                if not _check_syncable_folder(v_dir):
                    continue
                xml_path = v_dir / "question_validated.xml"
                if not xml_path.exists():
                    continue
                item_id = f"alt-{test_dir.name}-Q{q_num}-{seq:03d}"
                items.append((
                    item_id,
                    "variant",
                    str(xml_path),
                    _read_text(xml_path),
                    item_id,
                ))
    return items


def _iter_generated_questions() -> list[ScanItem]:
    items: list[ScanItem] = []
    gen_logger = logging.getLogger(
        "app.sync.generated_question_extractor",
    )
    prev_level = gen_logger.level
    gen_logger.setLevel(logging.WARNING)
    try:
        rows = extract_generated_questions()
    finally:
        gen_logger.setLevel(prev_level)
    for row in rows:
        ckpt = (
            Path("app/data/question-generation")
            / row.atom_id / "checkpoints/phase_9_final_validation.json"
        )
        item_id = row.id
        items.append((
            item_id,
            "generated-question",
            str(ckpt),
            row.qti_xml,
            item_id,
        ))
    return items


def _iter_lessons() -> list[ScanItem]:
    items: list[ScanItem] = []
    base = Path("app/data/mini-lessons")
    for lesson in extract_lessons():
        html_path = base / lesson.atom_id / "mini-class.html"
        item_id = f"lesson-{lesson.atom_id}"
        items.append((
            item_id,
            "lesson",
            str(html_path),
            lesson.lesson_html,
            item_id,
        ))
    return items


def load_items(only: str | None, limit: int | None) -> list[ScanItem]:
    selected = canonical_pool(only)
    items: list[ScanItem] = []
    if selected in (None, "official-questions"):
        items.extend(_iter_official_questions())
    if selected in (None, "variants"):
        items.extend(_iter_variants())
    if selected in (None, "generated-questions"):
        items.extend(_iter_generated_questions())
    if selected in (None, "lessons"):
        items.extend(_iter_lessons())
    items.sort(key=lambda x: x[0])
    if limit:
        items = items[:limit]
    return items
