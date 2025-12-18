#!/usr/bin/env python3
"""
Script para regenerar QTI XML desde contenido ya procesado.

Este script lee processed_content.json y extracted_content.json existentes
y solo regenera el QTI XML, sin reprocesar el PDF. Esto es mucho más eficiente
y no agota la cuota de API innecesariamente.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
# Go up from scripts/ -> pdf-to-qti/ -> pruebas/ -> app/ -> root
project_root = Path(__file__).parent.parent.parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ Loaded environment variables from {env_file}")
else:
    # Try alternative path (if running from different location)
    alt_env = Path(__file__).parent.parent.parent.parent.parent / ".env"
    if alt_env.exists():
        load_dotenv(alt_env)
        print(f"✅ Loaded environment variables from {alt_env}")

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.qti_transformer import transform_to_qti
from modules.validation import validate_qti_xml
from modules.content_processing import restore_large_content, ExtractedContent
from modules.utils.s3_uploader import upload_image_to_s3
import re


def regenerate_qti_from_processed(
    question_dir: Path,
    api_key: str,
    paes_mode: bool = True,
    test_name: str | None = None,
) -> dict[str, any]:
    """
    Regenera QTI XML desde contenido ya procesado.
    
    Args:
        question_dir: Directorio de la pregunta (ej: Q19/)
        api_key: API key para transformación
        paes_mode: Si True, usa modo PAES (choice, 4 alternativas)
        test_name: Nombre del test para organizar imágenes en S3
        
    Returns:
        Resultado del procesamiento
    """
    processed_json = question_dir / "processed_content.json"
    detection_json = question_dir / "detection_result.json"
    extracted_json = question_dir / "extracted_content.json"
    
    # Verificar que existe el archivo necesario
    if not processed_json.exists():
        return {
            "success": False,
            "error": f"processed_content.json no encontrado en {question_dir}"
        }
    
    # Cargar contenido procesado (igual que el pipeline original)
    print(f"📖 Cargando processed_content.json...")
    with open(processed_json, "r", encoding="utf-8") as f:
        processed_content = json.load(f)
    
    # Preparar extracted_content_list para restore_large_content (igual que el pipeline original)
    extracted_content_list: list[ExtractedContent] = []
    question_id = question_dir.name
    
    if extracted_json.exists():
        print(f"📖 Cargando extracted_content.json para construir ExtractedContent...")
        with open(extracted_json, "r", encoding="utf-8") as f:
            extracted_content = json.load(f)
        
        # Construir lista de ExtractedContent desde el JSON
        # Buscar placeholders en processed_content y mapear con imágenes en extracted_content
        if processed_content.get('image_base64') and processed_content['image_base64'].startswith('CONTENT_PLACEHOLDER_'):
            placeholder = processed_content['image_base64']
            match = re.search(r'P(\d+)', placeholder)
            if match:
                idx = int(match.group(1))
                base64_data = None
                # Buscar en all_images del extracted_content
                if 'all_images' in extracted_content and idx < len(extracted_content['all_images']):
                    extracted_img = extracted_content['all_images'][idx]
                    if extracted_img.get('image_base64') and not extracted_img['image_base64'].startswith('CONTENT_PLACEHOLDER'):
                        base64_data = extracted_img['image_base64']
                # También intentar en image_base64 raíz del extracted_content si es P0
                elif idx == 0 and extracted_content.get('image_base64'):
                    if not extracted_content['image_base64'].startswith('CONTENT_PLACEHOLDER'):
                        base64_data = extracted_content['image_base64']
                
                if base64_data:
                    # Asegurar formato data URI
                    if not base64_data.startswith('data:'):
                        base64_data = f"data:image/png;base64,{base64_data}"
                    extracted_content_list.append(ExtractedContent(
                        placeholder=placeholder,
                        original_content=base64_data,
                        content_type='base64-image',
                        metadata={}
                    ))
        
        # Procesar all_images
        if processed_content.get('all_images'):
            for i, img_info in enumerate(processed_content['all_images']):
                placeholder = img_info.get('image_base64', '')
                if placeholder.startswith('CONTENT_PLACEHOLDER_'):
                    match = re.search(r'P(\d+)', placeholder)
                    if match:
                        idx = int(match.group(1))
                        base64_data = None
                        # Buscar en all_images del extracted_content
                        if 'all_images' in extracted_content and idx < len(extracted_content['all_images']):
                            extracted_img = extracted_content['all_images'][idx]
                            if extracted_img.get('image_base64') and not extracted_img['image_base64'].startswith('CONTENT_PLACEHOLDER'):
                                base64_data = extracted_img['image_base64']
                        # Si no encontramos y es P0, buscar en image_base64 raíz
                        elif idx == 0 and extracted_content.get('image_base64'):
                            if not extracted_content['image_base64'].startswith('CONTENT_PLACEHOLDER'):
                                base64_data = extracted_content['image_base64']
                        
                        if base64_data:
                            # Asegurar formato data URI
                            if not base64_data.startswith('data:'):
                                base64_data = f"data:image/png;base64,{base64_data}"
                            extracted_content_list.append(ExtractedContent(
                                placeholder=placeholder,
                                original_content=base64_data,
                                content_type='base64-image',
                                metadata={'image_index': i}
                            ))
    
    # Determinar tipo de pregunta
    if paes_mode:
        question_type = "choice"
        print("⚡ PAES mode: Usando tipo 'choice'")
    elif detection_json.exists():
        with open(detection_json, "r", encoding="utf-8") as f:
            detection_result = json.load(f)
        question_type = detection_result.get("question_type", "choice")
        print(f"🔍 Tipo detectado: {question_type}")
    else:
        question_type = "choice"
        print("⚠️  detection_result.json no encontrado, usando 'choice' por defecto")
    
    # Cargar respuesta correcta si existe
    correct_answer = None
    if test_name:
        answer_key_path = (
            question_dir.parent.parent.parent / "data" / "pruebas" / "procesadas" 
            / test_name / "respuestas_correctas.json"
        )
        if answer_key_path.exists():
            with open(answer_key_path, "r", encoding="utf-8") as f:
                answer_key_data = json.load(f)
            answers = answer_key_data.get("answers", {})
            
            # Extraer número de pregunta del nombre de la carpeta
            q_num_match = re.search(r'(\d+)', question_dir.name)
            if q_num_match:
                q_num = q_num_match.group(1)
                correct_answer = answers.get(q_num)
                if correct_answer:
                    print(f"✅ Respuesta correcta encontrada: {correct_answer}")
    
    # Transformar a QTI
    print(f"🔄 Transformando a QTI XML...")
    transformation_result = transform_to_qti(
        processed_content,
        question_type,
        api_key,
        question_id=question_id,
        use_s3=True,
        paes_mode=paes_mode,
        test_name=test_name,
        correct_answer=correct_answer,
        output_dir=str(question_dir),
    )
    
    if not transformation_result["success"]:
        return {
            "success": False,
            "error": f"Transformación falló: {transformation_result.get('error')}"
        }
    
    qti_xml = transformation_result["qti_xml"]
    
    # OPTIMIZACIÓN: Cargar s3_image_mapping.json si existe (imágenes ya subidas)
    s3_mapping_file = question_dir / "s3_image_mapping.json"
    s3_image_mapping: dict[str, str] = {}
    if s3_mapping_file.exists():
        print(f"📖 Cargando mapeo de imágenes S3 existente...")
        with open(s3_mapping_file, "r", encoding="utf-8") as f:
            s3_image_mapping = json.load(f)
        print(f"   ✅ Encontradas {len(s3_image_mapping)} URL(s) S3 en mapeo")
        
        # OPTIMIZACIÓN: Reemplazar placeholders directos en XML si ya tenemos URLs S3
        placeholder_pattern = r'CONTENT_PLACEHOLDER_([^"\'>\s]+)'
        placeholder_matches = re.findall(placeholder_pattern, qti_xml)
        if placeholder_matches:
            replaced_count = 0
            for placeholder in placeholder_matches:
                full_placeholder = f"CONTENT_PLACEHOLDER_{placeholder}"
                # Buscar en el mapeo por diferentes keys
                s3_url = None
                for key in [full_placeholder, f"CONTENT_PLACEHOLDER_{placeholder}"]:
                    if key in s3_image_mapping:
                        s3_url = s3_image_mapping[key]
                        break
                # También buscar por índices (P0, P1, etc.)
                if not s3_url:
                    match = re.search(r'P(\d+)', placeholder)
                    if match:
                        idx = int(match.group(1))
                        for key in [f"image_{idx}", f"{question_id}_img{idx}"]:
                            if key in s3_image_mapping:
                                s3_url = s3_image_mapping[key]
                                break
                
                if s3_url:
                    qti_xml = qti_xml.replace(full_placeholder, s3_url)
                    replaced_count += 1
                    print(f"   🔄 Reemplazado {full_placeholder} → {s3_url}")
            
            if replaced_count > 0:
                print(f"   ✅ Reemplazados {replaced_count} placeholder(s) con URLs S3 existentes")
    
    # Validar QTI XML (igual que el pipeline original - ANTES de restore_large_content)
    print(f"🔍 Validando QTI XML...")
    validation_result = validate_qti_xml(qti_xml)
    
    # OPTIMIZACIÓN: Cargar s3_image_mapping.json si existe (imágenes ya subidas)
    s3_mapping_file = question_dir / "s3_image_mapping.json"
    s3_image_mapping: dict[str, str] = {}
    if s3_mapping_file.exists():
        print(f"📖 Cargando mapeo de imágenes S3 existente...")
        with open(s3_mapping_file, "r", encoding="utf-8") as f:
            s3_image_mapping = json.load(f)
        print(f"   ✅ Encontradas {len(s3_image_mapping)} URL(s) S3 en mapeo")
    
    # Restaurar placeholders con base64 (igual que el pipeline original)
    # Solo hacerlo si la validación pasó y hay extracted_content
    if validation_result["success"] and extracted_content_list:
        print(f"🔄 Restaurando placeholders con imágenes desde extracted_content...")
        qti_xml = restore_large_content(qti_xml, extracted_content_list)
        
        # OPTIMIZACIÓN: Usar URLs S3 existentes del mapeo si están disponibles
        # Esto evita subir imágenes que ya están en S3
        print(f"🔍 Verificando imágenes restauradas...")
        base64_pattern = r'(data:image/([^;]+);base64,)([A-Za-z0-9+/=\s]+)'
        base64_matches = re.findall(base64_pattern, qti_xml)
        
        if base64_matches:
            print(f"   Encontradas {len(base64_matches)} imagen(es) base64...")
            uploaded_count = 0
            skipped_count = 0
            
            for i, match in enumerate(base64_matches):
                full_prefix = match[0]  # data:image/png;base64,
                base64_data = match[2]  # actual base64 data
                full_data_uri = full_prefix + base64_data
                
                # OPTIMIZACIÓN: Verificar si ya existe en el mapeo S3
                # Buscar en el mapeo usando diferentes keys posibles
                s3_url = None
                for key in [f"image_{i}", f"{question_id}_img{i}", f"{question_id}_restored_{i}"]:
                    if key in s3_image_mapping:
                        s3_url = s3_image_mapping[key]
                        print(f"   ✅ Usando URL S3 existente para imagen {i+1}: {s3_url}")
                        skipped_count += 1
                        break
                
                # Si no encontramos en el mapeo, subir a S3
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
                        # Guardar en el mapeo para futuros usos
                        s3_image_mapping[f"image_{i}"] = s3_url
                        s3_image_mapping[img_id] = s3_url
                
                if s3_url:
                    # Reemplazar en XML
                    qti_xml = qti_xml.replace(full_data_uri, s3_url, 1)
                    print(f"   ✅ Reemplazado con URL de S3: {s3_url}")
                else:
                    print(f"   ⚠️  Falló la subida a S3, dejando base64 en XML")
            
            # Guardar mapeo actualizado
            if s3_image_mapping:
                with open(s3_mapping_file, "w", encoding="utf-8") as f:
                    json.dump(s3_image_mapping, f, indent=2)
                if uploaded_count > 0:
                    print(f"   💾 Mapeo S3 actualizado ({uploaded_count} nueva(s), {skipped_count} existente(s))")
            else:
                print(f"   📊 Resumen: {uploaded_count} subida(s), {skipped_count} existente(s)")
    
    if not validation_result["success"]:
        return {
            "success": False,
            "error": f"Validación falló: {validation_result.get('validation_errors', validation_result.get('error'))}"
        }
    
    # Guardar QTI XML
    xml_path = question_dir / "question.xml"
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(qti_xml)
    
    print(f"✅ QTI XML guardado: {xml_path}")
    
    return {
        "success": True,
        "xml_path": str(xml_path),
        "question_type": question_type,
    }


def main():
    """Función principal."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Regenerar QTI XML desde contenido ya procesado"
    )
    parser.add_argument(
        "--question-numbers",
        nargs="+",
        type=int,
        required=True,
        help="Números de pregunta a procesar (ej: 19 22 23)"
    )
    parser.add_argument(
        "--output-dir",
        default="../../data/pruebas/procesadas/seleccion-regular-2026/qti",
        help="Directorio base con las carpetas de preguntas"
    )
    parser.add_argument(
        "--test-name",
        default="seleccion-regular-2026",
        help="Nombre del test para cargar respuestas correctas"
    )
    parser.add_argument(
        "--paes-mode",
        action="store_true",
        default=True,
        help="Usar modo PAES (default: True)"
    )
    
    args = parser.parse_args()
    
    # Obtener API key
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ No API key found. Set GEMINI_API_KEY or OPENAI_API_KEY in environment")
        sys.exit(1)
    
    output_base_dir = Path(args.output_dir)
    
    print("=" * 60)
    print("Regeneración de QTI desde contenido procesado")
    print("=" * 60)
    print(f"📁 Directorio: {output_base_dir}")
    print(f"📋 Preguntas: {len(args.question_numbers)}")
    print(f"⚡ PAES mode: {args.paes_mode}")
    print()
    
    success_count = 0
    failed_count = 0
    
    for i, q_num in enumerate(args.question_numbers, 1):
        question_dir = output_base_dir / f"Q{q_num}"
        
        print(f"[{i}/{len(args.question_numbers)}] Procesando Q{q_num}...")
        
        if not question_dir.exists():
            print(f"   ❌ Carpeta no encontrada: {question_dir}")
            failed_count += 1
            continue
        
        try:
            result = regenerate_qti_from_processed(
                question_dir=question_dir,
                api_key=api_key,
                paes_mode=args.paes_mode,
                test_name=args.test_name,
            )
            
            if result.get("success"):
                print(f"   ✅ Éxito")
                success_count += 1
            else:
                print(f"   ❌ Falló: {result.get('error', 'Unknown')}")
                failed_count += 1
        except Exception as e:
            print(f"   ❌ Excepción: {e}")
            failed_count += 1
        
        print()
    
    print("=" * 60)
    print(f"✅ Exitosas: {success_count}")
    print(f"❌ Fallidas: {failed_count}")
    print(f"📊 Total: {len(args.question_numbers)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
