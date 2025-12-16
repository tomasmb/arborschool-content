"""
QTI Transformer

This module implements step 2 of the conversion process:
Transform PDF content to QTI 3.0 XML format using the detected question type.
It leverages patterns from the existing HTML to QTI transformer.

Refactored to use content_processor and prompt_builder for better separation.
"""

import json
from typing import Dict, Any, Optional

# Local helpers
from .ai_processing import chat_completion
from .qti_configs import QTI_TYPE_CONFIGS
from .prompt_builder import (
    create_transformation_prompt,
    create_error_correction_prompt,
)


def transform_to_qti(
    processed_content: Dict[str, Any], 
    question_type: str, 
    openai_api_key: str,
    validation_feedback: Optional[str] = None
) -> Dict[str, Any]:
    """
    Transform PDF content to QTI 3.0 XML format.
    
    This implements step 2 of the conversion guidelines:
    Use the detected question type to transform the PDF content
    into valid QTI 3.0 XML.
    
    Args:
        processed_content: Already processed PDF content with placeholders
        question_type: Detected question type
        openai_api_key: OpenAI API key
        validation_feedback: Optional feedback from validation errors
        
    Returns:
        Dictionary with transformation results
    """
    try:
        # Get configuration for the question type
        config = QTI_TYPE_CONFIGS.get(question_type)
        if not config:
            return {
                "success": False,
                "error": f"Unsupported question type: {question_type}"
            }
        
        # Create the transformation prompt using the already processed content
        prompt = create_transformation_prompt(
            processed_content, 
            question_type, 
            config,
            validation_feedback
        )
        
        # Prepare messages for GPT-5.1
        messages = [
            {
                "role": "system",
                "content": "You are an expert at converting educational content into QTI 3.0 XML format. You must respond with valid JSON format only."
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
        
        # Add all extracted images from PDF structure
        if processed_content.get('all_images'):
            for i, image_info in enumerate(processed_content['all_images']):
                if image_info.get('image_base64') and not image_info['image_base64'].startswith('CONTENT_PLACEHOLDER'):
                    image_data = image_info['image_base64']
                    if not image_data.startswith('data:'):
                        image_data = f"data:image/png;base64,{image_data}"
                    
                    messages[1]["content"].append({
                        "type": "image_url",
                        "image_url": {
                            "url": image_data
                        }
                    })
        
        # Call the LLM for transformation via shared helper (uses GPT-5.1 by default)
        response_text = chat_completion(
            messages,
            api_key=openai_api_key,
            json_only=True,
        )
        
        # Parse the transformation response
        result = parse_transformation_response(response_text)
        
        if result["success"]:
            # Clean up any remaining placeholders
            result["qti_xml"] = clean_qti_xml(result["qti_xml"])
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"QTI transformation failed: {str(e)}"
        }


def fix_qti_xml_with_llm(
    invalid_xml: str,
    validation_errors: str,
    question_type: str,
    openai_api_key: str,
    retry_attempt: int = 1,
    max_attempts: int = 3
) -> Dict[str, Any]:
    """
    Attempt to fix invalid QTI XML using LLM.
    
    Args:
        invalid_xml: The invalid QTI XML string (with placeholders, not images)
        validation_errors: String containing validation error messages
        question_type: The detected question type for context
        openai_api_key: OpenAI API key
        retry_attempt: Current attempt number (1-based)
        max_attempts: Maximum number of attempts for context
        
    Returns:
        Dictionary with success status and corrected XML
    """
    try:
        # Basic validation check that the XML is well-formed
        try:
            import xml.etree.ElementTree as ET
            ET.fromstring(invalid_xml)
        except ET.ParseError as e:
            return {
                "success": False, 
                "error": f"XML structure error: {str(e)}"
            }
        
        # Create error correction prompt
        correction_prompt = create_error_correction_prompt(
            invalid_xml, 
            validation_errors, 
            question_type,
            retry_attempt,
            max_attempts
        )
        
        # Call the model to fix the XML via shared helper (uses GPT-5.1 with high reasoning)
        corrected_content = chat_completion(
            [
                {"role": "system", "content": "You are an expert in QTI 3.0 XML. Fix the provided XML to make it valid."},
                {"role": "user", "content": correction_prompt},
            ],
            api_key=openai_api_key,
            json_only=True,
            reasoning_effort="high",
            max_tokens=8000,
        ).strip()
        
        # Parse the correction response
        result = parse_correction_response(corrected_content)
        
        if result["success"]:
            # Clean the result
            cleaned_xml = clean_qti_xml(result["qti_xml"])
            
            # Basic validation
            try:
                import xml.etree.ElementTree as ET
                ET.fromstring(cleaned_xml)
            except ET.ParseError as e:
                return {"success": False, "error": f"LLM produced invalid XML: {str(e)}"}
            
            return {
                "success": True,
                "qti_xml": cleaned_xml
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Failed to parse LLM correction response")
            }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"LLM correction failed: {str(e)}"
        }


