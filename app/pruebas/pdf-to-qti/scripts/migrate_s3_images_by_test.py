#!/usr/bin/env python3
"""
Script to migrate existing S3 images to organize them by test name.

This script moves images from images/ to images/{test_name}/ to avoid conflicts
when processing multiple tests.

Usage:
    python migrate_s3_images_by_test.py --test-name prueba-invierno-2026 [--dry-run]
"""

from __future__ import annotations

import os
import sys
import argparse
import re
from pathlib import Path
from typing import List, Dict, Optional

# Load environment variables
from dotenv import load_dotenv
# Calculate project root: scripts/ -> pdf-to-qti/ -> pruebas/ -> app/ -> arborschool-content/
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent.parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    print("❌ boto3 not available. Install it with: pip install boto3")
    sys.exit(1)


def get_s3_client():
    """Get S3 client with credentials from environment."""
    aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    aws_region = os.environ.get("AWS_REGION", "us-east-1")
    
    if not aws_access_key or not aws_secret_key:
        raise ValueError("AWS credentials not found in environment. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
    
    session = boto3.Session(
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=aws_region,
    )
    return session.client("s3"), aws_region


def list_images_in_prefix(s3_client, bucket_name: str, prefix: str) -> List[str]:
    """List all image keys in S3 with the given prefix."""
    images = []
    paginator = s3_client.get_paginator("list_objects_v2")
    
    try:
        for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
            if "Contents" in page:
                for obj in page["Contents"]:
                    key = obj["Key"]
                    # Only include image files
                    if key.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
                        images.append(key)
        return images
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchBucket":
            raise ValueError(f"Bucket '{bucket_name}' does not exist")
        raise


def copy_image_in_s3(
    s3_client, 
    bucket_name: str, 
    source_key: str, 
    dest_key: str,
    dry_run: bool = False
) -> bool:
    """Copy an image from source_key to dest_key in S3."""
    if dry_run:
        print(f"  [DRY RUN] Would copy: s3://{bucket_name}/{source_key} -> s3://{bucket_name}/{dest_key}")
        return True
    
    try:
        # Use copy_object to copy within the same bucket
        copy_source = {"Bucket": bucket_name, "Key": source_key}
        s3_client.copy_object(
            CopySource=copy_source,
            Bucket=bucket_name,
            Key=dest_key,
        )
        print(f"  ✅ Copied: {source_key} -> {dest_key}")
        return True
    except ClientError as e:
        print(f"  ❌ Failed to copy {source_key}: {e}")
        return False


def delete_image_from_s3(
    s3_client,
    bucket_name: str,
    key: str,
    dry_run: bool = False
) -> bool:
    """Delete an image from S3."""
    if dry_run:
        print(f"  [DRY RUN] Would delete: s3://{bucket_name}/{key}")
        return True
    
    try:
        s3_client.delete_object(Bucket=bucket_name, Key=key)
        print(f"  ✅ Deleted: {key}")
        return True
    except ClientError as e:
        print(f"  ❌ Failed to delete {key}: {e}")
        return False


def update_xml_urls(
    xml_dir: Path,
    bucket_name: str,
    aws_region: str,
    test_name: str,
    dry_run: bool = False
) -> Dict[str, any]:
    """Update S3 image URLs in XML files to use the new test folder structure."""
    
    print(f"📝 Updating URLs in XML files...")
    print(f"   XML directory: {xml_dir}")
    print(f"   Pattern: images/{{filename}} -> images/{test_name}/{{filename}}")
    print()
    
    if not xml_dir.exists():
        print(f"⚠️  XML directory does not exist: {xml_dir}")
        return {
            "success": True,
            "updated": 0,
            "failed": 0,
            "files": []
        }
    
    # Find all XML files
    xml_files = list(xml_dir.glob("*.xml"))
    if not xml_files:
        print(f"   ℹ️  No XML files found in {xml_dir}")
        return {
            "success": True,
            "updated": 0,
            "failed": 0,
            "files": []
        }
    
    print(f"   Found {len(xml_files)} XML file(s)")
    print()
    
    # Pattern to match S3 URLs with images/ path
    # Matches: https://bucket.s3.region.amazonaws.com/images/filename.ext
    url_pattern = re.compile(
        rf'https://{re.escape(bucket_name)}\.s3\.{re.escape(aws_region)}\.amazonaws\.com/images/([^/"]+\.(?:png|jpg|jpeg|gif|svg))',
        re.IGNORECASE
    )
    
    results = {
        "updated": 0,
        "failed": 0,
        "files": []
    }
    
    for xml_file in sorted(xml_files):
        try:
            # Read XML file
            with open(xml_file, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            original_content = xml_content
            
            # Replace URLs
            def replace_url(match):
                filename = match.group(1)
                new_url = f'https://{bucket_name}.s3.{aws_region}.amazonaws.com/images/{test_name}/{filename}'
                return new_url
            
            xml_content = url_pattern.sub(replace_url, xml_content)
            
            # Check if any replacements were made
            if xml_content != original_content:
                replacements_count = len(url_pattern.findall(original_content))
                
                if not dry_run:
                    # Write updated XML
                    with open(xml_file, 'w', encoding='utf-8') as f:
                        f.write(xml_content)
                    print(f"✅ Updated {xml_file.name} ({replacements_count} URL(s))")
                else:
                    print(f"  [DRY RUN] Would update {xml_file.name} ({replacements_count} URL(s))")
                
                results["updated"] += 1
                results["files"].append({
                    "file": str(xml_file),
                    "replacements": replacements_count,
                    "status": "updated" if not dry_run else "would_update"
                })
            else:
                print(f"   ℹ️  No URLs to update in {xml_file.name}")
                results["files"].append({
                    "file": str(xml_file),
                    "replacements": 0,
                    "status": "no_change"
                })
                
        except Exception as e:
            print(f"❌ Failed to update {xml_file.name}: {e}")
            results["failed"] += 1
            results["files"].append({
                "file": str(xml_file),
                "status": "failed",
                "error": str(e)
            })
    
    print()
    print("=" * 60)
    print("XML UPDATE SUMMARY")
    print("=" * 60)
    print(f"Updated: {results['updated']}")
    print(f"Failed: {results['failed']}")
    
    results["success"] = results["failed"] == 0
    return results


def migrate_images_to_test_folder(
    bucket_name: str,
    test_name: str,
    dry_run: bool = False,
    delete_originals: bool = False
) -> Dict[str, any]:
    """Migrate images from images/ to images/{test_name}/."""
    
    print(f"📦 Migrating images to test folder: images/{test_name}/")
    print(f"   Bucket: {bucket_name}")
    print(f"   Dry run: {dry_run}")
    print()
    
    s3_client, aws_region = get_s3_client()
    
    # List all images in images/ (but not in subfolders)
    print(f"🔍 Listing images in images/...")
    all_images = list_images_in_prefix(s3_client, bucket_name, "images/")
    
    # Filter to only images directly in images/ (not in subfolders)
    root_images = [
        img for img in all_images 
        if img.startswith("images/") and img.count("/") == 1
    ]
    
    if not root_images:
        print("   ℹ️  No images found in images/")
        return {
            "success": True,
            "migrated": 0,
            "skipped": 0,
            "failed": 0
        }
    
    print(f"   Found {len(root_images)} image(s) in images/")
    print()
    
    # Migrate each image
    results = {
        "migrated": 0,
        "skipped": 0,
        "failed": 0,
        "operations": []
    }
    
    new_prefix = f"images/{test_name}/"
    
    for source_key in sorted(root_images):
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
            continue
        except ClientError as e:
            if e.response["Error"]["Code"] != "404":
                print(f"❌ Error checking {dest_key}: {e}")
                results["failed"] += 1
                continue
            # 404 means doesn't exist, which is good - we can proceed
        
        # Copy the image
        print(f"📋 Processing: {filename}")
        if copy_image_in_s3(s3_client, bucket_name, source_key, dest_key, dry_run):
            results["migrated"] += 1
            results["operations"].append({
                "source": source_key,
                "dest": dest_key,
                "status": "copied"
            })
            
            # Optionally delete original
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
    
    results["success"] = results["failed"] == 0
    return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate S3 images to organize them by test name and update XML URLs"
    )
    parser.add_argument(
        "--test-name",
        required=True,
        help="Test/prueba name (e.g., 'prueba-invierno-2026')"
    )
    parser.add_argument(
        "--bucket",
        default=None,
        help="S3 bucket name (uses AWS_S3_BUCKET from env if not provided)"
    )
    parser.add_argument(
        "--xml-dir",
        default=None,
        help="Directory containing QTI XML files to update (e.g., '../app/data/pruebas/procesadas/prueba-invierno-2026/qti')"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Perform a dry run without making changes (default: True)"
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Actually perform the migration (disables dry-run)"
    )
    parser.add_argument(
        "--delete-originals",
        action="store_true",
        help="Delete original images after copying (USE WITH CAUTION)"
    )
    parser.add_argument(
        "--skip-xml-update",
        action="store_true",
        help="Skip XML URL updates (only migrate images)"
    )
    
    args = parser.parse_args()
    
    # Get bucket name
    bucket_name = args.bucket or os.environ.get("AWS_S3_BUCKET", "paes-question-images")
    
    # Dry run logic
    dry_run = args.dry_run and not args.no_dry_run
    
    print("=" * 60)
    print("S3 Image Migration Tool")
    print("=" * 60)
    print()
    
    try:
        # Ensure .env is loaded (in case it wasn't loaded at module level)
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent.parent.parent.parent
        env_file = project_root / ".env"
        if env_file.exists():
            load_dotenv(env_file, override=True)
        
        # Get AWS region for XML URL updates (need to get client to determine region)
        # Only get credentials if not dry-run or if we need to migrate images
        aws_region = os.environ.get("AWS_REGION", "us-east-1")
        if not dry_run or not args.skip_xml_update:
            try:
                _, aws_region_from_client = get_s3_client()
                aws_region = aws_region_from_client
            except ValueError:
                # If credentials not available and dry-run, use default region
                if dry_run:
                    print("⚠️  AWS credentials not found, using default region for URL patterns")
                else:
                    raise
        
        # Step 1: Migrate images in S3 (only if not skipping)
        image_results = None
        if not args.skip_xml_update or not dry_run:
            try:
                print("STEP 1: Migrating images in S3")
                print("=" * 60)
                image_results = migrate_images_to_test_folder(
                    bucket_name=bucket_name,
                    test_name=args.test_name,
                    dry_run=dry_run,
                    delete_originals=args.delete_originals
                )
            except ValueError as e:
                if dry_run:
                    print(f"⚠️  {e}")
                    print("   Continuing with XML updates only (dry-run mode)")
                    image_results = {"success": True, "migrated": 0, "skipped": 0, "failed": 0}
                else:
                    raise
        
        # Step 2: Update XML URLs if directory provided
        xml_results = None
        if not args.skip_xml_update:
            print()
            print()
            print("STEP 2: Updating URLs in XML files")
            print("=" * 60)
            
            if args.xml_dir:
                xml_dir = Path(args.xml_dir)
            else:
                # Try to infer from test_name
                script_dir = Path(__file__).parent
                project_root = script_dir.parent.parent
                xml_dir = project_root / "app" / "data" / "pruebas" / "procesadas" / args.test_name / "qti"
                print(f"   Using inferred XML directory: {xml_dir}")
            
            xml_results = update_xml_urls(
                xml_dir=xml_dir,
                bucket_name=bucket_name,
                aws_region=aws_region,
                test_name=args.test_name,
                dry_run=dry_run
            )
        else:
            print()
            print("⏭️  Skipping XML URL updates (--skip-xml-update)")
        
        # Final summary
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
        
        overall_success = (image_results is None or image_results["success"]) and (xml_results is None or xml_results["success"])
        
        if overall_success:
            print()
            print("✅ Migration completed successfully!")
            if dry_run:
                print("   Run with --no-dry-run to actually perform the migration.")
        else:
            print()
            print("❌ Migration completed with errors")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
