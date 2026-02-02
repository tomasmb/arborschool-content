"""
Question Type Detector

This module implements step 1 of the conversion process:
Using the AI content analysis results to determine if the question
can be represented in QTI 3.0 format, and if so, what type.

Following converter guidelines: leverages AI analysis from pdf_processor
instead of redundant LLM calls.
"""

import json
from typing import Any, Dict

# Use the shared LLM helper to avoid code duplication
from .ai_processing import chat_completion
from .content_processing import extract_large_content
from .content_processing.content_processor import clean_pdf_content_for_llm
from .prompt_builder import create_detection_prompt

# Supported QTI 3.0 question types - EXACT MATCH from the working HTML transformer
SUPPORTED_QTI_TYPES = [
    'choice',
    'match',
    'text-entry',
    'hotspot',
    'extended-text',
    'hot-text',
    'gap-match',
    'order',
    'graphic-gap-match',
    'inline-choice',
    'select-point',
    'media-interaction',
    'composite'  # Multi-part questions with different interaction types
]


def detect_question_type(pdf_content: Dict[str, Any], openai_api_key: str) -> Dict[str, Any]:
    """
    Detect the question type from PDF content, leveraging AI analysis results.

    Following converter guidelines: use AI analysis from pdf_processor if available,
    otherwise fall back to direct analysis.

    Args:
        pdf_content: Extracted PDF content with AI analysis results
        openai_api_key: OpenAI API key

    Returns:
        Dictionary with detection results
    """
    try:
        # Step 1: Check if AI analysis is already available from pdf_processor
        ai_analysis = extract_ai_analysis_from_content(pdf_content)

        if ai_analysis and ai_analysis.get("success", False):
            print("🧠 Using AI analysis results from pdf_processor")
            return build_detection_result_from_ai_analysis(ai_analysis)

        # Step 2: Fallback to direct analysis if no AI results available
        print("🧠 AI analysis not available, performing direct question type detection")
        return perform_direct_question_detection(pdf_content, openai_api_key)

    except Exception as e:
        return {
            "success": False,
            "error": f"Question type detection failed: {str(e)}"
        }


def extract_ai_analysis_from_content(pdf_content: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract AI analysis results from PDF content structure.

    The new pdf_processor includes AI analysis in the page-level data.
    """
    # Look for AI analysis in pages
    pages = pdf_content.get("pages", [])

    for page in pages:
        ai_analysis = page.get("ai_analysis", {})
        if ai_analysis and ai_analysis.get("success", False):
            return ai_analysis

    # Also check at the top level
    return pdf_content.get("ai_analysis", {})


def build_detection_result_from_ai_analysis(ai_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build question detection result from AI content analysis.

    Following converter guidelines: leverage existing AI analysis instead of
    redundant LLM calls.
    """
    compatibility = ai_analysis.get("compatibility", {})

    can_represent = compatibility.get("can_represent", False)
    question_type = compatibility.get("question_type")
    confidence = compatibility.get("confidence", 0.0)
    reasoning = compatibility.get("reasoning", "")

    # Validate question type
    if can_represent and question_type not in SUPPORTED_QTI_TYPES:
        return {
            "success": False,
            "error": f"Invalid question type from AI analysis: {question_type}. Must be one of: {SUPPORTED_QTI_TYPES}"
        }

    return {
        "success": True,
        "can_represent": can_represent,
        "question_type": question_type,
        "confidence": confidence,
        "reason": reasoning,
        "key_elements": [],  # Could extract from AI analysis if needed
        "potential_issues": [],  # Could extract from AI analysis if needed
        "source": "ai_content_analysis"  # Indicate this came from AI analysis
    }


def perform_direct_question_detection(pdf_content: Dict[str, Any], openai_api_key: str) -> Dict[str, Any]:
    """
    Perform direct question type detection as fallback.

    This is the original logic, used when AI analysis is not available.
    """
    try:
        # Clean and prepare content for LLM processing
        cleaned_content = clean_pdf_content_for_llm(pdf_content)

        # Extract large content to avoid token limits
        processed_content, extracted_content = extract_large_content(cleaned_content, 'D')

        # Create the sophisticated detection prompt
        prompt = create_detection_prompt(processed_content)

        # Prepare messages for GPT-5.1
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert in educational assessment and QTI 3.0 standards. "
                    "Your task is to analyze PDF question content and determine if it can "
                    "be accurately represented using standard QTI 3.0 interaction types. "
                    "You must respond with valid JSON format only."
                )
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]

        # Add image if available and not extracted as placeholder
        if processed_content.get('image_base64') and not processed_content['image_base64'].startswith('CONTENT_PLACEHOLDER'):
            image_data = processed_content['image_base64']
            if not image_data.startswith('data:'):
                image_data = f"data:image/png;base64,{image_data}"

            messages[1]["content"].append({
                "type": "image_url",
                "image_url": {
                    "url": image_data
                }
            })

        # Call the model through the shared helper (uses GPT-5.1 by default)
        response_text = chat_completion(
            messages,
            api_key=openai_api_key,
            json_only=True,
        )

        # Parse the JSON response
        result = parse_detection_response(response_text)
        result["source"] = "direct_detection"  # Indicate this came from direct detection

        return result

    except Exception as e:
        return {
            "success": False,
            "error": f"Direct question type detection failed: {str(e)}"
        }


