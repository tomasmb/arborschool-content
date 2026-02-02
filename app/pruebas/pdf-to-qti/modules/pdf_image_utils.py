"""
PDF Image Utilities Module

Handles image rendering, trimming, and quality assessment for PDF extraction.
"""

from __future__ import annotations

import base64
import io
from typing import Any

import fitz  # type: ignore
from PIL import Image, ImageChops

from .image_processing.bbox_utils import MIN_IMAGE_HEIGHT, MIN_IMAGE_WIDTH


def is_meaningful_image(bbox: list[float]) -> bool:
    """
    Check if an image bbox represents meaningful content.
    Uses conservative thresholds to avoid overfitting.

    Args:
        bbox: Bounding box [x0, y0, x1, y1]

    Returns:
        True if the image appears to contain meaningful content
    """
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    area = width * height
    aspect_ratio = max(width, height) / min(width, height) if min(width, height) > 0 else float("inf")

    # Conservative criteria without overfitted thresholds
    return (
        area > 100
        and aspect_ratio < 30
        and width >= MIN_IMAGE_WIDTH
        and height >= MIN_IMAGE_HEIGHT
    )


def trim_whitespace(image_bytes: bytes) -> bytes:
    """
    Trims whitespace from an image.

    Args:
        image_bytes: PNG image bytes

    Returns:
        Trimmed image bytes (or original if trimming fails)
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))

        # Get the background color of the top-left pixel
        bg_color = image.getpixel((0, 0))

        # Create a background image of the same size
        bg = Image.new(image.mode, image.size, bg_color)

        # Find the difference between the image and the background
        diff = ImageChops.difference(image, bg)

        # Find the bounding box of the non-background area
        bbox = diff.getbbox()

        if bbox:
            # Crop the image to the bounding box
            trimmed_image = image.crop(bbox)

            # Save the trimmed image back to bytes
            buf = io.BytesIO()
            trimmed_image.save(buf, format="PNG")
            return buf.getvalue()

    except Exception as e:
        print(f"⚠️ Error trimming whitespace: {e}")

    # If anything fails, return the original image bytes
    return image_bytes


def render_image_area(
    page: fitz.Page,
    final_bbox: list[float],
    original_bbox: list[float],
    idx: int,
    mask_areas: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """
    Render the final image area with optional text masking.

    Args:
        page: PyMuPDF page object
        final_bbox: Final bounding box for the image
        original_bbox: Original bounding box (for reference)
        idx: Image index
        mask_areas: Optional list of text areas to mask (for choice letters in diagrams)

    Returns:
        Dictionary with rendered image data, or None if rendering fails
    """
    try:
        render_rect = fitz.Rect(final_bbox)

        if not render_rect.is_empty and render_rect.width > 1 and render_rect.height > 1:
            scale = 2.0
            matrix = fitz.Matrix(scale, scale)

            # If we have mask areas, create a temporary page with masked text
            if mask_areas:
                pix = _render_with_masks(page, render_rect, matrix, mask_areas)
            else:
                # Regular rendering without masking
                pix = page.get_pixmap(matrix=matrix, clip=render_rect, alpha=False)

            img_bytes = pix.tobytes("png")

            # Trim whitespace from the rendered image
            trimmed_bytes = trim_whitespace(img_bytes)

            # Get new dimensions from trimmed image
            trimmed_img_pil = Image.open(io.BytesIO(trimmed_bytes))
            new_width, new_height = trimmed_img_pil.size

            # Convert image bytes to base64 string for consistent processing
            image_base64 = base64.b64encode(trimmed_bytes).decode("utf-8")

            result = {
                "bbox": final_bbox,
                "width": new_width,
                "height": new_height,
                "ext": "png",
                "image_base64": image_base64,
                "is_table": False,
                "is_grouped": False,
                "is_expanded": True,
                "original_bbox": original_bbox,
                "has_text_masking": bool(mask_areas),
            }

            if mask_areas:
                print(
                    f"📸 ✅ Rendered and trimmed masked image {idx+1}: "
                    f"{new_width}x{new_height} (masked {len(mask_areas)} areas)"
                )
            else:
                print(f"📸 ✅ Rendered and trimmed image {idx+1}: {new_width}x{new_height}")

            return result

    except Exception as e:
        print(f"⚠️ Error rendering image {idx+1}: {e}")

    return None


def _render_with_masks(
    page: fitz.Page,
    render_rect: fitz.Rect,
    matrix: fitz.Matrix,
    mask_areas: list[dict[str, Any]],
) -> fitz.Pixmap:
    """
    Render a page area with text areas masked (covered with white rectangles).

    Args:
        page: PyMuPDF page object
        render_rect: Rectangle to render
        matrix: Transformation matrix for scaling
        mask_areas: List of areas to mask with their bounding boxes

    Returns:
        Rendered pixmap with masks applied
    """
    # Create a copy of the page for masking
    temp_doc = fitz.open()
    temp_page = temp_doc.new_page(width=page.rect.width, height=page.rect.height)

    # Copy the page content
    temp_page.show_pdf_page(page.rect, page.parent, page.number)

    # Apply text masks by drawing background-colored rectangles over choice letters
    for mask_area in mask_areas:
        mask_bbox = mask_area.get("bbox", [])
        if len(mask_bbox) == 4:
            mask_rect = fitz.Rect(mask_bbox)

            # Expand slightly to ensure complete coverage of choice letters
            expanded_rect = fitz.Rect(
                mask_rect.x0 - 10,
                mask_rect.y0 - 5,
                mask_rect.x1 + 10,
                mask_rect.y1 + 5,
            )

            # Draw white rectangle to mask the text
            temp_page.draw_rect(expanded_rect, color=(1, 1, 1), fill=(1, 1, 1))
            print(f"🎭 Masked text area: {mask_area.get('text_to_mask', 'unknown')} at {mask_bbox}")

    # Render from the masked page
    pix = temp_page.get_pixmap(matrix=matrix, clip=render_rect, alpha=False)
    temp_doc.close()

    return pix
