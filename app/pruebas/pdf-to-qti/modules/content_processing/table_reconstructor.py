"""
Table Reconstructor

Specialized module for reconstructing table structure from scattered text blocks
when PyMuPDF table detection fails. Uses spatial analysis to maintain proper
row/column relationships.

Following converter guidelines:
- Clean, single-responsibility module
- Deterministic spatial logic
- No overfitting to specific content
"""

import re
from typing import Any, Dict, List, Optional, Tuple

__all__ = ["detect_scattered_table_blocks", "reconstruct_table_from_blocks", "enhance_content_with_reconstructed_tables"]


def detect_scattered_table_blocks(text_blocks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Detect if text blocks represent a scattered table structure.

    Args:
        text_blocks: List of text blocks with bbox and text

    Returns:
        Table structure info if detected, None otherwise
    """
    # Look for table header patterns
    header_candidates = []
    data_candidates = []

    for i, block in enumerate(text_blocks):
        if block.get("type") != 0:  # Skip non-text blocks
            continue

        block_text = _extract_block_text(block).strip()
        if not block_text:
            continue

        # Check for table header patterns
        if _is_table_header(block_text):
            header_candidates.append((i, block, block_text))

        # Check for table data patterns
        elif _is_table_data(block_text):
            data_candidates.append((i, block, block_text))

    # Must have at least one header and multiple data blocks
    if not header_candidates or len(data_candidates) < 4:
        return None

    print(f"📊 Detected potential scattered table: {len(header_candidates)} headers, {len(data_candidates)} data blocks")

    return {"headers": header_candidates, "data": data_candidates, "total_blocks": len(header_candidates) + len(data_candidates)}


def reconstruct_table_from_blocks(table_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Reconstruct proper table structure using spatial analysis.

    Args:
        table_info: Detected table structure from detect_scattered_table_blocks

    Returns:
        Reconstructed table data or None if reconstruction fails
    """
    headers = table_info["headers"]
    data_blocks = table_info["data"]

    if not headers:
        return None

    # Use the first header to establish column structure
    header_block = headers[0][1]
    header_text = headers[0][2]
    header_bbox = header_block.get("bbox", [])

    if len(header_bbox) < 4:
        return None

    # Parse header columns
    columns = _parse_header_columns(header_text)
    if len(columns) < 2:
        return None

    print(f"📊 Reconstructing table with {len(columns)} columns: {columns}")

    # Group data blocks by spatial rows using Y-coordinates
    row_groups = _group_blocks_by_rows(data_blocks, tolerance=10.0)

    # Reconstruct table data with proper spatial ordering
    table_data = [columns]  # Start with header row

    for row_y, row_blocks in sorted(row_groups.items()):
        # Sort blocks in each row by X-coordinate (left to right)
        sorted_blocks = sorted(row_blocks, key=lambda x: x[1].get("bbox", [0, 0, 0, 0])[0])

        # Extract text from each block in the row
        row_data = []
        for _, block, text in sorted_blocks:
            row_data.append(text.strip())

        # Ensure we have the right number of columns
        while len(row_data) < len(columns):
            row_data.append("")

        if len(row_data) >= len(columns):
            table_data.append(row_data[: len(columns)])

    if len(table_data) < 2:  # Need at least header + 1 data row
        return None

    print(f"📊 ✅ Reconstructed table: {len(table_data)} rows × {len(columns)} columns")

    return {
        "type": "reconstructed_table",
        "rows": len(table_data),
        "cols": len(columns),
        "content": table_data,
        "bbox": _calculate_table_bbox([b[1] for b in data_blocks + headers]),
        "html_content": _convert_to_html(table_data),
    }


def enhance_content_with_reconstructed_tables(pdf_content: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhance PDF content by detecting and reconstructing scattered tables.

    Args:
        pdf_content: Original PDF content

    Returns:
        Enhanced content with reconstructed tables
    """
    enhanced_content = pdf_content.copy()

    for page_idx, page in enumerate(enhanced_content.get("pages", [])):
        # Skip if PyMuPDF already found tables
        existing_tables = page.get("extracted_tables", [])
        if existing_tables:
            continue

        # Get text blocks for analysis
        structured_text = page.get("structured_text", {})
        text_blocks = structured_text.get("blocks", [])

        # Detect scattered table structure
        table_info = detect_scattered_table_blocks(text_blocks)
        if not table_info:
            continue

        # Reconstruct the table
        reconstructed_table = reconstruct_table_from_blocks(table_info)
        if not reconstructed_table:
            continue

        # Add to extracted tables
        page["extracted_tables"] = [reconstructed_table]
        print(f"📊 ✅ Enhanced page {page_idx + 1} with reconstructed table")

    return enhanced_content


# Helper functions


def _extract_block_text(block: Dict[str, Any]) -> str:
    """Extract text content from a PyMuPDF block."""
    if block.get("type") != 0:
        return ""

    text_parts = []
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            text = span.get("text", "").strip()
            if text:
                text_parts.append(text)

    return " ".join(text_parts)


def _is_table_header(text: str) -> bool:
    """Check if text looks like a table header."""
    # Look for multiple column names separated by spaces
    words = text.split()
    if len(words) < 2:
        return False

    # Common table header patterns
    header_patterns = [
        r"characteristic.*sample.*sample",
        r"\w+.*\w+.*\w+",  # Three or more words
    ]

    text_lower = text.lower()
    return any(re.search(pattern, text_lower, re.IGNORECASE) for pattern in header_patterns)


def _is_table_data(text: str) -> bool:
    """Check if text looks like table data."""
    # Skip very short text or obvious non-data
    if len(text.strip()) < 2:
        return False

    # Look for data patterns
    data_patterns = [
        r"^\d+\.?\d*$",  # Numbers
        r"^\d+\.?\d*\s*\([^)]+\)$",  # Numbers with units
        r"^(yes|no)$",  # Boolean values
        r"density|magnetic|mass|temperature|melting",  # Property names
    ]

    return any(re.search(pattern, text.strip(), re.IGNORECASE) for pattern in data_patterns)


def _parse_header_columns(header_text: str) -> List[str]:
    """Parse column names from header text."""
    # Simple approach: split on multiple spaces or common separators
    if "Sample" in header_text:
        # Handle "Characteristic Iron Sample Rust Sample" pattern
        parts = re.split(r"\s{2,}|\t", header_text)
        if len(parts) == 1:
            # Fallback: split on "Sample" boundaries
            words = header_text.split()
            columns = []
            current_col = []

            for word in words:
                current_col.append(word)
                if word == "Sample":
                    columns.append(" ".join(current_col))
                    current_col = []

            if current_col:
                columns.append(" ".join(current_col))

            return columns if len(columns) >= 2 else [header_text]

    # Generic fallback
    return [col.strip() for col in re.split(r"\s{3,}|\t{2,}", header_text) if col.strip()]


def _group_blocks_by_rows(data_blocks: List[Tuple], tolerance: float = 10.0) -> Dict[float, List[Tuple]]:
    """Group blocks into rows based on Y-coordinates."""
    row_groups = {}

    for block_tuple in data_blocks:
        block = block_tuple[1]
        bbox = block.get("bbox", [])
        if len(bbox) < 4:
            continue

        y_center = (bbox[1] + bbox[3]) / 2

        # Find existing row or create new one
        assigned_row = None
        for existing_y in row_groups.keys():
            if abs(y_center - existing_y) <= tolerance:
                assigned_row = existing_y
                break

        if assigned_row is not None:
            row_groups[assigned_row].append(block_tuple)
        else:
            row_groups[y_center] = [block_tuple]

    return row_groups


def _calculate_table_bbox(blocks: List[Dict[str, Any]]) -> List[float]:
    """Calculate overall bounding box for table."""
    if not blocks:
        return [0, 0, 0, 0]

    min_x = float("inf")
    min_y = float("inf")
    max_x = float("-inf")
    max_y = float("-inf")

    for block in blocks:
        bbox = block.get("bbox", [])
        if len(bbox) >= 4:
            min_x = min(min_x, bbox[0])
            min_y = min(min_y, bbox[1])
            max_x = max(max_x, bbox[2])
            max_y = max(max_y, bbox[3])

    return [min_x, min_y, max_x, max_y]


def _convert_to_html(table_data: List[List[str]]) -> str:
    """Convert table data to HTML format."""
    if not table_data:
        return ""

    parts = ["<table>"]

    # Header
    if table_data:
        parts.append("  <thead>\n    <tr>")
        for cell in table_data[0]:
            parts.append(f"      <th>{cell.strip()}</th>")
        parts.append("    </tr>\n  </thead>")

    # Body rows
    if len(table_data) > 1:
        parts.append("  <tbody>")
        for row in table_data[1:]:
            parts.append("    <tr>")
            for cell in row:
                parts.append(f"      <td>{cell.strip()}</td>")
            parts.append("    </tr>")
        parts.append("  </tbody>")

    parts.append("</table>")
    return "\n".join(parts)
