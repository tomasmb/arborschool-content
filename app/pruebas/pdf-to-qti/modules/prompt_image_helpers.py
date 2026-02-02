"""
Image-related helper functions for prompt building.

This module handles finding nearby text for images, collecting large images,
and formatting image information for prompts.
"""

from __future__ import annotations

from typing import Any

import fitz  # type: ignore # For Rect operations

from .prompt_templates import IMAGE_PLACEMENT_GUIDELINES


def get_text_from_block(block: dict[str, Any]) -> str:
    """Extracts all text from spans within lines of a block."""
    block_text = []
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            block_text.append(span.get("text", ""))
    return " ".join(block_text).strip()


def find_nearby_text_for_image(
    image_bbox_coords: list[float],
    image_page_num: int,
    all_document_blocks: list[dict[str, Any]],
    max_vertical_gap: int = 50,
    min_horizontal_overlap_percentage: float = 0.1,
) -> str:
    """Finds text blocks near an image bbox and returns semantic context for placement."""
    img_rect = fitz.Rect(image_bbox_coords)

    # Collect text blocks with their relative positions
    text_blocks = _collect_nearby_text_blocks(img_rect, image_page_num, all_document_blocks, max_vertical_gap, min_horizontal_overlap_percentage)

    if not text_blocks:
        return "No nearby text context found"

    return _format_text_context(text_blocks)


def _collect_nearby_text_blocks(
    img_rect: fitz.Rect,
    image_page_num: int,
    all_document_blocks: list[dict[str, Any]],
    max_vertical_gap: int,
    min_horizontal_overlap_percentage: float,
) -> list[dict[str, Any]]:
    """Collect text blocks near the image with their positions."""
    text_blocks = []

    for block in all_document_blocks:
        if block.get("page_number") != image_page_num or block.get("type") != 0:
            continue

        text_bbox_coords = block.get("bbox")
        if not text_bbox_coords:
            continue

        text_rect = fitz.Rect(text_bbox_coords)
        text_content = get_text_from_block(block)
        if not text_content.strip():
            continue

        # Check spatial relationship
        block_info = _analyze_spatial_relationship(img_rect, text_rect, text_content, max_vertical_gap, min_horizontal_overlap_percentage)

        if block_info:
            text_blocks.append(block_info)

    # Sort by distance (closest first)
    text_blocks.sort(key=lambda x: x["distance"])
    return text_blocks


def _analyze_spatial_relationship(
    img_rect: fitz.Rect, text_rect: fitz.Rect, text_content: str, max_vertical_gap: int, min_horizontal_overlap_percentage: float
) -> dict[str, Any] | None:
    """Analyze spatial relationship between image and text block."""
    # Check for horizontal overlap (more lenient)
    overlap_x0 = max(img_rect.x0, text_rect.x0)
    overlap_x1 = min(img_rect.x1, text_rect.x1)
    horizontal_overlap_width = overlap_x1 - overlap_x0
    min_width = min(img_rect.width, text_rect.width) * min_horizontal_overlap_percentage

    # Include text that's horizontally close (not just overlapping)
    horizontal_distance = min(
        abs(text_rect.x1 - img_rect.x0),  # Text left of image
        abs(img_rect.x1 - text_rect.x0),  # Text right of image
        0 if horizontal_overlap_width >= min_width else float("inf"),
    )

    if horizontal_overlap_width < min_width and horizontal_distance >= 100:
        return None

    # Calculate vertical relationship
    vertical_distance = min(
        abs(text_rect.y1 - img_rect.y0),  # Text above image
        abs(img_rect.y1 - text_rect.y0),  # Text below image
        0 if (text_rect.y0 <= img_rect.y1 and text_rect.y1 >= img_rect.y0) else float("inf"),
    )

    if vertical_distance > max_vertical_gap:
        return None

    # Determine relationship
    relationship = _determine_relationship(img_rect, text_rect)

    return {"content": text_content.strip(), "relationship": relationship, "distance": vertical_distance, "y_pos": text_rect.y0}


def _determine_relationship(img_rect: fitz.Rect, text_rect: fitz.Rect) -> str:
    """Determine spatial relationship between image and text."""
    if text_rect.y1 <= img_rect.y0:
        return "above"
    elif text_rect.y0 >= img_rect.y1:
        return "below"
    elif text_rect.x1 <= img_rect.x0:
        return "left"
    elif text_rect.x0 >= img_rect.x1:
        return "right"
    return "overlapping"


