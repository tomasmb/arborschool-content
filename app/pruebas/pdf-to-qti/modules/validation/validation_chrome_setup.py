"""
Chrome WebDriver setup for QTI validation.

This module handles Chrome browser configuration for both Lambda
and local development environments.
"""

from __future__ import annotations

import os
import platform
from typing import Any

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Chrome paths for different environments
LAMBDA_CHROME_PATHS = [
    "/opt/chrome/chrome",  # chrome-aws-lambda layer
    "/opt/chrome-linux/chrome",  # alternative layer
    "/opt/bin/chrome",  # another common path
    "/usr/bin/google-chrome",  # system install
]

LAMBDA_CHROMEDRIVER_PATHS = [
    "/opt/chromedriver",  # chrome-aws-lambda layer
    "/opt/bin/chromedriver",  # alternative
    "/usr/bin/chromedriver",  # system install
]

MACOS_CHROME_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]

LINUX_CHROME_PATHS = ["/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser", "/snap/bin/chromium"]


def is_lambda_environment() -> bool:
    """Check if running in AWS Lambda environment."""
    return os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None


def find_binary_path(paths: list[str]) -> str | None:
    """Find first existing binary from a list of paths."""
    for path in paths:
        if os.path.exists(path):
            return path
    return None


def create_chrome_options(is_lambda: bool) -> Options:
    """Create Chrome options for headless operation.

    Args:
        is_lambda: Whether running in Lambda environment

    Returns:
        Configured Chrome Options object
    """
    chrome_options = Options()

    # Core headless options
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1400,1000")

    # Security and performance options
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--silent")

    # User agent and automation detection
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-default-apps")

    return chrome_options


def setup_lambda_chrome(chrome_options: Options) -> dict[str, Any]:
    """Setup Chrome for Lambda environment.

    Args:
        chrome_options: Chrome options to configure

    Returns:
        Dict with success status and service/error info
    """
    print("   🐍 Lambda environment detected")

    chrome_binary_path = find_binary_path(LAMBDA_CHROME_PATHS)
    if chrome_binary_path:
        chrome_options.binary_location = chrome_binary_path
        print(f"   🔧 Using Lambda Chrome binary: {chrome_binary_path}")
    else:
        print(f"   ❌ Chrome not found in Lambda. Checked paths: {LAMBDA_CHROME_PATHS}")
        return {"success": False, "error": "Chrome Lambda layer not found. Please add Chrome Lambda layer."}

    chromedriver_path = find_binary_path(LAMBDA_CHROMEDRIVER_PATHS)
    if chromedriver_path:
        print(f"   🔧 Using Lambda chromedriver: {chromedriver_path}")
        return {"success": True, "service": Service(chromedriver_path)}
    else:
        print(f"   ❌ ChromeDriver not found. Checked paths: {LAMBDA_CHROMEDRIVER_PATHS}")
        return {"success": False, "error": "ChromeDriver not found in Lambda layer."}


def setup_local_chrome(chrome_options: Options) -> dict[str, Any]:
    """Setup Chrome for local development environment.

    Args:
        chrome_options: Chrome options to configure

    Returns:
        Dict with success status and service/error info
    """
    system = platform.system()

    if system == "Darwin":  # macOS
        chrome_binary_path = find_binary_path(MACOS_CHROME_PATHS)
        if chrome_binary_path:
            chrome_options.binary_location = chrome_binary_path
            print(f"   🔧 Using Chrome binary: {chrome_binary_path}")
        else:
            print("   ⚠️  Chrome not found in common macOS locations. Trying webdriver-manager...")

    elif system == "Linux":
        chrome_binary_path = find_binary_path(LINUX_CHROME_PATHS)
        if chrome_binary_path:
            chrome_options.binary_location = chrome_binary_path
            print(f"   🔧 Using Chrome binary: {chrome_binary_path}")

    # Use webdriver-manager for local development
    print("   🔧 Using webdriver-manager")
    return {"success": True, "service": Service(ChromeDriverManager().install())}


def create_webdriver() -> dict[str, Any]:
    """Create and configure Chrome WebDriver.

    Returns:
        Dict with success status and driver/error info
    """
    is_lambda = is_lambda_environment()
    chrome_options = create_chrome_options(is_lambda)

    try:
        if is_lambda:
            setup_result = setup_lambda_chrome(chrome_options)
        else:
            setup_result = setup_local_chrome(chrome_options)

        if not setup_result["success"]:
            return setup_result

        driver = webdriver.Chrome(service=setup_result["service"], options=chrome_options)

        return {"success": True, "driver": driver, "is_lambda": is_lambda}

    except Exception as chrome_error:
        print(f"   ❌ Chrome setup failed: {str(chrome_error)}")
        return _create_chrome_error_response(chrome_error, is_lambda)


def _create_chrome_error_response(error: Exception, is_lambda: bool) -> dict[str, Any]:
    """Create helpful error response for Chrome setup failures."""
    error_str = str(error)

    if is_lambda:
        return {
            "success": False,
            "error": (f"Chrome Lambda layer setup failed. Ensure Chrome Lambda layer is properly configured. Original error: {error_str}"),
        }
    elif "chrome binary" in error_str.lower():
        return {
            "success": False,
            "error": (
                f"Chrome browser not found. Please install Google Chrome from "
                f"https://www.google.com/chrome/ or run 'brew install --cask google-chrome'. "
                f"Original error: {error_str}"
            ),
        }
    else:
        return {"success": False, "error": f"WebDriver setup failed: {error_str}"}
