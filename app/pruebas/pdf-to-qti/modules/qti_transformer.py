"""
QTI Transformer

This module implements step 2 of the conversion process:
Transform PDF content to QTI 3.0 XML format using the detected question type.
It leverages patterns from the existing HTML to QTI transformer.

Refactored to use content_processor and prompt_builder for better separation.
"""

import json
import re
from typing import Dict, Any, Optional

# Local helpers
from .ai_processing import chat_completion
from .qti_configs import QTI_TYPE_CONFIGS
from .prompt_builder import (
    create_transformation_prompt,
    create_error_correction_prompt,
)
from .utils.s3_uploader import upload_image_to_s3, upload_multiple_images_to_s3


# Mapeo de errores de codificación comunes a caracteres correctos
ENCODING_FIXES = {
    # Tildes comunes
    'e1cido': 'ácido',
    'e1tomos': 'átomos',
    'e1tomo': 'átomo',
    'c1cido': 'ácido',
    'c1tomo': 'átomo',
    'oxedgeno': 'oxígeno',
    'hidrf3geno': 'hidrógeno',
    'sulffarico': 'sulfúrico',
    'quedmico': 'químico',
    'informacif3n': 'información',
    'continuacif3n': 'continuación',
    'reflexif3n': 'reflexión',
    'traslacif3n': 'traslación',
    'isome9tricas': 'isométricas',
    've9rtice': 'vértice',
    've9rtices': 'vértices',
    'producif3n': 'producción',
    'tecnolf3gica': 'tecnológica',
    'cumplif3': 'cumplió',
    'me1s': 'más',
    'd1a': 'día',
    'd1as': 'días',
    'Mi1rcoles': 'Miércoles',
    'Gr1fico': 'Gráfico',
    
    # Ñ
    'af1o': 'año',
    'af1os': 'años',
    
    # Signos de interrogación
    'bfCue1l': '¿Cuál',
    'bfcue1l': '¿cuál',
    'bfcue1ntos': '¿cuántos',
    'bfcue1les': '¿cuáles',
    'bfCue': '¿Cu',
    'bfcue': '¿cu',
    
    # Otros
    'sere1': 'será',
    'produciredan': 'producirían',
    'comenzare1': 'comenzará',
    'restaurare1': 'restaurará',
    
    # Comillas mal codificadas
    'ab bajabb': '"baja"',
    'ab no bajabb': '"no baja"',
    'bfCon cue1l': '¿Con cuál',
    'bfCon': '¿Con',
    'cue1l': 'cuál',
    
    # Más tildes
    'orge1nicos': 'orgánicos',
    'gre1ficos': 'gráficos',
    'construccif3n': 'construcción',
    'comparacif3n': 'comparación',
    'afirmacif3n': 'afirmación',
    'continfachn': 'continuación',
    'este1n': 'están',
    'este1': 'está',
    'este1 graduados': 'están graduados',
    'este1 escritos': 'están escritos',
    'este1 juntas': 'están juntas',
    'Ilustracif3n': 'Ilustración',
    'ilustracif3n': 'ilustración',
}


def verify_and_fix_encoding(qti_xml: str) -> tuple[str, bool]:
    """
    Verifica y corrige automáticamente problemas de codificación comunes en el QTI XML.
    
    Detecta y corrige errores como:
    - Tildes mal codificados (e1cido → ácido, reflexif3n → reflexión)
    - Letra "ñ" mal codificada (af1o → año)
    - Signos de interrogación mal codificados (bfCue1l → ¿Cuál)
    
    Args:
        qti_xml: El QTI XML a verificar y corregir
        
    Returns:
        Tupla con (xml_corregido, se_encontraron_problemas)
    """
    if not qti_xml:
        return qti_xml, False
    
    # Verificar si hay problemas de codificación
    has_issues = any(wrong in qti_xml for wrong in ENCODING_FIXES.keys())
    
    if not has_issues:
        return qti_xml, False
    
    # Aplicar correcciones en orden (más específicas primero)
    fixed_xml = qti_xml
    for wrong, correct in sorted(ENCODING_FIXES.items(), key=lambda x: -len(x[0])):
        fixed_xml = fixed_xml.replace(wrong, correct)
        # También buscar en mayúsculas/minúsculas
        fixed_xml = fixed_xml.replace(wrong.capitalize(), correct.capitalize())
        fixed_xml = fixed_xml.replace(wrong.upper(), correct.upper())
    
    return fixed_xml, True


