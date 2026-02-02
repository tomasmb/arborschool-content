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

import base64
import json
import os
import time
from typing import Any, Dict, Optional

from openai import OpenAI
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


def validate_qti_question(
    qti_xml: str,
    original_pdf_image: str,
    openai_api_key: str,
    output_dir: Optional[str] = None,
    sandbox_url: str = "https://qti.amp-up.io/testrunner/sandbox/"
) -> Dict[str, Any]:
    """
    Comprehensive QTI question validation using GPT-5.1.
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

    try:
        # Save original PDF screenshot immediately for debugging
        screenshot_paths = {}
        if output_dir and original_pdf_image:
            import os

            # Always save original PDF image for debugging
            original_path = os.path.join(output_dir, "validation_original_pdf.png")
            try:
                with open(original_path, "wb") as f:
                    f.write(base64.b64decode(original_pdf_image))
                screenshot_paths["original_pdf"] = original_path
                print(f"   💾 Saved original PDF screenshot: {original_path}")
            except Exception as e:
                print(f"   ⚠️  Failed to save original PDF screenshot: {str(e)}")

        # Step 1: Render QTI in sandbox and capture screenshot
        print("   📸 Capturing screenshot of rendered question...")
        screenshot_result = capture_qti_screenshot(qti_xml, sandbox_url)

        rendered_image = None
        if screenshot_result["success"]:
            rendered_image = screenshot_result["screenshot_base64"]

            # Save rendered QTI screenshot
            if output_dir:
                rendered_path = os.path.join(output_dir, "validation_rendered_qti.png")
                try:
                    with open(rendered_path, "wb") as f:
                        f.write(base64.b64decode(rendered_image))
                    screenshot_paths["rendered_qti"] = rendered_path
                    print(f"   💾 Saved rendered QTI screenshot: {rendered_path}")
                except Exception as e:
                    print(f"   ⚠️  Failed to save rendered screenshot: {str(e)}")
        else:
            print(f"   ❌ Screenshot capture failed: {screenshot_result['error']}")

            # Return early but with saved screenshots for debugging
            return {
                "success": False,
                "validation_passed": False,
                "error": f"Failed to capture screenshot: {screenshot_result['error']}",
                "screenshot_paths": screenshot_paths,
                "validation_details": {
                    "screenshot_capture_failed": True,
                    "chrome_setup_error": "cannot find Chrome binary" in screenshot_result['error']
                }
            }

        # Step 2: Comprehensive validation using GPT-5.1
        if rendered_image:
            print("   🤖 Performing comprehensive validation with GPT-5.1...")
            validation_result = perform_comprehensive_validation(
                original_pdf_image,
                rendered_image,
                qti_xml,
                openai_api_key
            )
        else:
            # Fallback: validation without rendered screenshot
            print("   ⚠️  Performing validation without rendered screenshot...")
            validation_result = {
                "success": True,
                "validation_passed": False,
                "overall_score": 0,
                "error": "Could not capture rendered screenshot for comparison",
                "validation_summary": "Validation incomplete - screenshot capture failed"
            }

        # Add screenshot paths to result
        validation_result["screenshot_paths"] = screenshot_paths

        # Log validation results
        if validation_result.get("validation_passed"):
            print("   ✅ Question validation PASSED")
        else:
            print("   ❌ Question validation FAILED")
            print(f"   📋 Issues: {validation_result.get('error', 'Screenshot capture failed')}")

        return validation_result

    except Exception as e:
        print(f"   ❌ Question validation error: {str(e)}")

        # Still return screenshot paths if we have them
        return {
            "success": False,
            "validation_passed": False,
            "error": f"Validation process failed: {str(e)}",
            "screenshot_paths": screenshot_paths if 'screenshot_paths' in locals() else {},
            "validation_details": {}
        }


def capture_qti_screenshot(qti_xml: str, sandbox_url: str) -> Dict[str, Any]:
    """
    Capture screenshot of QTI question rendered in sandbox.

    Args:
        qti_xml: QTI XML content to render
        sandbox_url: QTI sandbox URL

    Returns:
        Dictionary with success status and screenshot data
    """
    driver = None
    try:
        # Detect Lambda environment
        is_lambda = os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is not None

        # Setup Chrome options for production use
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Re-enabled for production
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")  # Re-enabled for headless
        chrome_options.add_argument("--window-size=1400,1000")  # Larger window for debugging
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--disable-extensions")  # Re-enabled for production
        chrome_options.add_argument("--disable-logging")  # Re-enabled for production
        chrome_options.add_argument("--silent")  # Re-enabled for production

        # Add user agent and other options to help with loading
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--disable-default-apps")

        # Lambda-specific Chrome configuration
        if is_lambda:
            print("   🐍 Lambda environment detected")

            # Try multiple Chrome paths for different Lambda layers
            chrome_paths = [
                "/opt/chrome/chrome",  # chrome-aws-lambda layer
                "/opt/chrome-linux/chrome",  # alternative layer
                "/opt/bin/chrome",  # another common path
                "/usr/bin/google-chrome"  # system install
            ]

            chromedriver_paths = [
                "/opt/chromedriver",  # chrome-aws-lambda layer
                "/opt/bin/chromedriver",  # alternative
                "/usr/bin/chromedriver"  # system install
            ]

            chrome_binary_path = None
            for path in chrome_paths:
                if os.path.exists(path):
                    chrome_binary_path = path
                    break

            if chrome_binary_path:
                chrome_options.binary_location = chrome_binary_path
                print(f"   🔧 Using Lambda Chrome binary: {chrome_binary_path}")
            else:
                print(f"   ❌ Chrome not found in Lambda. Checked paths: {chrome_paths}")
                return {
                    "success": False,
                    "error": "Chrome Lambda layer not found. Please add Chrome Lambda layer to your serverless deployment."
                }
        else:
            # Local development - find Chrome binary
            import platform

            chrome_binary_path = None
            if platform.system() == "Darwin":  # macOS
                common_chrome_paths = [
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                    "/Applications/Chromium.app/Contents/MacOS/Chromium",
                    "/usr/bin/google-chrome",
                    "/usr/bin/chromium"
                ]

                for path in common_chrome_paths:
                    if os.path.exists(path):
                        chrome_binary_path = path
                        break

                if chrome_binary_path:
                    chrome_options.binary_location = chrome_binary_path
                    print(f"   🔧 Using Chrome binary: {chrome_binary_path}")
                else:
                    print("   ⚠️  Chrome not found in common macOS locations. Trying webdriver-manager...")
            elif platform.system() == "Linux":  # Linux
                linux_chrome_paths = [
                    "/usr/bin/google-chrome",
                    "/usr/bin/chromium",
                    "/usr/bin/chromium-browser",
                    "/snap/bin/chromium"
                ]

                for path in linux_chrome_paths:
                    if os.path.exists(path):
                        chrome_binary_path = path
                        break

                if chrome_binary_path:
                    chrome_options.binary_location = chrome_binary_path
                    print(f"   🔧 Using Chrome binary: {chrome_binary_path}")

        # Create WebDriver with environment-specific service
        try:
            if is_lambda:
                # Find chromedriver in Lambda layer
                chromedriver_path = None
                for path in chromedriver_paths:
                    if os.path.exists(path):
                        chromedriver_path = path
                        break

                if chromedriver_path:
                    service = Service(chromedriver_path)
                    print(f"   🔧 Using Lambda chromedriver: {chromedriver_path}")
                else:
                    print(f"   ❌ ChromeDriver not found in Lambda. Checked paths: {chromedriver_paths}")
                    return {
                        "success": False,
                        "error": "ChromeDriver not found in Lambda layer. Please ensure Chrome Lambda layer includes chromedriver."
                    }
            else:
                # Use webdriver-manager for local development
                service = Service(ChromeDriverManager().install())
                print("   🔧 Using webdriver-manager")

            driver = webdriver.Chrome(service=service, options=chrome_options)

        except Exception as chrome_error:
            print(f"   ❌ Chrome setup failed: {str(chrome_error)}")

            # Provide helpful error messages
            if is_lambda:
                return {
                    "success": False,
                    "error": f"Chrome Lambda layer setup failed. Ensure Chrome Lambda layer is properly configured. Original error: {str(chrome_error)}"
                }
            elif "chrome binary" in str(chrome_error).lower():
                return {
                    "success": False,
                    "error": f"Chrome browser not found. Please install Google Chrome from https://www.google.com/chrome/ or run 'brew install --cask google-chrome'. Original error: {str(chrome_error)}"
                }
            else:
                return {
                    "success": False,
                    "error": f"WebDriver setup failed: {str(chrome_error)}"
                }

        # Navigate to sandbox
        print("   🌐 Navigating to QTI sandbox...")

        try:
            driver.get(sandbox_url)
            print("   ✅ Successfully navigated to sandbox")
        except Exception as nav_error:
            print(f"   ❌ Navigation failed: {str(nav_error)}")
            return {
                "success": False,
                "error": f"Failed to navigate to sandbox: {str(nav_error)}"
            }

        # Wait for page to load
        timeout = 30 if is_lambda else 15
        wait = WebDriverWait(driver, timeout)
        print(f"   ⏳ Waiting for page load (timeout: {timeout}s)...")

        # Basic page check
        try:
            page_source_length = len(driver.page_source)
            if page_source_length < 1000:  # Page seems too small
                print("   ⚠️  Page seems incomplete, trying refresh...")
                driver.refresh()
                time.sleep(3)
        except Exception:
            pass

        # Find the QTI XML textarea
        print("   📝 Looking for QTI XML input area...")
        textarea_found = False

        try:
            xml_textarea = wait.until(
                EC.presence_of_element_located((By.TAG_NAME, "textarea"))
            )
            textarea_found = True
            print("   ✅ Found QTI XML textarea")

        except TimeoutException as e:
            print(f"   ❌ Timeout finding textarea: {str(e)}")
            return {
                "success": False,
                "error": f"Could not find QTI XML input textarea: {str(e)}"
            }

        if not textarea_found:
            return {
                "success": False,
                "error": "QTI XML textarea not found"
            }

        # Clear and input QTI XML
        print(f"   📄 Inserting QTI XML ({len(qti_xml)} characters)...")

        try:
            # Clear the textarea first
            xml_textarea.clear()
            print("   🧹 Textarea cleared")

            # Use JavaScript injection for reliable insertion
            escaped_xml = qti_xml.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
            js_script = f'arguments[0].value = "{escaped_xml}";'
            driver.execute_script(js_script, xml_textarea)
            print("   ✅ QTI XML injected via JavaScript")

            # Verify the content was inserted
            inserted_length = len(xml_textarea.get_attribute('value'))
            print(f"   🔍 Verification: {inserted_length}/{len(qti_xml)} characters in textarea")

            # CRITICAL: Simulate user input to trigger QTI rendering
            print("   ⌨️  Simulating user input to trigger rendering...")
            xml_textarea.send_keys(" ")  # Add a space
            time.sleep(0.5)  # Brief pause
            xml_textarea.send_keys("\b")  # Delete the space (backspace)
            print("   ✅ Input simulation complete - should trigger QTI rendering")

        except Exception as insert_error:
            print(f"   ❌ Error inserting XML: {str(insert_error)}")
            return {
                "success": False,
                "error": f"Failed to insert QTI XML: {str(insert_error)}"
            }

        # Wait for QTI content to render
        print("   ⏳ Waiting for QTI auto-rendering to complete...")

        # Monitor the question area for content changes
        question_area_selector = ".col-lg-8"
        max_wait_time = 15  # Reduced from 20 since we know it works

        for second in range(max_wait_time):
            time.sleep(1)

            try:
                current_area = driver.find_element(By.CSS_SELECTOR, question_area_selector)
                current_text = current_area.text.strip()

                if len(current_text) > 50:  # Has meaningful text content
                    print("   ✅ QTI content rendered successfully")
                    break

            except Exception:
                continue

        # Give final time for stabilization
        print("   😴 Final stabilization wait...")
        time.sleep(3)

        # Find the rendered question area - use what we know works
        print("   🎯 Looking for rendered question area...")
        question_area = None

        # Try the main QTI container first (what we know works)
        try:
            question_area = driver.find_element(By.CSS_SELECTOR, ".col-lg-8 .qti3-player-container-fluid")
            print("   ✅ Found QTI container")
        except Exception:
            # Fallback to broader area
            try:
                question_area = driver.find_element(By.CSS_SELECTOR, ".col-lg-8")
                print("   ✅ Found question area (fallback)")
            except Exception:
                question_area = driver.find_element(By.TAG_NAME, "body")
                print("   ⚠️  Using body element as fallback")

        # Quick content check
        area_text = question_area.text.strip()
        print(f"   📝 Content length: {len(area_text)} characters")
        if area_text:
            preview = area_text[:100].replace('\n', ' ')
            print(f"   📄 Preview: '{preview}{'...' if len(area_text) > 100 else ''}'")

        # Take screenshot of the question area
        print("   📸 Attempting to capture screenshot...")

        # Scroll the question area into view to ensure it's fully visible
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", question_area)
            time.sleep(1)  # Brief pause after scrolling
        except Exception as scroll_error:
            print(f"   ⚠️  Scroll failed: {str(scroll_error)}")

        # Debug: Show what we're about to screenshot
        try:
            area_text_sample = question_area.text[:200].replace('\n', ' ').strip()
            print(f"   🔍 Content preview: '{area_text_sample}{'...' if len(question_area.text) > 200 else ''}'")

            # Check for specific QTI elements in the area
            qti_elements_in_area = []
            qti_check_selectors = [
                "input", "textarea", "button", "img", ".qti-interaction",
                ".qti-item-body", ".qti-prompt", "svg", "canvas"
            ]

            for check_selector in qti_check_selectors:
                try:
                    elements = question_area.find_elements(By.CSS_SELECTOR, check_selector)
                    if elements:
                        qti_elements_in_area.append(f"{check_selector}({len(elements)})")
                except Exception:
                    pass

            if qti_elements_in_area:
                print(f"   🎯 Elements in screenshot area: {', '.join(qti_elements_in_area)}")
            else:
                print("   ⚠️  No interactive elements found in screenshot area")

        except Exception as debug_error:
            print(f"   ⚠️  Debug info failed: {str(debug_error)}")

        try:
            screenshot_png = question_area.screenshot_as_png
            screenshot_base64 = base64.b64encode(screenshot_png).decode('utf-8')
            print(f"   ✅ Screenshot captured successfully ({len(screenshot_base64)} chars)")

            return {
                "success": True,
                "screenshot_base64": screenshot_base64
            }

        except Exception as screenshot_error:
            print(f"   ❌ Screenshot capture failed: {str(screenshot_error)}")
            return {
                "success": False,
                "error": f"Screenshot capture failed: {str(screenshot_error)}"
            }

    except Exception as e:
        error_message = str(e)
        print(f"   ❌ Screenshot capture error: {error_message}")

        # Provide more helpful error messages
        if "chrome binary" in error_message.lower():
            if is_lambda:
                error_message = f"Chrome Lambda layer not configured properly. Original error: {error_message}"
            else:
                error_message = f"Chrome browser not found. Please install Google Chrome. Original error: {error_message}"
        elif "timeout" in error_message.lower():
            error_message = f"Timeout waiting for page elements. The QTI sandbox may be slow or unavailable. Original error: {error_message}"
        elif "connection" in error_message.lower():
            error_message = f"Network connection issue. Check internet connectivity and sandbox URL. Original error: {error_message}"

        return {
            "success": False,
            "error": error_message
        }
    finally:
        if driver:
            try:
                driver.quit()
                print("   🔧 Chrome driver closed")
            except Exception:
                pass


def perform_comprehensive_validation(
    original_pdf_image: str,
    rendered_image: str,
    qti_xml: str,
    openai_api_key: str
) -> Dict[str, Any]:
    """
    Perform comprehensive validation using GPT-5.1.

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

        # Create comprehensive validation prompt
        validation_prompt = create_validation_prompt()

        # Prepare images for the API call
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": validation_prompt
                    },
                    {
                        "type": "text",
                        "text": f"\n\nQTI XML for context:\n```xml\n{qti_xml[:2000]}{'...' if len(qti_xml) > 2000 else ''}\n```"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{original_pdf_image}",
                            "detail": "high"
                        }
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{rendered_image}",
                            "detail": "high"
                        }
                    }
                ]
            }
        ]

        # Call GPT-5.1 for validation with high reasoning effort for accurate analysis
        response = client.chat.completions.create(
            model="gpt-5.1",
            messages=messages,
            reasoning_effort="high",
            seed=42,
        )

        response_text = response.choices[0].message.content

        # Parse the validation response
        validation_result = parse_validation_response(response_text)

        return validation_result

    except Exception as e:
        return {
            "success": False,
            "validation_passed": False,
            "error": f"GPT-5.1 validation failed: {str(e)}",
            "validation_details": {}
        }


