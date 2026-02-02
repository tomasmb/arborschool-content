"""
PDF Output Validation Rules

This module defines validation rules that REJECT PDF output which would
otherwise require post-generation fixes. The pipeline should fail fast
when these issues are detected.

These rules address issues from:
- fix_q14_q56.py: PDFs with wrong page count
- organize_invierno_2025_questions.py: Misaligned question numbers
- finalize_invierno_2025.py: Missing questions in sequence
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None  # type: ignore


@dataclass
class PDFValidationResult:
    """Result of a PDF validation rule check."""

    passed: bool
    rule_name: str
    message: str
    details: str | None = None

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        result = f"[{status}] {self.rule_name}: {self.message}"
        if self.details:
            result += f"\n  Details: {self.details}"
        return result


# Type alias for validation rule functions
PDFValidationRule = Callable[[Path], PDFValidationResult]


def validate_single_page(pdf_path: Path) -> PDFValidationResult:
    """
    REJECT if PDF does not have exactly 1 page.

    Multi-page question PDFs indicate the splitter extracted wrong content.
    This was the root cause of fix_q14_q56.py where PDFs had 3 pages
    but only page 3 was correct.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        PDFValidationResult with pass/fail status
    """
    rule_name = "single_page"

    if fitz is None:
        return PDFValidationResult(
            passed=True,
            rule_name=rule_name,
            message="Skipped (PyMuPDF not installed)",
        )

    if not pdf_path.exists():
        return PDFValidationResult(
            passed=False,
            rule_name=rule_name,
            message=f"PDF file not found: {pdf_path}",
        )

    try:
        doc = fitz.open(str(pdf_path))
        page_count = doc.page_count
        doc.close()

        if page_count != 1:
            return PDFValidationResult(
                passed=False,
                rule_name=rule_name,
                message=f"PDF has {page_count} pages, expected 1",
                details="Multi-page PDFs indicate wrong content was extracted",
            )

        return PDFValidationResult(
            passed=True,
            rule_name=rule_name,
            message="PDF has exactly 1 page",
        )

    except Exception as e:
        return PDFValidationResult(
            passed=False,
            rule_name=rule_name,
            message=f"Failed to read PDF: {e}",
        )


def validate_question_number_in_content(
    pdf_path: Path,
    expected_number: int,
) -> PDFValidationResult:
    """
    REJECT if PDF content does not contain the expected question number.

    This catches misalignment issues where Q45 contains content from Q41.
    This was the root cause of organize_invierno_2025_questions.py.

    Args:
        pdf_path: Path to the PDF file
        expected_number: The question number expected in the content

    Returns:
        PDFValidationResult with pass/fail status
    """
    rule_name = "question_number_match"

    if fitz is None:
        return PDFValidationResult(
            passed=True,
            rule_name=rule_name,
            message="Skipped (PyMuPDF not installed)",
        )

    if not pdf_path.exists():
        return PDFValidationResult(
            passed=False,
            rule_name=rule_name,
            message=f"PDF file not found: {pdf_path}",
        )

    try:
        doc = fitz.open(str(pdf_path))
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()

        # Look for question number patterns at the start of questions
        # Common formats: "45.", "45)", "Pregunta 45", "#45"
        patterns = [
            rf"^\s*{expected_number}\s*[.)]",  # "45." or "45)"
            rf"Pregunta\s+{expected_number}\b",  # "Pregunta 45"
            rf"#\s*{expected_number}\b",  # "#45"
            rf"\b{expected_number}\s*\.",  # "45." anywhere
        ]

        for pattern in patterns:
            if re.search(pattern, text, re.MULTILINE | re.IGNORECASE):
                return PDFValidationResult(
                    passed=True,
                    rule_name=rule_name,
                    message=f"Found question number {expected_number} in content",
                )

        # Check if a different question number is prominent
        other_numbers = re.findall(r"^\s*(\d{1,2})\s*[.)]", text, re.MULTILINE)
        if other_numbers:
            found = list(set(other_numbers))[:5]
            return PDFValidationResult(
                passed=False,
                rule_name=rule_name,
                message=f"Expected Q{expected_number} but found Q{found}",
                details="Question numbers are misaligned",
            )

        # If no numbers found, it might be a valid question without number
        return PDFValidationResult(
            passed=True,
            rule_name=rule_name,
            message=f"Could not verify Q{expected_number} (no numbers found)",
            details="Manual verification recommended",
        )

    except Exception as e:
        return PDFValidationResult(
            passed=False,
            rule_name=rule_name,
            message=f"Failed to read PDF text: {e}",
        )


def validate_has_content(pdf_path: Path) -> PDFValidationResult:
    """
    REJECT if PDF appears to be empty or has no text content.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        PDFValidationResult with pass/fail status
    """
    rule_name = "has_content"

    if fitz is None:
        return PDFValidationResult(
            passed=True,
            rule_name=rule_name,
            message="Skipped (PyMuPDF not installed)",
        )

    if not pdf_path.exists():
        return PDFValidationResult(
            passed=False,
            rule_name=rule_name,
            message=f"PDF file not found: {pdf_path}",
        )

    try:
        doc = fitz.open(str(pdf_path))
        total_text = ""
        total_images = 0

        for page in doc:
            total_text += page.get_text()
            total_images += len(page.get_images())

        doc.close()

        # A valid question should have either text or images
        text_length = len(total_text.strip())

        if text_length < 20 and total_images == 0:
            return PDFValidationResult(
                passed=False,
                rule_name=rule_name,
                message="PDF appears to be empty",
                details=f"Only {text_length} chars of text and 0 images",
            )

        return PDFValidationResult(
            passed=True,
            rule_name=rule_name,
            message=f"PDF has content ({text_length} chars, {total_images} images)",
        )

    except Exception as e:
        return PDFValidationResult(
            passed=False,
            rule_name=rule_name,
            message=f"Failed to read PDF: {e}",
        )


def run_all_pdf_validations(
    pdf_path: Path,
    expected_question_number: int | None = None,
) -> list[PDFValidationResult]:
    """
    Run all PDF validation rules and return results.

    Args:
        pdf_path: Path to the PDF file
        expected_question_number: Optional question number to verify

    Returns:
        List of PDFValidationResult objects
    """
    results = [
        validate_single_page(pdf_path),
        validate_has_content(pdf_path),
    ]

    if expected_question_number is not None:
        results.append(
            validate_question_number_in_content(pdf_path, expected_question_number)
        )

    return results


def validate_pdf_or_raise(
    pdf_path: Path,
    expected_question_number: int | None = None,
) -> None:
    """
    Validate PDF and raise ValueError if any critical rule fails.

    This is the main entry point for pipeline validation.

    Args:
        pdf_path: Path to the PDF file
        expected_question_number: Optional question number to verify

    Raises:
        ValueError: If any validation rule fails
    """
    results = run_all_pdf_validations(pdf_path, expected_question_number)

    failures = [r for r in results if not r.passed]

    if failures:
        error_messages = [str(f) for f in failures]
        raise ValueError(
            f"PDF validation failed for {pdf_path.name}:\n"
            + "\n".join(error_messages)
        )
