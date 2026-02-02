#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF to QTI Converter Main Module

This is the main entry point for the PDF to QTI converter application.
It converts single question PDFs into valid QTI 3.0 XML format following
a two-step process: question type detection and XML transformation.
"""

from __future__ import annotations

import argparse
import os
from typing import Any, Optional

import fitz  # type: ignore
from modules.content_processing import extract_large_content
from modules.external_validation import (
    build_validation_result_dict,
    is_validation_error_recoverable,
    print_validation_debug,
    validate_with_external_service,
)
from modules.pdf_processor import extract_pdf_content
from modules.pipeline_cache import (
    check_existing_xml,
    extract_test_name_from_path,
    try_auto_regenerate_on_error,
    try_regenerate_from_processed,
)
from modules.pipeline_helpers import (
    build_output_files_dict,
    generate_question_id,
    load_answer_key,
    save_conversion_result,
    save_debug_files,
    save_detection_result,
)
from modules.pipeline_s3 import (
    initialize_s3_mapping_from_xml,
    post_validation_s3_processing,
)
from modules.qti_transformer import transform_to_qti
from modules.question_detector import detect_question_type
from modules.validation import should_proceed_with_qti, validate_qti_xml


def process_single_question_pdf(
    input_pdf_path: str,
    output_dir: str,
    openai_api_key: Optional[str] = None,
    validation_endpoint: Optional[str] = None,
    paes_mode: bool = False,
    skip_if_exists: bool = True,
) -> dict[str, Any]:
    """
    Complete pipeline: extract PDF content, detect question type,
    transform to QTI, validate, and return results.

    Uses Gemini by default (from GEMINI_API_KEY env var),
    with automatic fallback to OpenAI if Gemini fails.

    Args:
        input_pdf_path: Path to the input PDF file
        output_dir: Directory to save output files
        openai_api_key: Optional API key (uses env vars if None)
        validation_endpoint: Optional QTI validation endpoint URL
        paes_mode: If True, optimizes for PAES format
        skip_if_exists: If True, skip processing if valid XML already exists

    Returns:
        Dictionary with processing results
    """
    if not os.path.exists(input_pdf_path):
        return {"success": False, "error": f"Input PDF not found at {input_pdf_path}"}

    is_lambda = os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None

    # Create output directory (skip in Lambda)
    if not is_lambda and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

    # Check cache and try to skip processing
    if skip_if_exists and not is_lambda:
        cached_result = check_existing_xml(output_dir, validation_endpoint)
        if cached_result:
            return cached_result

        api_key = _get_api_key(openai_api_key)
        if api_key:
            test_name = extract_test_name_from_path(output_dir)
            regen_result = try_regenerate_from_processed(output_dir, api_key, paes_mode, test_name)
            if regen_result:
                return regen_result

    try:
        return _process_pdf_core(
            input_pdf_path,
            output_dir,
            openai_api_key,
            validation_endpoint,
            paes_mode,
            is_lambda,
        )
    except Exception as e:
        return _handle_processing_error(e, output_dir, openai_api_key, paes_mode, is_lambda)


def _get_api_key(openai_api_key: Optional[str] = None) -> Optional[str]:
    """Get API key from parameter or environment variables."""
    return openai_api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")


def _process_pdf_core(
    input_pdf_path: str,
    output_dir: str,
    openai_api_key: Optional[str],
    validation_endpoint: Optional[str],
    paes_mode: bool,
    is_lambda: bool,
) -> dict[str, Any]:
    """Core PDF processing logic."""
    doc = fitz.open(input_pdf_path)
    print(f"Processing PDF: {input_pdf_path} ({doc.page_count} pages)")

    api_key = _get_api_key(openai_api_key)
    if not api_key:
        return {
            "success": False,
            "error": "No API key. Set GEMINI_API_KEY or OPENAI_API_KEY in environment",
        }

    # Step 1: Extract PDF content
    pdf_content = extract_pdf_content(doc, api_key)
    processed_content, extracted_content = extract_large_content(pdf_content, openai_api_key=api_key)

    # Include AI analysis in processed content
    if "pages" in pdf_content:
        for page in pdf_content["pages"]:
            if "ai_analysis" in page:
                processed_content["ai_analysis"] = page["ai_analysis"]
                break

    if not is_lambda:
        save_debug_files(output_dir, pdf_content, processed_content)

    # Step 2: Detect question type
    detection_result, question_type, can_represent = _detect_question_type(processed_content, api_key, paes_mode, output_dir, is_lambda)

    if not can_represent:
        return {
            "success": False,
            "error": f"Cannot represent in QTI 3.0: {detection_result.get('reason', 'Unknown')}",
            "question_type": question_type,
            "can_represent": False,
        }

    # Step 3: Prepare transformation
    question_id = generate_question_id(output_dir, input_pdf_path, processed_content)
    test_name = extract_test_name_from_path(output_dir) or extract_test_name_from_path(input_pdf_path)

    if test_name:
        print(f"📁 Test name: {test_name}, 📦 Images → S3: images/{test_name}/")

    correct_answer = load_answer_key(output_dir, test_name, question_id)

    # Step 4: Transform to QTI
    print("🔄 Transforming to QTI XML...")
    transformation_result = transform_to_qti(
        processed_content,
        question_type,
        api_key,
        question_id=question_id,
        use_s3=True,
        paes_mode=paes_mode,
        test_name=test_name,
        correct_answer=correct_answer,
    )

    if not transformation_result["success"]:
        return {
            "success": False,
            "error": f"QTI transformation failed: {transformation_result['error']}",
            "question_type": question_type,
        }

    qti_xml = transformation_result["qti_xml"]
    title = transformation_result.get("title", "Untitled Question")
    description = transformation_result.get("description", "")
    print(f"✅ Generated QTI XML: {title}")

    if not is_lambda:
        initialize_s3_mapping_from_xml(qti_xml, output_dir, question_id)
        _save_pre_validation_xml(output_dir, qti_xml)

    # Step 5: Initial validation
    validation_result = validate_qti_xml(qti_xml, validation_endpoint)

    # Step 6: Post-validation S3 processing
    if validation_result["success"]:
        qti_xml = post_validation_s3_processing(
            qti_xml,
            extracted_content,
            output_dir,
            question_id,
            test_name,
            is_lambda,
        )

    if not validation_result["success"]:
        return {
            "success": False,
            "error": f"Validation failed: {validation_result.get('validation_errors', validation_result.get('error'))}",
            "question_type": question_type,
        }

    # Step 7: Comprehensive validation
    return _run_comprehensive_validation(
        qti_xml,
        pdf_content,
        api_key,
        question_type,
        can_represent,
        title,
        description,
        validation_result,
        output_dir,
        is_lambda,
        doc,
    )


def _detect_question_type(
    processed_content: dict[str, Any],
    api_key: str,
    paes_mode: bool,
    output_dir: str,
    is_lambda: bool,
) -> tuple[dict[str, Any], str, bool]:
    """Detect question type or use PAES mode defaults."""
    if paes_mode:
        print("⚡ PAES mode: Skipping type detection (always choice)")
        from modules.paes_optimizer import get_paes_question_type

        return get_paes_question_type(), "choice", True

    print("🔍 Detecting question type...")
    detection_result = detect_question_type(processed_content, api_key)

    if not is_lambda:
        save_detection_result(output_dir, detection_result)

    if not detection_result["success"]:
        return detection_result, "unknown", False

    question_type = detection_result["question_type"]
    print(f"✅ Detected question type: {question_type}")
    return detection_result, question_type, detection_result["can_represent"]


def _save_pre_validation_xml(output_dir: str, qti_xml: str) -> None:
    """Save pre-validation XML for debugging."""
    path = os.path.join(output_dir, "pre_validation_qti.xml")
    with open(path, "w", encoding="utf-8") as f:
        f.write(qti_xml)
    print(f"📝 Saved pre-validation XML: {path}")


def _run_comprehensive_validation(
    qti_xml: str,
    pdf_content: dict[str, Any],
    api_key: str,
    question_type: str,
    can_represent: bool,
    title: str,
    description: str,
    initial_validation: dict[str, Any],
    output_dir: str,
    is_lambda: bool,
    doc: Any,
) -> dict[str, Any]:
    """Run comprehensive validation with external service."""
    print("🔍 Performing comprehensive question validation...")

    original_pdf_image = pdf_content.get("image_base64")
    if not original_pdf_image:
        print("❌ Cannot validate: Missing PDF image")
        return {
            "success": False,
            "error": "Validation failed: PDF image could not be extracted",
            "question_type": question_type,
            "can_represent": True,
        }

    print("🌐 Using external QTI validation service")
    validation_result = validate_with_external_service(qti_xml, original_pdf_image, api_key)
    question_validation_result = build_validation_result_dict(validation_result)

    error_result = _check_validation_passes(validation_result, question_type)
    if error_result:
        return error_result

    if validation_result.get("success") and validation_result.get("validation_passed"):
        print("✅ Question validation passed - QTI is ready for use")

    return _build_final_result(
        qti_xml,
        question_type,
        can_represent,
        title,
        description,
        initial_validation,
        question_validation_result,
        output_dir,
        is_lambda,
        doc,
    )


def _check_validation_passes(
    validation_result: dict[str, Any],
    question_type: str,
) -> Optional[dict[str, Any]]:
    """Check if validation passes and return error dict if not."""
    xml_valid = validation_result.get("valid", False)
    overall_score = validation_result.get("overall_score", 0)
    error_msg = validation_result.get("error", "")

    is_recoverable = is_validation_error_recoverable(error_msg)
    should_proceed = should_proceed_with_qti(validation_result)
    can_proceed = should_proceed or (xml_valid and (is_recoverable or overall_score >= 0.5))

    if can_proceed:
        if xml_valid and (is_recoverable or overall_score >= 0.7):
            print("⚠️  Validation issues, but XML valid - proceeding")
        return None

    print("❌ Question validation failed")
    print_validation_debug(validation_result)
    return {
        "success": False,
        "error": "Question validation failed",
        "question_type": question_type,
        "can_represent": True,
        "question_validation": validation_result,
    }


def _build_final_result(
    qti_xml: str,
    question_type: str,
    can_represent: bool,
    title: str,
    description: str,
    initial_validation: dict[str, Any],
    question_validation_result: dict[str, Any],
    output_dir: str,
    is_lambda: bool,
    doc: Any,
) -> dict[str, Any]:
    """Build the final result dictionary."""
    xml_path = os.path.join(output_dir, "question.xml") if not is_lambda else None

    result = {
        "success": True,
        "question_type": question_type,
        "can_represent": can_represent,
        "title": title,
        "description": description,
        "qti_xml": qti_xml,
        "xml_valid": initial_validation["success"],
        "validation_errors": initial_validation.get("validation_errors"),
        "question_validation": question_validation_result,
        "validation_summary": question_validation_result.get("validation_summary", "Passed"),
        "output_files": build_output_files_dict(xml_path, output_dir, is_lambda, question_validation_result),
    }

    if not is_lambda:
        save_conversion_result(output_dir, result)

    doc.close()

    if result["success"]:
        print("🎉 Conversion successful!")
        print(f"📄 Title: {title}")
        print(f"📊 Score: {question_validation_result.get('overall_score', 'N/A')}")

    return result


def _handle_processing_error(
    error: Exception,
    output_dir: str,
    openai_api_key: Optional[str],
    paes_mode: bool,
    is_lambda: bool,
) -> dict[str, Any]:
    """Handle processing errors with auto-recovery attempt."""
    error_str = str(error)
    print(f"❌ Error processing PDF: {error_str}")

    processed_json_path = os.path.join(output_dir, "processed_content.json")
    has_processed = os.path.exists(processed_json_path)

    if has_processed and not is_lambda:
        api_key = _get_api_key(openai_api_key)
        if api_key:
            test_name = extract_test_name_from_path(output_dir)
            regen_result = try_auto_regenerate_on_error(output_dir, api_key, error_str, paes_mode, test_name)
            if regen_result:
                return regen_result

    return {"success": False, "error": error_str}


def main() -> None:
    """Main entry point for the PDF to QTI converter application."""
    parser = argparse.ArgumentParser(description="Converts a single question PDF into QTI 3.0 XML format.")
    parser.add_argument("input_pdf", help="Path to the input PDF file.")
    parser.add_argument("output_dir", help="Directory to save the output results.")
    parser.add_argument("--openai-api-key", help="API key (uses env vars by default).")
    parser.add_argument(
        "--validation-endpoint",
        default="http://qti-validator-prod.eba-dvye2j6j.us-east-2.elasticbeanstalk.com/validate",
        help="QTI validation endpoint URL.",
    )
    parser.add_argument("--paes-mode", action="store_true", help="Optimize for PAES format.")
    parser.add_argument("--clean", action="store_true", help="Clean output directory first.")

    args = parser.parse_args()

    if args.clean and os.path.exists(args.output_dir):
        print(f"🧹 Cleaning: {args.output_dir}")
        import shutil

        shutil.rmtree(args.output_dir)

    print("🚀 Starting PDF to QTI Conversion...")
    if args.paes_mode:
        print("⚡ PAES mode: choice questions, math optimization, full validation")

    result = process_single_question_pdf(
        args.input_pdf,
        args.output_dir,
        args.openai_api_key,
        args.validation_endpoint,
        paes_mode=args.paes_mode,
    )

    if result["success"]:
        print("✅ Conversion finished successfully.")
        exit(0)
    else:
        print(f"❌ Conversion failed: {result.get('error', 'Unknown error')}")
        exit(1)


if __name__ == "__main__":
    main()
