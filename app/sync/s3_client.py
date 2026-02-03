"""S3 client for uploading question images.

Handles uploading images referenced in QTI XML to S3 and updating the XML
with the new S3 URLs.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

# Default S3 bucket for question images (shared across environments)
DEFAULT_S3_BUCKET = "paes-question-images"
DEFAULT_S3_REGION = "us-east-1"


@dataclass
class S3Config:
    """S3 configuration for image uploads."""

    bucket: str
    region: str
    access_key_id: str
    secret_access_key: str
    endpoint_url: str | None = None  # For S3-compatible services like R2
    public_url_base: str | None = None  # Custom CDN/public URL base

    @classmethod
    def from_env(cls) -> "S3Config":
        """Create config from environment variables.

        Uses the default bucket (paes-question-images) unless S3_BUCKET is set.

        Expected variables:
            AWS_S3_KEY: Access key (required)
            AWS_S3_SECRET: Secret key (required)
            S3_BUCKET: (optional) Override default bucket
            S3_REGION: (optional) Override default region (us-east-1)
            S3_ENDPOINT_URL: (optional) For S3-compatible services
            S3_PUBLIC_URL_BASE: (optional) Custom CDN URL base
        """
        # Support both naming conventions for AWS credentials
        access_key = os.getenv("AWS_S3_KEY") or os.getenv("AWS_ACCESS_KEY_ID", "")
        secret_key = os.getenv("AWS_S3_SECRET") or os.getenv("AWS_SECRET_ACCESS_KEY", "")

        if not access_key or not secret_key:
            msg = "AWS_S3_KEY and AWS_S3_SECRET environment variables are required for S3"
            raise ValueError(msg)

        return cls(
            bucket=os.getenv("S3_BUCKET", DEFAULT_S3_BUCKET),
            region=os.getenv("S3_REGION", DEFAULT_S3_REGION),
            access_key_id=access_key,
            secret_access_key=secret_key,
            endpoint_url=os.getenv("S3_ENDPOINT_URL"),
            public_url_base=os.getenv("S3_PUBLIC_URL_BASE"),
        )

    @classmethod
    def is_configured(cls) -> bool:
        """Check if S3 credentials are configured (keys present)."""
        access_key = os.getenv("AWS_S3_KEY") or os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_S3_SECRET") or os.getenv("AWS_SECRET_ACCESS_KEY")
        return bool(access_key and secret_key)


# -----------------------------------------------------------------------------
# S3 Operations
# -----------------------------------------------------------------------------


class ImageUploader:
    """Handles uploading images to S3 and tracking uploaded files."""

    def __init__(self, config: S3Config):
        """Initialize the uploader with S3 configuration.

        Args:
            config: S3 configuration
        """
        self.config = config
        self._client: S3Client | None = None
        self._uploaded_cache: dict[str, str] = {}  # content_hash -> s3_url

    @property
    def client(self) -> "S3Client":
        """Lazy-load boto3 S3 client."""
        if self._client is None:
            import boto3

            client_kwargs = {
                "service_name": "s3",
                "region_name": self.config.region,
                "aws_access_key_id": self.config.access_key_id,
                "aws_secret_access_key": self.config.secret_access_key,
            }
            if self.config.endpoint_url:
                client_kwargs["endpoint_url"] = self.config.endpoint_url

            self._client = boto3.client(**client_kwargs)

        return self._client

    def _get_content_hash(self, content: bytes) -> str:
        """Generate a hash for file content to detect duplicates."""
        return hashlib.sha256(content).hexdigest()[:16]

    def _get_s3_key(self, original_path: str, content_hash: str) -> str:
        """Generate S3 key for an image.

        Format: questions/images/{content_hash}_{filename}
        """
        filename = Path(original_path).name
        return f"questions/images/{content_hash}_{filename}"

    def _get_public_url(self, s3_key: str) -> str:
        """Get the public URL for an uploaded file."""
        if self.config.public_url_base:
            return f"{self.config.public_url_base.rstrip('/')}/{s3_key}"

        if self.config.endpoint_url:
            # For S3-compatible services
            return f"{self.config.endpoint_url.rstrip('/')}/{self.config.bucket}/{s3_key}"

        # Standard AWS S3 URL
        return f"https://{self.config.bucket}.s3.{self.config.region}.amazonaws.com/{s3_key}"

    def check_exists(self, s3_key: str) -> bool:
        """Check if a file already exists in S3.

        Args:
            s3_key: The S3 object key

        Returns:
            True if file exists, False otherwise
        """
        try:
            self.client.head_object(Bucket=self.config.bucket, Key=s3_key)
            return True
        except self.client.exceptions.ClientError:
            return False

    def upload_file(
        self,
        local_path: Path,
        content_type: str | None = None,
    ) -> str:
        """Upload a file to S3 and return its public URL.

        Uses content hashing to avoid duplicate uploads.

        Args:
            local_path: Path to the local file
            content_type: MIME type (auto-detected if not provided)

        Returns:
            Public URL of the uploaded file
        """
        # Read file content
        with open(local_path, "rb") as f:
            content = f.read()

        content_hash = self._get_content_hash(content)

        # Check cache first
        if content_hash in self._uploaded_cache:
            return self._uploaded_cache[content_hash]

        s3_key = self._get_s3_key(str(local_path), content_hash)

        # Check if already in S3
        if self.check_exists(s3_key):
            url = self._get_public_url(s3_key)
            self._uploaded_cache[content_hash] = url
            return url

        # Auto-detect content type
        if content_type is None:
            suffix = local_path.suffix.lower()
            content_type = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".gif": "image/gif",
                ".webp": "image/webp",
                ".svg": "image/svg+xml",
            }.get(suffix, "application/octet-stream")

        # Upload to S3
        self.client.put_object(
            Bucket=self.config.bucket,
            Key=s3_key,
            Body=content,
            ContentType=content_type,
        )

        url = self._get_public_url(s3_key)
        self._uploaded_cache[content_hash] = url
        return url


# -----------------------------------------------------------------------------
# QTI Image Processing
# -----------------------------------------------------------------------------


def process_qti_images(
    qti_xml: str,
    base_dir: Path,
    uploader: ImageUploader,
) -> tuple[str, list[str]]:
    """Process a QTI XML string, uploading any local images to S3.

    Args:
        qti_xml: The QTI XML content
        base_dir: Base directory for resolving relative image paths
        uploader: ImageUploader instance

    Returns:
        Tuple of (updated QTI XML with S3 URLs, list of uploaded URLs)
    """
    uploaded_urls: list[str] = []

    # Find all image references
    img_pattern = re.compile(r'(<img[^>]+src=["\'])([^"\']+)(["\'][^>]*>)', re.IGNORECASE)

    def replace_image(match: re.Match) -> str:
        prefix, src, suffix = match.groups()

        # Skip if already an S3/HTTP URL
        if src.startswith(("http://", "https://", "s3://")):
            return match.group(0)

        # Resolve local path
        if src.startswith("/"):
            local_path = Path(src)
        else:
            local_path = base_dir / src

        if not local_path.exists():
            # Try common locations
            for alt_dir in [base_dir, base_dir.parent, base_dir / "images"]:
                alt_path = alt_dir / Path(src).name
                if alt_path.exists():
                    local_path = alt_path
                    break

        if not local_path.exists():
            # Image not found, keep original reference
            return match.group(0)

        # Upload and get URL
        s3_url = uploader.upload_file(local_path)
        uploaded_urls.append(s3_url)

        return f"{prefix}{s3_url}{suffix}"

    updated_xml = img_pattern.sub(replace_image, qti_xml)

    return updated_xml, uploaded_urls


def process_all_questions_images(
    questions: list,  # list of ExtractedQuestion
    pruebas_dir: Path,
    uploader: ImageUploader,
) -> dict[str, str]:
    """Process images for all questions, returning updated QTI XML.

    Args:
        questions: List of ExtractedQuestion objects
        pruebas_dir: Base directory for pruebas/finalizadas
        uploader: ImageUploader instance

    Returns:
        Dict mapping question_id -> updated qti_xml
    """
    updated_qti: dict[str, str] = {}

    for q in questions:
        # Determine base directory for this question
        # Format: {test_id}/qti/Q{num}/
        test_dir = pruebas_dir / q.test_id / "qti" / f"Q{q.question_number}"

        if test_dir.exists():
            updated_xml, _ = process_qti_images(q.qti_xml, test_dir, uploader)
            updated_qti[q.id] = updated_xml
        else:
            updated_qti[q.id] = q.qti_xml

    return updated_qti
