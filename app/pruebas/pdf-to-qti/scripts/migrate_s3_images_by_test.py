#!/usr/bin/env python3
"""
Script to migrate existing S3 images to organize them by test name.

This script moves images from images/ to images/{test_name}/ to avoid conflicts
when processing multiple tests.

Usage:
    python migrate_s3_images_by_test.py --test-name prueba-invierno-2026 [--dry-run]
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Calculate project root and load env
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent.parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)

# Import utilities
try:
    from app.pruebas.pdf_to_qti.scripts.s3_migration_utils import (
        copy_image_in_s3,
        delete_image_from_s3,
        get_s3_client,
        list_images_in_prefix,
        update_xml_urls,
    )
except ImportError:
    # Fallback for direct script execution
    from s3_migration_utils import (
        copy_image_in_s3,
        delete_image_from_s3,
        get_s3_client,
        list_images_in_prefix,
        update_xml_urls,
    )

try:
    from botocore.exceptions import ClientError
except ImportError:
    print("❌ boto3 not available. Install it with: pip install boto3")
    sys.exit(1)


def migrate_images_to_test_folder(
    bucket_name: str,
    test_name: str,
    dry_run: bool = False,
    delete_originals: bool = False
) -> dict[str, Any]:
    """
    Migrate images from images/ to images/{test_name}/.

    Args:
        bucket_name: S3 bucket name
        test_name: Test name for folder organization
        dry_run: If True, only print what would happen
        delete_originals: If True, delete originals after copying

    Returns:
        Results dictionary with migration stats
    """
    print(f"📦 Migrating images to test folder: images/{test_name}/")
    print(f"   Bucket: {bucket_name}")
    print(f"   Dry run: {dry_run}")
    print()

    s3_client, _ = get_s3_client()

    print("🔍 Listing images in images/...")
    all_images = list_images_in_prefix(s3_client, bucket_name, "images/")

    # Filter to only images directly in images/ (not in subfolders)
    root_images = [
        img for img in all_images
        if img.startswith("images/") and img.count("/") == 1
    ]

    if not root_images:
        print("   ℹ️  No images found in images/")
        return {"success": True, "migrated": 0, "skipped": 0, "failed": 0}

    print(f"   Found {len(root_images)} image(s) in images/")
    print()

    results: dict[str, Any] = {
        "migrated": 0,
        "skipped": 0,
        "failed": 0,
        "operations": []
    }

    new_prefix = f"images/{test_name}/"

    for source_key in sorted(root_images):
        _migrate_single_image(
            s3_client, bucket_name, source_key, new_prefix,
            dry_run, delete_originals, results
        )

    _print_migration_summary(results, dry_run)
    results["success"] = results["failed"] == 0
    return results


def _migrate_single_image(
    s3_client: Any,
    bucket_name: str,
    source_key: str,
    new_prefix: str,
    dry_run: bool,
    delete_originals: bool,
    results: dict[str, Any]
) -> None:
    """Migrate a single image to the new folder structure."""
    filename = source_key.split("/")[-1]
    dest_key = f"{new_prefix}{filename}"

    # Check if destination already exists
    try:
        s3_client.head_object(Bucket=bucket_name, Key=dest_key)
        print(f"⚠️  Skipping {source_key} (destination {dest_key} already exists)")
        results["skipped"] += 1
        results["operations"].append({
            "source": source_key,
            "dest": dest_key,
            "status": "skipped",
            "reason": "destination exists"
        })
        return
    except ClientError as e:
        if e.response["Error"]["Code"] != "404":
            print(f"❌ Error checking {dest_key}: {e}")
            results["failed"] += 1
            return

    # Copy the image
    print(f"📋 Processing: {filename}")
    if copy_image_in_s3(s3_client, bucket_name, source_key, dest_key, dry_run):
        results["migrated"] += 1
        results["operations"].append({
            "source": source_key,
            "dest": dest_key,
            "status": "copied"
        })

        if delete_originals:
            delete_image_from_s3(s3_client, bucket_name, source_key, dry_run)
            results["operations"][-1]["original_deleted"] = True
    else:
        results["failed"] += 1
        results["operations"].append({
            "source": source_key,
            "dest": dest_key,
            "status": "failed"
        })


def _print_migration_summary(results: dict[str, Any], dry_run: bool) -> None:
    """Print migration summary."""
    print()
    print("=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    print(f"Migrated: {results['migrated']}")
    print(f"Skipped: {results['skipped']}")
    print(f"Failed: {results['failed']}")

    if dry_run:
        print()
        print("💡 This was a dry run. Use --no-dry-run to actually perform the migration.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate S3 images to organize them by test name and update XML URLs"
    )
    parser.add_argument(
        "--test-name", required=True,
        help="Test/prueba name (e.g., 'prueba-invierno-2026')"
    )
    parser.add_argument(
        "--bucket", default=None,
        help="S3 bucket name (uses AWS_S3_BUCKET from env if not provided)"
    )
    parser.add_argument(
        "--xml-dir", default=None,
        help="Directory containing QTI XML files to update"
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=True,
        help="Perform a dry run without making changes (default: True)"
    )
    parser.add_argument(
        "--no-dry-run", action="store_true",
        help="Actually perform the migration (disables dry-run)"
    )
    parser.add_argument(
        "--delete-originals", action="store_true",
        help="Delete original images after copying (USE WITH CAUTION)"
    )
    parser.add_argument(
        "--skip-xml-update", action="store_true",
        help="Skip XML URL updates (only migrate images)"
    )

    args = parser.parse_args()

    bucket_name = args.bucket or os.environ.get("AWS_S3_BUCKET", "paes-question-images")
    dry_run = args.dry_run and not args.no_dry_run

    print("=" * 60)
    print("S3 Image Migration Tool")
    print("=" * 60)
    print()

    try:
        # Reload env
        if env_file.exists():
            load_dotenv(env_file, override=True)

        aws_region = os.environ.get("AWS_REGION", "us-east-1")
        if not dry_run or not args.skip_xml_update:
            try:
                _, aws_region = get_s3_client()
            except ValueError:
                if dry_run:
                    print("⚠️  AWS credentials not found, using default region for URL patterns")
                else:
                    raise

        # Step 1: Migrate images in S3
        image_results = _run_image_migration(args, bucket_name, dry_run)

        # Step 2: Update XML URLs
        xml_results = _run_xml_update(args, bucket_name, aws_region, dry_run)

        # Final summary
        _print_final_summary(image_results, xml_results, dry_run)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def _run_image_migration(
    args: argparse.Namespace,
    bucket_name: str,
    dry_run: bool
) -> dict[str, Any] | None:
    """Run the image migration step."""
    if args.skip_xml_update and dry_run:
        return None

    try:
        print("STEP 1: Migrating images in S3")
        print("=" * 60)
        return migrate_images_to_test_folder(
            bucket_name=bucket_name,
            test_name=args.test_name,
            dry_run=dry_run,
            delete_originals=args.delete_originals
        )
    except ValueError as e:
        if dry_run:
            print(f"⚠️  {e}")
            print("   Continuing with XML updates only (dry-run mode)")
            return {"success": True, "migrated": 0, "skipped": 0, "failed": 0}
        raise


def _run_xml_update(
    args: argparse.Namespace,
    bucket_name: str,
    aws_region: str,
    dry_run: bool
) -> dict[str, Any] | None:
    """Run the XML URL update step."""
    if args.skip_xml_update:
        print()
        print("⏭️  Skipping XML URL updates (--skip-xml-update)")
        return None

    print()
    print()
    print("STEP 2: Updating URLs in XML files")
    print("=" * 60)

    if args.xml_dir:
        xml_dir = Path(args.xml_dir)
    else:
        xml_dir = (
            project_root / "app" / "data" / "pruebas" / "procesadas" /
            args.test_name / "qti"
        )
        print(f"   Using inferred XML directory: {xml_dir}")

    return update_xml_urls(
        xml_dir=xml_dir,
        bucket_name=bucket_name,
        aws_region=aws_region,
        test_name=args.test_name,
        dry_run=dry_run
    )


def _print_final_summary(
    image_results: dict[str, Any] | None,
    xml_results: dict[str, Any] | None,
    dry_run: bool
) -> None:
    """Print final summary."""
    print()
    print()
    print("=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)

    if image_results:
        print(f"Images migrated: {image_results['migrated']}")
        print(f"Images skipped: {image_results['skipped']}")
        print(f"Images failed: {image_results['failed']}")

    if xml_results:
        print(f"XML files updated: {xml_results['updated']}")
        print(f"XML files failed: {xml_results['failed']}")

    overall_success = (
        (image_results is None or image_results["success"]) and
        (xml_results is None or xml_results["success"])
    )

    if overall_success:
        print()
        print("✅ Migration completed successfully!")
        if dry_run:
            print("   Run with --no-dry-run to actually perform the migration.")
    else:
        print()
        print("❌ Migration completed with errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
