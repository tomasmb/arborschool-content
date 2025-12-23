#!/usr/bin/env python3
"""Extract specific questions from PDF for manual review.

This tool helps with manual review by extracting question content
directly from the PDF for comparison with segmented questions.
"""

from __future__ import annotations

import re
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    logger.warning("PyPDF2 not available. Install with: pip install PyPDF2")

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


def extract_all_text_from_pdf(pdf_path: str) -> str:
    """
    Extract all text from PDF file.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        All text content from PDF
        
    Raises:
        ImportError: If PyPDF2 is not available
        FileNotFoundError: If PDF doesn't exist
    """
    if not PYPDF2_AVAILABLE:
        raise ImportError(
            "PyPDF2 not available. Install with: pip install PyPDF2"
        )
    
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    text_parts = []
    
    with open(pdf_path, 'rb') as f:
        pdf_reader = PyPDF2.PdfReader(f)
        
        for page_num, page in enumerate(pdf_reader.pages, 1):
            try:
                text = page.extract_text()
                if text.strip():
                    text_parts.append(f"[PAGE {page_num}]\n{text}")
            except Exception as e:
                logger.warning(f"Failed to extract text from page {page_num}: {e}")
    
    return "\n\n".join(text_parts)


def find_question_in_text(text: str, question_number: int) -> Optional[str]:
    """
    Find a specific question in extracted PDF text.
    
    Args:
        text: Full text from PDF
        question_number: Question number (e.g., 46 for Q46)
        
    Returns:
        Question content if found, None otherwise
    """
    # Pattern to find question start: "46." or "46)" or "46)"
    patterns = [
        rf"^{question_number}\.\s",  # "46. "
        rf"^{question_number}\)\s",  # "46) "
        rf"^{question_number}\s+\.",  # "46 ."
    ]
    
    lines = text.split('\n')
    question_start_idx = None
    
    # Find question start
    for i, line in enumerate(lines):
        for pattern in patterns:
            if re.match(pattern, line.strip(), re.IGNORECASE):
                question_start_idx = i
                break
        if question_start_idx is not None:
            break
    
    if question_start_idx is None:
        return None
    
    # Find question end (next question or end of text)
    question_lines = []
    next_question_pattern = rf"^{question_number + 1}\."
    
    for i in range(question_start_idx, len(lines)):
        line = lines[i]
        # Stop if we hit next question
        if i > question_start_idx and re.match(next_question_pattern, line.strip()):
            break
        question_lines.append(line)
    
    return '\n'.join(question_lines).strip()


def extract_question_from_pdf(
    pdf_path: str,
    question_number: int
) -> Optional[tuple[str, int]]:
    """
    Extract a specific question from PDF.
    
    Args:
        pdf_path: Path to PDF file
        question_number: Question number (e.g., 46 for Q46)
        
    Returns:
        Tuple of (question_text, page_number) if found, None otherwise
    """
    if not PYPDF2_AVAILABLE:
        raise ImportError(
            "PyPDF2 not available. Install with: pip install PyPDF2"
        )
    
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    question_text = None
    page_number = None
    
    with open(pdf_path, 'rb') as f:
        pdf_reader = PyPDF2.PdfReader(f)
        
        for page_num, page in enumerate(pdf_reader.pages, 1):
            try:
                page_text = page.extract_text()
                if not page_text.strip():
                    continue
                
                # Try to find question on this page
                found = find_question_in_text(page_text, question_number)
                if found:
                    question_text = found
                    page_number = page_num
                    break
                    
            except Exception as e:
                logger.warning(f"Error processing page {page_num}: {e}")
    
    if question_text:
        return (question_text, page_number)
    return None


def compare_question_with_segmented(
    pdf_path: str,
    question_number: int,
    segmented_content: str
) -> dict[str, any]:
    """
    Compare PDF question with segmented content.
    
    Args:
        pdf_path: Path to PDF file
        question_number: Question number
        segmented_content: Content from segmented question (.md file)
        
    Returns:
        Dictionary with comparison results
    """
    pdf_question = extract_question_from_pdf(pdf_path, question_number)
    
    if not pdf_question:
        return {
            "found": False,
            "error": f"Question {question_number} not found in PDF"
        }
    
    pdf_text, page_num = pdf_question
    
    # Simple comparison
    pdf_lines = set(pdf_text.lower().split())
    segmented_lines = set(segmented_content.lower().split())
    
    # Find differences (very simple approach)
    only_in_pdf = pdf_lines - segmented_lines
    only_in_segmented = segmented_lines - pdf_lines
    
    return {
        "found": True,
        "page_number": page_num,
        "pdf_text": pdf_text,
        "segmented_text": segmented_content,
        "differences": {
            "only_in_pdf": list(only_in_pdf)[:20],  # Limit to 20
            "only_in_segmented": list(only_in_segmented)[:20],
        },
        "similarity": len(pdf_lines & segmented_lines) / max(len(pdf_lines), len(segmented_lines), 1)
    }


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Extract questions from PDF for manual review'
    )
    parser.add_argument(
        'pdf_path',
        help='Path to PDF file'
    )
    parser.add_argument(
        'question_number',
        type=int,
        help='Question number (e.g., 46 for Q46)'
    )
    parser.add_argument(
        '--compare',
        help='Path to segmented question .md file for comparison'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        if args.compare:
            # Compare mode
            with open(args.compare, 'r', encoding='utf-8') as f:
                segmented_content = f.read()
            
            result = compare_question_with_segmented(
                args.pdf_path,
                args.question_number,
                segmented_content
            )
            
            if result['found']:
                print(f"\n=== Question {args.question_number} (Page {result['page_number']}) ===")
                print("\nPDF Text:")
                print(result['pdf_text'])
                print("\n" + "="*70)
                print(f"\nSimilarity: {result['similarity']:.2%}")
            else:
                print(f"Error: {result['error']}")
        else:
            # Extract mode
            result = extract_question_from_pdf(args.pdf_path, args.question_number)
            
            if result:
                text, page_num = result
                print(f"\n=== Question {args.question_number} (Page {page_num}) ===")
                print(text)
            else:
                print(f"Question {args.question_number} not found in PDF")
                
    except Exception as e:
        logger.exception(f"Error: {e}")
        exit(1)
