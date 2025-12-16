"""
S3 Image Uploader

Uploads images to AWS S3 bucket and returns public URLs for use in QTI XML.
"""

from __future__ import annotations

import os
import base64
import hashlib
import logging
from typing import Optional
from pathlib import Path

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
) -> Optional[str]:
    """
    Upload a base64-encoded image to S3 and return the public URL.
    
    Images are organized by test name to avoid conflicts between different tests.
    Structure: images/{test_name}/{question_id}.png
    
    Args:
        image_base64: Base64-encoded image data (with or without data: prefix)
        question_id: Optional question identifier for naming
        bucket_name: S3 bucket name (uses AWS_S3_BUCKET from env if None)
        path_prefix: S3 path prefix base (default: "images/")
        test_name: Optional test/prueba name to organize images (e.g., "prueba-invierno-2026")
                   If provided, images will be stored in images/{test_name}/
        
    Returns:
        Public S3 URL of uploaded image, or None if upload failed
    """
    if not BOTO3_AVAILABLE:
        _logger.error("CRITICAL: boto3 not available, cannot upload to S3. Image upload will fail.")
        return None
    
    # Get bucket name from env if not provided
    if not bucket_name:
        bucket_name = os.environ.get("AWS_S3_BUCKET", "paes-question-images")
    
    # Get AWS credentials from env
    aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    aws_region = os.environ.get("AWS_REGION", "us-east-1")
    
    if not aws_access_key or not aws_secret_key:
        _logger.error(f"CRITICAL: AWS credentials not found (bucket: {bucket_name}). Cannot upload to S3. Image upload will fail.")
        return None
    
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
            # Sanitize test_name for use in S3 path
            safe_test_name = "".join(c for c in test_name if c.isalnum() or c in "-_")
            path_prefix = f"{path_prefix}{safe_test_name}/"
        
        s3_key = f"{path_prefix}{filename}"
        
        # Create S3 client
        session = boto3.Session(
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region,
        )
        s3_client = session.client("s3")
        
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
        if error_code == "NoSuchBucket":
            _logger.error(f"CRITICAL: S3 bucket '{bucket_name}' does not exist. Image upload failed. Pipeline will fail.")
        elif error_code == "AccessDenied":
            _logger.error(f"CRITICAL: Access denied to S3 bucket '{bucket_name}'. Check AWS credentials and permissions. Pipeline will fail.")
        else:
            _logger.error(f"CRITICAL: S3 upload failed with error code '{error_code}': {e}. Pipeline will fail.")
        return None
    except Exception as e:
        _logger.error(f"CRITICAL: Unexpected error uploading to S3 (bucket: {bucket_name}): {e}. Pipeline will fail.")
        return None


def upload_multiple_images_to_s3(
    images: list[dict[str, any]],
    question_id: Optional[str] = None,
    bucket_name: Optional[str] = None,
    path_prefix: str = "images/",
    test_name: Optional[str] = None,
) -> dict[str, Optional[str]]:
    """
    Upload multiple images to S3 and return mapping of original to S3 URLs.
    
    Images are organized by test name to avoid conflicts between different tests.
    
    Args:
        images: List of image dicts with 'image_base64' key
        question_id: Optional question identifier
        bucket_name: S3 bucket name
        path_prefix: S3 path prefix base (default: "images/")
        test_name: Optional test/prueba name to organize images (e.g., "prueba-invierno-2026")
        
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
        
        s3_url = upload_image_to_s3(
            image_base64=image_base64,
            question_id=img_id,
            bucket_name=bucket_name,
            path_prefix=path_prefix,
            test_name=test_name,
        )
        
        # Store mapping (use index or a unique identifier)
        image_key = f"image_{i}"
        results[image_key] = s3_url
        
        # Also store in image_info for reference
        if s3_url:
            image_info["s3_url"] = s3_url
    
    return results
