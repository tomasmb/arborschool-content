#!/usr/bin/env python3
"""
Script para corregir las preguntas mal segmentadas de Prueba-invierno-2025.

Errores identificados:
- Q28 no capturó las alternativas, Q29 son las alternativas de Q28 -> combinar
- Faltan preguntas 40-44
- Desplazamientos: Q45-Q63 tienen contenido incorrecto (desplazados)
- Faltan Q64 y Q65
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("❌ PyMuPDF (fitz) no está instalado. Instala con: pip install pymupdf")
    sys.exit(1)

from modules.pdf_utils import create_pdf_from_region, merge_pdfs


def extract_full_page_for_question(
    doc: fitz.Document,
    page_num: int,
    output_path: str
) -> bool:
    """Extrae una página completa como PDF."""
    try:
        page = doc.load_page(page_num - 1)
        rect = page.rect
        create_pdf_from_region(page, rect, output_path)
        return True
    except Exception as e:
        print(f"   ❌ Error extrayendo página {page_num}: {e}")
        return False


def combine_questions_from_pages(
    doc: fitz.Document,
    page_nums: list[int],
    output_path: str
) -> bool:
    """Combina múltiples páginas completas en un PDF."""
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            page_paths = []
            for page_num in page_nums:
                temp_path = os.path.join(tmpdir, f"page_{page_num}.pdf")
                if extract_full_page_for_question(doc, page_num, temp_path):
                    page_paths.append(temp_path)

            if page_paths:
                merge_pdfs(page_paths, output_path)
                return True
            return False
    except Exception as e:
        print(f"   ❌ Error combinando páginas: {e}")
        return False


def main():
    """Punto de entrada principal."""
    original_pdf = Path("../../data/pruebas/raw/Prueba-invierno-2025/2025-24-06-19-paes-invierno-oficial-matematica1-p2025.pdf")
    output_dir = Path("../../data/pruebas/procesadas/Prueba-invierno-2025/pdf")
    segmentation_file = Path("../../data/pruebas/procesadas/Prueba-invierno-2025/pdf-splitter-output/part_1/segmentation_results.json")

    # Crear directorio de salida
    output_dir.mkdir(parents=True, exist_ok=True)

    # Cargar segmentación para obtener información de bboxes cuando sea posible
    with open(segmentation_file, 'r', encoding='utf-8') as f:
        segmentation = json.load(f)

    questions_dict = {q.get('id'): q for q in segmentation.get('questions', [])}

    # Abrir PDF original
    doc = fitz.open(original_pdf)
    print(f"📄 PDF abierto: {doc.page_count} páginas")
    print()

    # Mapeo de correcciones basado en el análisis del usuario
    # Las preguntas van de la página 3 a la 55 según el usuario
    # Necesitamos re-extraer las problemáticas

    print("🔧 Este script necesita ser completado con la lógica de corrección")
    print("   basada en el análisis manual de las páginas del PDF.")
    print()
    print("   Para corregir esto correctamente, necesitamos:")
    print("   1. Re-segmentar el PDF completo de nuevo")
    print("   2. O extraer manualmente las páginas completas donde están las preguntas problemáticas")
    print()
    print("   Recomendación: Re-ejecutar el pdf-splitter con mejor configuración")

    doc.close()


if __name__ == "__main__":
    main()
