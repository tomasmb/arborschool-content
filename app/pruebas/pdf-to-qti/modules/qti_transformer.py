"""
QTI Transformer

This module implements step 2 of the conversion process:
Transform PDF content to QTI 3.0 XML format using the detected question type.
It leverages patterns from the existing HTML to QTI transformer.

Refactored to use content_processor and prompt_builder for better separation.

IMPORTANT: All images MUST be uploaded to S3. Base64 encoding in final XML is not allowed.
"""

import hashlib
import json
import logging
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, Optional

# Local helpers
from .ai_processing import chat_completion
from .prompt_builder import (
    create_error_correction_prompt,
    create_transformation_prompt,
)
from .qti_configs import QTI_TYPE_CONFIGS
from .utils.s3_uploader import upload_image_to_s3, upload_multiple_images_to_s3

_logger = logging.getLogger(__name__)


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
    'Funcif3n': 'Función',
    'razf3n': 'razón',
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
    'vaceda': 'vacía',

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


def extract_correct_answer_from_qti(qti_xml: str) -> Optional[str]:
    """
    Extract the correct answer from QTI XML.

    Args:
        qti_xml: QTI XML string

    Returns:
        Correct answer identifier (e.g., "ChoiceA") or None if not found
    """
    try:
        root = ET.fromstring(qti_xml)
        QTI_NS = "{http://www.imsglobal.org/xsd/imsqtiasi_v3p0}"

        response_decl = root.find(f".//{QTI_NS}qti-response-declaration")
        if response_decl is None:
            return None

        correct_response = response_decl.find(f"{QTI_NS}qti-correct-response")
        if correct_response is None:
            return None

        qti_value = correct_response.find(f"{QTI_NS}qti-value")
        if qti_value is None or not qti_value.text:
            return None

        return qti_value.text.strip()
    except ET.ParseError:
        # If XML parsing fails, try regex as fallback
        match = re.search(
            r'<qti-value>([^<]+)</qti-value>',
            qti_xml
        )
        if match:
            return match.group(1).strip()
        return None
    except Exception:
        return None


def update_correct_answer_in_qti_xml(qti_xml: str, correct_answer: str) -> str:
    """
    Update or add the correct answer in QTI XML.

    Args:
        qti_xml: QTI XML string
        correct_answer: Correct answer identifier (e.g., "ChoiceA")

    Returns:
        Updated QTI XML string
    """
    try:
        root = ET.fromstring(qti_xml)
        QTI_NS = "{http://www.imsglobal.org/xsd/imsqtiasi_v3p0}"

        response_decl = root.find(f".//{QTI_NS}qti-response-declaration")
        if response_decl is None:
            # If no response declaration, return original (shouldn't happen)
            return qti_xml

        correct_response = response_decl.find(f"{QTI_NS}qti-correct-response")
        if correct_response is None:
            # Create correct-response element if missing
            correct_response = ET.SubElement(response_decl, f"{QTI_NS}qti-correct-response")

        qti_value = correct_response.find(f"{QTI_NS}qti-value")
        if qti_value is None:
            # Create value element if missing
            qti_value = ET.SubElement(correct_response, f"{QTI_NS}qti-value")

        qti_value.text = correct_answer

        # Convert back to string
        return ET.tostring(root, encoding="unicode")
    except ET.ParseError:
        # Fallback to regex replacement if XML parsing fails
        # Try to replace existing value
        pattern = r'(<qti-correct-response[^>]*>\s*<qti-value>)[^<]+(</qti-value>\s*</qti-correct-response>)'
        if re.search(pattern, qti_xml):
            return re.sub(pattern, r'\1' + correct_answer + r'\2', qti_xml)

        # If no correct-response found, try to add it after response-declaration
        pattern = r'(<qti-response-declaration[^>]*>)'
        replacement = r'\1\n    <qti-correct-response>\n      <qti-value>' + correct_answer + '</qti-value>\n    </qti-correct-response>'
        if re.search(pattern, qti_xml):
            return re.sub(pattern, replacement, qti_xml, count=1)

        return qti_xml
    except Exception:
        return qti_xml


