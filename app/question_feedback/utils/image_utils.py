"""Utilities for handling question images."""

from __future__ import annotations

import re


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
