"""
External Validation Service Client

Handles communication with the external Node.js QTI validation service,
including retry logic for transient errors.
"""

from __future__ import annotations

import os
import time
from typing import Any, Optional

import requests

# Default external validation service URL
DEFAULT_VALIDATION_URL = "https://klx2kb3qmf5wlb3dzqg436wysm0cwlat.lambda-url.us-east-1.on.aws/"


def validate_with_external_service(
    qti_xml: str,
    original_pdf_image: str,
    api_key: Optional[str],
    validation_service_url: Optional[str] = None,
    max_retries: int = 3,
    backoff_factor: int = 2,
) -> dict[str, Any]:
    """
    Validate QTI using external Node.js validation service with retry mechanism.

    Args:
        qti_xml: QTI XML content to validate
        original_pdf_image: Base64 encoded original PDF image
        api_key: API key (Gemini or OpenAI, uses env vars if None)
        validation_service_url: URL of external validation service (uses default if None)
        max_retries: Maximum number of retries for 5xx errors
        backoff_factor: Factor to determine sleep time between retries

    Returns:
        Dictionary with validation results including:
        - success: Whether validation completed
        - validation_passed: Whether QTI passed validation
        - overall_score: Validation score (0-1)
        - error: Error message if failed
        - And other validation details
    """
    if validation_service_url is None:
        validation_service_url = DEFAULT_VALIDATION_URL

    retries = 0
    sleep_time = 1  # Initial sleep time in seconds

    while retries < max_retries:
        try:
            print(f"🌐 Calling external validation service: {validation_service_url}")
            print(f"📄 QTI XML length: {len(qti_xml)} characters")
            print(f"🖼️  PDF image length: {len(original_pdf_image)} characters")

            # Get API key from env if not provided
            # External validation service requires OPENAI_API_KEY specifically
            service_api_key = api_key or os.environ.get("OPENAI_API_KEY")
            if not service_api_key:
                # Fallback to GEMINI_API_KEY only if OPENAI_API_KEY is not available
                service_api_key = os.environ.get("GEMINI_API_KEY")

            payload = {
                "qti_xml": qti_xml,
                "original_pdf_image": original_pdf_image,
                "openai_api_key": service_api_key,
            }

            print("📡 Sending validation request...")
            response = requests.post(
                validation_service_url,
                json=payload,
                timeout=120,  # Match Lambda timeout
            )

            print(f"📊 Response status: {response.status_code}")

            # Retry on 5xx server errors
            if response.status_code in [500, 502, 503, 504]:
                retries += 1
                if retries < max_retries:
                    print(f"❌ Received status {response.status_code}. Retrying in {sleep_time}s... ({retries}/{max_retries})")
                    time.sleep(sleep_time)
                    sleep_time *= backoff_factor
                    continue
                else:
                    print(f"❌ Received status {response.status_code}. Max retries reached.")
                    response.raise_for_status()

            response.raise_for_status()

            result = response.json()
            print(f"📋 Response received: {result.get('success', 'N/A')} success")

            if result.get("success"):
                print("✅ External validation service completed successfully")
                print(f"   - validation_passed: {result.get('validation_passed', 'N/A')}")
                print(f"   - overall_score: {result.get('overall_score', 'N/A')}")
                return result
            else:
                print(f"❌ External validation service failed: {result.get('error')}")
                return _create_failure_result(result.get("error", "External validation failed"))

        except requests.exceptions.Timeout:
            retries += 1
            if retries < max_retries:
                print(f"❌ Request timed out. Retrying in {sleep_time}s... ({retries}/{max_retries})")
                time.sleep(sleep_time)
                sleep_time *= backoff_factor
                continue
            else:
                print("❌ Request timed out. Max retries reached.")
                return _create_failure_result("External validation service timeout after multiple retries")

        except requests.exceptions.ConnectionError as e:
            retries += 1
            if retries < max_retries:
                print(f"❌ Connection error: {e}. Retrying in {sleep_time}s... ({retries}/{max_retries})")
                time.sleep(sleep_time)
                sleep_time *= backoff_factor
                continue
            else:
                print("❌ Connection error. Max retries reached.")
                return _create_failure_result("External validation service connection error after multiple retries")

        except Exception as e:
            print(f"❌ Failed to call external validation service: {str(e)}")
            return _create_failure_result(f"External validation service error: {str(e)}")

    # Fallback (should be unreachable if loop logic is correct)
    return _create_failure_result("Max retries reached for external validation service.")


def _create_failure_result(error_message: str) -> dict[str, Any]:
    """Create a standardized failure result dictionary."""
    return {
        "success": False,
        "validation_passed": False,
        "overall_score": 0,
        "error": error_message,
        "validation_summary": "External validation service unavailable",
        "screenshot_paths": {},
    }


def is_validation_error_recoverable(error_msg: str) -> bool:
    """
    Check if a validation error is recoverable (API key issues, service unavailable).

    These errors mean the QTI might still be valid, but we couldn't verify it.

    Args:
        error_msg: The error message from validation

    Returns:
        True if the error is recoverable (QTI can proceed with warning)
    """
    recoverable_keywords = [
        "api key",
        "api_key",
        "401",
        "connection",
        "timeout",
        "unavailable",
        "chrome",
        "screenshot",
    ]
    error_lower = error_msg.lower()
    return any(keyword in error_lower for keyword in recoverable_keywords)


def build_validation_result_dict(validation_result: dict[str, Any]) -> dict[str, Any]:
    """
    Build a standardized validation result dictionary from raw validation response.

    Args:
        validation_result: Raw response from validation service

    Returns:
        Standardized dictionary with all validation fields
    """
    return {
        "success": validation_result.get("success", False),
        "validation_passed": validation_result.get("validation_passed", False),
        "overall_score": validation_result.get("overall_score", 0),
        "completeness_score": validation_result.get("completeness_score", 0),
        "accuracy_score": validation_result.get("accuracy_score", 0),
        "visual_score": validation_result.get("visual_score", 0),
        "functionality_score": validation_result.get("functionality_score", 0),
        "issues_found": validation_result.get("issues_found", []),
        "missing_elements": validation_result.get("missing_elements", []),
        "recommendations": validation_result.get("recommendations", []),
        "validation_summary": validation_result.get("validation_summary", ""),
        "screenshot_paths": validation_result.get("screenshot_paths", {}),
    }


def print_validation_debug(validation_result: dict[str, Any]) -> None:
    """Print detailed validation debug information."""
    print("🔍 VALIDATION DEBUG:")
    debug_keys = [
        "success",
        "validation_passed",
        "overall_score",
        "completeness_score",
        "functionality_score",
        "error",
        "validation_summary",
        "issues_found",
        "missing_elements",
    ]
    for key in debug_keys:
        print(f"   - {key}: {validation_result.get(key, 'N/A')}")
