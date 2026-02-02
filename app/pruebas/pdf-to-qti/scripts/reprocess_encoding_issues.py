#!/usr/bin/env python3
"""
Script para reprocesar preguntas con problemas de codificación de caracteres.
Reprocesa solo las preguntas 9, 41, 52, 54 que tienen problemas de tildes y "ñ".
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
project_root = Path(__file__).parent.parent.parent  # Go up to arborschool-content root
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ Loaded environment variables from {env_file}")
else:
    # Try alternative location
    alt_env = Path(__file__).parent.parent / ".env"
    if alt_env.exists():
        load_dotenv(alt_env)
        print(f"✅ Loaded environment variables from {alt_env}")
    else:
        print(f"⚠️  .env file not found at {env_file} or {alt_env}")

# Agregar el directorio padre al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import process_single_question_pdf


def main():
    """Reprocesar preguntas con problemas de codificación."""
    # Preguntas con problemas de codificación
    questions_to_reprocess = [9, 41, 52, 54]

    # Directorios base
    base_dir = Path(__file__).parent.parent
    input_dir = base_dir.parent / "pdf-splitter" / "output" / "paes-invierno" / "questions_pdfs"
    output_base = base_dir / "output" / "paes-invierno-2026-new"

    print(f"🔄 Reprocesando {len(questions_to_reprocess)} preguntas con problemas de codificación...")
    print(f"   Preguntas: {', '.join(map(str, questions_to_reprocess))}")
    print()

    success_count = 0
    failed_count = 0

    for question_num in questions_to_reprocess:
        question_num_str = f"{question_num:03d}"
        input_pdf = input_dir / f"question_{question_num_str}.pdf"
        output_dir = output_base / f"question_{question_num_str}"

        if not input_pdf.exists():
            print(f"❌ Pregunta {question_num}: PDF no encontrado en {input_pdf}")
            failed_count += 1
            continue

        print(f"📄 Procesando pregunta {question_num}...")

        try:
            result = process_single_question_pdf(
                input_pdf_path=str(input_pdf),
                output_dir=str(output_dir),
                openai_api_key=None,  # Use from .env
                paes_mode=True,
            )

            if result.get("success"):
                print(f"✅ Pregunta {question_num}: Procesada exitosamente")
                success_count += 1
            else:
                error = result.get("error", "Error desconocido")
                print(f"❌ Pregunta {question_num}: Error - {error}")
                failed_count += 1
        except Exception as e:
            print(f"❌ Pregunta {question_num}: Excepción - {str(e)}")
            failed_count += 1

        print()

    print("=" * 60)
    print("📊 Resumen:")
    print(f"   ✅ Exitosas: {success_count}")
    print(f"   ❌ Fallidas: {failed_count}")
    print(f"   📝 Total: {len(questions_to_reprocess)}")
    print("=" * 60)

if __name__ == "__main__":
    main()
