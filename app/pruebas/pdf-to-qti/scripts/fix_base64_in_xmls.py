#!/usr/bin/env python3
"""
Script para corregir XMLs que contienen base64, subiendo las imágenes a S3
y reemplazando el base64 con URLs de S3.

Uso:
    python scripts/fix_base64_in_xmls.py <test_name> [--dry-run]

Ejemplo:
    python scripts/fix_base64_in_xmls.py seleccion-regular-2026
    python scripts/fix_base64_in_xmls.py seleccion-regular-2026 --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.utils.s3_uploader import upload_image_to_s3


def find_xmls_with_base64(test_name: str) -> List[Path]:
    """Find all XML files in the test directory that contain base64."""
    base_dir = Path(f"app/data/pruebas/procesadas/{test_name}/qti")

    if not base_dir.exists():
        print(f"❌ Directory not found: {base_dir}")
        return []

    xmls_with_base64 = []

    # Pattern to match base64 data URIs
    base64_pattern = r'data:image/[^;]+;base64,[A-Za-z0-9+/=\s]+'

    for q_folder in base_dir.iterdir():
        if q_folder.is_dir() and q_folder.name.startswith('Q'):
            xml_file = q_folder / "question.xml"
            if xml_file.exists():
                with open(xml_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if re.search(base64_pattern, content):
                        xmls_with_base64.append(xml_file)

    return xmls_with_base64


def extract_base64_from_xml(xml_content: str) -> List[Tuple[str, str]]:
    """
    Extract all base64 data URIs from XML content.

    Returns:
        List of tuples: (full_data_uri, base64_data_without_prefix)
    """
    # Pattern to match data:image/<type>;base64,<data>
    pattern = r'(data:image/([^;]+);base64,)([A-Za-z0-9+/=\s]+)'

    matches = re.findall(pattern, xml_content)
    results = []

    for match in matches:
        full_prefix = match[0]  # data:image/png;base64,
        match[1]    # png, svg+xml, etc.
        base64_data = match[2]   # actual base64 data
        full_data_uri = full_prefix + base64_data

        results.append((full_data_uri, base64_data))

    return results


def replace_base64_with_s3_url(
    xml_content: str,
    base64_uri: str,
    s3_url: str
) -> str:
    """Replace a base64 data URI with an S3 URL in XML content."""
    # Escape special regex characters in the URI
    escaped_uri = re.escape(base64_uri)
    # Replace in src attributes
    xml_content = re.sub(
        rf'src=["\']{escaped_uri}["\']',
        f'src="{s3_url}"',
        xml_content
    )
    return xml_content


def fix_xml_file(
    xml_file: Path,
    test_name: str,
    dry_run: bool = False
) -> Dict[str, any]:
    """
    Fix a single XML file by uploading base64 images to S3 and replacing them.

    Returns:
        Dictionary with results
    """
    question_id = xml_file.parent.name  # e.g., "Q1", "Q19"

    print(f"\n📄 Processing: {xml_file}")

    with open(xml_file, 'r', encoding='utf-8') as f:
        xml_content = f.read()

    # Extract all base64 URIs
    base64_matches = extract_base64_from_xml(xml_content)

    if not base64_matches:
        print("  ✅ No base64 found (already fixed?)")
        return {"success": True, "fixed": 0, "question_id": question_id}

    print(f"  🔍 Found {len(base64_matches)} base64 image(s)")

    if dry_run:
        print(f"  🔍 DRY RUN: Would upload {len(base64_matches)} image(s) to S3")
        return {"success": True, "fixed": 0, "question_id": question_id, "dry_run": True}

    fixed_count = 0
    errors = []

    for i, (full_uri, base64_data) in enumerate(base64_matches):
        print(f"  📤 Uploading image {i+1}/{len(base64_matches)} to S3...")

        # Add data URI prefix back for upload function
        data_uri = f"data:image/png;base64,{base64_data}"

        # Upload to S3
        s3_url = upload_image_to_s3(
            image_base64=data_uri,
            question_id=f"{question_id}_img{i+1}",
            test_name=test_name
        )

        if not s3_url:
            error_msg = f"Failed to upload image {i+1} to S3"
            print(f"  ❌ {error_msg}")
            errors.append(error_msg)
            continue

        print(f"  ✅ Uploaded to: {s3_url}")

        # Replace in XML
        xml_content = replace_base64_with_s3_url(xml_content, full_uri, s3_url)
        fixed_count += 1

    if errors:
        return {
            "success": False,
            "fixed": fixed_count,
            "errors": errors,
            "question_id": question_id
        }

    # Write fixed XML
    if fixed_count > 0:
        with open(xml_file, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        print(f"  ✅ Fixed {fixed_count} image(s) in XML")

    return {
        "success": True,
        "fixed": fixed_count,
        "question_id": question_id
    }


def main():
    parser = argparse.ArgumentParser(
        description="Fix XMLs with base64 by uploading images to S3"
    )
    parser.add_argument(
        "test_name",
        help="Test name (e.g., 'seleccion-regular-2026')"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only show what would be fixed, don't make changes"
    )

    args = parser.parse_args()

    print(f"🔍 Looking for XMLs with base64 in: {args.test_name}")

    # Find XMLs with base64
    xmls_with_base64 = find_xmls_with_base64(args.test_name)

    if not xmls_with_base64:
        print("✅ No XMLs with base64 found!")
        return 0

    print(f"📊 Found {len(xmls_with_base64)} XML file(s) with base64")

    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made\n")

    results = []
    for xml_file in xmls_with_base64:
        result = fix_xml_file(xml_file, args.test_name, dry_run=args.dry_run)
        results.append(result)

    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)

    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]
    total_fixed = sum(r.get("fixed", 0) for r in results)

    print(f"✅ Successfully processed: {len(successful)}")
    print(f"❌ Failed: {len(failed)}")
    print(f"🖼️  Total images fixed: {total_fixed}")

    if failed:
        print("\n❌ Failed questions:")
        for r in failed:
            print(f"   - {r.get('question_id')}: {r.get('errors')}")

    if args.dry_run:
        print("\n💡 Run without --dry-run to apply fixes")

    return 0 if len(failed) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
