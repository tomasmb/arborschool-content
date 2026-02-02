"""
PDF Rendering and Text Extraction

Functions for extracting text and rendering images from PDF pages,
including fallback strategies for complex pages.
"""

from __future__ import annotations

import base64
import json
from json import JSONEncoder

import fitz  # type: ignore # PyMuPDF


class CustomJSONEncoder(JSONEncoder):
    """Custom JSON encoder that can handle bytes objects."""

    def default(self, obj):
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode('utf-8')
        return JSONEncoder.default(self, obj)


def get_page_structured_text(page: fitz.Page) -> str:
    """
    Extracts structured text from a PyMuPDF page object.
    Uses the "dict" output and serializes it to a JSON string for the LLM.

    Args:
        page: The fitz.Page object to extract text from.

    Returns:
        A JSON string containing the structured text.
    """
    structured_output = page.get_text("dict", sort=True)
    return json.dumps(structured_output, cls=CustomJSONEncoder)


def get_optimized_page_content(page: fitz.Page, max_length: int = 8000) -> str:
    """
    Creates an optimized representation of page content that prioritizes
    important elements while keeping the output size manageable.

    Args:
        page: The fitz.Page object to process
        max_length: Target maximum length for the optimized content

    Returns:
        A string containing the optimized representation of the page content
    """
    import re

    blocks_data = page.get_text("dict", sort=True)

    summary: dict = {
        "page_size": {"width": page.rect.width, "height": page.rect.height},
        "blocks_count": len(blocks_data.get("blocks", [])),
        "page_description": "PDF page with the following elements:"
    }

    blocks = blocks_data.get("blocks", [])

    # Extract text blocks and sort by position (top to bottom)
    text_blocks = [b for b in blocks if b.get("type") == 0]
    text_blocks.sort(key=lambda b: b.get("bbox", [0, 0, 0, 0])[1])

    important_texts = []
    question_markers = []

    # First pass: identify question markers and headers
    for block in text_blocks:
        text = _extract_block_text(block)
        if not text:
            continue

        if re.search(r'question\s+\d+|^\d+\.\s+', text.lower()) or text.upper() == text:
            question_markers.append({
                "text": text,
                "bbox": block.get("bbox"),
                "type": "question_marker"
            })
        elif len(text) < 100:
            important_texts.append({
                "text": text,
                "bbox": block.get("bbox"),
                "type": "header"
            })

    # Second pass: get a representative sample of content
    remaining_length = (
        max_length
        - len(json.dumps(summary))
        - len(json.dumps(question_markers))
        - len(json.dumps(important_texts))
    )

    content_samples = _extract_content_samples(
        text_blocks, question_markers, important_texts, remaining_length
    )

    summary["question_markers"] = question_markers
    summary["important_texts"] = important_texts
    summary["content_samples"] = content_samples
    summary["original_block_count"] = len(blocks)

    return json.dumps(summary, cls=CustomJSONEncoder)


def _extract_block_text(block: dict) -> str:
    """Extract text from a single block."""
    text = ""
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            span_text = span.get("text", "").strip()
            text += span_text + " "
    return text.strip()


def _extract_content_samples(
    text_blocks: list,
    question_markers: list,
    important_texts: list,
    remaining_length: int
) -> list:
    """Extract a representative sample of content blocks."""
    content_samples = []

    if remaining_length <= 1000:
        return content_samples

    current_length = 0
    existing_texts = {item["text"] for item in question_markers + important_texts}

    for block in text_blocks:
        if current_length > remaining_length:
            break

        text = _extract_block_text(block)
        if not text or text in existing_texts:
            continue

        block_summary = {
            "text": text[:min(len(text), 200)],
            "bbox": block.get("bbox"),
            "type": "content"
        }

        content_samples.append(block_summary)
        current_length += len(json.dumps(block_summary))

    return content_samples


def get_page_image(page: fitz.Page, scale: float = 2.0) -> bytes:
    """
    Renders a page as an image with fallback strategies for complex pages.

    Args:
        page: The fitz.Page to render
        scale: Scale factor for resolution (higher = better quality but larger size)

    Returns:
        PNG image data as bytes
    """
    # Strategy 1: Try normal rendering
    try:
        matrix = fitz.Matrix(scale, scale)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        return pixmap.tobytes("png")
    except RuntimeError as e:
        if "Private data too large" in str(e):
            print("⚠️  Complex page detected, trying fallback strategies...")
        else:
            raise e

    # Strategy 2: Reduce scale factor
    fallback_scales = [1.5, 1.0, 0.75, 0.5]
    for fallback_scale in fallback_scales:
        try:
            print(f"🔄 Trying reduced scale: {fallback_scale}")
            matrix = fitz.Matrix(fallback_scale, fallback_scale)
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            return pixmap.tobytes("png")
        except RuntimeError as e:
            if "Private data too large" not in str(e):
                raise e
            continue

    # Strategy 3: Try without display list (direct rendering)
    try:
        print("🔄 Trying direct rendering without display list...")
        matrix = fitz.Matrix(1.0, 1.0)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False, annots=False)
        return pixmap.tobytes("png")
    except RuntimeError as e:
        if "Private data too large" not in str(e):
            raise e

    # Strategy 4: Create a minimal placeholder image
    return _create_placeholder_image(page)


def _create_placeholder_image(page: fitz.Page) -> bytes:
    """Create a placeholder image when rendering fails."""
    print("⚠️  All rendering strategies failed, creating placeholder image")
    try:
        import io

        from PIL import Image, ImageDraw, ImageFont  # type: ignore

        img = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.load_default()
        except Exception:
            font = None

        text = f"Page {page.number + 1}\nContent too complex to render\nText extraction available"
        draw.text((50, 250), text, fill='black', font=font)

        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        return img_bytes.getvalue()

    except Exception as fallback_error:
        print(f"❌ Even placeholder creation failed: {fallback_error}")
        # Return a minimal 1x1 white pixel as absolute fallback
        return (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13'
            b'\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x12IDATx\x9cc```'
            b'bPPP\x00\x02\xac\xea\x05\x1b\x00\x00\x00\x00IEND\xaeB`\x82'
        )
