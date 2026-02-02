"""
Pipeline Cache Handler

Handles caching, skip logic, and regeneration of QTI from processed content.
Optimizes pipeline by reusing existing valid XMLs and regenerating from
intermediate JSON files when possible.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Optional

from .validation import validate_qti_xml


def check_existing_xml(
    output_dir: str,
    validation_endpoint: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """
    Check if a valid QTI XML already exists in the output directory.

    If valid XML exists, returns a result dict that can be used directly.
    Otherwise returns None to indicate processing should continue.

    Args:
        output_dir: Directory where question.xml would be stored
        validation_endpoint: Optional QTI validation endpoint URL

    Returns:
        Result dict if valid XML exists, None otherwise
    """
    xml_path = os.path.join(output_dir, "question.xml")

    if not os.path.exists(xml_path):
        return None

    # Validate the existing XML
    try:
        with open(xml_path, "r", encoding="utf-8") as f:
            existing_xml = f.read()

        validation_result = validate_qti_xml(existing_xml, validation_endpoint)

        if validation_result.get("success", False):
            print(f"✅ QTI XML already exists and is valid: {xml_path}")
            print("   ⏭️  Skipping processing (disable with skip_if_exists=False)")

            # Extract title from existing XML
            title_match = re.search(r'<qti-assessment-item[^>]*title="([^"]*)"', existing_xml)
            title = title_match.group(1) if title_match else "Existing Question"

            return {
                "success": True,
                "title": title,
                "skipped": True,
                "xml_path": xml_path,
                "message": "Reused existing valid XML",
            }
        else:
            print("⚠️  Existing XML not valid, regenerating...")
            return None

    except Exception as e:
        print(f"⚠️  Error validating existing XML: {e}, regenerating...")
        return None


def try_regenerate_from_processed(
    output_dir: str,
    api_key: str,
    paes_mode: bool = False,
    test_name: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """
    Try to regenerate QTI XML from processed_content.json if it exists.

    This is useful when XML doesn't exist but the intermediate processing
    results are available, avoiding full reprocessing.

    Args:
        output_dir: Directory containing processed_content.json
        api_key: API key for LLM calls
        paes_mode: Whether to use PAES optimizations
        test_name: Test name for S3 organization

    Returns:
        Result dict if regeneration successful, None otherwise
    """
    xml_path = os.path.join(output_dir, "question.xml")
    processed_json_path = os.path.join(output_dir, "processed_content.json")

    # Only try if XML doesn't exist but processed content does
    if os.path.exists(xml_path) or not os.path.exists(processed_json_path):
        return None

    print("📖 Found processed_content.json, attempting to regenerate XML...")

    try:
        # Import regeneration function (lazy import to avoid circular deps)
        from scripts.regenerate_qti_from_processed import regenerate_qti_from_processed

        result = regenerate_qti_from_processed(
            question_dir=Path(output_dir),
            api_key=api_key,
            paes_mode=paes_mode,
            test_name=test_name,
        )

        if result.get("success"):
            print("✅ XML regenerated successfully from processed_content.json")

            # Read title from regenerated XML
            if os.path.exists(xml_path):
                with open(xml_path, "r", encoding="utf-8") as f:
                    regenerated_xml = f.read()
                title_match = re.search(r'<qti-assessment-item[^>]*title="([^"]*)"', regenerated_xml)
                title = title_match.group(1) if title_match else "Regenerated Question"

                return {
                    "success": True,
                    "title": title,
                    "regenerated": True,
                    "xml_path": xml_path,
                    "message": "Regenerated from processed_content.json",
                }

        return None

    except Exception as e:
        print(f"⚠️  Error regenerating from processed_content.json: {e}")
        print("   Continuing with full processing...")
        return None


def try_auto_regenerate_on_error(
    output_dir: str,
    api_key: str,
    original_error: str,
    paes_mode: bool = False,
    test_name: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """
    Attempt auto-regeneration from processed_content.json after an error.

    This is a recovery mechanism when the main processing fails but
    intermediate results are available.

    Args:
        output_dir: Directory containing processed_content.json
        api_key: API key for LLM calls
        original_error: The original error message that triggered recovery
        paes_mode: Whether to use PAES optimizations
        test_name: Test name for S3 organization

    Returns:
        Result dict if regeneration successful, None otherwise
    """
    processed_json_path = os.path.join(output_dir, "processed_content.json")

    if not os.path.exists(processed_json_path):
        return None

    print("🔄 Attempting auto-regeneration from processed_content.json...")

    try:
        from scripts.regenerate_qti_from_processed import regenerate_qti_from_processed

        result = regenerate_qti_from_processed(
            question_dir=Path(output_dir),
            api_key=api_key,
            paes_mode=paes_mode,
            test_name=test_name,
        )

        if result.get("success"):
            print("✅ Auto-regeneration successful!")

            xml_path = os.path.join(output_dir, "question.xml")
            if os.path.exists(xml_path):
                with open(xml_path, "r", encoding="utf-8") as f:
                    regenerated_xml = f.read()
                title_match = re.search(r'<qti-assessment-item[^>]*title="([^"]*)"', regenerated_xml)
                title = title_match.group(1) if title_match else "Regenerated Question"

                return {
                    "success": True,
                    "title": title,
                    "regenerated": True,
                    "auto_regenerated": True,
                    "xml_path": xml_path,
                    "message": f"Auto-regenerated after error: {original_error}",
                }

        return None

    except Exception as regen_error:
        print(f"⚠️  Auto-regeneration failed: {regen_error}")
        print(f"   Original error: {original_error}")
        return None


def extract_test_name_from_path(path: str) -> Optional[str]:
    """
    Extract test name from a file path.

    Looks for patterns like 'prueba-invierno-2025' or 'seleccion-xxx' in the path.

    Args:
        path: File or directory path

    Returns:
        Test name if found, None otherwise
    """
    test_match = re.search(r"prueba-[^/]+|seleccion-[^/]+", path)
    return test_match.group(0) if test_match else None
