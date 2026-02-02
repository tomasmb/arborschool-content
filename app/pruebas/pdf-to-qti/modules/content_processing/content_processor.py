"""
PDF Content Processor

This module handles the processing of PDF content including:
- Image embedding as base64
- Content extraction and placeholder management
- Large content handling for LLM processing
- Content restoration after transformation

Similar to the HTML transformer's content-handler.ts
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ..ai_processing.image_filter import get_indices_of_images_to_keep
from ..ai_processing.table_filter import get_indices_of_tables_to_keep
from ..pdf_text_processing import extract_block_text


@dataclass
class ExtractedContent:
    """Represents extracted content with placeholder information"""

    placeholder: str
    original_content: str
    content_type: str  # 'base64-image', 'svg', 'large-text'
    metadata: Dict[str, Any]


def extract_large_content(
    pdf_content: Dict[str, Any], prefix: str = "P", openai_api_key: Optional[str] = None
) -> Tuple[Dict[str, Any], List[ExtractedContent]]:
    """
    Extract large content from PDF data and replace with placeholders.

    This is similar to the HTML transformer's extractLargeContent function
    but adapted for PDF content structure.

    Args:
        pdf_content: PDF content dictionary
        prefix: Prefix for placeholder IDs

    Returns:
        Tuple of (processed_content, extracted_content_list)
    """
    extracted_content: List[ExtractedContent] = []
    processed_content = pdf_content.copy()

    images_to_process = processed_content.get("all_images", [])
    if images_to_process and openai_api_key:
        print(f"Filtering {len(images_to_process)} images to remove answer sheet elements...")
        indices_to_keep = get_indices_of_images_to_keep(images_to_process, openai_api_key)

        # Create a set of the original image objects to keep for efficient lookup
        images_to_keep_set = {id(images_to_process[i]) for i in indices_to_keep if i < len(images_to_process)}

        # Filter all_images and page-specific images
        processed_content["all_images"] = [img for img in images_to_process if id(img) in images_to_keep_set]

        if "pages" in processed_content:
            for page in processed_content["pages"]:
                if "extracted_images" in page:
                    page["extracted_images"] = [img for img in page["extracted_images"] if id(img) in images_to_keep_set]

        print(f"Kept {len(processed_content['all_images'])} images after filtering.")

    # 2. Handle extracted tables
    tables_to_process = []
    if "pages" in processed_content:
        for page in processed_content["pages"]:
            if "extracted_tables" in page:
                tables_to_process.extend(page["extracted_tables"])

    if tables_to_process and openai_api_key:
        print(f"Filtering {len(tables_to_process)} tables to remove answer sheet elements...")
        indices_to_keep = get_indices_of_tables_to_keep(tables_to_process, openai_api_key)

        tables_to_keep_set = {id(tables_to_process[i]) for i in indices_to_keep if i < len(tables_to_process)}

        for page in processed_content["pages"]:
            if "extracted_tables" in page:
                page["extracted_tables"] = [tbl for tbl in page["extracted_tables"] if id(tbl) in tables_to_keep_set]

        print(f"Kept {len(tables_to_keep_set)} tables after filtering.")

    # 1. Handle extracted images from PDF structure
    if "all_images" in processed_content and processed_content["all_images"]:
        processed_images = []

        for i, image_info in enumerate(processed_content["all_images"]):
            # Extract ALL images as placeholders, not just large ones
            if image_info.get("image_base64"):
                # Create placeholder for any image with base64 data
                placeholder_id = f"CONTENT_PLACEHOLDER_{prefix}{len(extracted_content)}"

                alt_text = f"Extracted image {i + 1} from page {image_info.get('page_number', 0) + 1}"
                if image_info.get("is_table"):
                    alt_text = f"Rendered table {i + 1} from page {image_info.get('page_number', 0) + 1}"

                extracted_content.append(
                    ExtractedContent(
                        placeholder=placeholder_id,
                        original_content=f"data:image/png;base64,{image_info['image_base64']}",
                        content_type="base64-image",
                        metadata={
                            "width": image_info.get("width", ""),
                            "height": image_info.get("height", ""),
                            "bbox": image_info.get("bbox", []),
                            "page_number": image_info.get("page_number", 0),
                            "ext": image_info.get("ext", "png"),
                            "is_table": image_info.get("is_table", False),
                            "alt": alt_text,
                        },
                    )
                )

                # Replace image data with placeholder
                processed_image = image_info.copy()
                processed_image["image_base64"] = placeholder_id
                processed_images.append(processed_image)
            else:
                # No image data - keep as is
                processed_images.append(image_info)

        processed_content["all_images"] = processed_images

    # 4. Process individual page images if they're large
    if "pages" in processed_content:
        for i, page in enumerate(processed_content["pages"]):
            # DISABLED: Handle page_image_base64 - this was causing full page images to be embedded
            # We only want individual extracted images, not full page renders
            # if 'page_image_base64' in page and len(page['page_image_base64']) > 30000:
            #     image_data = page['page_image_base64']
            #     placeholder_id = f"CONTENT_PLACEHOLDER_{prefix}{len(extracted_content)}"
            #
            #     extracted_content.append(ExtractedContent(
            #         placeholder=placeholder_id,
            #         original_content=f"data:image/png;base64,{image_data}",
            #         content_type='base64-image',
            #         metadata={
            #             'page': i,
            #             'width': page.get('width', ''),
            #             'height': page.get('height', ''),
            #             'alt': f'PDF page {i+1} image'
            #         }
            #     ))
            #
            #     processed_content['pages'][i]['page_image_base64'] = placeholder_id

            # Handle extracted images within pages - extract ALL images
            if "extracted_images" in page:
                processed_page_images = []
                for j, img in enumerate(page["extracted_images"]):
                    # Extract ALL images as placeholders, not just large ones
                    if img.get("image_base64"):
                        placeholder_id = f"CONTENT_PLACEHOLDER_{prefix}{len(extracted_content)}"

                        alt_text = f"Page {i + 1} extracted image {j + 1}"
                        if img.get("is_table"):
                            alt_text = f"Page {i + 1} rendered table {j + 1}"

                        extracted_content.append(
                            ExtractedContent(
                                placeholder=placeholder_id,
                                original_content=f"data:image/png;base64,{img['image_base64']}",
                                content_type="base64-image",
                                metadata={
                                    "width": img.get("width", ""),
                                    "height": img.get("height", ""),
                                    "bbox": img.get("bbox", []),
                                    "page_number": i,
                                    "ext": img.get("ext", "png"),
                                    "is_table": img.get("is_table", False),
                                    "alt": alt_text,
                                },
                            )
                        )

                        processed_img = img.copy()
                        processed_img["image_base64"] = placeholder_id
                        processed_page_images.append(processed_img)
                    else:
                        processed_page_images.append(img)

                processed_content["pages"][i]["extracted_images"] = processed_page_images

    # Ensure AI analysis is preserved if it exists
    if "ai_analysis" in pdf_content:
        processed_content["ai_analysis"] = pdf_content["ai_analysis"]

    return processed_content, extracted_content


def restore_large_content(qti_xml: str, extracted_content: List[ExtractedContent]) -> str:
    """
    Restore placeholders with original content in QTI XML.

    This handles both explicit placeholders (CONTENT_PLACEHOLDER_*) and
    simple image filenames (diagram.png, image1.png, etc.) that the LLM generates.

    Args:
        qti_xml: QTI XML with content placeholders
        extracted_content: List of extracted content with placeholders

    Returns:
        QTI XML with original content restored
    """
    restored_xml = qti_xml

    # First, handle explicit placeholders
    for content in extracted_content:
        if content.content_type == "base64-image":
            # Replace explicit placeholder with actual base64 data URL
            restored_xml = restored_xml.replace(content.placeholder, content.original_content)

    return restored_xml


def embed_pdf_images_as_base64(pdf_content: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure all PDF images are properly embedded as base64.

    This is similar to the HTML transformer's embedImagesAsBase64 function
    but for PDF content that's already extracted.

    Args:
        pdf_content: PDF content dictionary

    Returns:
        PDF content with properly formatted base64 images
    """
    processed_content = pdf_content.copy()

    # Ensure main image is properly formatted
    if "image_base64" in processed_content and processed_content["image_base64"]:
        image_data = processed_content["image_base64"]
        if not image_data.startswith("data:") and not image_data.startswith("CONTENT_PLACEHOLDER"):
            processed_content["image_base64"] = f"data:image/png;base64,{image_data}"

    # Process all extracted images
    if "all_images" in processed_content:
        for image_info in processed_content["all_images"]:
            if "image_base64" in image_info and image_info["image_base64"]:
                image_data = image_info["image_base64"]
                if not image_data.startswith("data:") and not image_data.startswith("CONTENT_PLACEHOLDER"):
                    image_info["image_base64"] = f"data:image/png;base64,{image_data}"

    # Process page images
    if "pages" in processed_content:
        for page in processed_content["pages"]:
            # Handle page_image_base64 (renamed from image_base64)
            if "page_image_base64" in page and page["page_image_base64"]:
                image_data = page["page_image_base64"]
                if not image_data.startswith("data:") and not image_data.startswith("CONTENT_PLACEHOLDER"):
                    page["page_image_base64"] = f"data:image/png;base64,{image_data}"

            # Handle extracted images within pages
            if "extracted_images" in page:
                for image_info in page["extracted_images"]:
                    if "image_base64" in image_info and image_info["image_base64"]:
                        image_data = image_info["image_base64"]
                        if not image_data.startswith("data:") and not image_data.startswith("CONTENT_PLACEHOLDER"):
                            image_info["image_base64"] = f"data:image/png;base64,{image_data}"

    return processed_content


