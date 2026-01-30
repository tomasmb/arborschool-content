#!/usr/bin/env python3
"""
Script para procesar las preguntas faltantes (53 y 59).
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ Loaded environment variables from {env_file}")

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent))

from main import process_single_question_pdf


def main():
    questions_to_process = [53, 59]
    base_dir = Path(__file__).parent

    results = {}

    for qnum in questions_to_process:
        qnum_str = f"{qnum:03d}"
        pdf_path = base_dir.parent / "pdf-splitter" / "output" / "paes-invierno" / "questions_pdfs" / f"question_{qnum_str}.pdf"
        output_dir = base_dir / "output" / "paes-invierno-2026-new" / f"question_{qnum_str}"

        print("=" * 60)
        print(f"Procesando pregunta {qnum}...")
        print("=" * 60)
        print(f"PDF: {pdf_path}")
        print(f"Output: {output_dir}")
        print()

        if not pdf_path.exists():
            print(f"❌ PDF no encontrado: {pdf_path}")
            results[qnum] = {"success": False, "error": "PDF not found"}
            continue

        try:
            result = process_single_question_pdf(
                input_pdf_path=str(pdf_path),
                output_dir=str(output_dir),
                openai_api_key=None,  # Use from .env
                paes_mode=True,
            )

            if result.get("success"):
                print(f"✅ Pregunta {qnum} procesada exitosamente")
                print(f"   Título: {result.get('title', 'N/A')}")
            else:
                print(f"❌ Error procesando pregunta {qnum}: {result.get('error', 'Unknown error')}")

            results[qnum] = result

        except Exception as e:
            print(f"❌ Excepción procesando pregunta {qnum}: {e}")
            results[qnum] = {"success": False, "error": str(e)}

        print()

    # Summary
    print("=" * 60)
    print("RESUMEN")
    print("=" * 60)
    for qnum in questions_to_process:
        status = "✅ Procesada" if results.get(qnum, {}).get("success") else "❌ Falló"
        print(f"Pregunta {qnum}: {status}")
        if not results.get(qnum, {}).get("success"):
            print(f"   Error: {results[qnum].get('error', 'Unknown')}")

    # Check if files were created
    print()
    print("Verificando archivos generados:")
    for qnum in questions_to_process:
        qnum_str = f"{qnum:03d}"
        xml_path = base_dir / "output" / "paes-invierno-2026-new" / f"question_{qnum_str}" / "question.xml"
        if xml_path.exists():
            print(f"   ✅ question_{qnum_str}/question.xml existe")
        else:
            print(f"   ❌ question_{qnum_str}/question.xml NO existe")

if __name__ == "__main__":
    main()
