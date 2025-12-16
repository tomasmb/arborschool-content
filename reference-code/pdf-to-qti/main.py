#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF to QTI Converter Main Module

This is the main entry point for the PDF to QTI converter application.
It converts single question PDFs into valid QTI 3.0 XML format following
a two-step process: question type detection and XML transformation.
"""

import os
import argparse
import fitz  # type: ignore
import json
import tempfile
import base64
import time
import requests
from typing import Dict, Any, Optional, Tuple
from modules.pdf_processor import extract_pdf_content
from modules.question_detector import detect_question_type
from modules.qti_transformer import transform_to_qti, fix_qti_xml_with_llm
from modules.validation import validate_qti_xml, validate_qti_question, should_proceed_with_qti
from modules.content_processing import extract_large_content, restore_large_content


def process_single_question_pdf(
    input_pdf_path: str, 
    output_dir: str,
    openai_api_key: str,
    validation_endpoint: Optional[str] = None
) -> Dict[str, Any]:
    """
    Complete pipeline: extract PDF content, detect question type, 
    transform to QTI, validate, and return results.
    
    Enhanced with comprehensive question validation using GPT-5.1
    to ensure QTI questions are complete and correctly rendered.
    
    Args:
        input_pdf_path: Path to the input PDF file
        output_dir: Directory to save output files
        openai_api_key: OpenAI API key for LLM calls
        validation_endpoint: Optional QTI validation endpoint URL
        
    Returns:
        Dictionary with processing results
    """
    if not os.path.exists(input_pdf_path):
        return {
            "success": False,
            "error": f"Input PDF not found at {input_pdf_path}"
        }
        
    # Create output directory (skip in production/Lambda)
    is_lambda = os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is not None
    if not is_lambda and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

    try:
        doc = fitz.open(input_pdf_path)
        print(f"Processing PDF: {input_pdf_path} ({doc.page_count} pages)")
        
        # Extract PDF content with AI-powered analysis
        pdf_content = extract_pdf_content(doc, openai_api_key)
        
        # Process large content  
        processed_content, extracted_content = extract_large_content(pdf_content, openai_api_key=openai_api_key)
        
        # Include AI analysis results in processed content for question detector
        if 'pages' in pdf_content:
            for page in pdf_content['pages']:
                if 'ai_analysis' in page:
                    processed_content['ai_analysis'] = page['ai_analysis']
                    break
        
        # Save extracted content for debugging (only in non-Lambda environments)
        if not is_lambda:
            with open(os.path.join(output_dir, "extracted_content.json"), "w") as f:
                json.dump(pdf_content, f, indent=2, default=str)
            with open(os.path.join(output_dir, "processed_content.json"), "w") as f:
                json.dump(processed_content, f, indent=2, default=str)
        
        # Detect question type
        print("🔍 Detecting question type...")
        detection_result = detect_question_type(processed_content, openai_api_key)
        
        if not detection_result["success"]:
            return {
                "success": False,
                "error": f"Question type detection failed: {detection_result['error']}"
            }
        
        question_type = detection_result["question_type"]
        can_represent = detection_result["can_represent"]
        
        print(f"✅ Detected question type: {question_type}")
        
        # Save detection results (only in non-Lambda environments)
        if not is_lambda:
            with open(os.path.join(output_dir, "detection_result.json"), "w") as f:
                json.dump(detection_result, f, indent=2)
        
        if not can_represent:
            return {
                "success": False,
                "error": f"Question cannot be represented in QTI 3.0: {detection_result.get('reason', 'Unknown reason')}",
                "question_type": question_type,
                "can_represent": False
            }
        
        # Transform to QTI XML
        print("🔄 Transforming to QTI XML...")
        transformation_result = transform_to_qti(processed_content, question_type, openai_api_key)
        
        if not transformation_result["success"]:
            return {
                "success": False,
                "error": f"QTI transformation failed: {transformation_result['error']}",
                "question_type": question_type
            }
        
        qti_xml = transformation_result["qti_xml"]
        
        title = transformation_result.get("title", "Untitled Question")
        description = transformation_result.get("description", "")
        
        print(f"✅ Generated QTI XML: {title}")
        
        # Save the pre-validation QTI XML for debugging (only in non-Lambda environments)
        if not is_lambda:
            pre_validation_xml_path = os.path.join(output_dir, "pre_validation_qti.xml")
            with open(pre_validation_xml_path, "w", encoding="utf-8") as f:
                f.write(qti_xml)
            print(f"📝 Saved pre-validation XML for debugging: {pre_validation_xml_path}")
        
        # Validate QTI XML BEFORE restoring images
        validation_result = validate_qti_xml(qti_xml, validation_endpoint)
        
        # Only restore large content AFTER validation passes
        if validation_result["success"]:
            qti_xml = restore_large_content(qti_xml, extracted_content)
            
            # Save QTI XML (only in non-Lambda environments)  
            xml_path = None
            if not is_lambda:
                xml_path = os.path.join(output_dir, "question.xml")
                with open(xml_path, "w", encoding="utf-8") as f:
                    f.write(qti_xml)
        
        # Final validation check - only return error if still invalid after retry attempt
        if not validation_result["success"]:
            return {
                "success": False,
                "error": f"Validation failed: {validation_result.get('validation_errors', validation_result.get('error'))}",
                "question_type": question_type
            }
        
        # Comprehensive Question Validation using GPT-5.1
        print("🔍 Performing comprehensive question validation...")
        
        # Get original PDF image for validation
        original_pdf_image = pdf_content.get("image_base64")
        
        if not original_pdf_image:
            print("❌ Cannot perform comprehensive validation: Missing base64 image for the PDF.")
            return {
                "success": False,
                "error": "Comprehensive validation failed because the PDF image could not be extracted.",
                "question_type": question_type,
                "can_represent": True,
                "validation_errors": ["Missing PDF image for validation."],
            }
        
        # ALWAYS use external validation service (hardcoded URL)
        external_validation_url = "https://klx2kb3qmf5wlb3dzqg436wysm0cwlat.lambda-url.us-east-1.on.aws/"
        
        print("🌐 Using external QTI validation service")
        validation_result = validate_with_external_service(
            qti_xml,
            original_pdf_image,
            openai_api_key,
            external_validation_url
        )
        
        # Build complete validation result
        question_validation_result = {
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
            "screenshot_paths": validation_result.get("screenshot_paths", {})
        }
        
        # Handle validation errors
        if not validation_result.get("success", False):
            error_msg = validation_result.get("error", "Validation failed")
            if "Chrome" in error_msg or "screenshot" in error_msg:
                print("❌ External validation service failed - screenshot/Chrome issue")
                return {
                    "success": False,
                    "error": "External validation service failed - screenshot capture issue",
                    "question_type": question_type,
                    "can_represent": True,
                    "validation_errors": [error_msg],
                    "question_validation": question_validation_result,
                    "validation_summary": "External validation failed - check service availability"
                }
            else:
                # Other validation errors
                question_validation_result["validation_summary"] = error_msg
        
        # Step 6: Comprehensive question validation (CRITICAL - MUST NOT SKIP)
        if validation_result.get("success", False):
            print("✅ Question validation passed - QTI is ready for use")
        else:
            print("❌ Question validation failed - QTI will not be returned")
            print(f"🔍 VALIDATION DEBUG:")
            print(f"   - success: {validation_result.get('success', 'N/A')}")
            print(f"   - validation_passed: {validation_result.get('validation_passed', 'N/A')}")
            print(f"   - overall_score: {validation_result.get('overall_score', 'N/A')}")
            print(f"   - completeness_score: {validation_result.get('completeness_score', 'N/A')}")
            print(f"   - functionality_score: {validation_result.get('functionality_score', 'N/A')}")
            print(f"   - error: {validation_result.get('error', 'N/A')}")
            print(f"   - validation_summary: {validation_result.get('validation_summary', 'N/A')}")
            print(f"   - issues_found: {validation_result.get('issues_found', [])}")
            print(f"   - missing_elements: {validation_result.get('missing_elements', [])}")
            
            return {
                "success": False,
                "error": "Question validation failed - QTI will not be returned",
                "question_type": question_type,
                "can_represent": True,
                "validation_errors": [],
                "question_validation": validation_result,
                "validation_summary": validation_result.get("validation_summary", "Validation criteria not met"),
                "validation_debug": {
                    "success": validation_result.get('success', False),
                    "validation_passed": validation_result.get('validation_passed', False),
                    "overall_score": validation_result.get('overall_score', 0),
                    "error": validation_result.get('error', 'N/A'),
                    "should_proceed_result": False
                }
            }
        
        # Only proceed if validation passed
        if not should_proceed_with_qti(validation_result):
            print("❌ Question validation criteria not met - QTI will not be returned")
            print(f"🔍 VALIDATION DEBUG:")
            print(f"   - success: {validation_result.get('success', 'N/A')}")
            print(f"   - validation_passed: {validation_result.get('validation_passed', 'N/A')}")
            print(f"   - overall_score: {validation_result.get('overall_score', 'N/A')}")
            print(f"   - completeness_score: {validation_result.get('completeness_score', 'N/A')}")
            print(f"   - functionality_score: {validation_result.get('functionality_score', 'N/A')}")
            print(f"   - error: {validation_result.get('error', 'N/A')}")
            print(f"   - validation_summary: {validation_result.get('validation_summary', 'N/A')}")
            print(f"   - issues_found: {validation_result.get('issues_found', [])}")
            print(f"   - missing_elements: {validation_result.get('missing_elements', [])}")
            
            return {
                "success": False,
                "error": "Question validation failed - QTI will not be returned",
                "question_type": question_type,
                "can_represent": True,
                "validation_errors": [],
                "question_validation": validation_result,
                "validation_summary": validation_result.get("validation_summary", "Validation criteria not met"),
                "validation_debug": {
                    "success": validation_result.get('success', False),
                    "validation_passed": validation_result.get('validation_passed', False),
                    "overall_score": validation_result.get('overall_score', 0),
                    "error": validation_result.get('error', 'N/A'),
                    "should_proceed_result": False
                }
            }
        
        # Prepare final results
        result = {
            "success": True,
            "question_type": question_type,
            "can_represent": can_represent,
            "title": title,
            "description": description,
            "qti_xml": qti_xml,
            "xml_valid": validation_result["success"],
            "validation_errors": validation_result.get("validation_errors"),
            "question_validation": question_validation_result,
            "validation_summary": question_validation_result.get("validation_summary", "Validation passed"),
            "output_files": {
                "xml_path": xml_path if validation_result["success"] else None,
                **({
                    "extracted_content": os.path.join(output_dir, "extracted_content.json"),
                    "processed_content": os.path.join(output_dir, "processed_content.json"),
                    "detection_result": os.path.join(output_dir, "detection_result.json"),
                    "validation_result": os.path.join(output_dir, "question_validation_result.json"),
                } if not is_lambda else {}),  # Only include debug files in non-Lambda environments
                **question_validation_result.get("screenshot_paths", {})  # Add screenshot paths
            }
        }
        
        # Save final results
        if not is_lambda:
            with open(os.path.join(output_dir, "conversion_result.json"), "w") as f:
                json.dump(result, f, indent=2, default=str)
        
        doc.close()
        
        if result["success"]:
            print(f"🎉 Conversion successful!")
            print(f"📄 Title: {title}")
            print(f"📊 Validation Score: {question_validation_result.get('overall_score', 'N/A')}")
        else:
            print(f"❌ Conversion failed: {result.get('validation_errors', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


def validate_with_external_service(
    qti_xml: str,
    original_pdf_image: str, 
    openai_api_key: str,
    validation_service_url: str,
    max_retries: int = 3,
    backoff_factor: int = 2
) -> Dict[str, Any]:
    """
    Validate QTI using external Node.js validation service with retry mechanism.
    
    Args:
        qti_xml: QTI XML content to validate
        original_pdf_image: Base64 encoded original PDF image
        openai_api_key: OpenAI API key
        validation_service_url: URL of external validation service
        max_retries: Maximum number of retries for 5xx errors
        backoff_factor: Factor to determine sleep time between retries
        
    Returns:
        Dictionary with validation results
    """
    retries = 0
    sleep_time = 1  # Initial sleep time in seconds
    
    while retries < max_retries:
        try:
            
            print(f"🌐 Calling external validation service: {validation_service_url}")
            print(f"📄 QTI XML length: {len(qti_xml)} characters")
            print(f"🖼️  PDF image length: {len(original_pdf_image)} characters")
            
            payload = {
                "qti_xml": qti_xml,
                "original_pdf_image": original_pdf_image,
                "openai_api_key": openai_api_key
            }
            
            print("📡 Sending validation request...")
            response = requests.post(
                validation_service_url,
                json=payload,
                timeout=120  # Increased to 120 seconds to match Lambda timeout
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
            
            if result.get('success'):
                print("✅ External validation service completed successfully")
                print(f"   - validation_passed: {result.get('validation_passed', 'N/A')}")
                print(f"   - overall_score: {result.get('overall_score', 'N/A')}")
                return result
            else:
                print(f"❌ External validation service failed: {result.get('error')}")
                return {
                    "success": False,
                    "validation_passed": False,
                    "overall_score": 0,
                    "error": result.get('error', 'External validation failed'),
                    "validation_summary": "External validation failed",
                    "screenshot_paths": {}
                }
                
        except requests.exceptions.Timeout:
            retries += 1
            if retries < max_retries:
                print(f"❌ Request timed out. Retrying in {sleep_time}s... ({retries}/{max_retries})")
                time.sleep(sleep_time)
                sleep_time *= backoff_factor
                continue
            else:
                print(f"❌ Request timed out. Max retries reached.")
                return {
                    "success": False,
                    "validation_passed": False,
                    "overall_score": 0,
                    "error": "External validation service timeout after multiple retries",
                    "validation_summary": "External validation service timed out",
                    "screenshot_paths": {}
                }

        except requests.exceptions.ConnectionError as e:
            retries += 1
            if retries < max_retries:
                print(f"❌ Connection error: {e}. Retrying in {sleep_time}s... ({retries}/{max_retries})")
                time.sleep(sleep_time)
                sleep_time *= backoff_factor
                continue
            else:
                print(f"❌ Connection error. Max retries reached.")
                return {
                    "success": False,
                    "validation_passed": False,
                    "overall_score": 0,
                    "error": "External validation service connection error after multiple retries",
                    "validation_summary": "External validation service unavailable",
                    "screenshot_paths": {}
                }
                
        except Exception as e:
            print(f"❌ Failed to call external validation service: {str(e)}")
            return {
                "success": False,
                "validation_passed": False,
                "overall_score": 0,
                "error": f"External validation service error: {str(e)}",
                "validation_summary": "External validation service unavailable",
                "screenshot_paths": {}
            }
            
    # This part should be unreachable if loop logic is correct, but as a fallback:
    return {
        "success": False,
        "validation_passed": False,
        "overall_score": 0,
        "error": "Max retries reached for external validation service.",
        "validation_summary": "External validation service failed after multiple retries.",
        "screenshot_paths": {}
    }


def main():
    """Main entry point for the PDF to QTI converter application."""
    parser = argparse.ArgumentParser(
        description="Converts a single question PDF into QTI 3.0 XML format."
    )
    parser.add_argument("input_pdf", help="Path to the input PDF file.")
    parser.add_argument("output_dir", help="Directory to save the output results.")
    parser.add_argument("--openai-api-key", required=True, 
                       help="OpenAI API key for LLM processing.")
    parser.add_argument("--validation-endpoint", 
                       default="http://qti-validator-prod.eba-dvye2j6j.us-east-2.elasticbeanstalk.com/validate",
                       help="QTI validation endpoint URL.")
    parser.add_argument("--clean", action="store_true", 
                       help="Clean the output directory before processing.")

    args = parser.parse_args()
    
    # Clean output directory if requested
    if args.clean and os.path.exists(args.output_dir):
        print(f"🧹 Cleaning output directory: {args.output_dir}")
        import shutil
        shutil.rmtree(args.output_dir)

    print("🚀 Starting PDF to QTI Conversion...")
    result = process_single_question_pdf(
        args.input_pdf, 
        args.output_dir,
        args.openai_api_key,
        args.validation_endpoint
    )
    
    if result["success"]:
        print("✅ PDF to QTI Conversion finished successfully.")
        exit(0)
    else:
        print(f"❌ PDF to QTI Conversion failed: {result.get('error', 'Unknown error')}")
        exit(1)


if __name__ == "__main__":
    main() 