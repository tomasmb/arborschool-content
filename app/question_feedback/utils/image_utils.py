"""Utilities for handling question images."""

from __future__ import annotations

import base64
import io
import logging
import re
from typing import Any

import requests

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore

logger = logging.getLogger(__name__)


def extract_image_urls(qti_xml: str) -> list[str]:
    """Extract all image URLs from QTI XML.

    Looks for img tags with src attributes and object/embed tags with data attributes.

    Args:
        qti_xml: QTI XML string.

    Returns:
        List of image URLs found in the XML.
    """
    urls: list[str] = []

    # Pattern for img tags with src attribute
    img_pattern = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)
    urls.extend(img_pattern.findall(qti_xml))

    # Pattern for object/embed tags with data attribute
    object_pattern = re.compile(
        r'<object[^>]+data=["\']([^"\']+)["\']', re.IGNORECASE
    )
    urls.extend(object_pattern.findall(qti_xml))

    return urls


def is_s3_url(url: str) -> bool:
    """Check if URL is an S3 URL.

    Args:
        url: URL string to check.

    Returns:
        True if the URL points to S3.
    """
    return "s3.amazonaws.com" in url or url.startswith("s3://")


def is_data_url(url: str) -> bool:
    """Check if URL is a data URL (base64 encoded).

    Args:
        url: URL string to check.

    Returns:
        True if the URL is a data URL.
    """
    return url.startswith("data:")


def normalize_image_url(url: str, base_url: str | None = None) -> str:
    """Normalize an image URL to an absolute URL.

    Args:
        url: Image URL (may be relative).
        base_url: Base URL for resolving relative paths.

    Returns:
        Absolute URL string.
    """
    # Already absolute
    if url.startswith("http://") or url.startswith("https://"):
        return url

    # S3 protocol
    if url.startswith("s3://"):
        return url

    # Data URL
    if url.startswith("data:"):
        return url

    # Relative URL - needs base
    if base_url:
        base_url = base_url.rstrip("/")
        url = url.lstrip("/")
        return f"{base_url}/{url}"

    return url


def download_image_from_url(url: str, timeout: int = 15) -> Any | None:
    """Download an image from HTTP/HTTPS URL and return PIL Image.

    Args:
        url: HTTP/HTTPS URL to download.
        timeout: Request timeout in seconds.

    Returns:
        PIL Image object or None if download fails.
    """
    if not Image:
        logger.warning("PIL not installed, skipping image download")
        return None

    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()

        img_io = io.BytesIO(response.content)
        img = Image.open(img_io)
        img.verify()

        # Re-open after verify (verify consumes the image)
        img_io.seek(0)
        img = Image.open(img_io)
        return img
    except Exception as e:
        logger.warning(f"Failed to download image from {url}: {e}")
        return None


def decode_data_url(data_url: str) -> Any | None:
    """Decode a base64 data URL and return PIL Image.

    Args:
        data_url: Data URL in format data:image/...;base64,...

    Returns:
        PIL Image object or None if decoding fails.
    """
    if not Image:
        logger.warning("PIL not installed, skipping image decode")
        return None

    try:
        # Extract base64 data from data URL
        match = re.match(r"data:image/[^;]+;base64,(.+)", data_url)
        if not match:
            logger.warning(f"Invalid data URL format: {data_url[:50]}...")
            return None

        base64_data = match.group(1)
        image_data = base64.b64decode(base64_data)
        img_io = io.BytesIO(image_data)
        img = Image.open(img_io)
        return img
    except Exception as e:
        logger.warning(f"Failed to decode data URL: {e}")
        return None


def load_images_from_urls(image_urls: list[str]) -> list[Any]:
    """Load images from URLs (HTTP, HTTPS, or data URLs).

    Args:
        image_urls: List of image URLs.

    Returns:
        List of PIL Image objects (only successfully loaded images).
    """
    images: list[Any] = []
    for url in image_urls:
        if url.startswith("data:"):
            img = decode_data_url(url)
        elif url.startswith("http://") or url.startswith("https://"):
            img = download_image_from_url(url)
        else:
            logger.warning(f"Unsupported image URL format: {url[:50]}...")
            continue

        if img:
            images.append(img)

    if images:
        logger.info(f"Successfully loaded {len(images)}/{len(image_urls)} images")

    return images
