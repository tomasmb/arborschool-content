"""
PDF Table Extraction Module

Handles table detection and extraction from PDF pages using PyMuPDF
and scattered block reconstruction.
"""

from __future__ import annotations

from typing import Any

import fitz  # type: ignore

from .content_processing.table_reconstructor import (
    detect_scattered_table_blocks,
    reconstruct_table_from_blocks,
)
from .utils import convert_table_to_html


def extract_tables_with_pymupdf(page: fitz.Page) -> list[dict[str, Any]]:
    """
    Extract tables using PyMuPDF's built-in detection.

    Args:
        page: PyMuPDF page object

    Returns:
        List of detected tables with content and metadata
    """
    detected_tables: list[dict[str, Any]] = []

    try:
        table_finder = page.find_tables()
        tables = list(table_finder)  # Convert TableFinder to list

        if tables:
            print(f"📊 PyMuPDF detected {len(tables)} tables")

            for i, table in enumerate(tables):
                table_data = table.extract()
                table_bbox = table.bbox

                structured_table = {
                    "type": "detected_table",
                    "table_index": i,
                    "bbox": list(table_bbox),
                    "rows": len(table_data) if table_data else 0,
                    "cols": len(table_data[0]) if table_data and len(table_data) > 0 else 0,
                    "content": table_data,
                    "html_content": convert_table_to_html(table_data),
                }

                detected_tables.append(structured_table)
                print(f"📊 ✅ Table {i+1}: {structured_table['rows']}x{structured_table['cols']}")
        else:
            print("📊 No tables detected by PyMuPDF")

    except Exception as e:
        print(f"⚠️ PyMuPDF table detection failed: {e}")

    return detected_tables


def try_reconstruct_table_from_blocks(
    all_blocks: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """
    Try to reconstruct a table from scattered text blocks.

    This is used when PyMuPDF's built-in table detection fails but
    the content appears to be tabular based on block layout.

    Args:
        all_blocks: All blocks from PyMuPDF structured data

    Returns:
        Reconstructed table dict, or None if reconstruction fails
    """
    print("📊 Step 1.5: PyMuPDF found no tables, trying reconstruction...")

    table_structure = detect_scattered_table_blocks(all_blocks)
    if table_structure:
        reconstructed_table = reconstruct_table_from_blocks(table_structure)
        if reconstructed_table:
            print("📊 ✅ Reconstructed table from scattered blocks")
            return reconstructed_table

    return None
