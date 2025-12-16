import base64
import hashlib
import json
import os
import re
from typing import Any

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

from app.io import EXEMPLAR_PATH


load_dotenv()

S3_BUCKET = "ai-first-incept-media"
S3_REGION = "us-east-1"


class ImageMigrator:
    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
            region_name=S3_REGION,
        )
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        try:
            self.s3_client.head_bucket(Bucket=S3_BUCKET)
            print(f"S3 bucket '{S3_BUCKET}' exists")
        except ClientError:
            try:
                if S3_REGION == "us-east-1":
                    self.s3_client.create_bucket(Bucket=S3_BUCKET)
                else:
                    self.s3_client.create_bucket(
                        Bucket=S3_BUCKET, CreateBucketConfiguration={"LocationConstraint": S3_REGION}
                    )
                print(f"Created S3 bucket '{S3_BUCKET}'")
            except Exception as e:
                print(f"Error creating S3 bucket: {e}")
                raise

    def migrate_base64_images(self, qti_xml: str, question_id: str) -> str:
        base64_pattern = r"data:image/([^;]+);base64,([A-Za-z0-9+/=]+)"
        matches = list(re.finditer(base64_pattern, qti_xml))

        if not matches:
            return qti_xml

        updated_xml = qti_xml
        for match in matches:
            image_format = match.group(1)
            base64_data = match.group(2)

            try:
                image_bytes = base64.b64decode(base64_data)
                image_hash = hashlib.md5(image_bytes).hexdigest()
                s3_key = f"questions/{question_id}/{image_hash}.{image_format}"

                self.s3_client.put_object(
                    Bucket=S3_BUCKET,
                    Key=s3_key,
                    Body=image_bytes,
                    ContentType=f"image/{image_format}",
                    ACL="public-read",
                )

                s3_url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{s3_key}"
                updated_xml = updated_xml.replace(match.group(0), s3_url)
                print(f"  Migrated image: {s3_key}")

            except Exception as e:
                print(f"  Error migrating image: {e}")
                continue

        return updated_xml

    def process_all_questions(self, data: dict[str, Any]) -> dict[str, Any]:
        total_images = 0
        for test in data["tests"]:
            for question in test["questions"]:
                question_id = question.get("id", "")
                qti_xml = question.get("qtiXml", "")

                matches = re.findall(r"data:image/([^;]+);base64,", qti_xml)
                if matches:
                    print(f"\nQuestion {question_id}: {len(matches)} image(s)")
                    updated_xml = self.migrate_base64_images(qti_xml, question_id)
                    question["qtiXml"] = updated_xml
                    total_images += len(matches)

        return data, total_images


def run() -> None:
    """Migrate base64 images in exemplar questions to S3."""
    input_file = EXEMPLAR_PATH

    with open(input_file, encoding="utf-8") as f:
        data = json.load(f)

    migrator = ImageMigrator()
    print(f"{'=' * 60}")
    print("MIGRATING BASE64 IMAGES TO S3")
    print(f"{'=' * 60}")

    updated_data, total = migrator.process_all_questions(data)

    with open(input_file, "w", encoding="utf-8") as f:
        json.dump(updated_data, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"Migrated {total} images total")
    print(f"Updated: {input_file}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    run()