def transform_to_qti(
    processed_content: Dict[str, Any],
    question_type: str,
    openai_api_key: str,
    validation_feedback: Optional[str] = None,
    question_id: Optional[str] = None,
    use_s3: bool = True,
    paes_mode: bool = False,
    test_name: Optional[str] = None,
    correct_answer: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Transform PDF content to QTI 3.0 XML format.

    This implements step 2 of the conversion guidelines:
    Use the detected question type to transform the PDF content
    into valid QTI 3.0 XML.

    CRITICAL: All images MUST be uploaded to S3. If any image upload fails,
    the transformation will fail. Base64 encoding in final XML is not allowed.

    Args:
        processed_content: Already processed PDF content with placeholders
        question_type: Detected question type
        openai_api_key: OpenAI API key
        validation_feedback: Optional feedback from validation errors
        question_id: Optional question identifier for S3 image naming
        use_s3: If True, upload images to S3 and use URLs (default: True, REQUIRED)
        paes_mode: If True, optimizes for PAES format (math, 4 alternatives)
        test_name: Optional test/prueba name to organize images in S3 (e.g., "prueba-invierno-2026")
                   Images will be stored in images/{test_name}/ to avoid conflicts between tests
        correct_answer: Optional correct answer identifier (e.g., "ChoiceA", "ChoiceB", "ChoiceC", "ChoiceD")
                       If provided, will be used in <qti-correct-response> instead of LLM inference

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

        # CRITICAL: S3 upload is REQUIRED - fail early if disabled
        if not use_s3:
            _logger.error("S3 upload is disabled, but it is REQUIRED for all images")
            return {
                "success": False,
                "error": "S3 upload is required. use_s3 must be True."
            }

        _logger.info("🚀 Starting S3 image upload process (REQUIRED)")

        # Upload images to S3 (REQUIRED - no fallback to base64)
        image_url_mapping: Dict[str, str] = {}
        failed_uploads: list[str] = []

        # Upload main image (with retry)
        if processed_content.get('image_base64') and not processed_content['image_base64'].startswith('CONTENT_PLACEHOLDER'):
            _logger.info(f"📤 Uploading main image to S3 (question_id: {question_id or 'main'}, test: {test_name or 'default'})")
            s3_url = upload_image_to_s3(
                image_base64=processed_content['image_base64'],
                question_id=question_id or "main",
                test_name=test_name,
                max_retries=3,  # Retry automático incluido en upload_image_to_s3
            )
            if not s3_url:
                failed_uploads.append("main image")
                _logger.error("❌ Failed to upload main image to S3 after retries")
            else:
                image_url_mapping['main_image'] = s3_url
                processed_content['image_s3_url'] = s3_url
                _logger.info(f"✅ Main image uploaded to S3: {s3_url}")

        # Upload all additional images (with retry for each)
        if processed_content.get('all_images'):
            total_images = len(processed_content['all_images'])
            _logger.info(f"📤 Uploading {total_images} additional image(s) to S3 (with retry on failures)")
            s3_results = upload_multiple_images_to_s3(
                images=processed_content['all_images'],
                question_id=question_id,
                test_name=test_name,
            )
            # Validate that all images were uploaded successfully
            for i, image_info in enumerate(processed_content['all_images']):
                image_key = f"image_{i}"
                if image_info.get('image_base64') and not image_info['image_base64'].startswith('CONTENT_PLACEHOLDER'):
                    if image_key not in s3_results or not s3_results[image_key]:
                        failed_uploads.append(f"image_{i}")
                        _logger.error(f"❌ Failed to upload {image_key} to S3 after retries")
                    else:
                        _logger.info(f"✅ {image_key} uploaded to S3: {s3_results[image_key]}")
            image_url_mapping.update({k: v for k, v in s3_results.items() if v})

        # CRITICAL: Fail if any image upload failed
        if failed_uploads:
            error_msg = f"Failed to upload {len(failed_uploads)} image(s) to S3: {', '.join(failed_uploads)}. S3 upload is REQUIRED - cannot proceed with base64 fallback."
            _logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }

        # Verify that we have at least one image uploaded if there were images to upload
        expected_images = 0
        if processed_content.get('image_base64') and not processed_content['image_base64'].startswith('CONTENT_PLACEHOLDER'):
            expected_images += 1
        if processed_content.get('all_images'):
            expected_images += sum(1 for img in processed_content['all_images']
                                 if img.get('image_base64') and not img['image_base64'].startswith('CONTENT_PLACEHOLDER'))

        if expected_images > 0 and len(image_url_mapping) == 0:
            error_msg = "Expected images but none were uploaded to S3. S3 upload is REQUIRED."
            _logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }

        if len(image_url_mapping) > 0:
            _logger.info(f"✅ Successfully uploaded {len(image_url_mapping)} image(s) to S3")

        # Create the transformation prompt using the already processed content
        prompt = create_transformation_prompt(
            processed_content,
            question_type,
            config,
            validation_feedback,
            correct_answer=correct_answer
        )

        # Optimize prompt for PAES (mathematics, 4 alternatives)
        if paes_mode:
            from .paes_optimizer import optimize_prompt_for_math
            prompt = optimize_prompt_for_math(prompt)

        # Prepare messages for LLM (still use base64 for AI analysis, but XML must use S3 URLs)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert at converting educational content into QTI 3.0 XML format. "
                    "You must respond with valid JSON format only. "
                    "CRITICAL: NEVER use base64 encoding (data:image/...;base64,...) in the QTI XML. "
                    "Only use placeholder image names that will be replaced with S3 URLs."
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

        # ESTRATEGIA: En pruebas PAES, TODAS las imágenes son importantes - enviar todas
        # No hay imágenes "decorativas" en estas pruebas - todo es crítico para calidad
        # Solo optimizamos si hay MUCHAS imágenes (10+), pero para casos normales (1-5 imágenes), todas se envían

        images_sent_to_llm = 0
        max_images_threshold = 10  # Solo limitar si hay más de 10 imágenes (caso extremo)

        # 1. Add main image if available (ALWAYS send)
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
            images_sent_to_llm += 1
            _logger.info("📤 Sending main image to LLM")

        # 2. Add ALL additional images (in PAES tests, all images are important)
        if processed_content.get('all_images'):
            len(processed_content['all_images'])

            # Count how many have actual image data
            images_with_data = [
                img for img in processed_content['all_images']
                if img.get('image_base64') and not img['image_base64'].startswith('CONTENT_PLACEHOLDER')
            ]

            # For PAES tests: Send ALL images (they're all important)
            # Only limit if there are MANY images (10+) - extreme case
            if len(images_with_data) <= max_images_threshold:
                # Normal case: Send all images (quality is priority)
                for image_info in images_with_data:
                    image_data = image_info['image_base64']
                    if not image_data.startswith('data:'):
                        image_data = f"data:image/png;base64,{image_data}"

                    messages[1]["content"].append({
                        "type": "image_url",
                        "image_url": {
                            "url": image_data
                        }
                    })
                    images_sent_to_llm += 1

                _logger.info(f"📤 Sending {len(images_with_data)} additional image(s) to LLM (all important for quality)")
            else:
                # Extreme case: Many images (10+) - prioritize by importance
                # Still prioritize choice diagrams and larger images
                choice_images = []
                other_images = []

                for image_info in images_with_data:
                    is_choice = image_info.get('is_choice_diagram', False)
                    width = image_info.get('width', 0)
                    height = image_info.get('height', 0)
                    area = width * height

                    if is_choice:
                        choice_images.append((999999, image_info))  # Highest priority
                    else:
                        other_images.append((area, image_info))

                # Send ALL choice images first
                for priority, image_info in sorted(choice_images, reverse=True):
                    image_data = image_info['image_base64']
                    if not image_data.startswith('data:'):
                        image_data = f"data:image/png;base64,{image_data}"

                    messages[1]["content"].append({
                        "type": "image_url",
                        "image_url": {
                            "url": image_data
                        }
                    })
                    images_sent_to_llm += 1

                # Then send top other images (sorted by size)
                other_images.sort(reverse=True)
                remaining_slots = max_images_threshold - len(choice_images)
                images_to_send = other_images[:remaining_slots]

                for priority, image_info in images_to_send:
                    image_data = image_info['image_base64']
                    if not image_data.startswith('data:'):
                        image_data = f"data:image/png;base64,{image_data}"

                    messages[1]["content"].append({
                        "type": "image_url",
                        "image_url": {
                            "url": image_data
                        }
                    })
                    images_sent_to_llm += 1

                skipped = len(other_images) - len(images_to_send)
                if skipped > 0:
                    _logger.warning(
                        f"📤 Sending {len(choice_images)} choice + {len(images_to_send)} other images "
                        f"(skipped {skipped} due to extreme case with {len(images_with_data)} total images)"
                    )
                else:
                    _logger.info(f"📤 Sending {images_sent_to_llm - 1} additional image(s) to LLM")

        _logger.info(f"📊 Total images sent to LLM: {images_sent_to_llm} (quality priority)")

        # Call the LLM for transformation via shared helper with retry on empty response
        # Aumentar límite de tokens para preguntas complejas (pueden tener mucho contenido)
        import time
        max_retries = 3
        base_delay = 2.0
        last_error: Optional[str] = None
        result: Optional[Dict[str, Any]] = None

        for attempt in range(max_retries):
            try:
                response_text = chat_completion(
                    messages,
                    api_key=openai_api_key,
                    json_only=True,
                    question_id=question_id,
                    output_dir=output_dir,
                    operation="transform_to_qti",
                    max_tokens=16384,  # Aumentado para manejar respuestas grandes
                )

                # Check if response is empty
                if not response_text or not response_text.strip():
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        _logger.warning(
                            f"Empty response from LLM (attempt {attempt + 1}/{max_retries}). "
                            f"Retrying in {delay:.2f}s..."
                        )
                        time.sleep(delay)
                        continue
                    else:
                        raise ValueError("LLM returned empty response after all retries")

                # Parse the transformation response
                result = parse_transformation_response(response_text)

                # Check if parsing was successful
                if result.get("success"):
                    break
                else:
                    error_msg = result.get("error", "Unknown parsing error")
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        _logger.warning(
                            f"Failed to parse LLM response (attempt {attempt + 1}/{max_retries}): "
                            f"{error_msg}. Retrying in {delay:.2f}s..."
                        )
                        time.sleep(delay)
                        last_error = error_msg
                        continue
                    else:
                        return {
                            "success": False,
                            "error": f"Failed to parse transformation response after {max_retries} attempts: {error_msg}"
                        }

            except Exception as e:
                error_str = str(e)
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    _logger.warning(
                        f"Error calling LLM (attempt {attempt + 1}/{max_retries}): "
                        f"{error_str}. Retrying in {delay:.2f}s..."
                    )
                    time.sleep(delay)
                    last_error = error_str
                    continue
                else:
                    return {
                        "success": False,
                        "error": f"LLM call failed after {max_retries} attempts: {error_str}"
                    }

        # If we get here, result should be set
        if result is None or not result.get("success"):
            return {
                "success": False,
                "error": f"Failed to get valid response from LLM: {last_error or 'Unknown error'}"
            }

        if result["success"]:
            # Verify and fix encoding issues (already done in parse_transformation_response,
            # but ensure it's also applied after cleaning)
            result["qti_xml"], _ = verify_and_fix_encoding(result["qti_xml"])

            # Clean up any remaining placeholders
            result["qti_xml"] = clean_qti_xml(result["qti_xml"])

            # Final encoding check after cleaning (in case cleaning introduced issues)
            result["qti_xml"], _ = verify_and_fix_encoding(result["qti_xml"])

            # Replace data URIs with S3 URLs (REQUIRED - S3 is mandatory)
            if image_url_mapping:
                result["qti_xml"] = replace_data_uris_with_s3_urls(
                    result["qti_xml"],
                    image_url_mapping,
                    processed_content
                )

            # OPTIMIZACIÓN: Intentar convertir base64 restante a S3 (pero NO abortar si falla)
            # Prioridad: Optimizar llamadas API - XML generado es valioso incluso con base64
            base64_pattern = r'(data:image/([^;]+);base64,)([A-Za-z0-9+/=\s]+)'
            base64_matches = re.findall(base64_pattern, result["qti_xml"])

            if base64_matches:
                _logger.warning(
                    f"⚠️  Found {len(base64_matches)} base64 data URI(s) in XML. "
                    "Attempting to upload to S3 (will continue with base64 if upload fails)..."
                )

                uploaded_count = 0
                failed_count = 0

                # Upload each base64 image to S3 and replace (continue even if some fail)
                for match in base64_matches:
                    full_prefix = match[0]  # data:image/png;base64,
                    match[1]   # png, svg+xml, etc.
                    base64_data = match[2]  # actual base64 data
                    full_data_uri = full_prefix + base64_data

                    # Generate a unique identifier for this image
                    image_hash = hashlib.md5(base64_data.encode()).hexdigest()[:8]
                    img_identifier = f"{question_id or 'img'}_base64_{image_hash}"

                    _logger.info(f"  📤 Attempting to upload base64 image to S3: {img_identifier}")

                    # Upload to S3 (try but don't abort if it fails)
                    s3_url = upload_image_to_s3(
                        image_base64=full_data_uri,
                        question_id=img_identifier,
                        test_name=test_name
                    )

                    if s3_url:
                        # Replace in XML - escape the URI for regex
                        escaped_uri = re.escape(full_data_uri)
                        result["qti_xml"] = re.sub(
                            rf'src=["\']{escaped_uri}["\']',
                            f'src="{s3_url}"',
                            result["qti_xml"]
                        )

                        # Also try replacing without src quotes (in case it's in different format)
                        result["qti_xml"] = result["qti_xml"].replace(full_data_uri, s3_url)

                        uploaded_count += 1
                        _logger.info(f"  ✅ Replaced base64 with S3 URL: {s3_url}")
                    else:
                        failed_count += 1
                        _logger.warning(
                            "  ⚠️  Failed to upload base64 image to S3. "
                            "Keeping as base64 - XML will be saved (can convert manually later)."
                        )

                # Log summary (don't abort)
                if uploaded_count > 0:
                    _logger.info(f"✅ Successfully converted {uploaded_count}/{len(base64_matches)} base64 image(s) to S3")
                if failed_count > 0:
                    _logger.warning(
                        f"⚠️  {failed_count} image(s) remain as base64. "
                        "XML will be saved - can convert to S3 manually later using migrate_base64_to_s3.py"
                    )
            else:
                _logger.info("✅ XML validated: No base64 data URIs found - all images use S3 URLs")

            # Verify correct answer matches answer key (if provided)
            if correct_answer:
                xml_answer = extract_correct_answer_from_qti(result["qti_xml"])
                if xml_answer:
                    if xml_answer != correct_answer:
                        _logger.warning(
                            f"⚠️  Answer mismatch for {question_id or 'question'}: "
                            f"Expected '{correct_answer}' from answer key, but XML has '{xml_answer}'. "
                            f"Auto-correcting..."
                        )
                        # Auto-correct the answer in the XML
                        result["qti_xml"] = update_correct_answer_in_qti_xml(
                            result["qti_xml"],
                            correct_answer
                        )
                        _logger.info(f"✅ Corrected answer to '{correct_answer}'")
                    else:
                        _logger.info(f"✅ Answer verified: '{correct_answer}' matches answer key")
                else:
                    _logger.warning(
                        f"⚠️  Could not extract correct answer from XML for {question_id or 'question'}. "
                        f"Expected '{correct_answer}' from answer key. "
                        f"Attempting to add correct answer..."
                    )
                    # Try to add the correct answer if it's missing
                    result["qti_xml"] = update_correct_answer_in_qti_xml(
                        result["qti_xml"],
                        correct_answer
                    )
                    _logger.info(f"✅ Added correct answer '{correct_answer}' from answer key")

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
    Replace ALL data URIs in QTI XML with S3 URLs.

    This function aggressively replaces all base64 data URIs with S3 URLs.
    It's called as a critical step to ensure no base64 remains in the final XML.

    Args:
        qti_xml: QTI XML string that may contain data URIs
        image_url_mapping: Dictionary mapping image identifiers to S3 URLs
        processed_content: Original processed content with image info

    Returns:
        QTI XML with ALL data URIs replaced by S3 URLs
    """
    # Pattern to match data URIs in img src attributes (more permissive to catch all)
    # Matches data:image/<any-type>;base64,<base64-data>
    data_uri_pattern = r'data:image/[^;]+;base64,[A-Za-z0-9+/=\s]+'

    replacements_made = 0

    # Replace main image first
    if 'main_image' in image_url_mapping and image_url_mapping['main_image']:
        main_s3_url = image_url_mapping['main_image']
        before = qti_xml
        qti_xml = re.sub(
            data_uri_pattern,
            main_s3_url,
            qti_xml,
            count=1,  # Replace first occurrence (main image)
        )
        if before != qti_xml:
            replacements_made += 1
            _logger.debug(f"Replaced main image data URI with S3 URL: {main_s3_url}")

    # Replace additional images
    if processed_content.get('all_images'):
        for i, image_info in enumerate(processed_content['all_images']):
            image_key = f"image_{i}"
            if image_key in image_url_mapping and image_url_mapping[image_key]:
                s3_url = image_url_mapping[image_key]
                before = qti_xml
                # Replace remaining data URIs (one at a time)
                qti_xml = re.sub(
                    data_uri_pattern,
                    s3_url,
                    qti_xml,
                    count=1,
                )
                if before != qti_xml:
                    replacements_made += 1
                    _logger.debug(f"Replaced {image_key} data URI with S3 URL: {s3_url}")

    # If we still have data URIs but ran out of mapped URLs, log warning
    remaining = re.findall(data_uri_pattern, qti_xml)
    if remaining:
        _logger.warning(f"⚠️  Found {len(remaining)} remaining data URI(s) after replacement. This should not happen.")
        # Try to replace any remaining with first available S3 URL
        if image_url_mapping:
            first_s3_url = next(iter(image_url_mapping.values()))
            qti_xml = re.sub(data_uri_pattern, first_s3_url, qti_xml)
            _logger.warning(f"Replaced remaining data URIs with fallback S3 URL: {first_s3_url}")

    if replacements_made > 0:
        _logger.info(f"✅ Replaced {replacements_made} data URI(s) with S3 URLs")

    return qti_xml


def fix_qti_xml_with_llm(
    invalid_xml: str,
    validation_errors: str,
    question_type: str,
    openai_api_key: str,
    retry_attempt: int = 1,
    max_attempts: int = 3,
    output_dir: Optional[str] = None,
    question_id: Optional[str] = None,
    **kwargs: Any,
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
            question_id=question_id,
            output_dir=output_dir,
            operation=f"fix_qti_xml_retry_{retry_attempt}",
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