def create_content_summary(pdf_content: Dict[str, Any]) -> str:
    """
    Create a comprehensive summary of PDF content for LLM processing.
    Enhanced to include structured table information.

    Args:
        pdf_content: PDF content dictionary

    Returns:
        Content summary string
    """
    summary_parts = []

    # Basic content info
    page_count = pdf_content.get("page_count", 1)
    if page_count > 1:
        summary_parts.append(f"Multi-page document ({page_count} pages)")

    # Text content
    combined_text = pdf_content.get("combined_text", "")
    if combined_text:
        text_length = len(combined_text)
        summary_parts.append(f"Text content: {text_length} characters")

        # NEW: Include full combined text if it's not too long (for multi-part questions)
        if text_length < 2000:  # Include full text for shorter content
            summary_parts.append(f"Full text content:\n{combined_text}")

        # ENHANCED: Add structured table content if available
        tables_found = []
        for page in pdf_content.get("pages", []):
            extracted_tables = page.get("extracted_tables", [])
            for table in extracted_tables:
                if table.get("html_content"):
                    table_info = f"Page {page.get('page_number', 0) + 1} table ({table.get('rows', '?')}x{table.get('cols', '?')} cells)"
                    tables_found.append(table_info)
                    summary_parts.append(f"Table found: {table_info}")
                    summary_parts.append(f"Table content:\n{table.get('html_content', '')}")

        if tables_found:
            summary_parts.append(f"📊 Found {len(tables_found)} structured tables with content")

        # Sample structured data
        all_blocks = []
        if pdf_content.get("pages"):
            # For multi-page, combine blocks from all pages
            for page in pdf_content.get("pages", []):
                structured_data = page.get("structured_text", {})
                if structured_data and "blocks" in structured_data:
                    all_blocks.extend(structured_data["blocks"])
        elif pdf_content.get("structured_data"):
            # Fallback for single-page or already combined
            structured_data = pdf_content["structured_data"]
            all_blocks = structured_data.get("blocks", [])

        # Get text blocks
        text_blocks = [block for block in all_blocks if block.get("type") == 0]

        # SMART: Use AI categorization to find key content blocks
        if text_blocks:
            sample_texts = []
            priority_blocks = []

            # Check if we have AI categorization available
            ai_categories = pdf_content.get("ai_analysis", {}).get("ai_categories", {})

            # Initialize lists to hold categorized blocks
            answer_choice_blocks = []
            question_blocks = []
            part_blocks = []
            other_blocks = []

            if ai_categories:
                # Use smart AI categorization to populate block lists
                for i, block in enumerate(text_blocks):
                    block_text = extract_block_text(block)
                    if block_text and len(block_text.strip()) > 1:
                        block_num = i + 1  # AI uses 1-indexed
                        category = ai_categories.get(block_num, "unknown")

                        # Check for Part A/B patterns even in AI categorization
                        part_patterns = [r"^[A-Z]\.\s", r"^[A-Z]\.\t", r"^Part\s+[A-Z]"]
                        is_part_block = any(re.match(pattern, block_text.strip()) for pattern in part_patterns)

                        if is_part_block:
                            part_blocks.append((i, block, block_text))
                        elif category == "answer_choice":
                            answer_choice_blocks.append((i, block, block_text))
                        elif category == "question_text":
                            question_blocks.append((i, block, block_text))
                        elif len(block_text.strip()) > 10:
                            other_blocks.append((i, block, block_text))

            # Build a priority list of blocks to include in the summary
            priority_blocks.extend(part_blocks)
            priority_blocks.extend(answer_choice_blocks)
            priority_blocks.extend(question_blocks[:2])
            remaining_slots = max(0, 12 - len(priority_blocks))
            priority_blocks.extend(other_blocks[:remaining_slots])

            # Sort by original order to maintain document flow
            priority_blocks.sort(key=lambda x: x[0])

            # Format sample texts, prioritizing answer choices and parts
            blocks_to_show = priority_blocks
            if ai_categories and answer_choice_blocks:
                # When AI found answer choices, show ALL of them + some context
                max_blocks = max(12, len(answer_choice_blocks) + 2)
                blocks_to_show = priority_blocks[:max_blocks]
            else:
                # Show more blocks for multi-part questions
                max_blocks = 15 if part_blocks else 12
                blocks_to_show = priority_blocks[:max_blocks]

            for i, (block_idx, block, block_text) in enumerate(blocks_to_show):
                # Don't truncate Part A/B content - show more
                if any(pattern in block_text for pattern in ["A.", "B.", "Part A", "Part B"]):
                    display_text = block_text[:150] + "..." if len(block_text) > 150 else block_text
                else:
                    display_text = block_text[:80] + "..." if len(block_text) > 80 else block_text
                sample_texts.append(f"Block {block_idx + 1}: {display_text}")

            if sample_texts:
                summary_parts.append("Sample content:")
                for text in sample_texts:
                    summary_parts.append(f"  {text}")

            # Add a note if answer choices were found
            if answer_choice_blocks:
                summary_parts.append(f"✓ Found {len(answer_choice_blocks)} answer choice blocks in sample")

            # Add note if parts were found
            if part_blocks:
                summary_parts.append(f"✓ Found {len(part_blocks)} multi-part question blocks (A/B) in sample")

    # Visual content
    if pdf_content.get("image_base64"):
        summary_parts.append("Visual: PDF page image available")

    return "\n".join(summary_parts)


