"""
PDF Text Processing Module

Handles extraction and processing of text blocks from PDF structured data.
Includes choice block splitting for multi-choice answer detection.
"""

from __future__ import annotations

import base64
import re
from json import JSONEncoder
from typing import Any


class CustomJSONEncoder(JSONEncoder):
    """Custom JSON encoder that can handle bytes objects."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode("utf-8")
        return JSONEncoder.default(self, obj)


def extract_text_blocks(structured_data: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extract text blocks from structured data.

    Args:
        structured_data: PyMuPDF structured text data

    Returns:
        List of text blocks with extracted text content
    """
    blocks = structured_data.get("blocks", [])
    text_blocks = []

    for i, block in enumerate(blocks):
        if block.get("type") == 0:  # Text block
            block_copy = block.copy()
            block_copy["text"] = extract_block_text(block)
            block_copy["number"] = i
            text_blocks.append(block_copy)

    return text_blocks


def extract_block_text(block: dict[str, Any]) -> str:
    """
    Extract text from a PyMuPDF text block.

    Note: Does NOT auto-fix encoding errors because string replacement
    is error-prone (could match IDs, codes, etc.). Encoding errors are
    detected and the pipeline rejects content that has them.

    Args:
        block: PyMuPDF block dictionary

    Returns:
        Extracted text string (raw, without auto-correction)
    """
    text_parts = []

    for line in block.get("lines", []):
        line_text = ""
        for span in line.get("spans", []):
            line_text += span.get("text", "")
        text_parts.append(line_text)

    return " ".join(text_parts).strip()


def extract_question_text(text_blocks: list[dict[str, Any]]) -> str:
    """
    Extract combined question text from all text blocks for choice diagram detection.

    Args:
        text_blocks: List of text blocks from PyMuPDF

    Returns:
        Combined text string
    """
    combined_text = ""

    for block in text_blocks:
        if block.get("type") == 0:  # Text block
            block_text = extract_block_text(block)
            if block_text.strip():
                combined_text += " " + block_text.strip()

    return combined_text.strip()


def split_choice_blocks(structured_data: dict[str, Any]) -> dict[str, Any]:
    """
    Split blocks that contain multiple answer choices into separate blocks.

    This fixes the issue where PyMuPDF groups multiple choice letters (e.g., "A B")
    into a single block, which causes problems with choice image extraction.

    Args:
        structured_data: PyMuPDF structured text data containing blocks

    Returns:
        Modified structured data with choice blocks split appropriately
    """
    blocks = structured_data.get("blocks", [])
    new_blocks = []

    for block in blocks:
        if block.get("type") != 0:  # Not a text block
            new_blocks.append(block)
            continue

        # Extract text from the block to check for multiple choices
        block_text = extract_block_text(block)

        # Check if this block contains multiple choice letters
        # Pattern: Look for blocks with multiple choice letters (A, B, C, D) separated by whitespace
        choice_pattern = r"(?:^|\s)([A-D])(?:\s|$)"
        choice_matches = re.findall(choice_pattern, block_text)

        # Only split if we find exactly 2 choice letters (common grouping pattern)
        # and the block is relatively short (to avoid splitting long text blocks)
        if len(choice_matches) == 2 and len(block_text.strip()) < 50:
            print(f"🔧 Splitting choice block: '{block_text.strip()}' -> {choice_matches}")
            split_blocks = _split_block_by_choices(block, choice_matches)
            new_blocks.extend(split_blocks)
        else:
            # Keep original block unchanged
            new_blocks.append(block)

    # Return modified structured data
    result = structured_data.copy()
    result["blocks"] = new_blocks
    return result


def _split_block_by_choices(
    block: dict[str, Any], choice_matches: list[str]
) -> list[dict[str, Any]]:
    """
    Split a block containing multiple choices into separate blocks.

    Args:
        block: The block to split
        choice_matches: List of choice letters found (e.g., ['A', 'B'])

    Returns:
        List of split blocks (or original block if split fails)
    """
    lines = block.get("lines", [])
    first_choice_lines: list[dict[str, Any]] = []
    second_choice_lines: list[dict[str, Any]] = []

    # Analyze each line to see which choice it belongs to
    for line in lines:
        line_text = ""
        for span in line.get("spans", []):
            line_text += span.get("text", "")

        # Check which choice letter this line contains
        if choice_matches[0] in line_text and choice_matches[1] not in line_text:
            first_choice_lines.append(line)
        elif choice_matches[1] in line_text and choice_matches[0] not in line_text:
            second_choice_lines.append(line)
        elif choice_matches[0] in line_text and choice_matches[1] in line_text:
            # Line contains both - split based on horizontal position
            first_spans, second_spans = _split_line_by_position(line)
            if first_spans:
                first_line = line.copy()
                first_line["spans"] = first_spans
                first_choice_lines.append(first_line)
            if second_spans:
                second_line = line.copy()
                second_line["spans"] = second_spans
                second_choice_lines.append(second_line)
        else:
            # Line doesn't contain either choice - could be shared content
            first_choice_lines.append(line)
            second_choice_lines.append(line)

    # Create the two new blocks if we successfully split
    if first_choice_lines and second_choice_lines:
        first_block = block.copy()
        first_block["lines"] = first_choice_lines
        first_block["bbox"] = _calculate_bbox_from_lines(first_choice_lines, block.get("bbox"))

        second_block = block.copy()
        second_block["lines"] = second_choice_lines
        second_block["bbox"] = _calculate_bbox_from_lines(second_choice_lines, block.get("bbox"))

        return [first_block, second_block]

    # Fallback: keep original block if we can't split properly
    return [block]


def _split_line_by_position(line: dict[str, Any]) -> tuple[list[Any], list[Any]]:
    """
    Split a line's spans into left and right halves based on horizontal position.

    Args:
        line: Line dictionary with spans

    Returns:
        Tuple of (left_spans, right_spans)
    """
    spans = line.get("spans", [])
    if not spans:
        return [], []

    first_spans: list[Any] = []
    second_spans: list[Any] = []

    # Find horizontal middle of the line
    line_left = min(span.get("bbox", [0, 0, 0, 0])[0] for span in spans if span.get("bbox"))
    line_right = max(span.get("bbox", [0, 0, 0, 0])[2] for span in spans if span.get("bbox"))
    line_middle = (line_left + line_right) / 2

    for span in spans:
        span_bbox = span.get("bbox", [0, 0, 0, 0])
        span_center = (span_bbox[0] + span_bbox[2]) / 2

        if span_center < line_middle:
            first_spans.append(span)
        else:
            second_spans.append(span)

    return first_spans, second_spans


def _calculate_bbox_from_lines(
    lines: list[dict[str, Any]], fallback_bbox: list[float] | None
) -> list[float]:
    """
    Calculate bounding box from a list of lines.

    Args:
        lines: List of line dictionaries with spans
        fallback_bbox: Fallback bbox if calculation fails

    Returns:
        Calculated or fallback bounding box
    """
    spans_bboxes: list[list[float]] = []

    for line in lines:
        for span in line.get("spans", []):
            if span.get("bbox"):
                spans_bboxes.append(span["bbox"])

    if spans_bboxes:
        return [
            min(bbox[0] for bbox in spans_bboxes),
            min(bbox[1] for bbox in spans_bboxes),
            max(bbox[2] for bbox in spans_bboxes),
            max(bbox[3] for bbox in spans_bboxes),
        ]

    return fallback_bbox if fallback_bbox else [0, 0, 0, 0]
