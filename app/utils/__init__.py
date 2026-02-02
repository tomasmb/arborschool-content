"""Shared utilities package for the arborschool-content application."""

from app.utils.data_loader import (
    find_item_by_id,
    find_items_by_ids,
    load_atoms_file,
    load_json_file,
    load_standards_file,
    save_json_file,
)
from app.utils.logging_config import get_logger, setup_logging
from app.utils.mathml_parser import process_mathml
from app.utils.prompt_helpers import format_habilidades_context
from app.utils.qti_extractor import (
    extract_choices_from_qti,
    extract_correct_answer_from_qti,
    extract_text_from_qti,
    parse_qti_xml,
)

__all__ = [
    # Data loading utilities
    "load_json_file",
    "save_json_file",
    "load_standards_file",
    "load_atoms_file",
    "find_item_by_id",
    "find_items_by_ids",
    # Logging utilities
    "setup_logging",
    "get_logger",
    # MathML utilities
    "process_mathml",
    # Prompt helpers
    "format_habilidades_context",
    # QTI extraction utilities
    "parse_qti_xml",
    "extract_text_from_qti",
    "extract_choices_from_qti",
    "extract_correct_answer_from_qti",
]
