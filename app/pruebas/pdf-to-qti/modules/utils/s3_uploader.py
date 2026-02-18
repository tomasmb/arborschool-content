"""
S3 Image Uploader

Uploads images to AWS S3 bucket and returns public URLs for use in QTI XML.
Also provides utilities for converting base64 images to S3 URLs in XML content.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
from typing import Optional

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError

    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    boto3 = None

_logger = logging.getLogger(__name__)


def upload_image_to_s3(
    image_base64: str,
    question_id: Optional[str] = None,
    bucket_name: Optional[str] = None,
    path_prefix: str = "images/",
    test_name: Optional[str] = None,
    max_retries: int = 3,
    force_upload: bool = False,  # NUEVO: Forzar re-subida incluso si existe
) -> Optional[str]:
    """
    Upload a base64-encoded image to S3 with retry logic and return the public URL.

    Images are organized by test name to avoid conflicts between different tests.
    Structure: images/{test_name}/{question_id}.png

    Args:
        image_base64: Base64-encoded image data (with or without data: prefix)
        question_id: Optional question identifier for naming
        bucket_name: S3 bucket name (uses AWS_S3_BUCKET from env if None)
        path_prefix: S3 path prefix base (default: "images/")
        test_name: Optional test/prueba name to organize images (e.g., "prueba-invierno-2026")
                   If provided, images will be stored in images/{test_name}/
        max_retries: Maximum number of retry attempts for transient errors (default: 3)

    Returns:
        Public S3 URL of uploaded image, or None if upload failed after retries
    """
    if not BOTO3_AVAILABLE:
        _logger.error("CRITICAL: boto3 not available, cannot upload to S3. Image upload will fail.")
        return None

    # Get bucket name from env if not provided
    if not bucket_name:
        bucket_name = os.environ.get("AWS_S3_BUCKET", "paes-question-images")

    # Support both naming conventions (AWS_S3_KEY is in .env)
    aws_access_key = os.environ.get("AWS_S3_KEY") or os.environ.get("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.environ.get("AWS_S3_SECRET") or os.environ.get("AWS_SECRET_ACCESS_KEY")
    aws_region = os.environ.get("AWS_REGION", "us-east-1")

    if not aws_access_key or not aws_secret_key:
        _logger.error(f"CRITICAL: AWS credentials not found (bucket: {bucket_name}). Cannot upload to S3. Image upload will fail.")
        return None

    # Prepare image data once (outside retry loop)
    try:
        # Clean base64 data (remove data:image/...;base64, prefix if present)
        if image_base64.startswith("data:"):
            # Extract mime type and data
            header, encoded = image_base64.split(",", 1)
            mime_type = header.split(":")[1].split(";")[0]
            image_data = base64.b64decode(encoded)
        else:
            # Assume PNG if no prefix
            image_data = base64.b64decode(image_base64)
            mime_type = "image/png"
    except Exception as e:
        _logger.error(f"CRITICAL: Failed to decode base64 image data: {e}")
        return None

    # Generate unique filename
    if question_id:
        # Use question_id as base for filename
        safe_id = "".join(c for c in question_id if c.isalnum() or c in "-_")
        filename = f"{safe_id}.png"
    else:
        # Generate hash-based filename
        image_hash = hashlib.md5(image_data).hexdigest()[:12]
        filename = f"img_{image_hash}.png"

    # Ensure path_prefix ends with /
    if path_prefix and not path_prefix.endswith("/"):
        path_prefix += "/"

    # Add test_name to path if provided (for organization: images/{test_name}/filename.png)
    if test_name:
        # Sanitize and lowercase test_name for use in S3 path (consistency with folder structure)
        safe_test_name = "".join(c for c in test_name.lower() if c.isalnum() or c in "-_")
        path_prefix = f"{path_prefix}{safe_test_name}/"

    s3_key = f"{path_prefix}{filename}"

    # Retry logic for transient errors
    import random
    import time

    base_delay = 1.0
    max_delay = 10.0

    for attempt in range(max_retries):
        try:
            # Create S3 client (recreate for each attempt in case of connection issues)
            session = boto3.Session(
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=aws_region,
            )
            s3_client = session.client("s3")

            # Check if object already exists (avoid re-uploading)
            # Skip check if force_upload is True
            if not force_upload:
                try:
                    s3_client.head_object(Bucket=bucket_name, Key=s3_key)
                    # Object exists, return URL without re-uploading
                    s3_url = f"https://{bucket_name}.s3.{aws_region}.amazonaws.com/{s3_key}"
                    _logger.info(f"Image already exists in S3 (reusing): {s3_url}")
                    return s3_url
                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code", "")
                    if error_code != "404":  # 404 means doesn't exist, which is fine
                        # Other error, might be transient
                        if attempt < max_retries - 1:
                            delay = min(base_delay * (2**attempt), max_delay)
                            jitter = random.uniform(0, delay * 0.1)
                            _logger.warning(
                                f"Error checking S3 object existence (attempt {attempt + 1}/{max_retries}): "
                                f"{error_code}. Retrying in {delay + jitter:.2f}s..."
                            )
                            time.sleep(delay + jitter)
                            continue
                        else:
                            _logger.error(f"Failed to check S3 object after {max_retries} attempts: {error_code}")
                            # Continue to try upload anyway

            # Upload to S3
            # Note: Bucket should be configured for public access via bucket policy
            # ACL is not used as modern S3 buckets often disable ACLs
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=image_data,
                ContentType=mime_type,
            )

            # Generate public URL
            s3_url = f"https://{bucket_name}.s3.{aws_region}.amazonaws.com/{s3_key}"

            _logger.info(f"Uploaded image to S3: {s3_url}")
            return s3_url

        except NoCredentialsError:
            _logger.error(f"CRITICAL: AWS credentials not configured. Cannot upload image to S3 bucket '{bucket_name}'. Pipeline will fail.")
            return None
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")

            # Non-retryable errors
            if error_code in ["NoSuchBucket", "AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch"]:
                _logger.error(f"CRITICAL: S3 upload failed with non-retryable error '{error_code}': {e}")
                return None

            # Retryable errors (transient network issues, throttling, etc.)
            if attempt < max_retries - 1:
                delay = min(base_delay * (2**attempt), max_delay)
                jitter = random.uniform(0, delay * 0.1)
                _logger.warning(
                    f"S3 upload failed (attempt {attempt + 1}/{max_retries}) with error '{error_code}': {e}. Retrying in {delay + jitter:.2f}s..."
                )
                time.sleep(delay + jitter)
                continue
            else:
                _logger.error(f"CRITICAL: S3 upload failed after {max_retries} attempts with error code '{error_code}': {e}")
                return None
        except Exception as e:
            # Other exceptions (network errors, timeouts, etc.) - retry
            if attempt < max_retries - 1:
                delay = min(base_delay * (2**attempt), max_delay)
                jitter = random.uniform(0, delay * 0.1)
                _logger.warning(f"Unexpected error uploading to S3 (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {delay + jitter:.2f}s...")
                time.sleep(delay + jitter)
                continue
            else:
                _logger.error(f"CRITICAL: Unexpected error uploading to S3 after {max_retries} attempts (bucket: {bucket_name}): {e}")
                return None

    return None


def upload_multiple_images_to_s3(
    images: list[dict[str, any]],
    question_id: Optional[str] = None,
    bucket_name: Optional[str] = None,
    path_prefix: str = "images/",
    test_name: Optional[str] = None,
    max_retries: int = 3,
) -> dict[str, Optional[str]]:
    """
    Upload multiple images to S3 with retry logic and return mapping of original to S3 URLs.

    Images are organized by test name to avoid conflicts between different tests.
    Each image upload includes automatic retry for transient errors.

    Args:
        images: List of image dicts with 'image_base64' key
        question_id: Optional question identifier
        bucket_name: S3 bucket name
        path_prefix: S3 path prefix base (default: "images/")
        test_name: Optional test/prueba name to organize images (e.g., "prueba-invierno-2026")
        max_retries: Maximum retry attempts per image (default: 3)

    Returns:
        Dictionary mapping original image identifiers to S3 URLs
    """
    results = {}

    for i, image_info in enumerate(images):
        image_base64 = image_info.get("image_base64")
        if not image_base64 or image_base64.startswith("CONTENT_PLACEHOLDER"):
            continue

        # Generate unique ID for this image
        img_id = f"{question_id}_img{i}" if question_id else f"img{i}"

        # Upload with retry (retry logic is inside upload_image_to_s3)
        s3_url = upload_image_to_s3(
            image_base64=image_base64,
            question_id=img_id,
            bucket_name=bucket_name,
            path_prefix=path_prefix,
            test_name=test_name,
            max_retries=max_retries,
        )

        # Store mapping (use index or a unique identifier)
        image_key = f"image_{i}"
        results[image_key] = s3_url

        # Also store in image_info for reference
        if s3_url:
            image_info["s3_url"] = s3_url

    return results


def convert_base64_to_s3_in_xml(
    qti_xml: str,
    question_id: Optional[str],
    test_name: Optional[str],
    output_dir: str,
) -> Optional[str]:
    """
    Manual conversion of base64 images to S3 URLs in XML (no LLM API calls).

    Detects base64 images in the XML, uploads them to S3 using upload_image_to_s3,
    and replaces the data URIs with S3 URLs.

    Args:
        qti_xml: QTI XML that may contain base64 images
        question_id: Question ID for naming the images
        test_name: Test name for organizing in S3
        output_dir: Output directory for saving S3 mapping

    Returns:
        Updated XML with S3 URLs, or None if there was a critical error
    """
    base64_pattern = r"(data:image/([^;]+);base64,)([A-Za-z0-9+/=\s]+)"
    base64_matches = list(re.finditer(base64_pattern, qti_xml))

    if not base64_matches:
        return qti_xml  # No base64, return XML unchanged

    _logger.info(f"Detected {len(base64_matches)} base64 image(s)")

    # Load existing S3 mapping if it exists
    s3_mapping_file = os.path.join(output_dir, "s3_image_mapping.json")
    s3_image_mapping: dict[str, str] = {}
    if os.path.exists(s3_mapping_file):
        try:
            with open(s3_mapping_file, "r", encoding="utf-8") as f:
                s3_image_mapping = json.load(f)
        except Exception:
            s3_image_mapping = {}

    updated_xml = qti_xml
    uploaded_count = 0
    reused_count = 0
    failed_count = 0

    for i, match in enumerate(base64_matches):
        full_data_uri = match.group(0)  # Complete URI

        # Check if already exists in S3 mapping
        s3_url = None
        img_keys = [f"image_{i}", f"{question_id}_manual_{i}", f"{question_id}_img{i}"]
        for key in img_keys:
            if key in s3_image_mapping:
                s3_url = s3_image_mapping[key]
                reused_count += 1
                _logger.info(f"Reusing image {i + 1} from S3 mapping")
                break

        # If not exists, upload to S3 (no LLM API - just S3 upload)
        if not s3_url:
            img_id = f"{question_id}_manual_{i}" if question_id else f"manual_{i}"
            _logger.info(f"Uploading image {i + 1}/{len(base64_matches)} to S3 (manual)...")

            s3_url = upload_image_to_s3(
                image_base64=full_data_uri,
                question_id=img_id,
                test_name=test_name,
            )

            if s3_url:
                uploaded_count += 1
                # Save in mapping
                for key in img_keys:
                    s3_image_mapping[key] = s3_url
                _logger.info(f"Image {i + 1} uploaded to S3: {s3_url}")
            else:
                failed_count += 1
                _logger.warning(f"Failed to upload image {i + 1} to S3 (will keep base64)")

        # Replace in XML if we have S3 URL
        if s3_url:
            updated_xml = updated_xml.replace(full_data_uri, s3_url, 1)

    # Save updated mapping
    if uploaded_count > 0 or reused_count > 0:
        try:
            with open(s3_mapping_file, "w", encoding="utf-8") as f:
                json.dump(s3_image_mapping, f, indent=2)
            status_parts = []
            if uploaded_count > 0:
                status_parts.append(f"{uploaded_count} new")
            if reused_count > 0:
                status_parts.append(f"{reused_count} reused")
            _logger.info(f"S3 mapping updated ({', '.join(status_parts)})")
        except Exception as e:
            _logger.error(f"Error saving S3 mapping: {e}")

    if failed_count > 0:
        _logger.warning(f"{failed_count} image(s) could not be uploaded (kept as base64)")

    return updated_xml
