"""
Content Validation Rules

This module defines validation rules that REJECT content which would
otherwise require post-generation fixes. The pipeline should fail fast
when these issues are detected, rather than producing bad content.

Following SOLID principles:
- Single Responsibility: Each rule validates one specific issue
- Open/Closed: New rules can be added without modifying existing ones
- DRY: Common patterns are extracted into helpers
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

# Import centralized encoding detection from qti_transformer
from ..qti_transformer import detect_encoding_errors as _detect_encoding_errors


@dataclass
class ValidationResult:
    """Result of a validation rule check."""

    passed: bool
    rule_name: str
    message: str
    details: str | None = None

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        result = f"[{status}] {self.rule_name}: {self.message}"
        if self.details:
            result += f"\n  Details: {self.details}"
        return result


# Type alias for validation rule functions
ValidationRule = Callable[[str], ValidationResult]


def validate_no_base64_images(xml_content: str) -> ValidationResult:
    """
    REJECT if XML contains base64-encoded images.

    Base64 images should never be in the final XML - all images must be
    uploaded to S3 and referenced by URL. This was the root cause of
    fix_base64_in_xmls.py.

    Args:
        xml_content: The XML content to validate

    Returns:
        ValidationResult with pass/fail status
    """
    rule_name = "no_base64_images"

    # Pattern to detect base64 data URIs
    base64_pattern = r'data:image/[^;]+;base64,[A-Za-z0-9+/=]+'

    matches = re.findall(base64_pattern, xml_content)

    if matches:
        # Truncate for readability
        sample = matches[0][:50] + "..." if len(matches[0]) > 50 else matches[0]
        return ValidationResult(
            passed=False,
            rule_name=rule_name,
            message=f"Found {len(matches)} base64 image(s) embedded in XML",
            details=f"Images must be uploaded to S3, not embedded. Sample: {sample}",
        )

    return ValidationResult(
        passed=True,
        rule_name=rule_name,
        message="No base64 images found",
    )


def validate_no_encoding_errors(content: str) -> ValidationResult:
    """
    REJECT if content contains known encoding error patterns.

    These patterns indicate PDF text extraction failed for Spanish
    characters with accents. Uses the centralized detection from qti_transformer.

    Args:
        content: The text content to validate (XML or plain text)

    Returns:
        ValidationResult with pass/fail status
    """
    rule_name = "no_encoding_errors"

    # Use centralized detection function (DRY principle)
    found_errors = _detect_encoding_errors(content)

    if found_errors:
        return ValidationResult(
            passed=False,
            rule_name=rule_name,
            message=f"Found {len(found_errors)} encoding error pattern(s)",
            details=f"Patterns like '{found_errors[0]}' indicate broken Spanish character encoding. "
                    "The source PDF has non-standard font mappings.",
        )

    return ValidationResult(
        passed=True,
        rule_name=rule_name,
        message="No encoding errors detected",
    )


def validate_xml_structure(xml_content: str) -> ValidationResult:
    """
    REJECT if XML is malformed or missing required QTI elements.

    Args:
        xml_content: The XML content to validate

    Returns:
        ValidationResult with pass/fail status
    """
    rule_name = "xml_structure"

    # Check for required QTI elements
    required_elements = [
        "qti-assessment-item",
        "qti-item-body",
        "qti-response-declaration",
    ]

    missing = []
    for elem in required_elements:
        if elem not in xml_content:
            missing.append(elem)

    if missing:
        return ValidationResult(
            passed=False,
            rule_name=rule_name,
            message=f"Missing required QTI element(s): {', '.join(missing)}",
        )

    # Basic XML well-formedness check
    import xml.etree.ElementTree as ET

    try:
        ET.fromstring(xml_content)
    except ET.ParseError as e:
        return ValidationResult(
            passed=False,
            rule_name=rule_name,
            message="XML is not well-formed",
            details=str(e),
        )

    return ValidationResult(
        passed=True,
        rule_name=rule_name,
        message="XML structure is valid",
    )


def validate_images_have_urls(xml_content: str) -> ValidationResult:
    """
    REJECT if img elements don't have valid S3 URLs.

    All images should reference S3 URLs (https://...) not local paths
    or data URIs.

    Args:
        xml_content: The XML content to validate

    Returns:
        ValidationResult with pass/fail status
    """
    rule_name = "images_have_urls"

    # Find all img src attributes
    img_pattern = r'<(?:img|qti-printed-variable)[^>]*src=["\']([^"\']+)["\']'
    sources = re.findall(img_pattern, xml_content, re.IGNORECASE)

    invalid_sources = []
    for src in sources:
        # Valid: https:// URLs (S3)
        if src.startswith("https://"):
            continue
        # Invalid: data URIs, local paths, http://
        invalid_sources.append(src[:50] + "..." if len(src) > 50 else src)

    if invalid_sources:
        return ValidationResult(
            passed=False,
            rule_name=rule_name,
            message=f"Found {len(invalid_sources)} image(s) without valid S3 URLs",
            details=f"Invalid sources: {invalid_sources[:3]}",
        )

    return ValidationResult(
        passed=True,
        rule_name=rule_name,
        message="All images have valid S3 URLs",
    )


def run_all_xml_validations(xml_content: str) -> list[ValidationResult]:
    """
    Run all XML validation rules and return results.

    Args:
        xml_content: The XML content to validate

    Returns:
        List of ValidationResult objects
    """
    rules: list[ValidationRule] = [
        validate_no_base64_images,
        validate_no_encoding_errors,
        validate_xml_structure,
        validate_images_have_urls,
    ]

    return [rule(xml_content) for rule in rules]


def validate_xml_or_raise(xml_content: str) -> None:
    """
    Validate XML content and raise ValueError if any rule fails.

    This is the main entry point for pipeline validation. Call this
    before accepting generated QTI XML.

    Args:
        xml_content: The XML content to validate

    Raises:
        ValueError: If any validation rule fails
    """
    results = run_all_xml_validations(xml_content)

    failures = [r for r in results if not r.passed]

    if failures:
        error_messages = [str(f) for f in failures]
        raise ValueError(
            f"Content validation failed with {len(failures)} error(s):\n"
            + "\n".join(error_messages)
        )
