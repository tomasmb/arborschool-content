"""
S3 Migration Utilities

Reusable functions for S3 operations during image migration.
Includes client initialization, listing, copying, and deleting images.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

try:
    import boto3
    from botocore.exceptions import ClientError

    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    boto3 = None  # type: ignore
    ClientError = Exception  # type: ignore


def get_s3_client() -> tuple[Any, str]:
    """
    Get S3 client with credentials from environment.

    Returns:
        Tuple of (s3_client, aws_region)

    Raises:
        ValueError: If AWS credentials not found
    """
    aws_access_key = os.environ.get("AWS_S3_KEY") or os.environ.get("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.environ.get("AWS_S3_SECRET") or os.environ.get("AWS_SECRET_ACCESS_KEY")
    aws_region = os.environ.get("AWS_REGION", "us-east-1")

    if not aws_access_key or not aws_secret_key:
        raise ValueError("AWS credentials not found. Set AWS_S3_KEY and AWS_S3_SECRET (or AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY)")

    session = boto3.Session(
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=aws_region,
    )
    return session.client("s3"), aws_region


def list_images_in_prefix(s3_client: Any, bucket_name: str, prefix: str) -> list[str]:
    """
    List all image keys in S3 with the given prefix.

    Args:
        s3_client: Boto3 S3 client
        bucket_name: Name of the S3 bucket
        prefix: S3 key prefix to list

    Returns:
        List of image keys matching the prefix
    """
    images = []
    paginator = s3_client.get_paginator("list_objects_v2")

    try:
        for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
            if "Contents" in page:
                for obj in page["Contents"]:
                    key = obj["Key"]
                    if key.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
                        images.append(key)
        return images
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchBucket":
            raise ValueError(f"Bucket '{bucket_name}' does not exist")
        raise


def copy_image_in_s3(s3_client: Any, bucket_name: str, source_key: str, dest_key: str, dry_run: bool = False) -> bool:
    """
    Copy an image from source_key to dest_key in S3.

    Args:
        s3_client: Boto3 S3 client
        bucket_name: Name of the S3 bucket
        source_key: Source object key
        dest_key: Destination object key
        dry_run: If True, only print what would happen

    Returns:
        True if successful, False otherwise
    """
    if dry_run:
        print(f"  [DRY RUN] Would copy: s3://{bucket_name}/{source_key} -> s3://{bucket_name}/{dest_key}")
        return True

    try:
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


def delete_image_from_s3(s3_client: Any, bucket_name: str, key: str, dry_run: bool = False) -> bool:
    """
    Delete an image from S3.

    Args:
        s3_client: Boto3 S3 client
        bucket_name: Name of the S3 bucket
        key: Object key to delete
        dry_run: If True, only print what would happen

    Returns:
        True if successful, False otherwise
    """
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


def update_xml_urls(xml_dir: Path, bucket_name: str, aws_region: str, test_name: str, dry_run: bool = False) -> dict[str, Any]:
    """
    Update S3 image URLs in XML files to use the new test folder structure.

    Args:
        xml_dir: Directory containing XML files
        bucket_name: S3 bucket name
        aws_region: AWS region
        test_name: Test name for the new folder structure
        dry_run: If True, only print what would happen

    Returns:
        Results dictionary with updated/failed counts
    """
    print("📝 Updating URLs in XML files...")
    print(f"   XML directory: {xml_dir}")
    print(f"   Pattern: images/{{filename}} -> images/{test_name}/{{filename}}")
    print()

    if not xml_dir.exists():
        print(f"⚠️  XML directory does not exist: {xml_dir}")
        return {"success": True, "updated": 0, "failed": 0, "files": []}

    xml_files = list(xml_dir.glob("*.xml"))
    if not xml_files:
        print(f"   ℹ️  No XML files found in {xml_dir}")
        return {"success": True, "updated": 0, "failed": 0, "files": []}

    print(f"   Found {len(xml_files)} XML file(s)")
    print()

    url_pattern = re.compile(
        rf"https://{re.escape(bucket_name)}\.s3\.{re.escape(aws_region)}\.amazonaws\.com"
        rf'/images/([^/"]+\.(?:png|jpg|jpeg|gif|svg))',
        re.IGNORECASE,
    )

    results: dict[str, Any] = {"updated": 0, "failed": 0, "files": []}

    for xml_file in sorted(xml_files):
        _process_xml_file(xml_file, url_pattern, bucket_name, aws_region, test_name, dry_run, results)

    _print_xml_summary(results)
    results["success"] = results["failed"] == 0
    return results


def _process_xml_file(
    xml_file: Path, url_pattern: re.Pattern, bucket_name: str, aws_region: str, test_name: str, dry_run: bool, results: dict[str, Any]
) -> None:
    """Process a single XML file for URL updates."""
    try:
        with open(xml_file, "r", encoding="utf-8") as f:
            xml_content = f.read()

        original_content = xml_content

        def replace_url(match: re.Match) -> str:
            filename = match.group(1)
            # Lowercase test_name for consistency with folder structure
            return f"https://{bucket_name}.s3.{aws_region}.amazonaws.com/images/{test_name.lower()}/{filename}"

        xml_content = url_pattern.sub(replace_url, xml_content)

        if xml_content != original_content:
            replacements_count = len(url_pattern.findall(original_content))

            if not dry_run:
                with open(xml_file, "w", encoding="utf-8") as f:
                    f.write(xml_content)
                print(f"✅ Updated {xml_file.name} ({replacements_count} URL(s))")
            else:
                print(f"  [DRY RUN] Would update {xml_file.name} ({replacements_count} URL(s))")

            results["updated"] += 1
            results["files"].append(
                {"file": str(xml_file), "replacements": replacements_count, "status": "updated" if not dry_run else "would_update"}
            )
        else:
            print(f"   ℹ️  No URLs to update in {xml_file.name}")
            results["files"].append({"file": str(xml_file), "replacements": 0, "status": "no_change"})

    except Exception as e:
        print(f"❌ Failed to update {xml_file.name}: {e}")
        results["failed"] += 1
        results["files"].append({"file": str(xml_file), "status": "failed", "error": str(e)})


def _print_xml_summary(results: dict[str, Any]) -> None:
    """Print XML update summary."""
    print()
    print("=" * 60)
    print("XML UPDATE SUMMARY")
    print("=" * 60)
    print(f"Updated: {results['updated']}")
    print(f"Failed: {results['failed']}")
