"""
QTI Response Parsers

This module handles parsing of LLM responses for QTI transformation and correction.
"""

from __future__ import annotations

import json
from typing import Any

from .qti_encoding import verify_and_fix_encoding


def parse_transformation_response(response_text: str) -> dict[str, Any]:
    """
    Parse the transformation response from the LLM.

    Args:
        response_text: Raw response text

    Returns:
        Parsed transformation result with keys:
        - success: bool
        - title: str (if success)
        - description: str (if success)
        - qti_xml: str (if success)
        - key_features: list (if success)
        - notes: str (if success)
        - error: str (if not success)
    """
    try:
        # Check for None or empty response
        if response_text is None:
            raise ValueError("Response text is None")

        if not response_text.strip():
            raise ValueError("Response text is empty")

        # Try to extract JSON from the response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1

        if json_start >= 0 and json_end > json_start:
            json_text = response_text[json_start:json_end]
            # Ensure UTF-8 encoding is preserved when parsing JSON
            result = json.loads(json_text)

            # Validate required fields
            if not isinstance(result, dict):
                raise ValueError("Response is not a dictionary")

            title = result.get('title', 'Untitled Question')
            description = result.get('description', '')
            qti_xml = result.get('qti_xml', '')

            # Ensure QTI XML is properly decoded as UTF-8
            if isinstance(qti_xml, bytes):
                qti_xml = qti_xml.decode('utf-8')

            if not qti_xml:
                raise ValueError("No QTI XML found in response")

            # Verify and fix encoding issues (tildes, ñ, etc.)
            qti_xml, _encoding_fixed = verify_and_fix_encoding(qti_xml)

            return {
                "success": True,
                "title": title,
                "description": description,
                "qti_xml": qti_xml,
                "key_features": result.get('key_features', []),
                "notes": result.get('notes', '')
            }
        else:
            raise ValueError("No JSON found in response")

    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Failed to parse JSON response: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error parsing transformation response: {str(e)}"
        }


def parse_correction_response(response_text: str) -> dict[str, Any]:
    """
    Parse the correction response from the LLM.

    Args:
        response_text: Raw response text

    Returns:
        Parsed correction result with keys:
        - success: bool
        - qti_xml: str (if success)
        - fixes_applied: list (if success)
        - notes: str (if success)
        - error: str (if not success)
    """
    try:
        # Try to extract JSON from the response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1

        if json_start >= 0 and json_end > json_start:
            json_text = response_text[json_start:json_end]
            result = json.loads(json_text)

            # Validate required fields
            if not isinstance(result, dict):
                raise ValueError("Response is not a dictionary")

            qti_xml = result.get('qti_xml', '')

            # Ensure QTI XML is properly decoded as UTF-8
            if isinstance(qti_xml, bytes):
                qti_xml = qti_xml.decode('utf-8')

            if not qti_xml:
                raise ValueError("No corrected QTI XML found in response")

            # Verify and fix encoding issues (tildes, ñ, etc.)
            qti_xml, _encoding_fixed = verify_and_fix_encoding(qti_xml)

            return {
                "success": True,
                "qti_xml": qti_xml,
                "fixes_applied": result.get('fixes_applied', []),
                "notes": result.get('notes', '')
            }
        else:
            raise ValueError("No JSON found in response")

    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Failed to parse JSON response: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error parsing correction response: {str(e)}"
        }
