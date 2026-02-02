"""MathML parsing utilities.

This module provides a centralized MathML-to-text conversion function used across
multiple modules (tagging, question_variants, etc.) to avoid code duplication.

The conversion produces a human-readable text representation of mathematical
expressions, suitable for LLM processing and display.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET


def process_mathml(element: ET.Element) -> str:
    """Recursively convert a MathML element to readable text representation.

    This function handles common MathML elements and converts them to a
    human-readable format suitable for text processing.

    Args:
        element: An XML Element representing MathML content.

    Returns:
        A string representation of the mathematical expression.

    Examples:
        <mfrac><mn>1</mn><mn>2</mn></mfrac> -> "(1/2)"
        <msup><mi>x</mi><mn>2</mn></msup> -> "x^(2)"
        <msqrt><mn>4</mn></msqrt> -> "sqrt(4)"
    """
    tag = element.tag.split('}')[-1].lower()  # Handle namespaced tags

    if tag == 'mfrac':
        return _process_fraction(element)
    elif tag == 'msup':
        return _process_superscript(element)
    elif tag == 'msub':
        return _process_subscript(element)
    elif tag in ('msqrt', 'mroot'):
        return _process_root(element, tag)
    elif tag == 'mfenced':
        return _process_fenced(element)
    elif tag == 'mtable':
        return _process_table(element)
    elif tag == 'mtr':
        return _process_table_row(element)
    elif tag == 'mtd':
        return _process_table_cell(element)
    elif tag in ('mi', 'mn', 'mo', 'mtext'):
        return (element.text or "").strip()
    elif tag in ('mrow', 'math', 'mstyle'):
        # Container elements - process children
        return _process_children(element)
    else:
        # Default: recursive join of all children text/processing
        return _process_default(element)


def _process_fraction(element: ET.Element) -> str:
    """Process mfrac element (fraction)."""
    children = list(element)
    if len(children) >= 2:
        num = process_mathml(children[0])
        den = process_mathml(children[1])
        return f"({num}/{den})"
    return _process_default(element)


def _process_superscript(element: ET.Element) -> str:
    """Process msup element (superscript/exponent)."""
    children = list(element)
    if len(children) >= 2:
        base = process_mathml(children[0])
        exp = process_mathml(children[1])
        return f"{base}^({exp})"
    return _process_default(element)


def _process_subscript(element: ET.Element) -> str:
    """Process msub element (subscript)."""
    children = list(element)
    if len(children) >= 2:
        base = process_mathml(children[0])
        sub = process_mathml(children[1])
        return f"{base}_({sub})"
    return _process_default(element)


def _process_root(element: ET.Element, tag: str) -> str:
    """Process msqrt or mroot element (square root or nth root)."""
    children = list(element)
    if tag == 'msqrt':
        inner = "".join([process_mathml(c) for c in children])
        return f"sqrt({inner})"
    elif len(children) >= 2:
        # mroot: first child is radicand, second is index
        inner = process_mathml(children[0])
        index = process_mathml(children[1])
        return f"root[{index}]({inner})"
    return _process_default(element)


def _process_fenced(element: ET.Element) -> str:
    """Process mfenced element (parentheses, brackets, etc.)."""
    inner = "".join([process_mathml(c) for c in element])
    return f"({inner})"


def _process_table(element: ET.Element) -> str:
    """Process mtable element (matrix/table)."""
    rows = []
    for row in element:
        rows.append(process_mathml(row))
    return " [ " + " ; ".join(rows) + " ] "


def _process_table_row(element: ET.Element) -> str:
    """Process mtr element (table row)."""
    cols = []
    for col in element:
        cols.append(process_mathml(col))
    return " ".join(cols)


def _process_table_cell(element: ET.Element) -> str:
    """Process mtd element (table cell)."""
    parts = []
    if element.text:
        parts.append(element.text.strip())
    for child in element:
        parts.append(process_mathml(child))
    return "".join(parts)


def _process_children(element: ET.Element) -> str:
    """Process children of container elements."""
    parts = []
    for child in element:
        parts.append(process_mathml(child))
    return "".join(parts)


def _process_default(element: ET.Element) -> str:
    """Default processing: recursive join of all children text."""
    parts = []
    if element.text:
        parts.append(element.text.strip())
    for child in element:
        parts.append(process_mathml(child))
        if child.tail:
            parts.append(child.tail.strip())
    return "".join(parts)


def extract_math_tokens(element: ET.Element) -> list[str]:
    """Extract individual math tokens from a MathML element.

    This is a simpler extraction that just gets the text content of
    mn, mi, mo, and mtext elements without structure.

    Args:
        element: An XML Element representing MathML content.

    Returns:
        A list of text tokens found in the MathML.
    """
    tokens = []
    for child in element.iter():
        tag = child.tag.split('}')[-1].lower()
        if tag in ('mn', 'mi', 'mo', 'mtext') and child.text:
            tokens.append(child.text.strip())
    return tokens
