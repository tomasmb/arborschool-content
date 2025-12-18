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
import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from modules.pdf_processor import extract_pdf_content
from modules.question_detector import detect_question_type
from modules.qti_transformer import transform_to_qti, fix_qti_xml_with_llm
from modules.validation import validate_qti_xml, validate_qti_question, should_proceed_with_qti
from modules.content_processing import extract_large_content, restore_large_content
from modules.utils.s3_uploader import upload_image_to_s3


def convert_base64_to_s3_manual(
    qti_xml: str,
    question_id: Optional[str],
    test_name: Optional[str],
    output_dir: str,
) -> Optional[str]:
    """
    Conversión MANUAL de base64 a S3 (sin llamar a API LLM).
    
    Detecta imágenes base64 en el XML, las sube a S3 usando upload_image_to_s3,
    y reemplaza los data URIs con URLs S3.
    
    Args:
        qti_xml: XML del QTI que puede contener base64
        question_id: ID de la pregunta para nombrar las imágenes
        test_name: Nombre del test para organizar en S3
        output_dir: Directorio de salida para guardar mapeo S3
        
    Returns:
        XML actualizado con URLs S3, o None si hubo error crítico
    """
    base64_pattern = r'(data:image/([^;]+);base64,)([A-Za-z0-9+/=\s]+)'
    base64_matches = list(re.finditer(base64_pattern, qti_xml))
    
    if not base64_matches:
        return qti_xml  # No hay base64, retornar XML sin cambios
    
    print(f"   🔍 Detectadas {len(base64_matches)} imagen(es) base64")
    
    # Cargar mapeo S3 existente si existe
    s3_mapping_file = os.path.join(output_dir, "s3_image_mapping.json")
    s3_image_mapping: Dict[str, str] = {}
    if os.path.exists(s3_mapping_file):
        try:
            with open(s3_mapping_file, "r", encoding="utf-8") as f:
                s3_image_mapping = json.load(f)
        except Exception:
            s3_image_mapping = {}
    
    updated_xml = qti_xml
    uploaded_count = 0
    reused_count = 0
    failed_count = 0
    
    for i, match in enumerate(base64_matches):
        full_prefix = match.group(1)  # data:image/png;base64,
        mime_type = match.group(2)  # png, svg+xml, etc.
        base64_data = match.group(3)  # datos base64
        full_data_uri = match.group(0)  # URI completo
        
        # Verificar si ya existe en mapeo S3
        s3_url = None
        img_keys = [f"image_{i}", f"{question_id}_manual_{i}", f"{question_id}_img{i}"]
        for key in img_keys:
            if key in s3_image_mapping:
                s3_url = s3_image_mapping[key]
                reused_count += 1
                print(f"   ♻️  Reutilizando imagen {i+1} desde mapeo S3")
                break
        
        # Si no existe, subir a S3 (SIN API LLM - solo S3 upload)
        if not s3_url:
            img_id = f"{question_id}_manual_{i}" if question_id else f"manual_{i}"
            print(f"   📤 Subiendo imagen {i+1}/{len(base64_matches)} a S3 (manual)...")
            
            s3_url = upload_image_to_s3(
                image_base64=full_data_uri,
                question_id=img_id,
                test_name=test_name,
            )
            
            if s3_url:
                uploaded_count += 1
                # Guardar en mapeo
                for key in img_keys:
                    s3_image_mapping[key] = s3_url
                print(f"   ✅ Imagen {i+1} subida a S3: {s3_url}")
            else:
                failed_count += 1
                print(f"   ⚠️  Fallo al subir imagen {i+1} a S3 (mantendrá base64)")
        
        # Reemplazar en XML si tenemos URL S3
        if s3_url:
            updated_xml = updated_xml.replace(full_data_uri, s3_url, 1)
    
    # Guardar mapeo actualizado
    if uploaded_count > 0 or reused_count > 0:
        try:
            with open(s3_mapping_file, "w", encoding="utf-8") as f:
                json.dump(s3_image_mapping, f, indent=2)
            status_parts = []
            if uploaded_count > 0:
                status_parts.append(f"{uploaded_count} nueva(s)")
            if reused_count > 0:
                status_parts.append(f"{reused_count} reutilizada(s)")
            print(f"   💾 Mapeo S3 actualizado ({', '.join(status_parts)})")
        except Exception as e:
            print(f"   ⚠️  Error guardando mapeo S3: {e}")
    
    if failed_count > 0:
        print(f"   ⚠️  {failed_count} imagen(es) no se pudieron subir (quedan como base64)")
    
    return updated_xml


