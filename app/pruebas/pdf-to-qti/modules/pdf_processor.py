"""
PDF Content Processor

This module extracts structured content and images from PDF files
for use in QTI conversion. Uses PyMuPDF for structured data and
GPT-5.1 vision for intelligent content categorization, following
converter guidelines to avoid overfitting and leverage AI capabilities.

This is the main entry point that orchestrates the extraction pipeline.
The implementation is split across several modules for maintainability:
- pdf_text_processing.py: Text block extraction and processing
- pdf_image_utils.py: Image rendering and utilities
- pdf_table_extraction.py: Table detection and extraction
- pdf_visual_pipeline.py: Visual content extraction pipeline
"""

from __future__ import annotations

import base64
import logging
from typing import Any

import fitz  # type: ignore

from .pdf_text_processing import (
    CustomJSONEncoder,
    extract_block_text,
    extract_question_text,
    extract_text_blocks,
    split_choice_blocks,
)
from .pdf_image_utils import is_meaningful_image, render_image_area, trim_whitespace
from .pdf_table_extraction import extract_tables_with_pymupdf
from .pdf_visual_pipeline import extract_images_and_tables
from .qti_transformer import detect_encoding_errors
from .utils import combine_structured_data, create_combined_image, get_page_image

# Re-export for backward compatibility
__all__ = [
    "CustomJSONEncoder",
    "extract_pdf_content",
    "extract_text_blocks",
    "extract_block_text",
    "extract_question_text",
    "split_choice_blocks",
    "extract_images_and_tables",
    "extract_tables_with_pymupdf",
    "is_meaningful_image",
    "render_image_area",
]

_logger = logging.getLogger(__name__)


def extract_pdf_content(
    doc: fitz.Document, openai_api_key: str | None = None
) -> dict[str, Any]:
    """
    Extract comprehensive content from a PDF document using AI-powered analysis.

    Following converter guidelines:
    - Use PyMuPDF first for structured data
    - Fallback to GPT-5.1 vision for image detection
    - Leverage AI categorization throughout the pipeline

    Args:
        doc: PyMuPDF document object
        openai_api_key: OpenAI API key for AI-powered content analysis

    Returns:
        Dictionary containing structured text, images, and metadata
    """
    content: dict[str, Any] = {
        "page_count": doc.page_count,
        "pages": [],
        "combined_text": "",
        "image_base64": None,
        "structured_data": None,
        "all_images": [],
    }

    # Process each page with AI-powered analysis
    for page_num in range(doc.page_count):
        page_content = _process_page(doc, page_num, openai_api_key)
        content["pages"].append(page_content)
        content["combined_text"] += page_content["plain_text"] + "\n"
        content["all_images"].extend(page_content["extracted_images"])

    # Set main image and structured data
    _finalize_content(doc, content)

    return content


def _process_page(
    doc: fitz.Document, page_num: int, openai_api_key: str | None
) -> dict[str, Any]:
    """
    Process a single PDF page and extract all content.

    Args:
        doc: PyMuPDF document object
        page_num: Page number to process
        openai_api_key: OpenAI API key for AI-powered analysis

    Returns:
        Dictionary with page content and metadata
    """
    page = doc.load_page(page_num)

    # Extract structured text data using PyMuPDF
    structured_text = page.get_text("dict", sort=True)

    # Extract plain text
    plain_text = page.get_text()

    # Check for encoding errors in extracted text (garbled Spanish characters)
    _check_encoding_errors(plain_text, page_num)

    # Get page image for AI analysis
    page_image = get_page_image(page)

    # Extract images and tables with AI categorization
    extracted_content = extract_images_and_tables(page, structured_text, openai_api_key)

    # Add page info to extracted images
    for img in extracted_content["images"]:
        img["page_number"] = page_num

    return {
        "page_number": page_num,
        "structured_text": structured_text,
        "plain_text": plain_text,
        "page_image_base64": (
            extracted_content.get("page_image_base64")
            or base64.b64encode(page_image).decode("utf-8")
        ),
        "bbox": [page.rect.x0, page.rect.y0, page.rect.x1, page.rect.y1],
        "width": page.rect.width,
        "height": page.rect.height,
        "extracted_images": extracted_content["images"],
        "extracted_tables": extracted_content["tables"],
        "ai_categories": extracted_content.get("ai_categories", {}),
    }


def _check_encoding_errors(plain_text: str, page_num: int) -> None:
    """Check for encoding errors and log warnings if found."""
    encoding_errors = detect_encoding_errors(plain_text)
    if encoding_errors:
        _logger.warning(
            f"PDF page {page_num} has encoding errors: {encoding_errors[:3]}. "
            "This indicates non-standard font mappings in the PDF."
        )


def _finalize_content(doc: fitz.Document, content: dict[str, Any]) -> None:
    """
    Finalize content dictionary with main image and structured data.

    Args:
        doc: PyMuPDF document object
        content: Content dictionary to finalize (modified in place)
    """
    # Set flags for extracted images
    content["has_extracted_images"] = bool(content["all_images"])

    # CRITICAL: Always provide the image_base64 for validation.
    # The presence of extracted images should not nullify the main page image.
    if doc.page_count == 1:
        content["image_base64"] = content["pages"][0]["page_image_base64"]
    else:
        # For multi-page docs, a combined image is the best representation
        content["image_base64"] = create_combined_image(doc)

    # Set structured data
    if doc.page_count == 1:
        content["structured_data"] = content["pages"][0]["structured_text"]
    else:
        content["structured_data"] = combine_structured_data(content["pages"])


# Legacy alias for backward compatibility
_trim_whitespace = trim_whitespace
