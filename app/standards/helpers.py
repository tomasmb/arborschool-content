"""Shared helper functions for the standards pipeline."""

from __future__ import annotations

import json
from typing import Any


def parse_json_response(response: str) -> dict[str, Any] | list[Any]:
    """
    Parse JSON from Gemini response, handling markdown wrappers and extra text.

    Gemini sometimes wraps JSON in markdown code blocks even when
    response_mime_type is set, or adds extra text after the JSON.
    This function handles that gracefully.

    Args:
        response: Raw response string from Gemini.

    Returns:
        Parsed JSON as dict or list.

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

    cleaned = cleaned.strip()

    # Try to parse the full cleaned response first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # If that fails, try to find the first valid JSON object/array
        # by looking for the first '{' or '[' and finding its matching closing
        depth = 0
        start_idx = -1
        for i, char in enumerate(cleaned):
            if char in '{[':
                if start_idx == -1:
                    start_idx = i
                depth += 1
            elif char in '}]':
                depth -= 1
                if depth == 0 and start_idx != -1:
                    # Found complete JSON
                    json_str = cleaned[start_idx:i+1]
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        # Continue searching
                        start_idx = -1
                        depth = 0

        # If we couldn't find valid JSON, raise the original error
        raise

