"""
QTI Transformer

This module implements step 2 of the conversion process:
Transform PDF content to QTI 3.0 XML format using the detected question type.
It leverages patterns from the existing HTML to QTI transformer.

Refactored to use content_processor and prompt_builder for better separation.

IMPORTANT: All images MUST be uploaded to S3. Base64 encoding in final XML is not allowed.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

# Local helpers
from .ai_processing import chat_completion
from .prompt_builder import create_transformation_prompt
from .qti_answer_utils import (
    extract_correct_answer_from_qti,
    update_correct_answer_in_qti_xml,
)
from .qti_configs import QTI_TYPE_CONFIGS

# Import from split modules
from .qti_encoding import (
    ENCODING_FIXES,
    detect_encoding_errors,
    validate_no_encoding_errors_or_raise,
    verify_and_fix_encoding,
)
from .qti_image_handler import (
    convert_remaining_base64_to_s3,
    prepare_llm_messages,
    upload_images_to_s3,
)
from .qti_response_parsers import (
    parse_correction_response,
    parse_transformation_response,
)
from .qti_xml_utils import (
    clean_qti_xml,
    fix_qti_xml_with_llm,
    replace_data_uris_with_s3_urls,
)

# Re-export all functions for backward compatibility
__all__ = [
    # Encoding
    "ENCODING_FIXES",
    "detect_encoding_errors",
    "validate_no_encoding_errors_or_raise",
    "verify_and_fix_encoding",
    # Answer utils
    "extract_correct_answer_from_qti",
    "update_correct_answer_in_qti_xml",
    # Response parsers
    "parse_transformation_response",
    "parse_correction_response",
    # XML utils
    "clean_qti_xml",
    "replace_data_uris_with_s3_urls",
    "fix_qti_xml_with_llm",
    # Image handler
    "upload_images_to_s3",
    "prepare_llm_messages",
    "convert_remaining_base64_to_s3",
    # Main function
    "transform_to_qti",
]

_logger = logging.getLogger(__name__)


def transform_to_qti(
    processed_content: dict[str, Any],
    question_type: str,
    openai_api_key: str,
    validation_feedback: Optional[str] = None,
    question_id: Optional[str] = None,
    use_s3: bool = True,
    paes_mode: bool = False,
    test_name: Optional[str] = None,
    correct_answer: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> dict[str, Any]:
    """
    Transform PDF content to QTI 3.0 XML format.

    This implements step 2 of the conversion guidelines:
    Use the detected question type to transform the PDF content
    into valid QTI 3.0 XML.

    CRITICAL: All images MUST be uploaded to S3. If any image upload fails,
    the transformation will fail. Base64 encoding in final XML is not allowed.

    Args:
        processed_content: Already processed PDF content with placeholders
        question_type: Detected question type
        openai_api_key: OpenAI API key
        validation_feedback: Optional feedback from validation errors
        question_id: Optional question identifier for S3 image naming
        use_s3: If True, upload images to S3 and use URLs (default: True, REQUIRED)
        paes_mode: If True, optimizes for PAES format (math, 4 alternatives)
        test_name: Optional test/prueba name to organize images in S3
        correct_answer: Optional correct answer identifier (e.g., "ChoiceA")
        output_dir: Optional output directory for logs

    Returns:
        Dictionary with transformation results
    """
    try:
        # Get configuration for the question type
        config = QTI_TYPE_CONFIGS.get(question_type)
        if not config:
            return {"success": False, "error": f"Unsupported question type: {question_type}"}

        # CRITICAL: S3 upload is REQUIRED - fail early if disabled
        if not use_s3:
            _logger.error("S3 upload is disabled, but it is REQUIRED for all images")
            return {"success": False, "error": "S3 upload is required. use_s3 must be True."}

        _logger.info("🚀 Starting S3 image upload process (REQUIRED)")

        # Upload images to S3 (REQUIRED - no fallback to base64)
        image_url_mapping = upload_images_to_s3(processed_content, question_id, test_name)
        if image_url_mapping is None:
            return {"success": False, "error": "Failed to upload images to S3. S3 upload is REQUIRED."}

        # Create the transformation prompt
        prompt = create_transformation_prompt(processed_content, question_type, config, validation_feedback, correct_answer=correct_answer)

        # Optimize prompt for PAES (mathematics, 4 alternatives)
        if paes_mode:
            from .paes_optimizer import optimize_prompt_for_math

            prompt = optimize_prompt_for_math(prompt)

        # Prepare messages for LLM
        messages = prepare_llm_messages(prompt, processed_content)

        # Call the LLM for transformation with retry
        result = _call_llm_with_retry(messages, openai_api_key, question_id, output_dir)
        if not result or not result.get("success"):
            return result or {"success": False, "error": "LLM call failed"}

        # Post-process the result
        result = _post_process_qti_result(result, image_url_mapping, processed_content, question_id, test_name, correct_answer)

        return result

    except Exception as e:
        return {"success": False, "error": f"QTI transformation failed: {str(e)}"}


def _call_llm_with_retry(
    messages: list[dict[str, Any]],
    api_key: str,
    question_id: Optional[str],
    output_dir: Optional[str],
) -> Optional[dict[str, Any]]:
    """
    Call the LLM for transformation with retry logic.

    Returns:
        Parsed transformation result or None if all retries failed.
    """
    max_retries = 3
    base_delay = 2.0
    last_error: Optional[str] = None

    for attempt in range(max_retries):
        try:
            response_text = chat_completion(
                messages,
                api_key=api_key,
                json_only=True,
                question_id=question_id,
                output_dir=output_dir,
                operation="transform_to_qti",
                max_tokens=16384,
            )

            # Check if response is empty
            if not response_text or not response_text.strip():
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    _logger.warning(f"Empty response from LLM (attempt {attempt + 1}/{max_retries}). Retrying in {delay:.2f}s...")
                    time.sleep(delay)
                    continue
                else:
                    raise ValueError("LLM returned empty response after all retries")

            # Parse the transformation response
            result = parse_transformation_response(response_text)

            if result.get("success"):
                return result
            else:
                error_msg = result.get("error", "Unknown parsing error")
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    _logger.warning(f"Failed to parse LLM response (attempt {attempt + 1}/{max_retries}): {error_msg}. Retrying in {delay:.2f}s...")
                    time.sleep(delay)
                    last_error = error_msg
                    continue
                else:
                    return {"success": False, "error": f"Failed to parse after {max_retries} attempts: {error_msg}"}

        except Exception as e:
            error_str = str(e)
            if attempt < max_retries - 1:
                delay = base_delay * (2**attempt)
                _logger.warning(f"Error calling LLM (attempt {attempt + 1}/{max_retries}): {error_str}. Retrying in {delay:.2f}s...")
                time.sleep(delay)
                last_error = error_str
                continue
            else:
                return {"success": False, "error": f"LLM call failed after {max_retries} attempts: {error_str}"}

    return {"success": False, "error": f"Failed to get valid response from LLM: {last_error or 'Unknown error'}"}


def _post_process_qti_result(
    result: dict[str, Any],
    image_url_mapping: dict[str, str],
    processed_content: dict[str, Any],
    question_id: Optional[str],
    test_name: Optional[str],
    correct_answer: Optional[str],
) -> dict[str, Any]:
    """
    Post-process the QTI transformation result.

    Handles encoding verification, S3 URL replacement, and answer verification.
    """
    if not result.get("success"):
        return result

    # Verify and fix encoding issues
    result["qti_xml"], _ = verify_and_fix_encoding(result["qti_xml"])

    # Clean up any remaining placeholders
    result["qti_xml"] = clean_qti_xml(result["qti_xml"])

    # Final encoding check after cleaning
    result["qti_xml"], _ = verify_and_fix_encoding(result["qti_xml"])

    # Replace data URIs with S3 URLs
    if image_url_mapping:
        result["qti_xml"] = replace_data_uris_with_s3_urls(result["qti_xml"], image_url_mapping, processed_content)

    # Handle any remaining base64 images
    result["qti_xml"] = convert_remaining_base64_to_s3(result["qti_xml"], question_id, test_name)

    # Verify correct answer matches answer key (if provided)
    if correct_answer:
        result["qti_xml"] = _verify_and_fix_answer(result["qti_xml"], correct_answer, question_id)

    return result


def _verify_and_fix_answer(
    qti_xml: str,
    correct_answer: str,
    question_id: Optional[str],
) -> str:
    """
    Verify and fix the correct answer in QTI XML.
    """
    xml_answer = extract_correct_answer_from_qti(qti_xml)

    if xml_answer:
        if xml_answer != correct_answer:
            _logger.warning(
                f"⚠️  Answer mismatch for {question_id or 'question'}: "
                f"Expected '{correct_answer}' from answer key, but XML has '{xml_answer}'. "
                f"Auto-correcting..."
            )
            qti_xml = update_correct_answer_in_qti_xml(qti_xml, correct_answer)
            _logger.info(f"✅ Corrected answer to '{correct_answer}'")
        else:
            _logger.info(f"✅ Answer verified: '{correct_answer}' matches answer key")
    else:
        _logger.warning(
            f"⚠️  Could not extract correct answer from XML for {question_id or 'question'}. "
            f"Expected '{correct_answer}' from answer key. Attempting to add..."
        )
        qti_xml = update_correct_answer_in_qti_xml(qti_xml, correct_answer)
        _logger.info(f"✅ Added correct answer '{correct_answer}' from answer key")

    return qti_xml
