"""
QTI Sandbox interaction utilities for validation.

This module handles navigation, QTI input, and screenshot capture
from the QTI testing sandbox.
"""

from __future__ import annotations

import base64
import time
from typing import Any

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def navigate_to_sandbox(driver: WebDriver, sandbox_url: str) -> dict[str, Any]:
    """Navigate to the QTI sandbox URL.

    Args:
        driver: Selenium WebDriver instance
        sandbox_url: QTI sandbox URL

    Returns:
        Dict with success status
    """
    print("   🌐 Navigating to QTI sandbox...")

    try:
        driver.get(sandbox_url)
        print("   ✅ Successfully navigated to sandbox")
        return {"success": True}
    except Exception as nav_error:
        print(f"   ❌ Navigation failed: {str(nav_error)}")
        return {"success": False, "error": f"Failed to navigate to sandbox: {str(nav_error)}"}


def wait_for_page_load(driver: WebDriver, is_lambda: bool) -> None:
    """Wait for page to load and verify basic content.

    Args:
        driver: Selenium WebDriver instance
        is_lambda: Whether running in Lambda environment
    """
    timeout = 30 if is_lambda else 15
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


def find_qti_textarea(driver: WebDriver, is_lambda: bool) -> dict[str, Any]:
    """Find and return the QTI XML textarea element.

    Args:
        driver: Selenium WebDriver instance
        is_lambda: Whether running in Lambda environment

    Returns:
        Dict with success status and textarea element
    """
    print("   📝 Looking for QTI XML input area...")
    timeout = 30 if is_lambda else 15
    wait = WebDriverWait(driver, timeout)

    try:
        xml_textarea = wait.until(EC.presence_of_element_located((By.TAG_NAME, "textarea")))
        print("   ✅ Found QTI XML textarea")
        return {"success": True, "textarea": xml_textarea}

    except TimeoutException as e:
        print(f"   ❌ Timeout finding textarea: {str(e)}")
        return {"success": False, "error": f"Could not find QTI XML input textarea: {str(e)}"}


def insert_qti_xml(driver: WebDriver, textarea, qti_xml: str) -> dict[str, Any]:
    """Insert QTI XML into the textarea and trigger rendering.

    Args:
        driver: Selenium WebDriver instance
        textarea: Textarea element
        qti_xml: QTI XML content to insert

    Returns:
        Dict with success status
    """
    print(f"   📄 Inserting QTI XML ({len(qti_xml)} characters)...")

    try:
        # Clear the textarea first
        textarea.clear()
        print("   🧹 Textarea cleared")

        # Use JavaScript injection for reliable insertion
        escaped_xml = qti_xml.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
        js_script = f'arguments[0].value = "{escaped_xml}";'
        driver.execute_script(js_script, textarea)
        print("   ✅ QTI XML injected via JavaScript")

        # Verify the content was inserted
        inserted_length = len(textarea.get_attribute("value"))
        print(f"   🔍 Verification: {inserted_length}/{len(qti_xml)} characters in textarea")

        # Simulate user input to trigger QTI rendering
        print("   ⌨️  Simulating user input to trigger rendering...")
        textarea.send_keys(" ")  # Add a space
        time.sleep(0.5)  # Brief pause
        textarea.send_keys("\b")  # Delete the space (backspace)
        print("   ✅ Input simulation complete - should trigger QTI rendering")

        return {"success": True}

    except Exception as insert_error:
        print(f"   ❌ Error inserting XML: {str(insert_error)}")
        return {"success": False, "error": f"Failed to insert QTI XML: {str(insert_error)}"}


def wait_for_qti_render(driver: WebDriver, max_wait_time: int = 15) -> None:
    """Wait for QTI content to render in the question area.

    Args:
        driver: Selenium WebDriver instance
        max_wait_time: Maximum seconds to wait for rendering
    """
    print("   ⏳ Waiting for QTI auto-rendering to complete...")

    question_area_selector = ".col-lg-8"

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

    # Final stabilization wait
    print("   😴 Final stabilization wait...")
    time.sleep(3)


def find_question_area(driver: WebDriver):
    """Find the rendered question area element.

    Args:
        driver: Selenium WebDriver instance

    Returns:
        WebElement for the question area
    """
    print("   🎯 Looking for rendered question area...")

    # Try the main QTI container first
    try:
        question_area = driver.find_element(By.CSS_SELECTOR, ".col-lg-8 .qti3-player-container-fluid")
        print("   ✅ Found QTI container")
        return question_area
    except Exception:
        pass

    # Fallback to broader area
    try:
        question_area = driver.find_element(By.CSS_SELECTOR, ".col-lg-8")
        print("   ✅ Found question area (fallback)")
        return question_area
    except Exception:
        pass

    # Last resort: body element
    question_area = driver.find_element(By.TAG_NAME, "body")
    print("   ⚠️  Using body element as fallback")
    return question_area


def log_question_area_debug_info(driver: WebDriver, question_area) -> None:
    """Log debug information about the question area.

    Args:
        driver: Selenium WebDriver instance
        question_area: Question area WebElement
    """
    area_text = question_area.text.strip()
    print(f"   📝 Content length: {len(area_text)} characters")

    if area_text:
        preview = area_text[:100].replace("\n", " ")
        print(f"   📄 Preview: '{preview}{'...' if len(area_text) > 100 else ''}'")

    try:
        area_text_sample = question_area.text[:200].replace("\n", " ").strip()
        print(f"   🔍 Content preview: '{area_text_sample}{'...' if len(question_area.text) > 200 else ''}'")

        # Check for specific QTI elements
        qti_check_selectors = ["input", "textarea", "button", "img", ".qti-interaction", ".qti-item-body", ".qti-prompt", "svg", "canvas"]

        qti_elements_in_area = []
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


def capture_element_screenshot(driver: WebDriver, element) -> dict[str, Any]:
    """Capture screenshot of a specific element.

    Args:
        driver: Selenium WebDriver instance
        element: WebElement to screenshot

    Returns:
        Dict with success status and base64 screenshot
    """
    print("   📸 Attempting to capture screenshot...")

    # Scroll element into view
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(1)  # Brief pause after scrolling
    except Exception as scroll_error:
        print(f"   ⚠️  Scroll failed: {str(scroll_error)}")

    try:
        screenshot_png = element.screenshot_as_png
        screenshot_base64 = base64.b64encode(screenshot_png).decode("utf-8")
        print(f"   ✅ Screenshot captured successfully ({len(screenshot_base64)} chars)")

        return {"success": True, "screenshot_base64": screenshot_base64}

    except Exception as screenshot_error:
        print(f"   ❌ Screenshot capture failed: {str(screenshot_error)}")
        return {"success": False, "error": f"Screenshot capture failed: {str(screenshot_error)}"}
