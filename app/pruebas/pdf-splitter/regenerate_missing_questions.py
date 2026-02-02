#!/usr/bin/env python3
"""
Script para regenerar PDFs de preguntas específicas que fallaron la validación.
Usa los resultados de segmentación existentes para crear los PDFs directamente.
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


def regenerate_question_pdf(
    question_data: dict,
    original_pdf_path: str,
    output_path: str,
    results: dict
) -> bool:
    """
    Regenera un PDF individual para una pregunta usando datos de segmentación.

    Args:
        question_data: Datos de la pregunta desde segmentation_results.json
        original_pdf_path: Ruta al PDF original
        output_path: Ruta donde guardar el PDF generado
        results: Resultados completos de segmentación (para referencias compartidas)

    Returns:
        True si se generó exitosamente, False en caso contrario
    """
    try:
        doc = fitz.open(original_pdf_path)

        with tempfile.TemporaryDirectory() as tmpdir:
            ref_paths = []
            q_paths = []

            # Primero, agregar referencias compartidas si las hay
            for ref_id in question_data.get('multi_question_references', []):
                ref = next(
                    (r for r in results.get('multi_question_references', [])
                     if r.get('id') == ref_id),
                    None
                )
                if ref:
                    for rp, rb in zip(ref.get('page_nums', []), ref.get('bboxes', [])):
                        rp_idx = rp - 1
                        if 0 <= rp_idx < doc.page_count:
                            rpage = doc.load_page(rp_idx)
                            # rb es [x1, y1, x2, y2]
                            rx1 = max(0, rb[0] - 10)
                            ry1 = max(0, rb[1] - 10)
                            rx2 = min(rpage.rect.width, rb[2] + 10)
                            ry2 = min(rpage.rect.height, rb[3] + 10)
                            rrect = fitz.Rect(rx1, ry1, rx2, ry2)
                            r_temp = os.path.join(tmpdir, f"ref_{ref_id}_p{rp}.pdf")
                            create_pdf_from_region(rpage, rrect, r_temp)
                            ref_paths.append(r_temp)

            # Luego, extraer las páginas de la pregunta
            page_nums = question_data.get('page_nums', [])
            bboxes = question_data.get('bboxes', [])

            if not page_nums or not bboxes:
                print("   ⚠️  Falta información de páginas o bboxes")
                doc.close()
                return False

            for p, bbox in zip(page_nums, bboxes):
                page_idx = p - 1
                if 0 <= page_idx < doc.page_count:
                    page = doc.load_page(page_idx)
                    # bbox es [x1, y1, x2, y2]
                    x1 = max(0, bbox[0] - 10)
                    y1 = max(0, bbox[1] - 10)
                    x2 = min(page.rect.width, bbox[2] + 10)
                    y2 = min(page.rect.height, bbox[3] + 10)
                    rect = fitz.Rect(x1, y1, x2, y2)
                    q_temp = os.path.join(tmpdir, f"q_p{p}.pdf")
                    create_pdf_from_region(page, rect, q_temp)
                    q_paths.append(q_temp)

            # Combinar referencias y páginas de la pregunta
            final_paths = ref_paths + q_paths
            if final_paths:
                merge_pdfs(final_paths, output_path)
                doc.close()
                return True
            else:
                doc.close()
                return False

    except Exception as e:
        print(f"   ❌ Error generando PDF: {e}")
        if 'doc' in locals():
            doc.close()
        return False


def main():
    """Punto de entrada principal."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Regenerar PDFs de preguntas específicas que fallaron validación"
    )
    parser.add_argument(
        "--segmentation-file",
        required=True,
        help="Ruta al archivo segmentation_results.json"
    )
    parser.add_argument(
        "--original-pdf",
        required=True,
        help="Ruta al PDF original"
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directorio donde guardar los PDFs regenerados"
    )
    parser.add_argument(
        "--question-numbers",
        nargs="+",
        type=int,
        help="Números de preguntas a regenerar (ej: 26 40 47). Si no se especifica, regenera todas las faltantes."
    )

    args = parser.parse_args()

    # Cargar resultados de segmentación
    seg_file = Path(args.segmentation_file)
    if not seg_file.exists():
        print(f"❌ Archivo de segmentación no encontrado: {seg_file}")
        sys.exit(1)

    with open(seg_file, 'r', encoding='utf-8') as f:
        results = json.load(f)

    # Verificar PDF original
    original_pdf = Path(args.original_pdf)
    if not original_pdf.exists():
        print(f"❌ PDF original no encontrado: {original_pdf}")
        sys.exit(1)

    # Crear directorio de salida
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determinar qué preguntas regenerar
    if args.question_numbers:
        questions_to_regenerate = args.question_numbers
    else:
        # Si no se especifican, usar todas las preguntas de la segmentación
        questions_to_regenerate = []
        for q in results.get('questions', []):
            q_id = q.get('id', '')
            if q_id.startswith('Q'):
                try:
                    num = int(q_id[1:])
                    questions_to_regenerate.append(num)
                except ValueError:
                    pass

    print(f"🔄 Regenerando {len(questions_to_regenerate)} preguntas...")
    print()

    success_count = 0
    failed_count = 0

    for q_num in sorted(questions_to_regenerate):
        q_id = f"Q{q_num}"

        # Buscar datos de la pregunta
        question_data = None
        for q in results.get('questions', []):
            if q.get('id') == q_id:
                question_data = q
                break

        if not question_data:
            print(f"⚠️  {q_id}: No encontrada en resultados de segmentación")
            failed_count += 1
            continue

        # Generar PDF
        output_path = output_dir / f"Q{q_num}.pdf"
        print(f"📄 Generando {q_id}...", end=" ")

        if regenerate_question_pdf(question_data, str(original_pdf), str(output_path), results):
            print(f"✅ Guardado en {output_path}")
            success_count += 1
        else:
            print("❌ Falló")
            failed_count += 1

    print()
    print("=" * 60)
    print(f"✅ Exitosas: {success_count}")
    print(f"❌ Fallidas: {failed_count}")
    print(f"📊 Total: {len(questions_to_regenerate)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
