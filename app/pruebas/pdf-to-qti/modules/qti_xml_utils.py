"""
QTI XML Utilities

This module provides utilities for cleaning, fixing, and processing QTI XML content,
including S3 URL replacement and LLM-based XML correction.
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from typing import Any, Optional

from .ai_processing import chat_completion
from .prompt_builder import create_error_correction_prompt
from .qti_encoding import verify_and_fix_encoding

_logger = logging.getLogger(__name__)


def clean_qti_xml(xml_content: str) -> str:
    """
    Clean and normalize QTI XML content.

    - Removes known LLM artifacts (e.g., ```xml wrapper)
    - Removes XML declaration if present
    - Strips leading/trailing whitespace
    - Removes invalid null characters that can exist in PDF text

    Args:
        xml_content: Raw XML content

    Returns:
        Cleaned XML content
    """
    # Remove any markdown code block markers
    if xml_content.strip().startswith("```xml"):
        xml_content = xml_content.strip()[6:-3].strip()

    # Remove XML declaration
    if xml_content.strip().startswith("<?xml"):
        xml_content = xml_content.split("?>", 1)[1].strip()

    # CRITICAL: Remove null characters (Unicode: 0x0) which are invalid in XML
    xml_content = xml_content.replace("\x00", "")

    # Strip any leading/trailing whitespace from the whole block
    return xml_content.strip()


def replace_data_uris_with_s3_urls(
    qti_xml: str,
    image_url_mapping: dict[str, str],
    processed_content: dict[str, Any],
) -> str:
    """
    Replace ALL data URIs in QTI XML with S3 URLs.

    This function aggressively replaces all base64 data URIs with S3 URLs.
    It's called as a critical step to ensure no base64 remains in the final XML.

    Args:
        qti_xml: QTI XML string that may contain data URIs
        image_url_mapping: Dictionary mapping image identifiers to S3 URLs
        processed_content: Original processed content with image info

    Returns:
        QTI XML with ALL data URIs replaced by S3 URLs
    """
    # Pattern to match data URIs in img src attributes (more permissive to catch all)
    # Matches data:image/<any-type>;base64,<base64-data>
    data_uri_pattern = r"data:image/[^;]+;base64,[A-Za-z0-9+/=\s]+"

    replacements_made = 0

    # Replace main image first
    if "main_image" in image_url_mapping and image_url_mapping["main_image"]:
        main_s3_url = image_url_mapping["main_image"]
        before = qti_xml
        qti_xml = re.sub(
            data_uri_pattern,
            main_s3_url,
            qti_xml,
            count=1,  # Replace first occurrence (main image)
        )
        if before != qti_xml:
            replacements_made += 1
            _logger.debug(f"Replaced main image data URI with S3 URL: {main_s3_url}")

    # Replace additional images
    if processed_content.get("all_images"):
        for i, _image_info in enumerate(processed_content["all_images"]):
            image_key = f"image_{i}"
            if image_key in image_url_mapping and image_url_mapping[image_key]:
                s3_url = image_url_mapping[image_key]
                before = qti_xml
                # Replace remaining data URIs (one at a time)
                qti_xml = re.sub(
                    data_uri_pattern,
                    s3_url,
                    qti_xml,
                    count=1,
                )
                if before != qti_xml:
                    replacements_made += 1
                    _logger.debug(f"Replaced {image_key} data URI with S3 URL: {s3_url}")

    # If we still have data URIs but ran out of mapped URLs, log warning
    remaining = re.findall(data_uri_pattern, qti_xml)
    if remaining:
        _logger.warning(f"⚠️  Found {len(remaining)} remaining data URI(s) after replacement. This should not happen.")
        # Try to replace any remaining with first available S3 URL
        if image_url_mapping:
            first_s3_url = next(iter(image_url_mapping.values()))
            qti_xml = re.sub(data_uri_pattern, first_s3_url, qti_xml)
            _logger.warning(f"Replaced remaining data URIs with fallback S3 URL: {first_s3_url}")

    if replacements_made > 0:
        _logger.info(f"✅ Replaced {replacements_made} data URI(s) with S3 URLs")

    return qti_xml


def fix_qti_xml_with_llm(
    invalid_xml: str,
    validation_errors: str,
    question_type: str,
    openai_api_key: str,
    retry_attempt: int = 1,
    max_attempts: int = 3,
    output_dir: Optional[str] = None,
    question_id: Optional[str] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Attempt to fix invalid QTI XML using LLM.

    Args:
        invalid_xml: The invalid QTI XML string (with placeholders, not images)
        validation_errors: String containing validation error messages
        question_type: The detected question type for context
        openai_api_key: OpenAI API key
        retry_attempt: Current attempt number (1-based)
        max_attempts: Maximum number of attempts for context
        output_dir: Optional output directory for logging
        question_id: Optional question ID for logging

    Returns:
        Dictionary with success status and corrected XML
    """
    # Import here to avoid circular imports
    from .qti_response_parsers import parse_correction_response

    try:
        # Basic validation check that the XML is well-formed
        try:
            ET.fromstring(invalid_xml)
        except ET.ParseError as e:
            return {"success": False, "error": f"XML structure error: {str(e)}"}

        # Create error correction prompt
        correction_prompt = create_error_correction_prompt(invalid_xml, validation_errors, question_type, retry_attempt, max_attempts)

        # Call the model to fix the XML via shared helper (uses GPT-5.1 with high reasoning)
        corrected_content = chat_completion(
            [
                {"role": "system", "content": "You are an expert in QTI 3.0 XML. Fix the provided XML to make it valid."},
                {"role": "user", "content": correction_prompt},
            ],
            api_key=openai_api_key,
            json_only=True,
            reasoning_effort="medium",  # XML structure understanding
            max_tokens=8000,
            question_id=question_id,
            output_dir=output_dir,
            operation=f"fix_qti_xml_retry_{retry_attempt}",
        ).strip()

        # Parse the correction response
        result = parse_correction_response(corrected_content)

        if result["success"]:
            # Verify and fix encoding issues
            result["qti_xml"], _ = verify_and_fix_encoding(result["qti_xml"])

            # Clean the result
            cleaned_xml = clean_qti_xml(result["qti_xml"])

            # Final encoding check after cleaning
            cleaned_xml, _ = verify_and_fix_encoding(cleaned_xml)

            # Basic validation
            try:
                ET.fromstring(cleaned_xml)
            except ET.ParseError as e:
                return {"success": False, "error": f"LLM produced invalid XML: {str(e)}"}

            return {"success": True, "qti_xml": cleaned_xml}
        else:
            return {"success": False, "error": result.get("error", "Failed to parse LLM correction response")}

    except Exception as e:
        return {"success": False, "error": f"LLM correction failed: {str(e)}"}
