"""
Visual Validator

This module implements visual validation by rendering QTI XML with amp-up
and comparing it with the original PDF using GPT-5.1 for visual similarity.
"""

import base64
import json
import time
from typing import Any, Dict, Optional

from openai import OpenAI
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..prompt_builder import create_visual_comparison_prompt


def validate_visual_output(
    original_pdf_image: str,
    qti_xml: str,
    openai_api_key: str,
    output_dir: Optional[str] = None,
    amp_up_url: str = "https://www.amp-up.io/testrunner/sandbox/"
) -> Dict[str, Any]:
    """
    Validate QTI XML by rendering it with amp-up and comparing visually.
    
    Args:
        original_pdf_image: Base64 encoded original PDF image
        qti_xml: QTI XML to render and validate
        openai_api_key: OpenAI API key for visual comparison
        output_dir: Optional output directory to save screenshots
        amp_up_url: amp-up sandbox URL
        
    Returns:
        Dictionary with visual validation results
    """
    try:
        # Step 1: Render QTI XML with amp-up
        print("Rendering QTI XML with amp-up...")
        rendered_image = render_qti_with_ampup(qti_xml, amp_up_url)

        if not rendered_image:
            return {
                "success": False,
                "error": "Failed to render QTI XML with amp-up"
            }

        # Step 2: Save screenshots if output directory is provided
        screenshot_paths = {}
        if output_dir:
            import os

            # Save original PDF image
            original_path = os.path.join(output_dir, "original_pdf_screenshot.png")
            with open(original_path, "wb") as f:
                f.write(base64.b64decode(original_pdf_image))
            screenshot_paths["original_pdf"] = original_path

            # Save amp-up rendered image
            ampup_path = os.path.join(output_dir, "ampup_rendered_screenshot.png")
            with open(ampup_path, "wb") as f:
                f.write(base64.b64decode(rendered_image))
            screenshot_paths["ampup_rendered"] = ampup_path

            print(f"   💾 Saved original PDF screenshot: {original_path}")
            print(f"   💾 Saved amp-up rendered screenshot: {ampup_path}")

        # Step 3: Compare images using GPT-5.1
        print("Comparing rendered output with original PDF...")
        comparison_result = compare_images_with_llm(
            original_pdf_image,
            rendered_image,
            openai_api_key
        )

        # Add screenshot paths to the result
        if screenshot_paths:
            comparison_result["screenshot_paths"] = screenshot_paths

        return comparison_result

    except Exception as e:
        return {
            "success": False,
            "error": f"Visual validation failed: {str(e)}"
        }


def render_qti_with_ampup(qti_xml: str, amp_up_url: str) -> Optional[str]:
    """
    Render QTI XML using amp-up and capture screenshot.
    
    Args:
        qti_xml: QTI XML content to render
        amp_up_url: amp-up sandbox URL
        
    Returns:
        Base64 encoded screenshot or None if failed
    """
    driver = None
    try:
        # Setup Chrome options for headless operation
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1200,800")

        # Create WebDriver
        driver = webdriver.Chrome(options=chrome_options)

        # Navigate to amp-up sandbox
        print(f"Navigating to amp-up: {amp_up_url}")
        driver.get(amp_up_url)

        # Wait for page to load
        wait = WebDriverWait(driver, 10)

        # Look for the specific XML input textarea (as specified in the question)
        try:
            # Try to find the specific sandbox textarea
            xml_input = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "sandbox-item-xml-textarea"))
            )
        except TimeoutException:
            # Fallback to generic textarea
            try:
                xml_input = wait.until(
                    EC.presence_of_element_located((By.TAG_NAME, "textarea"))
                )
            except TimeoutException:
                # Try alternative selectors
                xml_input = driver.find_element(By.CSS_SELECTOR, "[contenteditable='true']")

        # Clear existing content and input our QTI XML
        xml_input.clear()
        xml_input.send_keys(qti_xml)

        # Look for render/preview button - try multiple common button texts
        render_button = None
        button_texts = ['Render', 'Preview', 'Run', 'Submit', 'Execute', 'Test']

        for button_text in button_texts:
            try:
                render_button = driver.find_element(By.XPATH, f"//button[contains(text(), '{button_text}')]")
                break
            except:
                continue

        if render_button:
            render_button.click()
        else:
            # Try submitting the form or pressing Enter
            try:
                xml_input.submit()
            except:
                # As last resort, try to find any button and click it
                try:
                    any_button = driver.find_element(By.TAG_NAME, "button")
                    any_button.click()
                except:
                    pass

        # Wait for rendering to complete
        time.sleep(5)  # Increased wait time for rendering

        # Look for the rendered content area (col-lg-8 as specified in guidelines)
        try:
            content_area = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "col-lg-8"))
            )
        except TimeoutException:
            # Fallback to other common content selectors
            content_selectors = [
                ".col-lg-8",
                ".question-content",
                ".item-body",
                ".qti-item-body",
                ".content",
                "#content",
                ".main-content",
                "main"
            ]

            content_area = None
            for selector in content_selectors:
                try:
                    content_area = driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue

            if not content_area:
                # Use the entire body as fallback
                content_area = driver.find_element(By.TAG_NAME, "body")

        # Take screenshot of the content area
        screenshot = content_area.screenshot_as_png

        # Convert to base64
        screenshot_base64 = base64.b64encode(screenshot).decode('utf-8')

        return screenshot_base64

    except WebDriverException as e:
        print(f"WebDriver error: {str(e)}")
        return None
    except Exception as e:
        print(f"Error rendering with amp-up: {str(e)}")
        return None
    finally:
        if driver:
            driver.quit()


