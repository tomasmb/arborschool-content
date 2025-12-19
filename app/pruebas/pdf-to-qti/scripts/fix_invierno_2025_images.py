#!/usr/bin/env python3
"""
Script para corregir problemas de imágenes en Prueba Invierno 2025.

Problemas reportados:
1. Q6, Q7, Q8, Q9, Q29, Q31, Q33, Q35, Q43, Q45, Q46, Q48, Q51, Q54, Q56: 
   Tienen imagen incorrecta (la de Q14)
2. Q38: Imagen incorrecta de Q14 + no debería tener imagen en enunciado
3. Q27: Imagen cortada por la izquierda e incluye parte de pregunta de arriba
4. Q53: Falta imagen del mapa cartesiano en el enunciado
5. Q65: Imágenes incorrectas en las alternativas
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent.parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ Loaded environment variables from {env_file}")

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import process_single_question_pdf


def main():
    """Reprocesar preguntas con problemas de imágenes."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Fix image issues in Prueba Invierno 2025 questions"
    )
    parser.add_argument(
        "--questions-dir",
        default="../../data/pruebas/procesadas/Prueba-invierno-2025/pdf",
        help="Directory with question PDFs"
    )
    parser.add_argument(
        "--output-dir",
        default="../../data/pruebas/procesadas/Prueba-invierno-2025/qti",
        help="Output directory for QTI files"
    )
    parser.add_argument(
        "--question-numbers",
        nargs="+",
        type=int,
        help="Specific question numbers to fix (if not provided, fixes all reported issues)"
    )
    
    args = parser.parse_args()
    
    # Preguntas con problemas reportados
    questions_with_wrong_image = [6, 7, 8, 9, 29, 31, 33, 35, 43, 45, 46, 48, 51, 54, 56]
    questions_special_cases = {
        27: "Imagen cortada",
        38: "Imagen incorrecta + no debería tener imagen en enunciado",
        53: "Falta imagen del mapa cartesiano",
        65: "Imágenes incorrectas en alternativas"
    }
    
    # Determinar qué preguntas procesar
    if args.question_numbers:
        questions_to_fix = args.question_numbers
    else:
        questions_to_fix = questions_with_wrong_image + list(questions_special_cases.keys())
    
    questions_dir = Path(args.questions_dir)
    output_dir = Path(args.output_dir)
    
    print("=" * 60)
    print("🔧 CORRECCIÓN DE IMÁGENES - Prueba Invierno 2025")
    print("=" * 60)
    print(f"📋 Preguntas a corregir: {len(questions_to_fix)}")
    print(f"   {', '.join(f'Q{q}' for q in sorted(questions_to_fix))}")
    print()
    
    success_count = 0
    failed_count = 0
    
    for q_num in sorted(questions_to_fix):
        question_id = f"Q{q_num}"
        pdf_path = questions_dir / f"{question_id}.pdf"
        question_output_dir = output_dir / question_id
        
        print(f"[{questions_to_fix.index(q_num) + 1}/{len(questions_to_fix)}] 🔧 Corrigiendo {question_id}...")
        
        if q_num in questions_special_cases:
            print(f"   ⚠️  Caso especial: {questions_special_cases[q_num]}")
        
        if not pdf_path.exists():
            print(f"   ❌ PDF no encontrado: {pdf_path}")
            failed_count += 1
            continue
        
        try:
            # Reprocesar con skip_if_exists=False para forzar regeneración
            result = process_single_question_pdf(
                input_pdf_path=str(pdf_path),
                output_dir=str(question_output_dir),
                openai_api_key=None,  # Use from .env
                paes_mode=True,
                skip_if_exists=False,  # IMPORTANTE: Forzar regeneración
            )
            
            if result.get('success'):
                print(f"   ✅ {question_id} corregida exitosamente")
                success_count += 1
            else:
                error = result.get('error', 'Unknown error')
                print(f"   ❌ {question_id} falló: {error}")
                failed_count += 1
        except Exception as e:
            print(f"   ❌ {question_id} excepción: {e}")
            failed_count += 1
        
        print()
    
    print("=" * 60)
    print("📊 RESUMEN")
    print("=" * 60)
    print(f"✅ Exitosas: {success_count}")
    print(f"❌ Fallidas: {failed_count}")
    print(f"📊 Total: {len(questions_to_fix)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
