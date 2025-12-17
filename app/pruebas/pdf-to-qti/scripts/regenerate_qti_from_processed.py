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
    
    # Verificar que existe el archivo necesario
    if not processed_json.exists():
        return {
            "success": False,
            "error": f"processed_content.json no encontrado en {question_dir}"
        }
    
    # Cargar contenido procesado
    print(f"📖 Cargando processed_content.json...")
    with open(processed_json, "r", encoding="utf-8") as f:
        processed_content = json.load(f)
    
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
            import re
            q_num_match = re.search(r'(\d+)', question_dir.name)
            if q_num_match:
                q_num = q_num_match.group(1)
                correct_answer = answers.get(q_num)
                if correct_answer:
                    print(f"✅ Respuesta correcta encontrada: {correct_answer}")
    
    # Generar question_id desde el nombre de la carpeta
    question_id = question_dir.name
    
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
    )
    
    if not transformation_result["success"]:
        return {
            "success": False,
            "error": f"Transformación falló: {transformation_result.get('error')}"
        }
    
    qti_xml = transformation_result["qti_xml"]
    
    # Validar QTI XML
    print(f"🔍 Validando QTI XML...")
    validation_result = validate_qti_xml(qti_xml)
    
    if not validation_result["success"]:
        return {
            "success": False,
            "error": f"Validación falló: {validation_result.get('validation_errors', validation_result.get('error'))}"
        }
    
    # Nota: No necesitamos restore_large_content porque las imágenes ya están en S3
    # y los placeholders en el QTI XML ya son URLs de S3, no base64
    
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