def create_validation_prompt() -> str:
    """
    Create comprehensive validation prompt for GPT-5.1.

    Returns:
        Detailed validation prompt string
    """

    return """You are a QTI question validation expert. You will receive two images:
1. ORIGINAL PDF: The source question from a PDF document
2. RENDERED QTI: The same question rendered in a QTI testing platform

Your task is to validate if the rendered QTI question is functionally complete and correct for assessment purposes.

VALIDATION FOCUS - ONLY CHECK THESE:
□ QUESTION CONTENT: Is the core question text present and correct?
□ ANSWER ELEMENTS: Are all answer choices, input fields, or response areas working?
□ VISUAL CONTENT: Are essential images, diagrams, charts, or tables displayed properly?
□ INSTRUCTIONS: Are the question instructions clear and complete?
□ FUNCTIONALITY: Do interactive elements (inputs, buttons) work as expected?
□ SEMANTIC COMPLETENESS: Does the question make sense and is answerable?

IGNORE THESE (NOT QTI VALIDITY CONCERNS):
✗ Page numbers, headers, footers
✗ "GO ON" or navigation indicators
✗ PDF document formatting artifacts
✗ Minor spacing or font differences
✗ Test booklet metadata
✗ Page layout variations that don't affect question clarity

CRITICAL ISSUES TO FLAG:
- Missing or corrupted question text
- Missing answer choices or input fields
- Essential images/diagrams not displaying
- Broken interactive elements
- Question is unanswerable due to missing information
- Weird rendering that affects question understanding

RESPONSE FORMAT:
Provide your response in this JSON format:

{
  "validation_passed": true/false,
  "overall_score": 0-100,
  "completeness_score": 0-100,
  "accuracy_score": 0-100,
  "visual_score": 0-100,
  "functionality_score": 0-100,
  "issues_found": [
    "Only list issues that affect QTI question validity"
  ],
  "missing_elements": [
    "Only essential question elements, not document artifacts"
  ],
  "recommendations": [
    "Suggestions for fixing actual QTI problems"
  ],
  "validation_summary": "Brief summary focusing on QTI assessment validity"
}

VALIDATION CRITERIA:
- PASS: Overall score ≥ 80 AND no critical question content missing
- FAIL: Overall score < 80 OR essential question elements missing

Focus on whether a student can properly understand and answer the question, not exact PDF replication."""


