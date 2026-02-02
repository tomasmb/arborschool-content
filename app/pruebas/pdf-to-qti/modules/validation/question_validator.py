"""
Question Validator Module

This module implements comprehensive question validation using GPT-5.1 to:
1. Compare rendered QTI questions with original PDF content
2. Validate question completeness and correctness
3. Ensure proper rendering in the QTI sandbox
4. Return pass/fail validation results

Uses the existing visual validator infrastructure and extends it with
comprehensive validation logic.
"""

from __future__ import annotations

import base64
import os
from typing import Any

from openai import OpenAI

from .validation_chrome_setup import create_webdriver, is_lambda_environment
from .validation_prompts import (
    create_validation_prompt,
    parse_validation_response,
    should_proceed_with_qti,
)
from .validation_sandbox import (
    capture_element_screenshot,
    find_qti_textarea,
    find_question_area,
    insert_qti_xml,
    log_question_area_debug_info,
    navigate_to_sandbox,
    wait_for_page_load,
    wait_for_qti_render,
)

# Re-export for backward compatibility
__all__ = [
    "validate_qti_question",
    "capture_qti_screenshot",
    "perform_comprehensive_validation",
    "create_validation_prompt",
    "parse_validation_response",
    "should_proceed_with_qti",
]


def validate_qti_question(
    qti_xml: str,
    original_pdf_image: str,
    openai_api_key: str,
    output_dir: str | None = None,
    sandbox_url: str = "https://qti.amp-up.io/testrunner/sandbox/",
) -> dict[str, Any]:
    """Comprehensive QTI question validation using GPT-5.1.

    CRITICAL: This function must work properly - validation cannot be skipped.

    This is the main validation function that:
    1. Renders the QTI XML in the sandbox
    2. Takes a screenshot of the rendered question
    3. Uses GPT-5.1 to validate against original PDF
    4. Returns pass/fail with detailed analysis

    Args:
        qti_xml: QTI XML content to validate
        original_pdf_image: Base64 encoded original PDF image
        openai_api_key: OpenAI API key for GPT-5.1 validation
        output_dir: Optional directory to save screenshots
        sandbox_url: QTI sandbox URL for rendering

    Returns:
        Dictionary with validation results and pass/fail status
    """
    print("🔍 Starting comprehensive question validation...")
    screenshot_paths: dict[str, str] = {}

    try:
        # Save original PDF screenshot for debugging
        if output_dir and original_pdf_image:
            screenshot_paths = _save_original_pdf_screenshot(original_pdf_image, output_dir)

        # Step 1: Render QTI in sandbox and capture screenshot
        print("   📸 Capturing screenshot of rendered question...")
        screenshot_result = capture_qti_screenshot(qti_xml, sandbox_url)

        rendered_image = None
        if screenshot_result["success"]:
            rendered_image = screenshot_result["screenshot_base64"]
            _save_rendered_screenshot(rendered_image, output_dir, screenshot_paths)
        else:
            print(f"   ❌ Screenshot capture failed: {screenshot_result['error']}")
            return _create_screenshot_failure_result(screenshot_result, screenshot_paths)

        # Step 2: Comprehensive validation using GPT-5.1
        if rendered_image:
            print("   🤖 Performing comprehensive validation with GPT-5.1...")
            validation_result = perform_comprehensive_validation(original_pdf_image, rendered_image, qti_xml, openai_api_key)
        else:
            validation_result = _create_no_screenshot_result()

        # Add screenshot paths and log results
        validation_result["screenshot_paths"] = screenshot_paths
        _log_validation_result(validation_result)

        return validation_result

    except Exception as e:
        print(f"   ❌ Question validation error: {str(e)}")
        return {
            "success": False,
            "validation_passed": False,
            "error": f"Validation process failed: {str(e)}",
            "screenshot_paths": screenshot_paths,
            "validation_details": {},
        }


def _save_original_pdf_screenshot(original_pdf_image: str, output_dir: str) -> dict[str, str]:
    """Save original PDF screenshot for debugging."""
    screenshot_paths: dict[str, str] = {}
    original_path = os.path.join(output_dir, "validation_original_pdf.png")

    try:
        with open(original_path, "wb") as f:
            f.write(base64.b64decode(original_pdf_image))
        screenshot_paths["original_pdf"] = original_path
        print(f"   💾 Saved original PDF screenshot: {original_path}")
    except Exception as e:
        print(f"   ⚠️  Failed to save original PDF screenshot: {str(e)}")

    return screenshot_paths


def _save_rendered_screenshot(rendered_image: str, output_dir: str | None, screenshot_paths: dict[str, str]) -> None:
    """Save rendered QTI screenshot."""
    if not output_dir:
        return

    rendered_path = os.path.join(output_dir, "validation_rendered_qti.png")
    try:
        with open(rendered_path, "wb") as f:
            f.write(base64.b64decode(rendered_image))
        screenshot_paths["rendered_qti"] = rendered_path
        print(f"   💾 Saved rendered QTI screenshot: {rendered_path}")
    except Exception as e:
        print(f"   ⚠️  Failed to save rendered screenshot: {str(e)}")