def clean_pdf_content_for_llm(pdf_content: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean and prepare PDF content for LLM processing.

    Args:
        pdf_content: Raw PDF content

    Returns:
        Cleaned PDF content suitable for LLM
    """
    cleaned_content = pdf_content.copy()

    # Clean combined text
    if "combined_text" in cleaned_content:
        text = cleaned_content["combined_text"]
        # Remove excessive whitespace
        text = " ".join(text.split())
        # Remove control characters
        text = "".join(char for char in text if ord(char) >= 32 or char in "\n\t")
        cleaned_content["combined_text"] = text

    # Clean structured data if present
    if "structured_data" in cleaned_content:
        # Process structured data for LLM consumption - NO ARBITRARY LIMITS
        # GPT-5.1 has large token context, so let it handle the full content
        structured = cleaned_content["structured_data"]
        if isinstance(structured, dict) and "blocks" in structured:
            all_blocks = structured.get("blocks", [])

            # Process all blocks, just clean up the content format
            essential_blocks = []
            for block in all_blocks:
                if block.get("type") == 0:  # Text block
                    essential_blocks.append(
                        {
                            "type": block.get("type"),
                            "bbox": block.get("bbox"),
                            "text": extract_block_text(block),  # Keep full text, no arbitrary truncation
                        }
                    )
                elif block.get("type") == 1:  # Image block
                    essential_blocks.append(
                        {"type": block.get("type"), "bbox": block.get("bbox"), "width": block.get("width"), "height": block.get("height")}
                    )

            print(f"📝 Processing {len(essential_blocks)} blocks for LLM analysis")

            cleaned_content["structured_data"] = {"width": structured.get("width"), "height": structured.get("height"), "blocks": essential_blocks}

    return cleaned_content
