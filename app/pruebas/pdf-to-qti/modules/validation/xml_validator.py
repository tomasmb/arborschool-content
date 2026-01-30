"""
XML Validator

This module validates QTI 3.0 XML against the official XSD schema
using the provided validation endpoint.
"""

import json
import os
import time  # Added for retry delay
from typing import Any, Dict, Optional

import requests


def validate_qti_xml(
    qti_xml: str,
    validation_endpoint: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validate QTI XML against the XSD schema.
    
    Args:
        qti_xml: QTI XML content to validate
        validation_endpoint: Validation endpoint URL
        
    Returns:
        Dictionary with validation results
    """
    if not validation_endpoint:
        validation_endpoint = "http://qti-validator-prod.eba-dvye2j6j.us-east-2.elasticbeanstalk.com/validate"

    max_retries = 3
    retry_delay_seconds = 2  # Wait 2 seconds between retries

    for attempt in range(max_retries):
        try:
            # Strip any XML declaration and whitespace for validation
            stripped_xml = qti_xml.strip()
            if stripped_xml.startswith('<?xml'):
                stripped_xml = stripped_xml.split('?>', 1)[1].strip()

            # Use production endpoint with schema parameter
            validation_url = f"{validation_endpoint}?schema=qti3"

            # Simple headers
            headers = {"Content-Type": "application/xml"}

            # LAMBDA WORKAROUND: Use raw HTTP instead of requests library
            if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
                import urllib.request

                xml_bytes = stripped_xml.encode('utf-8')
                req = urllib.request.Request(
                    validation_url,
                    data=xml_bytes,
                    headers={'Content-Type': 'application/xml'}
                )

                with urllib.request.urlopen(req, timeout=30) as response:
                    response_data = response.read().decode('utf-8')
                    status_code = response.status
            else:
                response = requests.post(
                    validation_url,
                    data=stripped_xml,
                    headers=headers,
                    timeout=30
                )
                response_data = response.text
                status_code = response.status_code

            # Parse response (same logic for both methods)
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
                    # Format validation errors for LLM feedback
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

                    validation_errors = "\n".join(error_messages) if error_messages else "Unknown validation error"

                    return {
                        "success": False,
                        "valid": False,
                        "validation_errors": validation_errors,
                        "errors": errors,
                        "warnings": result.get('warnings', [])
                    }
            elif status_code == 422:
                if attempt < max_retries - 1:
                    print(f"Validation returned 422, attempt {attempt + 1} of {max_retries}. Retrying in {retry_delay_seconds}s...")
                    time.sleep(retry_delay_seconds)
                    continue # Retry the loop
                else:
                    # Max retries reached for 422
                    print(f"Validation returned 422 after {max_retries} attempts. Giving up.")
                    # Fall through to the generic error handling for non-200 below

            # Handle other non-200 responses (validation failures)
            # This part is reached if status_code is not 200 and not 422 (or 422 after max retries)
            try:
                error_data = json.loads(response_data)
                errors = error_data.get('errors', [])

                # Format errors for LLM feedback
                if isinstance(errors, list):
                    error_messages = []
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

                    validation_errors = "\n".join(error_messages)
                else:
                    validation_errors = str(errors)

                return {
                    "success": False,
                    "valid": False,
                    "validation_errors": validation_errors,
                    "errors": errors,
                    "statusCode": status_code
                }
            except json.JSONDecodeError: # If response_data is not JSON
                 return {
                    "success": False,
                    "error": f"Validation service returned status {status_code}: {response_data}",
                    "statusCode": status_code # Include status code for non-JSON 422s etc.
                }

        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                print(f"Validation request timed out, attempt {attempt + 1} of {max_retries}. Retrying in {retry_delay_seconds}s...")
                time.sleep(retry_delay_seconds)
                continue
            return {
                "success": False,
                "error": "Validation request timed out after multiple retries"
            }
        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                print(f"Could not connect to validation service, attempt {attempt + 1} of {max_retries}. Retrying in {retry_delay_seconds}s...")
                time.sleep(retry_delay_seconds)
                continue
            return {
                "success": False,
                "error": "Could not connect to validation service after multiple retries"
            }
        except requests.exceptions.RequestException as e:
            # For other request exceptions, probably not worth retrying unless specific
            return {
                "success": False,
                "error": f"Validation request failed: {str(e)}"
            }
        except json.JSONDecodeError: # This catches JSON errors if the successful (status 200) response is not valid JSON
            return {
                "success": False,
                "error": "Invalid JSON response from validation service on successful request"
            }
        except Exception as e: # Catch-all for other errors within the try block
            if attempt < max_retries -1:
                print(f"An unexpected error occurred during validation (attempt {attempt + 1}/{max_retries}): {str(e)}. Retrying in {retry_delay_seconds}s...")
                time.sleep(retry_delay_seconds)
                continue
            return {
                "success": False,
                "error": f"Validation failed after multiple retries: {str(e)}"
            }

    # This part should ideally not be reached if logic is correct,
    # but as a fallback, return a generic failure.
    return {
        "success": False,
        "error": "Validation failed after all retry attempts."
    }


def validate_xml_structure(qti_xml: str) -> Dict[str, Any]:
    """
    Perform basic XML structure validation without external service.
    
    Args:
        qti_xml: QTI XML content to validate
        
    Returns:
        Dictionary with basic validation results
    """
    try:
        import xml.etree.ElementTree as ET

        # Try to parse the XML
        root = ET.fromstring(qti_xml)

        # Basic structure checks
        issues = []

        # Check for required namespace
        if 'http://www.imsglobal.org/xsd/imsqtiasi_v3p0' not in qti_xml:
            issues.append("Missing required QTI 3.0 namespace")

        # Check for required root element
        if not root.tag.endswith('qti-assessment-item'):
            issues.append("Root element should be qti-assessment-item")

        # Check for required attributes
        required_attrs = ['identifier', 'title']
        for attr in required_attrs:
            if attr not in root.attrib:
                issues.append(f"Missing required attribute: {attr}")

        # Check for required child elements
        required_children = ['qti-response-declaration', 'qti-item-body']
        for child_tag in required_children:
            if not any(child.tag.endswith(child_tag) for child in root):
                issues.append(f"Missing required child element: {child_tag}")

        if issues:
            return {
                "success": False,
                "valid": False,
                "validation_errors": "\n".join(issues),
                "errors": issues
            }
        else:
            return {
                "success": True,
                "valid": True,
                "message": "Basic XML structure is valid"
            }

    except ET.ParseError as e:
        return {
            "success": False,
            "valid": False,
            "validation_errors": f"XML parsing error: {str(e)}",
            "errors": [str(e)]
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Structure validation failed: {str(e)}"
        }


def format_validation_errors(errors: Any) -> str:
    """
    Format validation errors into a readable string.
    
    Args:
        errors: Validation errors from the service
        
    Returns:
        Formatted error string
    """
    if not errors:
        return "No specific errors provided"

    if isinstance(errors, str):
        return errors

    if isinstance(errors, list):
        formatted_errors = []
        for error in errors:
            if isinstance(error, dict):
                message = error.get('message', str(error))
                line = error.get('line')
                column = error.get('column')

                if line is not None and column is not None:
                    formatted_errors.append(f"Line {line}, Column {column}: {message}")
                else:
                    formatted_errors.append(message)
            else:
                formatted_errors.append(str(error))

        return "\n".join(formatted_errors)

    return str(errors)


def extract_validation_feedback(validation_result: Dict[str, Any]) -> str:
    """
    Extract validation feedback for use in LLM correction.
    
    Args:
        validation_result: Result from validation
        
    Returns:
        Formatted feedback string for LLM
    """
    if validation_result.get("success") and validation_result.get("valid"):
        return "XML is valid - no corrections needed"

    feedback_parts = []

    # Add main error message
    if "validation_errors" in validation_result:
        feedback_parts.append("Validation Errors:")
        feedback_parts.append(validation_result["validation_errors"])

    # Add specific errors if available
    if "errors" in validation_result:
        errors = validation_result["errors"]
        if errors:
            feedback_parts.append("\nSpecific Issues:")
            formatted_errors = format_validation_errors(errors)
            feedback_parts.append(formatted_errors)

    # Add warnings if any
    if "warnings" in validation_result:
        warnings = validation_result["warnings"]
        if warnings:
            feedback_parts.append("\nWarnings:")
            feedback_parts.append(format_validation_errors(warnings))

    # Add general guidance
    feedback_parts.append("\nPlease fix these issues and ensure the XML follows QTI 3.0 standards.")

    return "\n".join(feedback_parts)


def is_validation_available(validation_endpoint: Optional[str] = None) -> bool:
    """
    Check if the validation service is available.
    
    Args:
        validation_endpoint: Validation endpoint URL
        
    Returns:
        True if service is available, False otherwise
    """
    if not validation_endpoint:
        validation_endpoint = "http://qti-validator-prod.eba-dvye2j6j.us-east-2.elasticbeanstalk.com/validate"

    try:
        # Try a simple GET request to check if service is up
        response = requests.get(
            validation_endpoint.replace('/validate', '/health'),
            timeout=5
        )
        return response.status_code < 500
    except:
        return False
