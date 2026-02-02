"""
PDF Manipulation Utilities

Low-level functions for creating, saving, and merging PDF documents.
"""

from __future__ import annotations

import os

import fitz  # type: ignore # PyMuPDF


def create_pdf_from_region(source_page: fitz.Page, rect: fitz.Rect, output_path: str) -> None:
    """
    Creates a new PDF file containing only the specified region of a source page.

    Args:
        source_page: The fitz.Page object to extract the region from.
        rect: A fitz.Rect defining the bounding box of the region to extract.
        output_path: Path to save the new PDF.
    """
    new_doc = fitz.open()
    new_page = new_doc.new_page(width=rect.width, height=rect.height)

    target_rect = fitz.Rect(0, 0, rect.width, rect.height)
    new_page.show_pdf_page(target_rect, source_page.parent, source_page.number, clip=rect)

    try:
        new_doc.save(output_path)
        print(f"Saved PDF region to: {output_path}")
    except Exception as e:
        print(f"Error saving PDF region {output_path}: {e}")
    finally:
        new_doc.close()


def save_pdf_pages(doc: fitz.Document, page_numbers: list[int], output_path: str) -> None:
    """
    Saves specified pages from a document to a new PDF file.

    Args:
        doc: The source fitz.Document.
        page_numbers: A list of 0-indexed page numbers to include.
        output_path: Path to save the new PDF.
    """
    new_doc = fitz.open()

    for page_num in page_numbers:
        if 0 <= page_num < doc.page_count:
            new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)

    if len(new_doc) > 0:
        new_doc.save(output_path)
        print(f"Saved PDF: {output_path} with pages: {[p + 1 for p in page_numbers]}")
    else:
        print(f"Warning: No pages selected for PDF: {output_path}")

    new_doc.close()


def merge_pdfs(pdf_paths: list[str], output_path: str) -> None:
    """
    Merges multiple PDF files into a single PDF file.

    Args:
        pdf_paths: List of paths to PDF files to merge.
        output_path: Path to save the merged PDF.
    """
    merged_doc = fitz.open()

    for pdf_path in pdf_paths:
        if os.path.exists(pdf_path):
            try:
                src_doc = fitz.open(pdf_path)
                merged_doc.insert_pdf(src_doc)
                src_doc.close()
            except Exception as e:
                print(f"Error merging {pdf_path}: {e}")
        else:
            print(f"Warning: PDF not found for merging: {pdf_path}")

    if len(merged_doc) > 0:
        merged_doc.save(output_path)
        print(f"Saved merged PDF: {output_path}")
    else:
        print(f"Warning: No documents to merge for: {output_path}")

    merged_doc.close()


def extract_page_region_with_margin(
    page: fitz.Page,
    bbox: list[float],
    margin: int = 10
) -> fitz.Rect:
    """
    Create a fitz.Rect from a bbox with margin, clamped to page boundaries.

    Args:
        page: The PDF page
        bbox: Bounding box as [x1, y1, x2, y2]
        margin: Margin to add around the bbox

    Returns:
        A fitz.Rect clamped to page boundaries
    """
    x1 = max(0, bbox[0] - margin)
    y1 = max(0, bbox[1] - margin)
    x2 = min(page.rect.width, bbox[2] + margin)
    y2 = min(page.rect.height, bbox[3] + margin)
    return fitz.Rect(x1, y1, x2, y2)
