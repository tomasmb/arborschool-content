"""Shared helper functions for the standards pipeline."""

from __future__ import annotations

import json
import re
from typing import Any


def _fix_invalid_escapes(text: str) -> str:
    """
    Fix invalid escape sequences in JSON strings.
    
    JSON only allows specific escape sequences. This function attempts to
    fix common invalid escapes by either escaping the backslash or removing
    the invalid escape sequence.
    
    Args:
        text: JSON string that may contain invalid escapes
        
    Returns:
        Text with fixed escape sequences
    """
    # Pattern to find invalid escape sequences (backslash not followed by
    # a valid escape character)
    # Valid escapes in JSON: \", \\, \/, \b, \f, \n, \r, \t, \uXXXX
    # We'll be conservative and only fix obvious cases
    
    # First, protect already valid escapes
    # Replace valid escapes with placeholders temporarily
    valid_escapes = {
        r'\\"': '__ESCAPE_DOUBLE_QUOTE__',
        r'\\\\': '__ESCAPE_BACKSLASH__',
        r'\\/': '__ESCAPE_SLASH__',
        r'\\b': '__ESCAPE_BACKSPACE__',
        r'\\f': '__ESCAPE_FORMFEED__',
        r'\\n': '__ESCAPE_NEWLINE__',
        r'\\r': '__ESCAPE_CARRIAGE__',
        r'\\t': '__ESCAPE_TAB__',
    }
    
    # Protect valid escapes
    protected = text
    for pattern, placeholder in valid_escapes.items():
        protected = protected.replace(pattern, placeholder)
    
    # Fix invalid escapes: \ followed by non-escape character
    # Replace \X (where X is not a valid escape) with \\X
    # But be careful not to break \uXXXX sequences
    fixed = re.sub(
        r'\\(?![u"\\/bfnrt])',  # \ not followed by valid escape char
        r'\\\\',  # Escape the backslash
        protected,
    )
    
    # Restore valid escapes
    for pattern, placeholder in valid_escapes.items():
        fixed = fixed.replace(placeholder, pattern)
    
    return fixed


def parse_json_response(response: str) -> dict[str, Any] | list[Any]:
    """
    Parse JSON from Gemini response, handling markdown wrappers and extra text.

    Gemini sometimes wraps JSON in markdown code blocks even when
    response_mime_type is set, or adds extra text after the JSON.
    This function handles that gracefully, including fixing invalid escape sequences.

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
    except json.JSONDecodeError as e:
        # If error mentions invalid escape, try fixing it
        if "Invalid \\escape" in str(e) or "Invalid escape" in str(e):
            try:
                fixed = _fix_invalid_escapes(cleaned)
                return json.loads(fixed)
            except json.JSONDecodeError:
                # If fixing didn't work, continue with original error handling
                pass
        
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
                    except json.JSONDecodeError as inner_e:
                        # Try fixing escapes in this substring
                        if "Invalid \\escape" in str(inner_e) or "Invalid escape" in str(inner_e):
                            try:
                                fixed = _fix_invalid_escapes(json_str)
                                return json.loads(fixed)
                            except json.JSONDecodeError:
                                pass
                        # Continue searching
                        start_idx = -1
                        depth = 0

        # If we couldn't find valid JSON, raise the original error
        raise