def transform_to_qti(
    processed_content: Dict[str, Any], 
    question_type: str, 
    openai_api_key: str,
    validation_feedback: Optional[str] = None,
    question_id: Optional[str] = None,
    use_s3: bool = True,
    paes_mode: bool = False,
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
        question_id: Optional question identifier for S3 image naming
        use_s3: If True, upload images to S3 and use URLs (default: True)
        paes_mode: If True, optimizes for PAES format (math, 4 alternatives)
        
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
        
        # Upload images to S3 if enabled
        image_url_mapping = {}
        if use_s3:
            # Upload main image
            if processed_content.get('image_base64') and not processed_content['image_base64'].startswith('CONTENT_PLACEHOLDER'):
                s3_url = upload_image_to_s3(
                    image_base64=processed_content['image_base64'],
                    question_id=question_id or "main",
                )
                if s3_url:
                    image_url_mapping['main_image'] = s3_url
                    processed_content['image_s3_url'] = s3_url
            
            # Upload all additional images
            if processed_content.get('all_images'):
                s3_results = upload_multiple_images_to_s3(
                    images=processed_content['all_images'],
                    question_id=question_id,
                )
                image_url_mapping.update(s3_results)
        
        # Create the transformation prompt using the already processed content
        prompt = create_transformation_prompt(
            processed_content, 
            question_type, 
            config,
            validation_feedback
        )
        
        # Optimize prompt for PAES (mathematics, 4 alternatives)
        if paes_mode:
            from .paes_optimizer import optimize_prompt_for_math
            prompt = optimize_prompt_for_math(prompt)
        
        # Prepare messages for LLM (still use base64 for AI analysis)
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
        
        # Add image if available (use base64 for AI, but we'll replace with S3 URL in XML)
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
        
        # Call the LLM for transformation via shared helper
        response_text = chat_completion(
            messages,
            api_key=openai_api_key,
            json_only=True,
        )
        
        # Parse the transformation response
        result = parse_transformation_response(response_text)
        
        if result["success"]:
            # Verify and fix encoding issues (already done in parse_transformation_response,
            # but ensure it's also applied after cleaning)
            result["qti_xml"], _ = verify_and_fix_encoding(result["qti_xml"])
            
            # Clean up any remaining placeholders
            result["qti_xml"] = clean_qti_xml(result["qti_xml"])
            
            # Final encoding check after cleaning (in case cleaning introduced issues)
            result["qti_xml"], _ = verify_and_fix_encoding(result["qti_xml"])
            
            # Replace data URIs with S3 URLs if available
            if use_s3 and image_url_mapping:
                result["qti_xml"] = replace_data_uris_with_s3_urls(
                    result["qti_xml"],
                    image_url_mapping,
                    processed_content
                )
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"QTI transformation failed: {str(e)}"
        }


def replace_data_uris_with_s3_urls(
    qti_xml: str,
    image_url_mapping: Dict[str, str],
    processed_content: Dict[str, Any],
) -> str:
    """
    Replace data URIs in QTI XML with S3 URLs.
    
    Args:
        qti_xml: QTI XML string that may contain data URIs
        image_url_mapping: Dictionary mapping image identifiers to S3 URLs
        processed_content: Original processed content with image info
        
    Returns:
        QTI XML with data URIs replaced by S3 URLs
    """
    # Pattern to match data URIs in img src attributes
    data_uri_pattern = r'data:image/[^;]+;base64,[A-Za-z0-9+/=]+'
    
    # Replace main image if available
    if 'main_image' in image_url_mapping:
        main_s3_url = image_url_mapping['main_image']
        # Replace any data URI with the main S3 URL
        qti_xml = re.sub(
            data_uri_pattern,
            main_s3_url,
            qti_xml,
            count=1,  # Replace first occurrence (main image)
        )
    
    # Replace additional images
    if processed_content.get('all_images'):
        for i, image_info in enumerate(processed_content['all_images']):
            image_key = f"image_{i}"
            if image_key in image_url_mapping and image_url_mapping[image_key]:
                s3_url = image_url_mapping[image_key]
                # Replace remaining data URIs
                qti_xml = re.sub(
                    data_uri_pattern,
                    s3_url,
                    qti_xml,
                    count=1,
                )
    
    return qti_xml


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
            # Verify and fix encoding issues (already done in parse_correction_response,
            # but ensure it's also applied after cleaning)
            result["qti_xml"], _ = verify_and_fix_encoding(result["qti_xml"])
            
            # Clean the result
            cleaned_xml = clean_qti_xml(result["qti_xml"])
            
            # Final encoding check after cleaning
            cleaned_xml, _ = verify_and_fix_encoding(cleaned_xml)
            
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
            # Ensure UTF-8 encoding is preserved when parsing JSON
            result = json.loads(json_text)
            
            # Validate required fields
            if not isinstance(result, dict):
                raise ValueError("Response is not a dictionary")
            
            title = result.get('title', 'Untitled Question')
            description = result.get('description', '')
            qti_xml = result.get('qti_xml', '')
            
            # Ensure QTI XML is properly decoded as UTF-8
            if isinstance(qti_xml, bytes):
                qti_xml = qti_xml.decode('utf-8')
            
            if not qti_xml:
                raise ValueError("No QTI XML found in response")
            
            # Verify and fix encoding issues (tildes, ñ, etc.)
            qti_xml, encoding_fixed = verify_and_fix_encoding(qti_xml)
            if encoding_fixed:
                # Log that encoding was fixed (could add logging here if needed)
                pass
            
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
            
            # Ensure QTI XML is properly decoded as UTF-8
            if isinstance(qti_xml, bytes):
                qti_xml = qti_xml.decode('utf-8')
            
            if not qti_xml:
                raise ValueError("No corrected QTI XML found in response")
            
            # Verify and fix encoding issues (tildes, ñ, etc.)
            qti_xml, encoding_fixed = verify_and_fix_encoding(qti_xml)
            if encoding_fixed:
                # Log that encoding was fixed (could add logging here if needed)
                pass
            
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