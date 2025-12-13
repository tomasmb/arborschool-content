"""table_utils.py
------------------
Table conversion helpers for PyMuPDF detected tables.
Following converter guidelines: use PyMuPDF first, avoid overfitted heuristics.
"""

from __future__ import annotations

from typing import Any, Dict, List

__all__ = [
    "convert_table_to_html",
]


def convert_table_to_html(data: List[List[str]]) -> str:
    """
    Convert PyMuPDF table data to HTML format.
    
    Args:
        data: List of rows, where each row is a list of cell strings
        
    Returns:
        HTML table string
    """
    if not data or not data[0]:
        return ""
        
    parts: List[str] = ["<table>"]
    
    # Check if first row should be treated as header
    header = data[0]
    has_header = any((cell or "").strip() for cell in header)
    
    if has_header:
        parts.append("  <thead>\n    <tr>")
        parts.extend(f"      <th>{(cell or '').strip()}</th>" for cell in header)
        parts.append("    </tr>\n  </thead>")
        body_rows = data[1:]
    else:
        body_rows = data
    
    # Add body rows
    parts.append("  <tbody>")
    for row in body_rows:
        parts.append("    <tr>")
        parts.extend(f"      <td>{(cell or '').strip()}</td>" for cell in row)
        parts.append("    </tr>")
    parts.append("  </tbody>\n</table>")
    
    return "\n".join(parts) 