def parse_detection_response(response_text: str) -> Dict[str, Any]:
    """
    Parse the JSON response from the detection LLM.

    Args:
        response_text: Raw response text from LLM

    Returns:
        Parsed detection result
    """
    try:
        # Try to extract JSON from the response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1

        if json_start >= 0 and json_end > json_start:
            json_text = response_text[json_start:json_end]
            result = json.loads(json_text)

            # Validate the response structure
            if not isinstance(result, dict):
                raise ValueError("Response is not a dictionary")

            # Ensure required fields
            can_represent = result.get('can_represent', False)
            question_type = result.get('question_type')

            # Validate question type if can_represent is True
            if can_represent and question_type not in SUPPORTED_QTI_TYPES:
                return {
                    "success": False,
                    "error": f"Invalid question type: {question_type}. Must be one of: {SUPPORTED_QTI_TYPES}"
                }

            # Return successful result
            return {
                "success": True,
                "can_represent": can_represent,
                "question_type": question_type,
                "confidence": result.get('confidence', 0.0),
                "reason": result.get('reason', ''),
                "key_elements": result.get('key_elements', []),
                "potential_issues": result.get('potential_issues', [])
            }
        else:
            raise ValueError("No JSON found in response")

    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Failed to parse JSON response: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error parsing detection response: {str(e)}"
        }


def validate_question_type(question_type: str) -> bool:
    """
    Validate that a question type is supported.

    Args:
        question_type: Question type string

    Returns:
        True if supported, False otherwise
    """
    return question_type in SUPPORTED_QTI_TYPES


def get_question_type_description(question_type: str) -> str:
    """
    Get a description of a question type.

    Args:
        question_type: Question type string

    Returns:
        Description string
    """
    descriptions = {
        'choice': 'Single or multiple-choice questions with selectable options',
        'match': 'Questions where items from two sets need to be paired',
        'text-entry': 'Questions requiring short text input',
        'hotspot': 'Questions requiring clicking on specific areas of an image',
        'extended-text': 'Questions requiring longer text input/essay responses',
        'hot-text': 'Questions where specific text needs to be selected',
        'gap-match': 'Questions where text must be dragged to fill gaps',
        'order': 'Questions requiring ordering/ranking items',
        'graphic-gap-match': 'Questions matching items to locations on an image',
        'inline-choice': 'Questions with dropdown selections within text',
        'select-point': 'Questions requiring clicking specific points on an image',
        'media-interaction': 'Questions involving audio or video media',
        'composite': 'Multi-part questions with different interaction types'
    }

    return descriptions.get(question_type, 'Unknown question type')