def _create_screenshot_failure_result(screenshot_result: dict[str, Any], screenshot_paths: dict[str, str]) -> dict[str, Any]:
    """Create result for screenshot capture failure."""
    return {
        "success": False,
        "validation_passed": False,
        "error": f"Failed to capture screenshot: {screenshot_result['error']}",
        "screenshot_paths": screenshot_paths,
        "validation_details": {"screenshot_capture_failed": True, "chrome_setup_error": "cannot find Chrome binary" in screenshot_result["error"]},
    }


def _create_no_screenshot_result() -> dict[str, Any]:
    """Create result when no rendered screenshot is available."""
    print("   ⚠️  Performing validation without rendered screenshot...")
    return {
        "success": True,
        "validation_passed": False,
        "overall_score": 0,
        "error": "Could not capture rendered screenshot for comparison",
        "validation_summary": "Validation incomplete - screenshot capture failed",
    }


def _log_validation_result(validation_result: dict[str, Any]) -> None:
    """Log validation results."""
    if validation_result.get("validation_passed"):
        print("   ✅ Question validation PASSED")
    else:
        print("   ❌ Question validation FAILED")
        error_msg = validation_result.get("error", "Screenshot capture failed")
        print(f"   📋 Issues: {error_msg}")


def capture_qti_screenshot(qti_xml: str, sandbox_url: str) -> dict[str, Any]:
    """Capture screenshot of QTI question rendered in sandbox.

    Args:
        qti_xml: QTI XML content to render
        sandbox_url: QTI sandbox URL

    Returns:
        Dictionary with success status and screenshot data
    """
    driver = None
    is_lambda = is_lambda_environment()

    try:
        # Create WebDriver
        driver_result = create_webdriver()
        if not driver_result["success"]:
            return driver_result

        driver = driver_result["driver"]

        # Navigate to sandbox
        nav_result = navigate_to_sandbox(driver, sandbox_url)
        if not nav_result["success"]:
            return nav_result

        # Wait for page load
        wait_for_page_load(driver, is_lambda)

        # Find QTI textarea
        textarea_result = find_qti_textarea(driver, is_lambda)
        if not textarea_result["success"]:
            return textarea_result

        # Insert QTI XML
        insert_result = insert_qti_xml(driver, textarea_result["textarea"], qti_xml)
        if not insert_result["success"]:
            return insert_result

        # Wait for rendering
        wait_for_qti_render(driver)

        # Find question area
        question_area = find_question_area(driver)
        log_question_area_debug_info(driver, question_area)

        # Capture screenshot
        return capture_element_screenshot(driver, question_area)

    except Exception as e:
        error_message = _format_screenshot_error(str(e), is_lambda)
        print(f"   ❌ Screenshot capture error: {error_message}")
        return {"success": False, "error": error_message}

    finally:
        if driver:
            try:
                driver.quit()
                print("   🔧 Chrome driver closed")
            except Exception:
                pass


def _format_screenshot_error(error_message: str, is_lambda: bool) -> str:
    """Format error message for screenshot capture failures."""
    if "chrome binary" in error_message.lower():
        if is_lambda:
            return f"Chrome Lambda layer not configured properly. Original error: {error_message}"
        else:
            return f"Chrome browser not found. Please install Google Chrome. Original error: {error_message}"
    elif "timeout" in error_message.lower():
        return f"Timeout waiting for page elements. The QTI sandbox may be slow. Original error: {error_message}"
    elif "connection" in error_message.lower():
        return f"Network connection issue. Check internet connectivity. Original error: {error_message}"
    return error_message


def perform_comprehensive_validation(original_pdf_image: str, rendered_image: str, qti_xml: str, openai_api_key: str) -> dict[str, Any]:
    """Perform comprehensive validation using GPT-5.1.

    Args:
        original_pdf_image: Base64 encoded original PDF image
        rendered_image: Base64 encoded rendered QTI screenshot
        qti_xml: QTI XML content for context
        openai_api_key: OpenAI API key

    Returns:
        Dictionary with detailed validation results
    """
    try:
        client = OpenAI(api_key=openai_api_key)

        # Create validation prompt
        validation_prompt = create_validation_prompt()

        # Truncate XML for context (avoid token limits)
        xml_context = qti_xml[:2000] + ("..." if len(qti_xml) > 2000 else "")

        # Prepare messages for the API call
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": validation_prompt},
                    {"type": "text", "text": f"\n\nQTI XML for context:\n```xml\n{xml_context}\n```"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{original_pdf_image}", "detail": "high"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{rendered_image}", "detail": "high"}},
                ],
            }
        ]

        # Call GPT-5.1 for validation
        response = client.chat.completions.create(
            model="gpt-5.1",
            messages=messages,
            reasoning_effort="high",
            seed=42,
        )

        response_text = response.choices[0].message.content

        # Parse the validation response
        return parse_validation_response(response_text)

    except Exception as e:
        return {"success": False, "validation_passed": False, "error": f"GPT-5.1 validation failed: {str(e)}", "validation_details": {}}
