"""
QTI Image Handler

This module handles image-related operations for QTI transformation:
- Uploading images to S3
- Preparing images for LLM messages
- Converting base64 images to S3 URLs
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any, Optional

from .utils.s3_uploader import upload_image_to_s3, upload_multiple_images_to_s3

_logger = logging.getLogger(__name__)


def upload_images_to_s3(
    processed_content: dict[str, Any],
    question_id: Optional[str],
    test_name: Optional[str],
) -> Optional[dict[str, str]]:
    """
    Upload all images from processed content to S3.

    Args:
        processed_content: Processed PDF content with image data
        question_id: Optional question identifier for S3 naming
        test_name: Optional test name for S3 organization

    Returns:
        Dictionary mapping image identifiers to S3 URLs, or None if upload failed.
    """
    image_url_mapping: dict[str, str] = {}
    failed_uploads: list[str] = []

    # Upload main image (with retry)
    main_image = processed_content.get('image_base64')
    if main_image and not main_image.startswith('CONTENT_PLACEHOLDER'):
        _logger.info(
            f"📤 Uploading main image to S3 "
            f"(question_id: {question_id or 'main'}, test: {test_name or 'default'})"
        )
        s3_url = upload_image_to_s3(
            image_base64=main_image,
            question_id=question_id or "main",
            test_name=test_name,
            max_retries=3,
        )
        if not s3_url:
            failed_uploads.append("main image")
            _logger.error("❌ Failed to upload main image to S3 after retries")
        else:
            image_url_mapping['main_image'] = s3_url
            processed_content['image_s3_url'] = s3_url
            _logger.info(f"✅ Main image uploaded to S3: {s3_url}")

    # Upload all additional images (with retry for each)
    if processed_content.get('all_images'):
        total_images = len(processed_content['all_images'])
        _logger.info(f"📤 Uploading {total_images} additional image(s) to S3")
        s3_results = upload_multiple_images_to_s3(
            images=processed_content['all_images'],
            question_id=question_id,
            test_name=test_name,
        )
        # Validate that all images were uploaded successfully
        for i, image_info in enumerate(processed_content['all_images']):
            image_key = f"image_{i}"
            img_base64 = image_info.get('image_base64')
            if img_base64 and not img_base64.startswith('CONTENT_PLACEHOLDER'):
                if image_key not in s3_results or not s3_results[image_key]:
                    failed_uploads.append(f"image_{i}")
                    _logger.error(f"❌ Failed to upload {image_key} to S3 after retries")
                else:
                    _logger.info(f"✅ {image_key} uploaded to S3: {s3_results[image_key]}")
        image_url_mapping.update({k: v for k, v in s3_results.items() if v})

    # CRITICAL: Fail if any image upload failed
    if failed_uploads:
        error_msg = (
            f"Failed to upload {len(failed_uploads)} image(s) to S3: "
            f"{', '.join(failed_uploads)}. S3 upload is REQUIRED."
        )
        _logger.error(f"❌ {error_msg}")
        return None

    # Verify that we have at least one image uploaded if there were images to upload
    expected_images = _count_expected_images(processed_content)

    if expected_images > 0 and len(image_url_mapping) == 0:
        _logger.error("❌ Expected images but none were uploaded to S3.")
        return None

    if len(image_url_mapping) > 0:
        _logger.info(f"✅ Successfully uploaded {len(image_url_mapping)} image(s) to S3")

    return image_url_mapping


def _count_expected_images(processed_content: dict[str, Any]) -> int:
    """Count the number of images expected to be uploaded."""
    expected = 0
    main_img = processed_content.get('image_base64')
    if main_img and not main_img.startswith('CONTENT_PLACEHOLDER'):
        expected += 1
    if processed_content.get('all_images'):
        expected += sum(
            1 for img in processed_content['all_images']
            if img.get('image_base64') and not img['image_base64'].startswith('CONTENT_PLACEHOLDER')
        )
    return expected


def prepare_llm_messages(
    prompt: str,
    processed_content: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Prepare messages for the LLM call, including images.

    Args:
        prompt: The transformation prompt text
        processed_content: Processed PDF content with image data

    Returns:
        List of messages for the LLM API call.
    """
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are an expert at converting educational content into QTI 3.0 XML format. "
                "You must respond with valid JSON format only. "
                "CRITICAL: NEVER use base64 encoding (data:image/...;base64,...) in the QTI XML. "
                "Only use placeholder image names that will be replaced with S3 URLs."
            )
        },
        {
            "role": "user",
            "content": [{"type": "text", "text": prompt}]
        }
    ]

    images_sent = 0
    max_images_threshold = 10

    # Add main image if available
    main_image = processed_content.get('image_base64')
    if main_image and not main_image.startswith('CONTENT_PLACEHOLDER'):
        image_data = main_image
        if not image_data.startswith('data:'):
            image_data = f"data:image/png;base64,{image_data}"

        messages[1]["content"].append({
            "type": "image_url",
            "image_url": {"url": image_data}
        })
        images_sent += 1
        _logger.info("📤 Sending main image to LLM")

    # Add additional images
    if processed_content.get('all_images'):
        images_with_data = [
            img for img in processed_content['all_images']
            if img.get('image_base64') and not img['image_base64'].startswith('CONTENT_PLACEHOLDER')
        ]

        if len(images_with_data) <= max_images_threshold:
            # Normal case: Send all images
            for image_info in images_with_data:
                image_data = image_info['image_base64']
                if not image_data.startswith('data:'):
                    image_data = f"data:image/png;base64,{image_data}"
                messages[1]["content"].append({
                    "type": "image_url",
                    "image_url": {"url": image_data}
                })
                images_sent += 1
            _logger.info(f"📤 Sending {len(images_with_data)} additional image(s) to LLM")
        else:
            # Extreme case: Prioritize by importance
            images_sent += _add_prioritized_images(messages, images_with_data, max_images_threshold)

    _logger.info(f"📊 Total images sent to LLM: {images_sent}")
    return messages


