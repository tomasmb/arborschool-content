"""
Pipeline S3 Handler

Handles S3 image mapping, URL extraction, and post-processing of images
in the QTI conversion pipeline.
"""

from __future__ import annotations

import json
import os
import re
from typing import Optional

from .utils.s3_uploader import upload_image_to_s3


def load_s3_mapping(output_dir: str) -> dict[str, str]:
    """
    Load existing S3 image mapping from output directory.

    Args:
        output_dir: Directory containing s3_image_mapping.json

    Returns:
        Dictionary mapping image keys to S3 URLs
    """
    s3_mapping_file = os.path.join(output_dir, "s3_image_mapping.json")

    if not os.path.exists(s3_mapping_file):
        return {}

    try:
        with open(s3_mapping_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_s3_mapping(output_dir: str, mapping: dict[str, str]) -> bool:
    """
    Save S3 image mapping to output directory.

    Args:
        output_dir: Directory to save s3_image_mapping.json
        mapping: Dictionary mapping image keys to S3 URLs

    Returns:
        True if saved successfully, False otherwise
    """
    s3_mapping_file = os.path.join(output_dir, "s3_image_mapping.json")

    try:
        with open(s3_mapping_file, "w", encoding="utf-8") as f:
            json.dump(mapping, f, indent=2)
        return True
    except Exception as e:
        print(f"⚠️  Error saving S3 mapping: {e}")
        return False


def extract_s3_urls_from_xml(
    qti_xml: str,
    question_id: Optional[str] = None,
) -> dict[str, str]:
    """
    Extract S3 URLs from QTI XML and create a mapping.

    This captures images that were uploaded during transform_to_qti.

    Args:
        qti_xml: QTI XML content
        question_id: Optional question ID for generating mapping keys

    Returns:
        Dictionary mapping image keys to S3 URLs
    """
    mapping: dict[str, str] = {}
    s3_url_pattern = r'src=["\'](https://[^"\']+\.(png|jpg|jpeg|svg))["\']'
    s3_urls_found = re.findall(s3_url_pattern, qti_xml)

    for i, (url, _ext) in enumerate(s3_urls_found):
        mapping[f"image_{i}"] = url
        if question_id:
            mapping[f"{question_id}_img{i}"] = url

    return mapping


def initialize_s3_mapping_from_xml(
    qti_xml: str,
    output_dir: str,
    question_id: Optional[str] = None,
) -> dict[str, str]:
    """
    Initialize S3 mapping by merging existing mapping with URLs found in XML.

    Args:
        qti_xml: QTI XML content
        output_dir: Directory for s3_image_mapping.json
        question_id: Optional question ID for generating mapping keys

    Returns:
        Merged S3 mapping dictionary
    """
    # Load existing mapping
    existing_mapping = load_s3_mapping(output_dir)

    # Extract URLs from XML
    xml_mapping = extract_s3_urls_from_xml(qti_xml, question_id)

    # Merge (existing takes precedence for conflicts)
    merged_mapping = {**xml_mapping, **existing_mapping}

    # Save merged mapping if there are new URLs
    if xml_mapping:
        if save_s3_mapping(output_dir, merged_mapping):
            print(f"💾 S3 mapping initialized: {len(xml_mapping)} URL(s) detected")

    return merged_mapping


def process_restored_base64_images(
    qti_xml: str,
    output_dir: str,
    question_id: Optional[str] = None,
    test_name: Optional[str] = None,
) -> tuple[str, dict[str, str]]:
    """
    Process base64 images that were restored by restore_large_content.

    Attempts to upload each base64 image to S3 and replace in XML.
    Non-critical: if upload fails, keeps base64 and continues.

    Args:
        qti_xml: QTI XML with potentially restored base64 images
        output_dir: Directory for s3_image_mapping.json
        question_id: Question ID for S3 naming
        test_name: Test name for S3 organization

    Returns:
        Tuple of (updated_xml, s3_mapping)
    """
    base64_pattern = r"(data:image/([^;]+);base64,)([A-Za-z0-9+/=\s]+)"
    base64_matches = list(re.finditer(base64_pattern, qti_xml))

    if not base64_matches:
        return qti_xml, load_s3_mapping(output_dir)

    print(f"🔍 Processing {len(base64_matches)} restored image(s) - uploading to S3...")

    # Load existing mapping
    s3_mapping = load_s3_mapping(output_dir)

    uploaded_count = 0
    reused_count = 0
    failed_uploads = []
    updated_xml = qti_xml

    for i, match in enumerate(base64_matches):
        full_data_uri = match.group(0)

        # Check if already in S3
        s3_url = None
        img_keys = [f"image_{i}", f"{question_id}_restored_{i}", f"{question_id}_img{i}"]
        for key in img_keys:
            if key in s3_mapping:
                s3_url = s3_mapping[key]
                reused_count += 1
                print(f"   ✅ Reusing image {i + 1} from S3: {s3_url}")
                break

        # If not in S3, upload
        if not s3_url:
            img_id = f"{question_id}_restored_{i}" if question_id else f"restored_{i}"
            print(f"   📤 Uploading image {i + 1}/{len(base64_matches)} to S3...")

            s3_url = upload_image_to_s3(
                image_base64=full_data_uri,
                question_id=img_id,
                test_name=test_name,
            )

            if s3_url:
                uploaded_count += 1
                for key in img_keys:
                    s3_mapping[key] = s3_url
                print(f"   ✅ Image {i + 1} uploaded to S3: {s3_url}")
            else:
                failed_uploads.append(f"image_{i + 1}")
                print(f"   ⚠️  Image {i + 1} failed to upload - keeping base64")

        # Replace in XML if we have S3 URL
        if s3_url:
            updated_xml = updated_xml.replace(full_data_uri, s3_url, 1)
            print(f"   ✅ Image {i + 1} replaced with S3 URL")
        else:
            print(f"   💡 Image {i + 1} kept as base64 (can convert to S3 later)")

    # Summary
    if failed_uploads:
        print(f"   ⚠️  Summary: {len(failed_uploads)} image(s) kept as base64")
        print("   💡 XML will be saved. Convert to S3 later with migrate_base64_to_s3.py")

    # Save updated mapping
    status_parts = []
    if uploaded_count > 0:
        status_parts.append(f"{uploaded_count} new")
    if reused_count > 0:
        status_parts.append(f"{reused_count} reused")
    if failed_uploads:
        status_parts.append(f"{len(failed_uploads)} failed")

    if status_parts:
        if save_s3_mapping(output_dir, s3_mapping):
            print(f"   💾 S3 mapping saved ({', '.join(status_parts)})")

    return updated_xml, s3_mapping


def count_remaining_base64(qti_xml: str) -> int:
    """
    Count remaining base64 images in QTI XML.

    Args:
        qti_xml: QTI XML content

    Returns:
        Number of base64 images found
    """
    return len(re.findall(r"data:image/[^;]+;base64,", qti_xml))


def validate_all_images_in_s3(qti_xml: str) -> bool:
    """
    Validate that all images in XML are S3 URLs (no base64).

    Args:
        qti_xml: QTI XML content

    Returns:
        True if no base64 images remain
    """
    remaining = count_remaining_base64(qti_xml)
    if remaining > 0:
        print(f"⚠️  WARNING: {remaining} base64 image(s) found in XML")
        return False

    print("✅ Validation: All images are in S3 (0 base64)")
    return True


def print_base64_warning_with_instructions(test_name: Optional[str], count: int) -> None:
    """
    Print warning about remaining base64 images with instructions to fix.

    Args:
        test_name: Test name for the migration command
        count: Number of base64 images remaining
    """
    print(f"⚠️  WARNING: {count} base64 image(s) found in XML")
    print("💡 XML will be saved with base64. Convert to S3 later using:")
    print(f"   python3 scripts/migrate_base64_to_s3.py --test-name {test_name or 'test-name'}")


def post_validation_s3_processing(
    qti_xml: str,
    extracted_content: dict[str, any],
    output_dir: str,
    question_id: Optional[str],
    test_name: Optional[str],
) -> str:
    """
    Handle post-validation processing: restore content and S3 conversion.

    This function is called after initial validation passes to restore
    placeholder content and convert any remaining base64 images to S3.

    Args:
        qti_xml: QTI XML content
        extracted_content: Content that was extracted earlier
        output_dir: Output directory path
        question_id: Question ID for S3 naming
        test_name: Test name for S3 organization

    Returns:
        Updated QTI XML with restored content and S3 URLs
    """
    # Import here to avoid circular dependency
    from modules.content_processing import restore_large_content

    print("🔄 Restoring placeholders with images from extracted_content...")
    qti_xml = restore_large_content(qti_xml, extracted_content)

    print("🔍 Checking restored images (converting base64 → S3)...")

    qti_xml, _ = process_restored_base64_images(qti_xml, output_dir, question_id, test_name)

    remaining_base64 = count_remaining_base64(qti_xml)
    if remaining_base64 > 0:
        print_base64_warning_with_instructions(test_name, remaining_base64)
    else:
        print("✅ Final validation: All images are in S3 (0 base64)")

    # Save XML
    xml_path = os.path.join(output_dir, "question.xml")
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(qti_xml)
    status = f" ({remaining_base64} with base64)" if remaining_base64 else " (100% S3)"
    print(f"✅ QTI XML saved{status}: {xml_path}")

    # Try manual conversion if base64 remains
    if remaining_base64 > 0:
        qti_xml = _try_manual_s3_conversion(qti_xml, xml_path, question_id, test_name, output_dir, remaining_base64)

    return qti_xml


def _try_manual_s3_conversion(
    qti_xml: str,
    xml_path: str,
    question_id: Optional[str],
    test_name: Optional[str],
    output_dir: str,
    remaining_count: int,
) -> str:
    """Attempt manual base64 to S3 conversion."""
    print(f"\n🔧 MANUAL CONVERSION: Converting {remaining_count} base64 image(s)...")
    converted_xml = convert_base64_to_s3_in_xml(qti_xml, question_id, test_name, output_dir)
    if converted_xml:
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(converted_xml)
        new_remaining = count_remaining_base64(converted_xml)
        if new_remaining == 0:
            print("   ✅ Manual conversion successful: all images now in S3")
        else:
            print(f"   ⚠️  Partial conversion: {new_remaining} image(s) still base64")
        return converted_xml
    return qti_xml


def convert_base64_to_s3_in_xml(
    qti_xml: str,
    question_id: Optional[str],
    test_name: Optional[str],
    output_dir: str,
) -> Optional[str]:
    """
    Convert base64 images to S3 URLs in XML.

    Wrapper that calls the s3_uploader function.
    """
    from .utils.s3_uploader import convert_base64_to_s3_in_xml as _convert

    return _convert(qti_xml, question_id, test_name, output_dir)