def parse_transformation_response(response_text: str) -> Dict[str, Any]:
    """
    Parse the transformation response from the LLM.
    
    Args:
        response_text: Raw response text
        
    Returns:
        Parsed transformation result
    """
    try:
        # Check for None or empty response
        if response_text is None:
            raise ValueError("Response text is None")
        
        if not response_text.strip():
            raise ValueError("Response text is empty")
        
        # Try to extract JSON from the response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_text = response_text[json_start:json_end]
            result = json.loads(json_text)
            
            # Validate required fields
            if not isinstance(result, dict):
                raise ValueError("Response is not a dictionary")
            
            title = result.get('title', 'Untitled Question')
            description = result.get('description', '')
            qti_xml = result.get('qti_xml', '')
            
            if not qti_xml:
                raise ValueError("No QTI XML found in response")
            
            return {
                "success": True,
                "title": title,
                "description": description,
                "qti_xml": qti_xml,
                "key_features": result.get('key_features', []),
                "notes": result.get('notes', '')
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
            "error": f"Error parsing transformation response: {str(e)}"
        }


def parse_correction_response(response_text: str) -> Dict[str, Any]:
    """
    Parse the correction response from the LLM.
    
    Args:
        response_text: Raw response text
        
    Returns:
        Parsed correction result
    """
    try:
        # Try to extract JSON from the response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_text = response_text[json_start:json_end]
            result = json.loads(json_text)
            
            # Validate required fields
            if not isinstance(result, dict):
                raise ValueError("Response is not a dictionary")
            
            qti_xml = result.get('qti_xml', '')
            
            if not qti_xml:
                raise ValueError("No corrected QTI XML found in response")
            
            return {
                "success": True,
                "qti_xml": qti_xml,
                "fixes_applied": result.get('fixes_applied', []),
                "notes": result.get('notes', '')
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
            "error": f"Error parsing correction response: {str(e)}"
        }


def clean_qti_xml(xml_content: str) -> str:
    """
    Clean and normalize QTI XML content.
    - Removes known LLM artifacts (e.g., ```xml wrapper)
    - Removes XML declaration if present
    - Strips leading/trailing whitespace
    - Removes invalid null characters that can exist in PDF text
    
    Args:
        xml_content: Raw XML content
        
    Returns:
        Cleaned XML content
    """
    # Remove any markdown code block markers
    if xml_content.strip().startswith('```xml'):
        xml_content = xml_content.strip()[6:-3].strip()
    
    # Remove XML declaration
    if xml_content.strip().startswith('<?xml'):
        xml_content = xml_content.split('?>', 1)[1].strip()

    # CRITICAL: Remove null characters (Unicode: 0x0) which are invalid in XML
    xml_content = xml_content.replace('\x00', '')
    
    # Strip any leading/trailing whitespace from the whole block
    return xml_content.strip() 