def _add_prioritized_images(
    messages: list[dict[str, Any]],
    images_with_data: list[dict[str, Any]],
    max_threshold: int,
) -> int:
    """
    Add images to messages prioritizing choice diagrams and larger images.

    Returns:
        Number of images added.
    """
    choice_images = []
    other_images = []

    for image_info in images_with_data:
        is_choice = image_info.get('is_choice_diagram', False)
        width = image_info.get('width', 0)
        height = image_info.get('height', 0)
        area = width * height

        if is_choice:
            choice_images.append((999999, image_info))
        else:
            other_images.append((area, image_info))

    images_added = 0

    # Send ALL choice images first
    for _priority, image_info in sorted(choice_images, reverse=True):
        image_data = image_info['image_base64']
        if not image_data.startswith('data:'):
            image_data = f"data:image/png;base64,{image_data}"
        messages[1]["content"].append({
            "type": "image_url",
            "image_url": {"url": image_data}
        })
        images_added += 1

    # Then send top other images (sorted by size)
    other_images.sort(reverse=True)
    remaining_slots = max_threshold - len(choice_images)
    for _priority, image_info in other_images[:remaining_slots]:
        image_data = image_info['image_base64']
        if not image_data.startswith('data:'):
            image_data = f"data:image/png;base64,{image_data}"
        messages[1]["content"].append({
            "type": "image_url",
            "image_url": {"url": image_data}
        })
        images_added += 1

    skipped = len(other_images) - remaining_slots
    if skipped > 0:
        _logger.warning(
            f"📤 Sending {len(choice_images)} choice + {remaining_slots} other images "
            f"(skipped {skipped} due to {len(images_with_data)} total)"
        )

    return images_added


def convert_remaining_base64_to_s3(
    qti_xml: str,
    question_id: Optional[str],
    test_name: Optional[str],
) -> str:
    """
    Convert any remaining base64 images in XML to S3 URLs.

    This is a best-effort operation - continues even if some uploads fail.

    Args:
        qti_xml: QTI XML that may contain base64 images
        question_id: Optional question ID for S3 naming
        test_name: Optional test name for S3 organization

    Returns:
        QTI XML with base64 images converted to S3 URLs where possible.
    """
    base64_pattern = r'(data:image/([^;]+);base64,)([A-Za-z0-9+/=\s]+)'
    base64_matches = re.findall(base64_pattern, qti_xml)

    if not base64_matches:
        _logger.info("✅ XML validated: No base64 data URIs found")
        return qti_xml

    _logger.warning(
        f"⚠️  Found {len(base64_matches)} base64 data URI(s) in XML. "
        "Attempting to upload to S3..."
    )

    uploaded_count = 0
    failed_count = 0

    for match in base64_matches:
        full_prefix = match[0]
        base64_data = match[2]
        full_data_uri = full_prefix + base64_data

        # Generate a unique identifier for this image
        image_hash = hashlib.md5(base64_data.encode()).hexdigest()[:8]
        img_identifier = f"{question_id or 'img'}_base64_{image_hash}"

        _logger.info(f"  📤 Attempting to upload base64 image to S3: {img_identifier}")

        s3_url = upload_image_to_s3(
            image_base64=full_data_uri,
            question_id=img_identifier,
            test_name=test_name
        )

        if s3_url:
            escaped_uri = re.escape(full_data_uri)
            qti_xml = re.sub(
                rf'src=["\']{escaped_uri}["\']',
                f'src="{s3_url}"',
                qti_xml
            )
            qti_xml = qti_xml.replace(full_data_uri, s3_url)
            uploaded_count += 1
            _logger.info(f"  ✅ Replaced base64 with S3 URL: {s3_url}")
        else:
            failed_count += 1
            _logger.warning("  ⚠️  Failed to upload base64 image to S3. Keeping as base64.")

    if uploaded_count > 0:
        _logger.info(f"✅ Converted {uploaded_count}/{len(base64_matches)} base64 image(s) to S3")
    if failed_count > 0:
        _logger.warning(f"⚠️  {failed_count} image(s) remain as base64.")

    return qti_xml