def _format_text_context(text_blocks: list[dict[str, Any]]) -> str:
    """Format nearby text blocks into context description."""
    # Group by relationship
    above_texts = [t["content"] for t in text_blocks if t["relationship"] == "above"]
    below_texts = [t["content"] for t in text_blocks if t["relationship"] == "below"]
    side_texts = [t["content"] for t in text_blocks if t["relationship"] in ["left", "right"]]

    # Create semantic description
    context_parts = []

    if above_texts:
        above_combined = " ".join(above_texts[:2])
        context_parts.append(f"Text above: '{above_combined}'")

    if below_texts:
        below_combined = " ".join(below_texts[:2])
        context_parts.append(f"Text below: '{below_combined}'")

    if side_texts:
        side_combined = " ".join(side_texts[:1])
        context_parts.append(f"Adjacent text: '{side_combined}'")

    # Analyze semantic meaning for placement hints
    all_text = " ".join([t["content"] for t in text_blocks[:3]]).lower()
    placement_hints = _analyze_placement_hints(all_text)

    result = " | ".join(context_parts)
    if placement_hints:
        result += f" | Context suggests: {', '.join(placement_hints)}"

    return result


def _analyze_placement_hints(text: str) -> list[str]:
    """Analyze text to determine placement hints for images."""
    hints = []

    if any(word in text for word in ["question", "which", "what", "how", "why", "when", "where"]):
        hints.append("appears to be part of question stem")
    if any(word in text for word in ["a)", "b)", "c)", "d)", "choice", "option"]):
        hints.append("near answer choices")
    if any(word in text for word in ["diagram", "figure", "image", "picture", "shows", "illustration"]):
        hints.append("referenced by text")
    if any(word in text for word in ["instruction", "direction", "note", "consider"]):
        hints.append("part of instructions")

    return hints


def prepare_document_blocks(pdf_content: dict[str, Any]) -> list[dict[str, Any]]:
    """Prepare document blocks with page info for nearby text search."""
    all_doc_blocks = []
    for i, page_data in enumerate(pdf_content.get("pages", [])):
        page_blocks = page_data.get("structured_text", {}).get("blocks", [])
        for block in page_blocks:
            block_copy = block.copy()
            block_copy["page_number"] = i
            all_doc_blocks.append(block_copy)
    return all_doc_blocks


def collect_large_images(pdf_content: dict[str, Any], all_doc_blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collect large images for inclusion in prompt."""
    large_images = []

    if not pdf_content.get("all_images"):
        return large_images

    for img_data in pdf_content["all_images"]:
        width = int(img_data.get("width", 0))
        height = int(img_data.get("height", 0))

        # Include choice images regardless of size
        if width * height > 5000 or img_data.get("is_choice_diagram"):
            placeholder = img_data.get("image_base64")
            if placeholder and placeholder.startswith("CONTENT_PLACEHOLDER_"):
                img_page_num = img_data.get("page_number", 0)

                nearby_text = find_nearby_text_for_image(
                    img_data.get("bbox", [0, 0, 0, 0]),
                    img_page_num,
                    all_doc_blocks,
                )

                alt_suggestion = f"Image {len(large_images) + 1} (size {width}x{height})"

                large_images.append(
                    {
                        "placeholder": placeholder,
                        "width": width,
                        "height": height,
                        "bbox": img_data.get("bbox", [0, 0, 0, 0]),
                        "page_number": img_page_num,
                        "alt_suggestion": alt_suggestion,
                        "nearby_text": nearby_text,
                    }
                )

    return large_images


def format_image_info(images: list[dict[str, Any]]) -> str:
    """Format image information for the prompt."""
    image_info = "\n## Relevant Extracted Images (Diagrams/Figures)\n"
    image_info += f"Found {len(images)} image(s) in logical reading order:\n"

    for i, img_details in enumerate(images):
        bbox_coords = img_details["bbox"]
        page_num = img_details["page_number"]
        width = img_details["width"]
        height = img_details["height"]
        nearby_text_info = img_details.get("nearby_text", "No nearby text context found.")

        # Determine position description
        y_pos = bbox_coords[1]
        page_height = 792  # Standard PDF height
        if y_pos < page_height * 0.3:
            position_desc = "top"
        elif y_pos > page_height * 0.7:
            position_desc = "bottom"
        else:
            position_desc = "middle"

        image_info += (
            f"  Image {i + 1}: Use placeholder '{img_details['placeholder']}'. "
            f"Location: Page {page_num + 1}, Position: {position_desc} of page, Size: {width}x{height}. "
            f"Contextual Text: {nearby_text_info}. "
            f"Alt text: '{img_details['alt_suggestion']}'.\n"
        )

    image_info += IMAGE_PLACEMENT_GUIDELINES
    return image_info


def build_image_info(pdf_content: dict[str, Any]) -> str:
    """Build image information section for the prompt."""
    all_doc_blocks = prepare_document_blocks(pdf_content)
    large_images = collect_large_images(pdf_content, all_doc_blocks)

    if large_images:
        return format_image_info(large_images)
    elif pdf_content.get("has_extracted_images"):
        return (
            "\n## Visual Content\n"
            "The PDF contains extracted images. If they are part of the question, "
            "include them using descriptive placeholder filenames like 'image1.png'.\n"
        )
    else:
        return "\n## Visual Content\nNo significant visual content detected or provided for transformation.\n"
