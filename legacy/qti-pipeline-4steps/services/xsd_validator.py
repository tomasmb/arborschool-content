"""XSD Validator - Validates QTI XML using external validation service."""

from __future__ import annotations

import time
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_VALIDATION_ENDPOINT = (
    "http://qti-validator-prod.eba-dvye2j6j.us-east-2.elasticbeanstalk.com/validate"
)


class XSDValidator:
    """Validates QTI XML using external validation service."""

    def __init__(self, xsd_path: str = None):
        """Initialize the validator."""
        self.validation_endpoint = DEFAULT_VALIDATION_ENDPOINT
        self.max_retries = 3
        self.retry_delay = 2

    def validate(self, xml_string: str) -> tuple[bool, str]:
        """
        Validate XML string using external validation service.

        Returns:
            Tuple of (is_valid, error_message)
        """
        result = self._validate_with_service(xml_string)

        if result.get("success") and result.get("valid"):
            return True, ""
        else:
            error_msg = result.get(
                "validation_errors",
                result.get("error", "Unknown validation error")
            )
            return False, error_msg

    def _validate_with_service(self, qti_xml: str) -> dict[str, Any]:
        """Validate QTI XML against the XSD schema using external service."""
        for attempt in range(self.max_retries):
            try:
                stripped_xml = qti_xml.strip()
                if stripped_xml.startswith('<?xml'):
                    stripped_xml = stripped_xml.split('?>', 1)[1].strip()

                validation_url = f"{self.validation_endpoint}?schema=qti3"
                response_data, status_code = self._request_local(validation_url, stripped_xml)

                if status_code == 200:
                    result = json.loads(response_data)
                    is_valid = result.get('valid', False)

                    if is_valid:
                        return {
                            "success": True,
                            "valid": True,
                            "message": "QTI XML is valid",
                            "warnings": result.get('warnings', [])
                        }
                    else:
                        return self._format_validation_errors(result)

                elif status_code == 422:
                    logger.warning(f"Validation returned 422: {response_data[:500]}")
                    return self._handle_error_response(response_data, status_code)

                return self._handle_error_response(response_data, status_code)

            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": "Invalid JSON response from validation service"
                }
            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.warning(
                        f"Validation error (attempt {attempt + 1}): {e}. Retrying..."
                    )
                    time.sleep(self.retry_delay)
                    continue
                return {
                    "success": False,
                    "error": f"Validation failed after retries: {str(e)}"
                }

        return {
            "success": False,
            "error": "Validation failed after all retry attempts."
        }

    def _request_local(self, url: str, xml_data: str) -> tuple[str, int]:
        """Make HTTP request using requests library."""
        import requests

        response = requests.post(
            url,
            data=xml_data,
            headers={'Content-Type': 'application/xml'},
            timeout=30
        )
        return response.text, response.status_code

    def _format_validation_errors(self, result: dict[str, Any]) -> dict[str, Any]:
        """Format validation errors from the service response."""
        errors = result.get('errors', [])
        error_messages = []

        if isinstance(errors, list):
            for error in errors:
                if isinstance(error, dict):
                    message = error.get('message', str(error))
                    line = error.get('line')
                    column = error.get('column')

                    if line is not None and column is not None:
                        error_messages.append(f"Line {line}, Column {column}: {message}")
                    else:
                        error_messages.append(message)
                else:
                    error_messages.append(str(error))

        validation_errors = (
            "\n".join(error_messages) if error_messages
            else "Unknown validation error"
        )

        return {
            "success": False,
            "valid": False,
            "validation_errors": validation_errors,
            "errors": errors,
            "warnings": result.get('warnings', [])
        }

    def _handle_error_response(self, response_data: str, status_code: int) -> dict[str, Any]:
        """Handle non-200 response from validation service."""
        try:
            error_data = json.loads(response_data)
            return self._format_validation_errors(error_data)
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": f"Validation service returned status {status_code}"
            }

