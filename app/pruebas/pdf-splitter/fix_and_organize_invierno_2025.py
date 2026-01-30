#!/usr/bin/env python3
"""
Script para corregir y organizar los PDFs de Prueba-invierno-2025.

Según el análisis del usuario:
- Q1-Q27: Están correctas (copiar)
- Q28: No capturó alternativas (necesita corrección - combinar con Q29)
- Q29: Son las alternativas de Q28 (necesita corrección)
- Q30-Q39: Necesitan verificación
- Q40-Q44: Faltan completamente
- Q45-Q63: Tienen contenido desplazado (Q45 tiene Q41, etc.)
- Q64-Q65: Faltan completamente

Este script organiza las preguntas correctas y prepara la estructura para las correcciones.
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

    original_pdf = project_root / "app" / "data" / "pruebas" / "raw" / "Prueba-invierno-2025" / "2025-24-06-19-paes-invierno-oficial-matematica1-p2025.pdf"
    source_dir = project_root / "app" / "data" / "pruebas" / "procesadas" / "Prueba-invierno-2025" / "pdf-splitter-output" / "part_1" / "questions"
    output_dir = project_root / "app" / "data" / "pruebas" / "procesadas" / "Prueba-invierno-2025" / "pdf"

    # Crear directorio de salida
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Organizando PDFs de Prueba-invierno-2025")
    print("=" * 60)
    print()

    # Verificar que el directorio source existe
    if not source_dir.exists():
        print(f"❌ Directorio source no encontrado: {source_dir}")
        sys.exit(1)

    # Preguntas que están correctas según el usuario (Q1-Q27)
    correct_questions = list(range(1, 28))

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
            print(f"   ⚠️  Q{q_num} no encontrada")

    print(f"   Copiadas: {copied}/{len(correct_questions)}")
    print()

    # Listar preguntas problemáticas que necesitan corrección
    print("⚠️  Preguntas que necesitan corrección:")
    print("   - Q28: Falta alternativas (combinar con Q29)")
    print("   - Q29: Son alternativas de Q28")
    print("   - Q40-Q44: Faltan completamente")
    print("   - Q45-Q63: Contenido desplazado (necesitan re-segmentación)")
    print("   - Q64-Q65: Faltan completamente")
    print()
    print("💡 Recomendación: Re-ejecutar pdf-splitter para estas secciones")
    print("   o corregir manualmente usando el PDF original.")
    print()

    print(f"📁 PDFs organizados en: {output_dir}")
    print(f"   Total copiados: {copied}")
    print()
    print("📝 Próximos pasos:")
    print("   1. Re-segmentar Q28-Q29 (combinar correctamente)")
    print("   2. Generar Q40-Q44 (faltantes)")
    print("   3. Re-segmentar Q45-Q63 (corregir desplazamientos)")
    print("   4. Generar Q64-Q65 (faltantes)")


if __name__ == "__main__":
    main()
