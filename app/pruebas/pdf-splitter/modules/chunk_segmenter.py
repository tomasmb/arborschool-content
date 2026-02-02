"""
PDF Question Segmentation using Gemini or OpenAI

Uses Gemini Preview 3 by default (with PDF converted to images),
with fallback to OpenAI's direct PDF upload if Gemini unavailable.

This module serves as the main entry point and orchestrator, delegating to:
- chunk_segmenter_prompts.py: Schema and prompt constants
- chunk_segmenter_validation.py: Post-segmentation validation and statistics
"""

from __future__ import annotations

import json
import os
from typing import Any

# Try to import Gemini SDK
try:
    from google import genai

    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None  # type: ignore

# Try to import OpenAI SDK
try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None  # type: ignore

# Try to import PyMuPDF for PDF to image conversion
try:
    import fitz  # PyMuPDF  # noqa: F401

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

# Import from split modules
from app.pruebas.pdf_splitter.modules.chunk_segmenter_prompts import (
    SEGMENT_PROMPT,
    SEGMENT_SCHEMA,
)
from app.pruebas.pdf_splitter.modules.chunk_segmenter_validation import (
    get_question_statistics,
    validate_coordinates,
    validate_segmentation_results,
)

# Clients will be initialized lazily
gemini_client = None
openai_client = None


def get_gemini_client():
    """Get or initialize Gemini client with API key from environment."""
    global gemini_client
    if gemini_client is None:
        if not GEMINI_AVAILABLE:
            raise ImportError("Gemini SDK not available. Install with: pip install google-genai")
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        gemini_client = genai.Client(api_key=api_key)
    return gemini_client


def get_openai_client():
    """Get or initialize OpenAI client with API key from environment."""
    global openai_client
    if openai_client is None:
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI SDK not available. Install with: pip install openai")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        openai_client = OpenAI(api_key=api_key)
    return openai_client


def segment_pdf_document(pdf_path: str) -> dict[str, Any]:
    """
    Segment PDF using OpenAI's direct PDF upload feature.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Dictionary containing questions and references with metadata
    """
    try:
        print(f"Processing PDF: {pdf_path}")

        # Get OpenAI client (lazy initialization)
        client = get_openai_client()

        # Upload PDF file to OpenAI
        with open(pdf_path, "rb") as pdf_file:
            file_response = client.files.create(file=pdf_file, purpose="user_data")

        print(f"PDF uploaded with ID: {file_response.id}")

        # Process PDF with direct file input and chain-of-thought
        completion = client.chat.completions.create(
            model="o4-mini-2025-04-16",
            messages=[
                {"role": "system", "content": SEGMENT_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "file", "file": {"file_id": file_response.id}},
                        {"type": "text", "text": "Please segment this PDF into question and reference segments as instructed."},
                    ],
                },
            ],
            response_format={"type": "json_schema", "json_schema": {"name": "pdf_segmentation", "schema": SEGMENT_SCHEMA, "strict": True}},
            seed=42,
        )

        # Parse response
        response_content = completion.choices[0].message.content
        result = _parse_response(response_content, pdf_path)

        # Add metadata
        result["metadata"] = {
            "pdf_path": pdf_path,
            "file_id": file_response.id,
            "processing_method": "direct_pdf_upload",
            "model_used": "o4-mini-2025-04-16",
            "total_questions": len(result.get("questions", [])),
            "total_multi_question_references": len(result.get("multi_question_references", [])),
            "total_unrelated_content_segments": len(result.get("unrelated_content_segments", [])),
        }

        _print_summary(result)
        _cleanup_uploaded_file(client, file_response.id)

        return result

    except Exception as e:
        print(f"❌ Error processing PDF: {str(e)}")
        raise


def _parse_response(response_content: Any, pdf_path: str) -> dict[str, Any]:
    """
    Parse the API response into a dictionary.

    Args:
        response_content: Raw response from the API
        pdf_path: Path to PDF (for debug output location)

    Returns:
        Parsed dictionary
    """
    if isinstance(response_content, dict):
        return response_content

    try:
        return json.loads(response_content)
    except json.JSONDecodeError as e:
        # Persist raw response for debugging, then fail loud
        debug_path = os.path.join(os.path.dirname(pdf_path), "debug_raw_response.json")
        try:
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(response_content)
            print(f"⚠️  Saved invalid JSON to {debug_path}")
        except Exception as write_err:
            print(f"⚠️  Could not save raw response for inspection: {write_err}")

        raise ValueError(f"OpenAI returned non-parsable JSON (error: {e}). Raw response has been written to debug_raw_response.json for inspection.")


def _print_summary(result: dict[str, Any]) -> None:
    """Print segmentation summary."""
    print("✅ Segmentation complete:")
    print(f"   Questions found: {result['metadata']['total_questions']}")
    print(f"   References found: {result['metadata']['total_multi_question_references']}")
    print(f"   Unrelated content segments found: {result['metadata']['total_unrelated_content_segments']}")


def _cleanup_uploaded_file(client: Any, file_id: str) -> None:
    """Clean up uploaded file from OpenAI."""
    try:
        client.files.delete(file_id)
        print(f"✓ Cleaned up uploaded file: {file_id}")
    except Exception as e:
        print(f"⚠️  Could not delete uploaded file: {e}")


def segment_pdf_with_llm(pdf_path: str, output_file: str | None = None) -> dict[str, Any]:
    """
    Main function to segment PDF and optionally save results.

    Args:
        pdf_path: Path to input PDF file
        output_file: Optional path to save JSON results

    Returns:
        Segmentation results dictionary
    """
    # Process the PDF
    results = segment_pdf_document(pdf_path)

    # Run post-segmentation validation
    validate_segmentation_results(results, pdf_path)

    # Save results if output file specified
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"📄 Results saved to: {output_file}")

    return results


# =============================================================================
# Backward-compatible exports
# =============================================================================

__all__ = [
    # Constants (re-exported from chunk_segmenter_prompts)
    "SEGMENT_SCHEMA",
    "SEGMENT_PROMPT",
    # Client availability flags
    "GEMINI_AVAILABLE",
    "OPENAI_AVAILABLE",
    "PYMUPDF_AVAILABLE",
    # Client getters
    "get_gemini_client",
    "get_openai_client",
    # Main functions
    "segment_pdf_document",
    "segment_pdf_with_llm",
    # Re-exported from chunk_segmenter_validation
    "validate_coordinates",
    "get_question_statistics",
]