def parse_validation_response(response_text: str) -> Dict[str, Any]:
    """
    Parse GPT-5.1 validation response into structured result.

    Args:
        response_text: Raw response from GPT-5.1

    Returns:
        Structured validation result dictionary
    """

    try:
        # Look for JSON in the response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1

        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            validation_data = json.loads(json_str)

            # Ensure required fields exist
            validation_passed = validation_data.get("validation_passed", False)
            overall_score = validation_data.get("overall_score", 0)

            return {
                "success": True,
                "validation_passed": validation_passed,
                "overall_score": overall_score,
                "completeness_score": validation_data.get("completeness_score", 0),
                "accuracy_score": validation_data.get("accuracy_score", 0),
                "visual_score": validation_data.get("visual_score", 0),
                "functionality_score": validation_data.get("functionality_score", 0),
                "issues_found": validation_data.get("issues_found", []),
                "missing_elements": validation_data.get("missing_elements", []),
                "recommendations": validation_data.get("recommendations", []),
                "validation_summary": validation_data.get("validation_summary", ""),
                "raw_response": response_text,
                "validation_details": validation_data
            }
        else:
            # Fallback parsing if JSON not found
            validation_passed = "validation_passed\": true" in response_text.lower() or "pass" in response_text.lower()

            return {
                "success": True,
                "validation_passed": validation_passed,
                "overall_score": 50 if validation_passed else 25,
                "issues_found": ["Could not parse detailed validation results"],
                "validation_summary": "Validation completed but response parsing failed",
                "raw_response": response_text,
                "validation_details": {}
            }

    except Exception as e:
        # Error handling - assume validation failed
        return {
            "success": False,
            "validation_passed": False,
            "overall_score": 0,
            "error": f"Failed to parse validation response: {str(e)}",
            "raw_response": response_text,
            "validation_details": {}
        }


