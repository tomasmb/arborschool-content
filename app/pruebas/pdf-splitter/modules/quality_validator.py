"""
AI-Powered Quality Validator Module

This module uses an LLM to perform a semantic quality check on a generated question PDF.
"""

import base64
import json
import os
import random
import time
from typing import Tuple

import fitz  # PyMuPDF
from openai import OpenAI

# OpenAI client will be initialized lazily
client = None


def get_openai_client() -> OpenAI:
    """Get or initialize OpenAI client with API key from environment."""
    global client
    if client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        client = OpenAI(api_key=api_key)
    return client


# JSON Schema for the quality validation response
VALIDATION_SCHEMA = {
    "type": "object",
    "properties": {
        "is_complete_and_answerable": {"type": "boolean", "description": "Is the question complete and answerable with the provided content?"},
        "reason": {"type": "string", "description": "A brief explanation for the decision, especially if false."},
    },
    "required": ["is_complete_and_answerable", "reason"],
    "additionalProperties": False,
}

# System prompt for the quality check AI
QUALITY_CHECK_PROMPT = """
You are an expert exam proctor. Your task is to perform a quality check on the
provided PDF file. The PDF should contain a single, complete, and self-contained
test question.

Questions will usually have a test question number, don't confuse this number with
question parts. So for example, if you see "2." by itself, that is the question
number, not a question part.

IMPORTANT: Actively examine any visual content (tables, diagrams, images, charts)
in the PDF to verify they contain the necessary information referenced by the question.

Analyze the PDF and determine if it meets the following criteria:
1.  **Completeness**: The question prompt, all its parts (e.g., a, b, c), and all
    answer choices (if any) must be fully visible and not cut off.
2.  **Self-Contained**: If the question refers to any external content (like a
    passage, source, document, figure, or table), that content MUST be included
    in the PDF.

Note: Some questions may reference external content like foundational documents that
students should have read before the test. In this case, the question is still
complete and answerable, even if the external content is not included in the PDF.

Note 2: When a question references visual content (like bar graphs, charts, diagrams,
or images), consider the question complete and answerable if ANY visual content is
present in the PDF, even if it's not perfectly clear or detailed. The presence of
visual elements should be interpreted generously - as long as there's some visual
content that could reasonably correspond to what the question references, the
question should pass validation.
    - For example a visual representation of "Should Government Officials Compromise
      or Stick to their Principles?" with percentages can be a bar graph for
      question purposes.

Note 3: If you see references to other questions that are not contained in the PDF,
you can just ignore that. Sometimes references are used across questions, so that
is why you could have a reference to a question that is not in this PDF.

Respond with a JSON object that strictly adheres to the provided schema.
- If the PDF contains a complete and answerable question with all its necessary
  references, set `is_complete_and_answerable` to `true`.
- If the question is incomplete, cut off, or is missing a reference it needs to be
  answered, set `is_complete_and_answerable` to `false` and provide a brief reason.
  For example: "The question prompt is missing, only the reference passage is present."
  or "The question refers to Document 2, but it is not included in the PDF."
"""


def validate_question_quality(pdf_path: str, max_retries: int = 3) -> Tuple[bool, str]:
    """
    Uses an AI to validate the quality and completeness of a generated question PDF.

    Args:
        pdf_path: The path to the question PDF to validate.
        max_retries: Maximum number of retry attempts for network/API errors.

    Returns:
        A tuple containing:
        - bool: True if the question is valid, False otherwise.
        - str: The reason for the validation decision.
    """
    print(f"🔬 Performing AI quality validation on: {os.path.basename(pdf_path)}")

    # Convert PDF to image for better vision analysis (do this once)
    doc = fitz.open(pdf_path)

    # Convert all pages to images and combine them
    images_base64 = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        # Convert to image with high DPI for better quality
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scaling for better resolution
        img_data = pix.tobytes("png")
        img_base64 = base64.b64encode(img_data).decode("utf-8")
        images_base64.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}})

    doc.close()

    # Prepare message content with images
    message_content = [{"type": "text", "text": "Please validate this question. Each image represents one page of the question PDF."}]
    message_content.extend(images_base64)

    # Retry logic for network/API errors
    for attempt in range(max_retries):
        try:
            openai_client = get_openai_client()

            # Call the chat completion API with the images
            completion = openai_client.chat.completions.create(
                model="o4-mini-2025-04-16",
                messages=[{"role": "system", "content": QUALITY_CHECK_PROMPT}, {"role": "user", "content": message_content}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "question_quality_validation", "schema": VALIDATION_SCHEMA, "strict": True},
                },
                seed=42,  # Deterministic output
            )

            # Parse the response
            response_content = completion.choices[0].message.content
            result = json.loads(response_content)

            is_valid = result.get("is_complete_and_answerable", False)
            reason = result.get("reason", "No reason provided.")

            if is_valid:
                print(f"👍 Quality Check PASSED for: {os.path.basename(pdf_path)}")
            else:
                print(f"👎 Quality Check FAILED for: {os.path.basename(pdf_path)}. Reason: {reason}")

            return is_valid, reason

        except Exception as e:
            error_str = str(e)
            is_retryable = any(
                error_type in error_str.lower()
                for error_type in [
                    "502",
                    "503",
                    "504",
                    "500",  # Server errors
                    "bad gateway",
                    "service unavailable",
                    "gateway timeout",
                    "internal server error",
                    "connection",
                    "timeout",
                    "network",
                    "rate limit",
                    "too many requests",
                ]
            )

            if is_retryable and attempt < max_retries - 1:
                # Exponential backoff with jitter
                delay = min(60, (2**attempt) + random.uniform(0, 1))
                print(f"🔄 Retryable error (attempt {attempt + 1}/{max_retries}): {error_str}")
                print(f"⏳ Retrying in {delay:.1f} seconds...")
                time.sleep(delay)
                continue
            else:
                # Non-retryable error or max retries reached
                error_message = f"An unexpected error occurred during AI quality validation: {error_str}"
                print(f"❌ {error_message}")
                return False, error_message

    # This should never be reached, but just in case
    return False, "Max retries exceeded"
