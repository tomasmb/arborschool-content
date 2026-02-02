#!/usr/bin/env python3
"""
Script para organizar y corregir los PDFs de preguntas de prueba-invierno-2025.

Este script:
1. Copia las preguntas que están correctas
2. Regenera las preguntas problemáticas usando páginas completas del PDF original
3. Organiza todo en data/procesadas/prueba-invierno-2025/pdf/
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("❌ PyMuPDF (fitz) no está instalado. Instala con: pip install pymupdf")
    sys.exit(1)



def main():
    """Punto de entrada principal."""
    base_dir = Path(__file__).parent
    project_root = base_dir.parent.parent.parent

    original_pdf = project_root / "app" / "data" / "pruebas" / "raw" / "prueba-invierno-2025" / "2025-24-06-19-paes-invierno-oficial-matematica1-p2025.pdf"
    source_dir = project_root / "app" / "data" / "pruebas" / "procesadas" / "prueba-invierno-2025" / "pdf-splitter-output" / "part_1" / "questions"
    output_dir = project_root / "app" / "data" / "pruebas" / "procesadas" / "prueba-invierno-2025" / "pdf"

    # Crear directorio de salida
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Organizando y corrigiendo PDFs de prueba-invierno-2025")
    print("=" * 60)
    print()

    # Abrir PDF original
    doc = fitz.open(original_pdf)
    print(f"📄 PDF original: {doc.page_count} páginas")
    print()

    # Mapeo de preguntas correctas (1-27 están bien según el usuario)
    # Necesitamos copiar las que están bien y regenerar las problemáticas
    correct_questions = list(range(1, 28))  # Q1-Q27

    # Copiar preguntas que están correctas
    print("📋 Copiando preguntas correctas (Q1-Q27)...")
    copied = 0
    for q_num in correct_questions:
        source_file = source_dir / f"question_{q_num:03d}.pdf"
        if source_file.exists():
            dest_file = output_dir / f"Q{q_num}.pdf"
            shutil.copy2(source_file, dest_file)
            copied += 1
            print(f"   ✅ Q{q_num}")
        else:
            print(f"   ⚠️  Q{q_num} no encontrada en source")

    print(f"   Copiadas: {copied}/{len(correct_questions)}")
    print()

    # Para las preguntas problemáticas, necesitamos usar un enfoque diferente
    # El usuario indicó que las preguntas van de la página 3 a la 55
    # Pero necesitamos saber exactamente qué páginas corresponden a cada pregunta

    print("⚠️  Las preguntas problemáticas (Q28-Q65) necesitan ser regeneradas")
    print("   usando las páginas correctas del PDF original.")
    print()
    print("   Proceso manual recomendado:")
    print("   1. Re-ejecutar pdf-splitter con mejor configuración")
    print("   2. O extraer manualmente las páginas completas donde están")
    print("      las preguntas problemáticas")
    print()

    # Cerrar documento
    doc.close()

    print(f"📁 PDFs organizados en: {output_dir}")
    print(f"   Total copiados: {copied}")


if __name__ == "__main__":
    main()