def should_proceed_with_qti(validation_result: Dict[str, Any]) -> bool:
    """
    Determine if QTI should be returned based on validation results.
    Focus on semantic correctness rather than perfect visual reproduction.

    Args:
        validation_result: Result from comprehensive validation

    Returns:
        Boolean indicating whether to proceed with QTI
    """

    if not validation_result.get("success", False):
        return False

    if not validation_result.get("validation_passed", False):
        return False

    # More lenient score threshold - focus on educational validity
    overall_score = validation_result.get("overall_score", 0)
    if overall_score < 60:  # Lowered from 80 to 60
        return False

    # Check for critical missing elements (only truly essential ones)
    missing_elements = validation_result.get("missing_elements", [])
    if missing_elements:
        # Only block for truly critical missing content
        critical_keywords = ["question text", "answer choices", "essential", "critical", "main"]
        has_critical_missing = False

        for missing in missing_elements:
            missing_lower = missing.lower()
            # Only consider it critical if it contains specific critical terms
            if any(keyword in missing_lower for keyword in critical_keywords):
                has_critical_missing = True
                break

        if has_critical_missing:
            return False

    # If completeness and functionality scores are reasonable, proceed
    completeness = validation_result.get("completeness_score", 0)
    functionality = validation_result.get("functionality_score", 0)

    # Allow if content is mostly complete and functional, even if formatting isn't perfect
    if completeness >= 65 and functionality >= 65:
        return True

    return False
