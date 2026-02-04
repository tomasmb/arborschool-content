"""
OpenAI API retry utilities.

Provides retry logic with exponential backoff for OpenAI API calls,
handling image download timeouts common with vision models.
"""

import json
import time
from typing import Any

from openai import BadRequestError, OpenAI


def call_with_retry(
    client: OpenAI,
    prompt: str,
    schema: dict[str, Any],
    schema_name: str,
    image_urls: list[str] | None = None,
    model: str = "gpt-4o",
    max_retries: int = 3,
    default_on_error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Call OpenAI API with retry logic for image download errors.

    Args:
        client: OpenAI client instance
        prompt: The text prompt to send
        schema: JSON schema for structured output
        schema_name: Name for the schema
        image_urls: Optional list of image URLs to include
        model: Model to use (default: gpt-4o)
        max_retries: Maximum retry attempts (default: 3)
        default_on_error: Default value to return on error (default: empty dict)

    Returns:
        Parsed JSON response dict, or default_on_error if all retries fail
    """
    if default_on_error is None:
        default_on_error = {}

    for attempt in range(max_retries):
        try:
            # Build messages with prompt and optional images
            content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]

            if image_urls:
                for img_url in image_urls:
                    content.append({"type": "image_url", "image_url": {"url": img_url}})

            # Call OpenAI chat completions API with structured output
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": content}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema_name,
                        "schema": schema,
                        "strict": True,
                    },
                },
            )

            # Parse response
            if response.choices and response.choices[0].message.content:
                return json.loads(response.choices[0].message.content)

            return default_on_error

        except BadRequestError as e:
            error_message = str(e)
            is_image_download_error = (
                "downloading" in error_message.lower()
                and "image" in error_message.lower()
                or ".png" in error_message
                or ".jpg" in error_message
            )

            if is_image_download_error and attempt < max_retries - 1:
                wait_time = 2**attempt
                print(f"Image download timeout (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue

            print(f"OpenAI API error: {e}")
            return default_on_error

        except Exception as e:
            print(f"OpenAI API error: {e}")
            return default_on_error

    return default_on_error