def compare_images_with_llm(
    original_image: str,
    rendered_image: str,
    openai_api_key: str
) -> Dict[str, Any]:
    """
    Compare original PDF image with rendered QTI using GPT-5.1.
    
    Args:
        original_image: Base64 encoded original PDF image
        rendered_image: Base64 encoded rendered QTI image
        openai_api_key: OpenAI API key
        
    Returns:
        Dictionary with comparison results
    """
    try:
        client = OpenAI(api_key=openai_api_key)

        # Create comparison prompt using the prompt builder
        prompt = create_visual_comparison_prompt()

        # Prepare messages with both images
        messages = [
            {
                "role": "system",
                "content": "You are an expert in educational assessment and visual comparison. Your task is to compare two images of the same question - one from the original PDF and one rendered from QTI XML - and determine how accurately the QTI version represents the original."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{original_image}",
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

        # Call GPT-5.1 for comparison with high reasoning effort for accurate analysis
        response = client.chat.completions.create(
            model="gpt-5.1",
            messages=messages,
            reasoning_effort="high",
            seed=42,
        )

        response_text = response.choices[0].message.content

        # Parse the comparison result
        result = parse_comparison_response(response_text)

        return result

    except Exception as e:
        return {
            "success": False,
            "error": f"Image comparison failed: {str(e)}"
        }


def create_comparison_prompt() -> str:
    """
    DEPRECATED: Use prompt_builder.create_visual_comparison_prompt() instead.
    
    Returns:
        Comparison prompt string
    """
    return create_visual_comparison_prompt()


def parse_comparison_response(response_text: str) -> Dict[str, Any]:
    """
    Parse the comparison response from GPT-5.1.
    
    Args:
        response_text: Raw response text
        
    Returns:
        Parsed comparison result
    """
    try:
        # Extract JSON from response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1

        if json_start >= 0 and json_end > json_start:
            json_text = response_text[json_start:json_end]
            result = json.loads(json_text)

            # Validate response structure
            if not isinstance(result, dict):
                raise ValueError("Response is not a dictionary")

            # Extract key metrics
            overall_match = result.get('overall_match', False)
            similarity_score = result.get('similarity_score', 0.0)
            recommendation = result.get('recommendation', 'reject')

            return {
                "success": True,
                "overall_match": overall_match,
                "similarity_score": similarity_score,
                "content_accuracy": result.get('content_accuracy', 0.0),
                "visual_layout": result.get('visual_layout', 0.0),
                "functionality": result.get('functionality', 0.0),
                "usability": result.get('usability', 0.0),
                "issues_found": result.get('issues_found', []),
                "positive_aspects": result.get('positive_aspects', []),
                "recommendation": recommendation,
                "notes": result.get('notes', ''),
                "visual_validation_passed": overall_match and similarity_score >= 0.7
            }
        else:
            raise ValueError("No JSON found in response")

    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Failed to parse comparison response: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error parsing comparison response: {str(e)}"
        }


def setup_selenium_driver() -> Optional[webdriver.Chrome]:
    """
    Setup and return a configured Chrome WebDriver.
    
    Returns:
        WebDriver instance or None if setup fails
    """
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1200,800")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")

        driver = webdriver.Chrome(options=chrome_options)
        return driver

    except Exception as e:
        print(f"Failed to setup WebDriver: {str(e)}")
        return None


def is_selenium_available() -> bool:
    """
    Check if Selenium and Chrome are available.
    
    Returns:
        True if available, False otherwise
    """
    try:
        driver = setup_selenium_driver()
        if driver:
            driver.quit()
            return True
        return False
    except:
        return False
