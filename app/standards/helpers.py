"""Shared helper functions for the standards pipeline."""

from __future__ import annotations

import json
from typing import Any


def parse_json_response(response: str) -> dict[str, Any]:
    """
    Parse JSON from Gemini response, handling markdown wrappers.

    Gemini sometimes wraps JSON in markdown code blocks even when
    response_mime_type is set. This function handles that gracefully.

    Args:
        response: Raw response string from Gemini.

    Returns:
        Parsed JSON as dict.

    Raises:
        json.JSONDecodeError: If parsing fails after cleanup.
    """
    cleaned = response.strip()

    # Remove markdown code block wrappers if present
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    return json.loads(cleaned.strip())