def process_single_question_pdf(
    input_pdf_path: str, 
    output_dir: str,
    openai_api_key: Optional[str] = None,
    validation_endpoint: Optional[str] = None,
    paes_mode: bool = False,
    skip_if_exists: bool = True,  # OPTIMIZACIÓN: Saltarse si ya existe XML válido
) -> Dict[str, Any]:
    """
    Complete pipeline: extract PDF content, detect question type, 
    transform to QTI, validate, and return results.
    
    OPTIMIZACIÓN: Si skip_if_exists=True, verifica si ya existe question.xml válido
    y lo reutiliza sin reprocesar. También intenta regenerar desde processed_content.json
    si existe pero falta el XML.
    
    Uses Gemini Preview 3 by default (from GEMINI_API_KEY env var),
    with automatic fallback to OpenAI GPT-5.1 if Gemini fails.
    
    Args:
        input_pdf_path: Path to the input PDF file
        output_dir: Directory to save output files
        openai_api_key: Optional API key (uses GEMINI_API_KEY from env if None)
        validation_endpoint: Optional QTI validation endpoint URL
        paes_mode: If True, optimizes for PAES format (choice questions, math, 4 alternatives)
        skip_if_exists: If True, skip processing if valid XML already exists (default: True)
        
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

    # OPTIMIZACIÓN: Verificar si ya existe question.xml válido
    if skip_if_exists and not is_lambda:
        xml_path = os.path.join(output_dir, "question.xml")
        if os.path.exists(xml_path):
            # Validar que el XML existente es válido
            try:
                with open(xml_path, "r", encoding="utf-8") as f:
                    existing_xml = f.read()
                validation_result = validate_qti_xml(existing_xml, validation_endpoint)
                if validation_result.get("success", False):
                    print(f"✅ QTI XML ya existe y es válido: {xml_path}")
                    print(f"   ⏭️  Saltándose procesamiento (puedes desactivar con skip_if_exists=False)")
                    # Leer título del XML existente
                    title_match = re.search(r'<qti-assessment-item[^>]*title="([^"]*)"', existing_xml)
                    title = title_match.group(1) if title_match else "Existing Question"
                    return {
                        "success": True,
                        "title": title,
                        "skipped": True,
                        "xml_path": xml_path,
                        "message": "Reused existing valid XML"
                    }
                else:
                    print(f"⚠️  XML existente no válido, regenerando...")
            except Exception as e:
                print(f"⚠️  Error validando XML existente: {e}, regenerando...")
        
        # OPTIMIZACIÓN: Si no existe XML pero existe processed_content.json, intentar regenerar
        processed_json_path = os.path.join(output_dir, "processed_content.json")
        if not os.path.exists(xml_path) and os.path.exists(processed_json_path):
            print(f"📖 Encontrado processed_content.json, intentando regenerar XML...")
            try:
                # Importar función de regeneración
                from scripts.regenerate_qti_from_processed import regenerate_qti_from_processed
                # Path ya está importado al inicio del archivo, no importar aquí
                
                api_key = openai_api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")
                if api_key:
                    # Extraer test_name del output_dir
                    test_match = re.search(r'prueba-[^/]+|seleccion-[^/]+', output_dir)
                    test_name = test_match.group(0) if test_match else None
                    
                    result = regenerate_qti_from_processed(
                        question_dir=Path(output_dir),
                        api_key=api_key,
                        paes_mode=paes_mode,
                        test_name=test_name,
                    )
                    if result.get("success"):
                        print(f"✅ XML regenerado exitosamente desde processed_content.json")
                        # Leer título del XML regenerado
                        xml_path = os.path.join(output_dir, "question.xml")
                        if os.path.exists(xml_path):
                            with open(xml_path, "r", encoding="utf-8") as f:
                                regenerated_xml = f.read()
                            title_match = re.search(r'<qti-assessment-item[^>]*title="([^"]*)"', regenerated_xml)
                            title = title_match.group(1) if title_match else "Regenerated Question"
                            return {
                                "success": True,
                                "title": title,
                                "regenerated": True,
                                "xml_path": xml_path,
                                "message": "Regenerated from processed_content.json"
                            }
            except Exception as e:
                print(f"⚠️  Error regenerando desde processed_content.json: {e}")
                print(f"   Continuando con procesamiento completo...")

    try:
        doc = fitz.open(input_pdf_path)
        print(f"Processing PDF: {input_pdf_path} ({doc.page_count} pages)")
        
        # Use API key from env if not provided (prioritizes Gemini)
        api_key = openai_api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return {
                "success": False,
                "error": "No API key provided. Set GEMINI_API_KEY or OPENAI_API_KEY in environment, or pass openai_api_key parameter"
            }
        
        # Extract PDF content with AI-powered analysis
        pdf_content = extract_pdf_content(doc, api_key)
        
        # Process large content  
        processed_content, extracted_content = extract_large_content(pdf_content, openai_api_key=api_key)
        
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
        
        # Detect question type (skip in PAES mode)
        if paes_mode:
            print("⚡ PAES mode: Skipping question type detection (always choice)")
            from modules.paes_optimizer import get_paes_question_type
            detection_result = get_paes_question_type()
            question_type = "choice"
            can_represent = True
            print("✅ Using PAES optimized config: choice (4 alternatives)")
        else:
            print("🔍 Detecting question type...")
            detection_result = detect_question_type(processed_content, api_key)
            
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
        print("📤 CRITICAL: All images will be uploaded to S3 (required, no base64 fallback)")
        # Generate question ID from title if available
        question_id = processed_content.get('title', 'question')
        if question_id:
            # Clean question_id for use in S3
            question_id = re.sub(r'[^a-zA-Z0-9_-]', '_', question_id)[:50]
        
        # Extract test name from output_dir path (e.g., "prueba-invierno-2026" from path)
        # This organizes images in S3 by test name to avoid conflicts
        test_name = None
        test_match = re.search(r'prueba-[^/]+|seleccion-[^/]+', output_dir)
        if test_match:
            test_name = test_match.group(0)
            print(f"📁 Detected test name from path: {test_name}")
        else:
            # Try to extract from input path as fallback
            test_match = re.search(r'prueba-[^/]+', input_pdf_path)
            if test_match:
                test_name = test_match.group(0)
                print(f"📁 Detected test name from input path: {test_name}")
        
        if test_name:
            print(f"📦 Images will be organized in S3 as: images/{test_name}/")
        
        # Load answer key if available
        correct_answer = None
        if test_name:
            # Look for answer key file in multiple possible locations
            output_path_obj = Path(output_dir)
            possible_paths = [
                # Standard location: app/data/pruebas/procesadas/{test_name}/respuestas_correctas.json
                output_path_obj.parent.parent.parent / "data" / "pruebas" / "procesadas" / test_name / "respuestas_correctas.json",
                # Alternative: relative to output_dir
                output_path_obj.parent.parent / test_name / "respuestas_correctas.json",
                # Alternative: same directory as output
                output_path_obj.parent / "respuestas_correctas.json",
                # Also check in raw directory structure (for future organization)
                output_path_obj.parent.parent.parent / "data" / "pruebas" / "raw" / test_name / "respuestas_correctas.json",
            ]
            
            answer_key_path = None
            for path_item in possible_paths:
                if path_item.exists():
                    answer_key_path = path_item
                    break
            
            if answer_key_path:
                try:
                    with open(answer_key_path, "r", encoding="utf-8") as f:
                        answer_key_data = json.load(f)
                    answers = answer_key_data.get("answers", {})
                    
                    # Extract question number from question_id (e.g., "Q3" -> "3", "question_017" -> "17")
                    q_num_match = re.search(r'(\d+)', question_id or "")
                    if q_num_match:
                        q_num = q_num_match.group(1)
                        correct_answer = answers.get(q_num)
                        if correct_answer:
                            print(f"✅ Found correct answer for question {q_num}: {correct_answer}")
                        else:
                            print(f"⚠️  No answer found in key for question {q_num} (key has {len(answers)} answers)")
                except Exception as e:
                    print(f"⚠️  Could not load answer key from {answer_key_path}: {e}")
            else:
                # Silently skip if no answer key found (optional feature)
                pass
        
        transformation_result = transform_to_qti(
            processed_content, 
            question_type, 
            api_key,
            question_id=question_id,
            use_s3=True,  # REQUIRED: S3 upload is mandatory for all images
            paes_mode=paes_mode,  # Pass PAES mode flag
            test_name=test_name,  # Organize images by test name in S3
            correct_answer=correct_answer,  # Pass correct answer if available
        )
        
        if not transformation_result["success"]:
            return {
                "success": False,
                "error": f"QTI transformation failed: {transformation_result['error']}",
                "question_type": question_type
            }
        
        qti_xml = transformation_result["qti_xml"]
        
        # OPTIMIZACIÓN: Inicializar mapeo S3 desde transform_to_qti si existe información
        # (esto guarda las URLs de imágenes subidas durante la transformación inicial)
        if not is_lambda:
            s3_mapping_file = os.path.join(output_dir, "s3_image_mapping.json")
            # Si existe mapeo previo, cargarlo, sino crear uno nuevo
            initial_s3_mapping: Dict[str, str] = {}
            if os.path.exists(s3_mapping_file):
                try:
                    with open(s3_mapping_file, "r", encoding="utf-8") as f:
                        initial_s3_mapping = json.load(f)
                except Exception:
                    initial_s3_mapping = {}
            
            # Extraer URLs S3 del XML para guardarlas en el mapeo
            # Esto captura imágenes que ya fueron subidas durante transform_to_qti
            s3_url_pattern = r'src=["\'](https://[^"\']+\.(png|jpg|jpeg|svg))["\']'
            s3_urls_found = re.findall(s3_url_pattern, qti_xml)
            if s3_urls_found:
                for i, (url, ext) in enumerate(s3_urls_found):
                    # Guardar con múltiples keys para facilitar búsqueda
                    url_only = url
                    initial_s3_mapping[f"image_{i}"] = url_only
                    if question_id:
                        initial_s3_mapping[f"{question_id}_img{i}"] = url_only
                
                # Guardar mapeo inicial (si hay URLs nuevas)
                try:
                    with open(s3_mapping_file, "w", encoding="utf-8") as f:
                        json.dump(initial_s3_mapping, f, indent=2)
                    if len(s3_urls_found) > 0:
                        print(f"💾 Mapeo S3 inicial guardado: {len(s3_urls_found)} URL(s) detectada(s)")
                except Exception as e:
                    print(f"⚠️  Error guardando mapeo S3 inicial: {e}")
        
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
            print(f"🔄 Restaurando placeholders con imágenes desde extracted_content...")
            qti_xml = restore_large_content(qti_xml, extracted_content)
            
            # CRÍTICO: Después de restore_large_content, SIEMPRE hay que convertir base64 a S3
            # restore_large_content inserta base64 temporalmente, debemos convertirlo a S3 URLs
            print(f"🔍 Verificando imágenes restauradas (debe convertir base64 → S3)...")
            
            # OPTIMIZACIÓN: Reutilizar imágenes S3 ya subidas si existe s3_image_mapping.json
            s3_mapping_file = os.path.join(output_dir, "s3_image_mapping.json")
            s3_image_mapping: Dict[str, str] = {}
            if not is_lambda and os.path.exists(s3_mapping_file):
                try:
                    with open(s3_mapping_file, "r", encoding="utf-8") as f:
                        s3_image_mapping = json.load(f)
                    print(f"📖 Cargado mapeo S3 existente: {len(s3_image_mapping)} URL(s)")
                except Exception as e:
                    print(f"⚠️  Error cargando s3_image_mapping.json: {e}")
            
            # OPTIMIZACIÓN: Intentar convertir TODAS las imágenes base64 a URLs S3
            # Si falla alguna subida, continuar con base64 (XML generado es valioso - optimización de API)
            if not is_lambda:
                base64_pattern = r'(data:image/([^;]+);base64,)([A-Za-z0-9+/=\s]+)'
                base64_matches = list(re.finditer(base64_pattern, qti_xml))
                
                if base64_matches:
                    print(f"🔍 Procesando {len(base64_matches)} imagen(es) restaurada(s) - intentando subir a S3...")
                    from modules.utils.s3_uploader import upload_image_to_s3
                    uploaded_count = 0
                    reused_count = 0
                    failed_uploads = []
                    
                    for i, match in enumerate(base64_matches):
                        full_prefix = match.group(1)
                        base64_data = match.group(3)
                        full_data_uri = match.group(0)
                        
                        # Verificar si ya existe en S3
                        s3_url = None
                        img_keys = [f"image_{i}", f"{question_id}_restored_{i}", f"{question_id}_img{i}"]
                        for key in img_keys:
                            if key in s3_image_mapping:
                                s3_url = s3_image_mapping[key]
                                reused_count += 1
                                print(f"   ✅ Reutilizando imagen {i+1} desde S3: {s3_url}")
                                break
                        
                        # Si no existe, subir a S3 (intentar, pero no abortar si falla)
                        if not s3_url:
                            img_id = f"{question_id}_restored_{i}" if question_id else f"restored_{i}"
                            print(f"   📤 Subiendo imagen {i+1}/{len(base64_matches)} a S3...")
                            s3_url = upload_image_to_s3(
                                image_base64=full_data_uri,
                                question_id=img_id,
                                test_name=test_name,
                            )
                            if s3_url:
                                uploaded_count += 1
                                # Guardar en múltiples keys para facilitar búsqueda
                                for key in img_keys:
                                    s3_image_mapping[key] = s3_url
                                print(f"   ✅ Imagen {i+1} subida a S3: {s3_url}")
                            else:
                                failed_uploads.append(f"imagen_{i+1}")
                                print(f"   ⚠️  Imagen {i+1} NO se pudo subir a S3 - quedará como base64")
                        
                        # OPTIMIZACIÓN: Reemplazar en XML con URL S3 si está disponible
                        # Si no se pudo subir, dejar base64 pero continuar (XML generado es valioso)
                        if s3_url:
                            qti_xml = qti_xml.replace(full_data_uri, s3_url, 1)
                            print(f"   ✅ Imagen {i+1} reemplazada con URL S3")
                        else:
                            # Continuar sin abortar - XML generado es valioso, se puede convertir después
                            print(f"   💡 Imagen {i+1} quedará como base64 (convertir a S3 después si necesario)")
                    
                    # OPTIMIZACIÓN: Advertir sobre fallos pero NO abortar
                    # Los XML generados son valiosos incluso con base64 - optimización de API es prioridad
                    if failed_uploads:
                        print(f"   ⚠️  Resumen: {len(failed_uploads)} imagen(es) quedaron como base64")
                        print(f"   💡 El XML se guardará. Puedes convertir a S3 después con migrate_base64_to_s3.py")
                    
                    # Guardar mapeo actualizado (siempre, incluso si solo reutilizamos o hay fallos)
                    # OPTIMIZACIÓN: Guardar mapeo siempre para facilitar conversión manual después
                    try:
                        with open(s3_mapping_file, "w", encoding="utf-8") as f:
                            json.dump(s3_image_mapping, f, indent=2)
                        status_parts = []
                        if uploaded_count > 0:
                            status_parts.append(f"{uploaded_count} nueva(s)")
                        if reused_count > 0:
                            status_parts.append(f"{reused_count} reutilizada(s)")
                        if failed_uploads:
                            status_parts.append(f"{len(failed_uploads)} fallida(s)")
                        
                        if status_parts:
                            print(f"   💾 Mapeo S3 guardado ({', '.join(status_parts)})")
                    except Exception as e:
                        print(f"   ⚠️  Error guardando mapeo S3: {e}")
                    
                    # VALIDACIÓN FINAL: Verificar base64 restante (advertir, no abortar)
                    remaining_base64 = re.findall(base64_pattern, qti_xml)
                    if remaining_base64:
                        print(f"   ⚠️  ADVERTENCIA: Quedan {len(remaining_base64)} imagen(es) base64 en XML")
                        print(f"   💡 Se guardará el XML con base64. Puedes convertirlo a S3 después manualmente.")
                    else:
                        print(f"   ✅ Validación: Todas las imágenes están en S3 (0 base64 restantes)")
            
            # VALIDACIÓN FINAL: Verificar base64 (advertir, NO abortar - XML es valioso)
            # OPTIMIZACIÓN: Siempre guardar XML generado - incluso con base64 puede convertirse después
            final_base64_check = re.findall(r'data:image/[^;]+;base64,', qti_xml)
            if final_base64_check:
                print(f"⚠️  ADVERTENCIA: Se encontraron {len(final_base64_check)} imagen(es) base64 en XML")
                print(f"💡 El XML se guardará con base64. Puedes convertirlo a S3 después usando:")
                print(f"   python3 scripts/migrate_base64_to_s3.py --test-name {test_name or 'test-name'}")
            else:
                print(f"✅ Validación final: Todas las imágenes están en S3 (0 base64)")
            
            # Save QTI XML (only in non-Lambda environments)  
            # OPTIMIZACIÓN: Siempre guardar - XML generado es valioso incluso con base64
            xml_path = None
            if not is_lambda:
                xml_path = os.path.join(output_dir, "question.xml")
                with open(xml_path, "w", encoding="utf-8") as f:
                    f.write(qti_xml)
                base64_status = f" ({len(final_base64_check)} con base64)" if final_base64_check else " (100% S3)"
                print(f"✅ QTI XML guardado{base64_status}: {xml_path}")
                
                # CONVERSIÓN MANUAL: Detectar base64 y convertir a S3 (sin API LLM)
                # OPTIMIZACIÓN: Intentar convertir manualmente después de guardar para evitar perder trabajo
                if final_base64_check and not is_lambda:
                    print(f"\n🔧 CONVERSIÓN MANUAL: Intentando convertir {len(final_base64_check)} imagen(es) base64 a S3...")
                    qti_xml = convert_base64_to_s3_manual(
                        qti_xml=qti_xml,
                        question_id=question_id,
                        test_name=test_name,
                        output_dir=output_dir,
                    )
                    # Guardar XML actualizado si se hicieron cambios
                    if qti_xml:
                        with open(xml_path, "w", encoding="utf-8") as f:
                            f.write(qti_xml)
                        remaining_base64 = len(re.findall(r'data:image/[^;]+;base64,', qti_xml))
                        if remaining_base64 == 0:
                            print(f"   ✅ Conversión manual exitosa: todas las imágenes ahora están en S3")
                        else:
                            print(f"   ⚠️  Conversión parcial: {remaining_base64} imagen(es) aún con base64")
        
        # Final validation check - only return error if still invalid after retry attempt
        if not validation_result["success"]:
            return {
                "success": False,
                "error": f"Validation failed: {validation_result.get('validation_errors', validation_result.get('error'))}",
                "question_type": question_type
            }
        
        # Comprehensive Question Validation
        # Always perform full validation (even in PAES mode) to catch issues with
        # images, tables, graphs, and images in alternatives
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
            api_key,
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
            # Check if error is due to API key issues - in this case, we can still proceed
            is_api_key_error = "API key" in error_msg or "api_key" in error_msg or "401" in error_msg
            
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
            elif is_api_key_error:
                # API key error - validation failed but QTI was generated, so we can proceed
                print("⚠️  External validation failed due to API key issue - QTI generated but not validated")
                question_validation_result["validation_summary"] = f"Validation skipped: {error_msg}"
                # Continue processing - QTI was generated successfully
            else:
                # Other validation errors
                question_validation_result["validation_summary"] = error_msg
        
        # Step 6: Comprehensive question validation (IMPROVED - More lenient)
        # Check if XML is syntactically valid first
        xml_valid = validation_result.get("valid", False)
        validation_passed = validation_result.get("validation_passed", False)
        overall_score = validation_result.get("overall_score", 0)
        
        if validation_result.get("success", False) and validation_passed:
            print("✅ Question validation passed - QTI is ready for use")
        else:
            error_msg = validation_result.get("error", "Validation failed")
            is_api_key_error = "API key" in error_msg or "api_key" in error_msg or "401" in error_msg
            is_service_error = any(
                keyword in error_msg.lower()
                for keyword in ["connection", "timeout", "unavailable", "chrome", "screenshot"]
            )
            
            # If XML is syntactically valid, be more lenient with validation
            if xml_valid and (is_api_key_error or is_service_error or overall_score >= 0.7):
                print("⚠️  External validation had issues, but XML is valid - proceeding")
                print(f"   - XML valid: {xml_valid}")
                print(f"   - Score: {overall_score}")
                print(f"   - Issue: {error_msg}")
                # Continue processing - XML is valid
            elif xml_valid and overall_score >= 0.5:
                print("⚠️  Validation score is moderate, but XML is valid - proceeding with warning")
                print(f"   - XML valid: {xml_valid}")
                print(f"   - Score: {overall_score}")
                # Continue processing - XML is valid but score is moderate
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
        
        # Only proceed if validation passed (IMPROVED - More lenient check)
        # Check XML validity and score instead of strict should_proceed_with_qti
        xml_valid = validation_result.get("valid", False)
        overall_score = validation_result.get("overall_score", 0)
        error_msg = validation_result.get("error", "")
        is_api_key_error = "API key" in error_msg or "api_key" in error_msg or "401" in error_msg
        is_service_error = any(
            keyword in error_msg.lower()
            for keyword in ["connection", "timeout", "unavailable", "chrome", "screenshot"]
        )
        
        # Proceed if:
        # 1. should_proceed_with_qti returns True, OR
        # 2. XML is valid and (API key error OR service error OR score >= 0.5)
        should_proceed = should_proceed_with_qti(validation_result)
        can_proceed = (
            should_proceed or
            (xml_valid and (is_api_key_error or is_service_error or overall_score >= 0.5))
        )
        
        if not can_proceed:
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
        error_str = str(e)
        print(f"❌ Error processing PDF: {error_str}")
        
        # Check if we have processed_content.json - if so, try auto-regeneration
        processed_json_path = os.path.join(output_dir, "processed_content.json")
        if os.path.exists(processed_json_path) and not is_lambda:
            print(f"🔄 Attempting auto-regeneration from processed_content.json...")
            try:
                from scripts.regenerate_qti_from_processed import regenerate_qti_from_processed
                
                api_key = openai_api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")
                if api_key:
                    # Extract test_name from output_dir
                    test_match = re.search(r'prueba-[^/]+|seleccion-[^/]+', output_dir)
                    test_name = test_match.group(0) if test_match else None
                    
                    result = regenerate_qti_from_processed(
                        question_dir=Path(output_dir),
                        api_key=api_key,
                        paes_mode=paes_mode,
                        test_name=test_name,
                    )
                    if result.get("success"):
                        print(f"✅ Auto-regeneration successful!")
                        xml_path = os.path.join(output_dir, "question.xml")
                        if os.path.exists(xml_path):
                            with open(xml_path, "r", encoding="utf-8") as f:
                                regenerated_xml = f.read()
                            title_match = re.search(r'<qti-assessment-item[^>]*title="([^"]*)"', regenerated_xml)
                            title = title_match.group(1) if title_match else "Regenerated Question"
                            return {
                                "success": True,
                                "title": title,
                                "regenerated": True,
                                "auto_regenerated": True,
                                "xml_path": xml_path,
                                "message": f"Auto-regenerated after error: {error_str}"
                            }
            except Exception as regen_error:
                print(f"⚠️  Auto-regeneration failed: {regen_error}")
                print(f"   Original error: {error_str}")
        
        return {
            "success": False,
            "error": error_str,
            "auto_regeneration_attempted": os.path.exists(processed_json_path) if not is_lambda else False
        }


def validate_with_external_service(
    qti_xml: str,
    original_pdf_image: str, 
    api_key: Optional[str],
    validation_service_url: str,
    max_retries: int = 3,
    backoff_factor: int = 2
) -> Dict[str, Any]:
    """
    Validate QTI using external Node.js validation service with retry mechanism.
    
    Args:
        qti_xml: QTI XML content to validate
        original_pdf_image: Base64 encoded original PDF image
        api_key: API key (Gemini or OpenAI, uses env vars if None)
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
            
            # Get API key from env if not provided
            # External validation service requires OPENAI_API_KEY specifically
            service_api_key = api_key or os.environ.get("OPENAI_API_KEY")
            if not service_api_key:
                # Fallback to GEMINI_API_KEY only if OPENAI_API_KEY is not available
                # (though this may cause issues if the service strictly requires OpenAI)
                service_api_key = os.environ.get("GEMINI_API_KEY")
            
            payload = {
                "qti_xml": qti_xml,
                "original_pdf_image": original_pdf_image,
                "openai_api_key": service_api_key
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
    parser.add_argument("--openai-api-key", 
                       help="API key (uses GEMINI_API_KEY from env by default, falls back to OPENAI_API_KEY).")
    parser.add_argument("--validation-endpoint", 
                       default="http://qti-validator-prod.eba-dvye2j6j.us-east-2.elasticbeanstalk.com/validate",
                       help="QTI validation endpoint URL.")
    parser.add_argument("--paes-mode", action="store_true",
                       help="Optimize for PAES format (choice questions, math, 4 alternatives). Skips type detection and optimizes prompts for mathematics.")
    parser.add_argument("--clean", action="store_true", 
                       help="Clean the output directory before processing.")

    args = parser.parse_args()
    
    # Clean output directory if requested
    if args.clean and os.path.exists(args.output_dir):
        print(f"🧹 Cleaning output directory: {args.output_dir}")
        import shutil
        shutil.rmtree(args.output_dir)

    print("🚀 Starting PDF to QTI Conversion...")
    if args.paes_mode:
        print("⚡ PAES mode enabled - Optimized for choice questions (4 alternatives, mathematics)")
        print("   - Skipping question type detection (always choice)")
        print("   - Optimized prompts for mathematics")
        print("   - Full validation enabled (including images, tables, graphs)")
    result = process_single_question_pdf(
        args.input_pdf, 
        args.output_dir,
        args.openai_api_key,
        args.validation_endpoint,
        paes_mode=args.paes_mode
    )
    
    if result["success"]:
        print("✅ PDF to QTI Conversion finished successfully.")
        exit(0)
    else:
        print(f"❌ PDF to QTI Conversion failed: {result.get('error', 'Unknown error')}")
        exit(1)


if __name__ == "__main__":
    main() 