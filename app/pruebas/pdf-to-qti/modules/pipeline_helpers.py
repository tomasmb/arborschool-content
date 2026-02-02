"""
Pipeline Helpers

Utility functions for the QTI conversion pipeline including
question ID generation, answer key loading, and debug file handling.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Optional


def generate_question_id(
    output_dir: str,
    input_pdf_path: str,
    processed_content: dict[str, Any],
) -> str:
    """
    Generate a unique question ID from output dir, PDF path, or content.

    Priority order:
    1. Output directory name (e.g., "Q14" from ".../Q14/")
    2. PDF filename (e.g., "Q14" from "Q14.pdf")
    3. Title with hash for uniqueness

    Args:
        output_dir: Output directory path
        input_pdf_path: Input PDF file path
        processed_content: Processed content dictionary

    Returns:
        Sanitized question ID suitable for S3 usage
    """
    output_path_obj = Path(output_dir)

    # Priority 1: Extract from output directory name
    if output_path_obj.name and output_path_obj.name != output_dir:
        question_id = output_path_obj.name
    # Priority 2: Extract from PDF filename
    elif input_pdf_path:
        question_id = Path(input_pdf_path).stem
    # Priority 3: Fallback to title with hash
    else:
        title = processed_content.get("title", "question")
        if title.lower() in ["question", "pregunta", ""]:
            content_str = str(processed_content.get("plain_text", ""))[:200]
            content_hash = hashlib.md5(content_str.encode()).hexdigest()[:8]
            question_id = f"question_{content_hash}"
            print(f"⚠️  Warning: Using generic title, generated unique ID: {question_id}")
        else:
            question_id = title

    # Clean for S3 usage (alphanumeric, underscore, hyphen only)
    return re.sub(r"[^a-zA-Z0-9_-]", "_", question_id)[:50]


def load_answer_key(
    output_dir: str,
    test_name: Optional[str],
    question_id: str,
) -> Optional[str]:
    """
    Load correct answer from answer key file if available.

    Searches for answer key in multiple possible locations.

    Args:
        output_dir: Output directory path
        test_name: Test name for locating answer key
        question_id: Question ID to look up in the key

    Returns:
        Correct answer letter (e.g., "A", "B") or None if not found
    """
    if not test_name:
        return None

    output_path_obj = Path(output_dir)
    possible_paths = [
        # Standard location: app/data/pruebas/procesadas/{test_name}/
        output_path_obj.parent.parent.parent / "data" / "pruebas" / "procesadas" / test_name / "respuestas_correctas.json",
        # Alternative: relative to output_dir
        output_path_obj.parent.parent / test_name / "respuestas_correctas.json",
        # Alternative: same directory as output
        output_path_obj.parent / "respuestas_correctas.json",
        # Also check in raw directory structure
        output_path_obj.parent.parent.parent / "data" / "pruebas" / "raw" / test_name / "respuestas_correctas.json",
    ]

    answer_key_path = next((p for p in possible_paths if p.exists()), None)
    if not answer_key_path:
        return None

    try:
        with open(answer_key_path, "r", encoding="utf-8") as f:
            answer_key_data = json.load(f)
        answers = answer_key_data.get("answers", {})

        # Extract question number from question_id (e.g., "Q3" -> "3")
        q_num_match = re.search(r"(\d+)", question_id or "")
        if q_num_match:
            q_num = q_num_match.group(1)
            correct_answer = answers.get(q_num)
            if correct_answer:
                print(f"✅ Found correct answer for question {q_num}: {correct_answer}")
                return correct_answer
            print(f"⚠️  No answer found for question {q_num} (key has {len(answers)} answers)")
    except Exception as e:
        print(f"⚠️  Could not load answer key from {answer_key_path}: {e}")

    return None


def save_debug_files(
    output_dir: str,
    pdf_content: dict[str, Any],
    processed_content: dict[str, Any],
) -> None:
    """
    Save extracted and processed content for debugging.

    Args:
        output_dir: Directory to save debug files
        pdf_content: Raw extracted PDF content
        processed_content: Processed content after extraction
    """
    with open(os.path.join(output_dir, "extracted_content.json"), "w") as f:
        json.dump(pdf_content, f, indent=2, default=str)
    with open(os.path.join(output_dir, "processed_content.json"), "w") as f:
        json.dump(processed_content, f, indent=2, default=str)


def save_detection_result(output_dir: str, detection_result: dict[str, Any]) -> None:
    """Save question type detection result for debugging."""
    with open(os.path.join(output_dir, "detection_result.json"), "w") as f:
        json.dump(detection_result, f, indent=2)


def save_conversion_result(output_dir: str, result: dict[str, Any]) -> None:
    """Save final conversion result."""
    with open(os.path.join(output_dir, "conversion_result.json"), "w") as f:
        json.dump(result, f, indent=2, default=str)


def build_output_files_dict(
    xml_path: Optional[str],
    output_dir: str,
    is_lambda: bool,
    question_validation_result: dict[str, Any],
) -> dict[str, Any]:
    """
    Build the output files dictionary for the result.

    Args:
        xml_path: Path to the generated XML file
        output_dir: Output directory path
        is_lambda: Whether running in AWS Lambda
        question_validation_result: Validation result with screenshot paths

    Returns:
        Dictionary of output file paths
    """
    output_files: dict[str, Any] = {"xml_path": xml_path}

    if not is_lambda:
        output_files.update(
            {
                "extracted_content": os.path.join(output_dir, "extracted_content.json"),
                "processed_content": os.path.join(output_dir, "processed_content.json"),
                "detection_result": os.path.join(output_dir, "detection_result.json"),
                "validation_result": os.path.join(output_dir, "question_validation_result.json"),
            }
        )

    output_files.update(question_validation_result.get("screenshot_paths", {}))
    return output_files
