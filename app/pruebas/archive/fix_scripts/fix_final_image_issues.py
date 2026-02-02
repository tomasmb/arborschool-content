#!/usr/bin/env python3
"""
Script para corregir problemas finales de imágenes.

Problemas a corregir:
1. Q27: Cortar más por arriba y alargar por la izquierda
2. Q38: Intercambiar imágenes (B↔A, D↔C) y extender bbox para incluir títulos de ejes
3. Q53: Recortar para mostrar solo el mapa de coordenadas (no toda la página)
4. Q50: Agregar imagen del enunciado
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict

# Load environment variables
from dotenv import load_dotenv

script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent.parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)

# Add modules to path
import sys

import fitz  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.pdf_processor import render_image_area
from modules.utils.s3_uploader import upload_image_to_s3


def fix_q27_final(question_dir: Path, pdf_path: Path, test_name: str) -> Dict[str, Any]:
    """
    Q27: Cortar más por arriba y alargar por la izquierda.
    """
    print("\n🔧 Corrigiendo Q27: Ajuste final de bbox")

    processed_file = question_dir / "processed_content.json"
    if not processed_file.exists():
        return {"success": False, "error": "processed_content.json no encontrado"}

    with open(processed_file, "r", encoding="utf-8") as f:
        processed_data = json.load(f)

    all_images = processed_data.get("all_images", [])
    if not all_images:
        return {"success": False, "error": "No hay imágenes en processed_content"}

    original_bbox = all_images[0].get("bbox", [])
    if len(original_bbox) != 4:
        return {"success": False, "error": "Bbox inválido"}

    # Ajustar: cortar más arriba y extender hacia la izquierda
    adjusted_bbox = original_bbox.copy()
    adjusted_bbox[0] = max(0, original_bbox[0] - 50)  # Extender más hacia la izquierda
    adjusted_bbox[1] = original_bbox[1] + 110  # Cortar más por arriba para excluir pregunta

    print(f"   📐 Bbox original: {[round(x, 1) for x in original_bbox]}")
    print(f"   📐 Bbox ajustado: {[round(x, 1) for x in adjusted_bbox]}")

    # Extraer imagen con bbox ajustado
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    rendered = render_image_area(page, adjusted_bbox, adjusted_bbox, 0)
    doc.close()

    if not rendered or not rendered.get("image_base64"):
        return {"success": False, "error": "No se pudo renderizar imagen ajustada"}

    # Subir a S3
    s3_url = upload_image_to_s3(
        image_base64=rendered["image_base64"],
        question_id="Q27_main",
        test_name=test_name,
    )

    if not s3_url:
        return {"success": False, "error": "No se pudo subir a S3"}

    # Actualizar XML
    xml_path = question_dir / "question.xml"
    with open(xml_path, "r", encoding="utf-8") as f:
        xml_content = f.read()

    img_pattern = r'(<img[^>]+src=")([^"]+)(")'
    matches = list(re.finditer(img_pattern, xml_content))
    if matches:
        old_url = matches[0].group(2)
        xml_content = xml_content.replace(old_url, s3_url, 1)

        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(xml_content)

        print("   ✅ Imagen actualizada con bbox final")

    return {"success": True, "s3_url": s3_url}


def fix_q38_swapped_and_extended(question_dir: Path, pdf_path: Path, test_name: str) -> Dict[str, Any]:
    """
    Q38: Intercambiar imágenes (B↔A, D↔C) y extender bbox para incluir títulos de ejes.
    """
    print("\n🔧 Corrigiendo Q38: Intercambiar imágenes y extender bbox")

    xml_path = question_dir / "question.xml"
    if not xml_path.exists():
        return {"success": False, "error": "XML no encontrado"}

    doc = fitz.open(str(pdf_path))
    page = doc[0]

    # Obtener todas las imágenes
    blocks = page.get_text("dict", sort=True)["blocks"]
    image_blocks = [b for b in blocks if b.get("type") == 1]

    if len(image_blocks) < 4:
        doc.close()
        return {"success": False, "error": f"Se esperaban 4 imágenes, se encontraron {len(image_blocks)}"}

    # Ordenar por posición (y primero, luego x)
    image_blocks.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))

    # Las primeras 2 son A y B (arriba), las siguientes 2 son C y D (abajo)
    # Pero están intercambiadas: B está en A, A está en B, D está en C, C está en D
    # Orden correcto: A, B, C, D
    # Orden actual en PDF: B, A, D, C

    # Extraer con bbox extendido para incluir títulos de ejes
    alternative_images = []
    order_map = [1, 0, 3, 2]  # Reordenar: B→A, A→B, D→C, C→D

    for i, original_idx in enumerate(order_map):
        if original_idx < len(image_blocks):
            img_block = image_blocks[original_idx]
            bbox = list(img_block["bbox"])  # Convertir tupla a lista

            # Extender bbox hacia arriba y abajo para incluir títulos de ejes
            bbox[1] = max(0, bbox[1] - 30)  # Extender hacia arriba
            bbox[3] = min(page.rect.height, bbox[3] + 30)  # Extender hacia abajo

            print(f"   📸 Extrayendo alternativa {chr(65+i)} (original {chr(65+original_idx)}) con bbox extendido: {[round(x, 1) for x in bbox]}")

            rendered = render_image_area(page, bbox, bbox, i)

            if rendered and rendered.get("image_base64"):
                s3_url = upload_image_to_s3(
                    image_base64=rendered["image_base64"],
                    question_id=f"Q38_alt{chr(65+i)}",
                    test_name=test_name,
                )
                if s3_url:
                    alternative_images.append(s3_url)
                    print(f"   ✅ Imagen alternativa {chr(65+i)} extraída y subida")

    doc.close()

    if len(alternative_images) != 4:
        return {"success": False, "error": f"Se esperaban 4 imágenes, se procesaron {len(alternative_images)}"}

    # Actualizar XML - reemplazar URLs en el orden correcto
    with open(xml_path, "r", encoding="utf-8") as f:
        xml_content = f.read()

    # Buscar cada alternativa y reemplazar su imagen
    for i, choice_letter in enumerate(['A', 'B', 'C', 'D']):
        pattern = rf'(<qti-simple-choice identifier="Choice{choice_letter}">.*?<img[^>]+src=")([^"]+)(")'
        replacement = f'\\1{alternative_images[i]}\\3'
        xml_content = re.sub(pattern, replacement, xml_content, flags=re.DOTALL)
        print(f"   ✅ Alternativa {choice_letter} actualizada")

    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(xml_content)

    return {"success": True}


def fix_q53_map_only(question_dir: Path, pdf_path: Path, test_name: str) -> Dict[str, Any]:
    """
    Q53: Recortar para mostrar solo el mapa de coordenadas (no toda la página).
    """
    print("\n🔧 Corrigiendo Q53: Recortar solo el mapa de coordenadas")

    processed_file = question_dir / "processed_content.json"
    if not processed_file.exists():
        return {"success": False, "error": "processed_content.json no encontrado"}

    with open(processed_file, "r", encoding="utf-8") as f:
        processed_data = json.load(f)

    # Obtener páginas para encontrar dónde termina la pregunta
    pages = processed_data.get("pages", [])
    if not pages:
        return {"success": False, "error": "No hay páginas"}

    page_data = pages[0]
    blocks = page_data.get("structured_text", {}).get("blocks", [])
    text_blocks = [b for b in blocks if b.get("type") == 0]

    # Encontrar dónde termina la pregunta
    question_end_y = 0
    for block in text_blocks:
        bbox = block.get("bbox", [])
        if len(bbox) == 4 and bbox[3] < 250:  # Texto antes de y=250
            question_end_y = max(question_end_y, bbox[3])

    # Agregar margen
    map_start_y = question_end_y + 40
    print(f"   📐 Mapa debería empezar en y={round(map_start_y, 1)}")

    # Extraer imagen del PDF recortando solo el área del mapa
    doc = fitz.open(str(pdf_path))

    # El mapa podría estar en la página 1 (segunda página)
    # Intentar página 1 primero, luego página 0
    map_bbox = None
    rendered = None

    for page_num in [1, 0]:
        if page_num < doc.page_count:
            page = doc[page_num]
            page_rect = page.rect

            # Si es página 1, usar toda la página (es pequeña, solo tiene el mapa)
            # Pero recortar más para mostrar solo el mapa, no toda la página
            if page_num == 1:
                # La página 1 tiene altura ~84, el mapa debería estar centrado
                # Recortar márgenes más agresivamente
                map_bbox = [
                    50,  # x0: margen izquierdo más grande
                    30,  # y0: margen superior
                    page_rect.width - 50,  # x1: margen derecho más grande
                    page_rect.height - 10  # y1: pequeño margen inferior
                ]
            else:
                # Página 0: recortar después de la pregunta
                map_bbox = [
                    50,  # x0: margen izquierdo
                    map_start_y,  # y0: después de la pregunta
                    page_rect.width - 50,  # x1: margen derecho
                    page_rect.height - 50  # y1: margen inferior
                ]

            print(f"   📐 Probando página {page_num}, bbox del mapa: {[round(x, 1) for x in map_bbox]}")

            rendered = render_image_area(page, map_bbox, map_bbox, 0)
            if rendered and rendered.get("image_base64"):
                print(f"   ✅ Mapa encontrado en página {page_num}")
                break

    doc.close()

    if not rendered or not rendered.get("image_base64"):
        return {"success": False, "error": "No se pudo renderizar mapa"}

    # Subir a S3
    map_image_url = upload_image_to_s3(
        image_base64=rendered["image_base64"],
        question_id="Q53_main",
        test_name=test_name,
    )

    if not map_image_url:
        return {"success": False, "error": "No se pudo subir a S3"}

    # Actualizar XML
    xml_path = question_dir / "question.xml"
    with open(xml_path, "r", encoding="utf-8") as f:
        xml_content = f.read()

    img_pattern = r'(<img[^>]+src=")([^"]+)(")'
    matches = list(re.finditer(img_pattern, xml_content))
    if matches:
        old_url = matches[0].group(2)
        xml_content = xml_content.replace(old_url, map_image_url, 1)

        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(xml_content)

        print("   ✅ Mapa recortado y actualizado")

    return {"success": True, "s3_url": map_image_url}


def fix_q50_enunciado(question_dir: Path, pdf_path: Path, test_name: str) -> Dict[str, Any]:
    """
    Q50: Agregar imagen del enunciado.
    """
    print("\n🔧 Corrigiendo Q50: Agregando imagen del enunciado")

    xml_path = question_dir / "question.xml"
    if not xml_path.exists():
        return {"success": False, "error": "XML no encontrado"}

    doc = fitz.open(str(pdf_path))
    page = doc[0]

    # Obtener todas las imágenes
    blocks = page.get_text("dict", sort=True)["blocks"]
    image_blocks = [b for b in blocks if b.get("type") == 1]

    # Buscar texto para encontrar dónde empiezan las alternativas
    text_blocks = [b for b in blocks if b.get("type") == 0]
    alt_start_y = 1000
    for block in text_blocks:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                if span.get("text", "").strip() == "A)":
                    alt_start_y = min(alt_start_y, block.get("bbox", [1000])[1])
                    break

    # La imagen del enunciado debería estar antes de alt_start_y
    enunciado_images = [img for img in image_blocks if img["bbox"][3] < alt_start_y]

    if not enunciado_images:
        doc.close()
        return {"success": False, "error": "No se encontró imagen del enunciado"}

    # Usar la imagen más grande del enunciado
    largest_enunciado = max(
        enunciado_images,
        key=lambda b: (b["bbox"][2] - b["bbox"][0]) * (b["bbox"][3] - b["bbox"][1])
    )

    bbox = largest_enunciado["bbox"]
    print(f"   📸 Extrayendo imagen del enunciado de bbox: {[round(x, 1) for x in bbox]}")

    rendered = render_image_area(page, bbox, bbox, 0)
    doc.close()

    if not rendered or not rendered.get("image_base64"):
        return {"success": False, "error": "No se pudo renderizar imagen del enunciado"}

    # Subir a S3
    s3_url = upload_image_to_s3(
        image_base64=rendered["image_base64"],
        question_id="Q50_enunciado",
        test_name=test_name,
    )

    if not s3_url:
        return {"success": False, "error": "No se pudo subir a S3"}

    # Actualizar XML - agregar imagen antes del choice-interaction (solo una vez)
    with open(xml_path, "r", encoding="utf-8") as f:
        xml_content = f.read()

    # Verificar si ya existe la imagen del enunciado
    if 'Q50_enunciado' in xml_content:
        # Ya existe, solo actualizar la primera ocurrencia
        pattern = r'(<p><img[^>]+src=")([^"]*Q50_enunciado[^"]*)(")'
        xml_content = re.sub(pattern, f'\\1{s3_url}\\3', xml_content, count=1)
    else:
        # Buscar el choice-interaction y agregar imagen antes (solo una vez)
        pattern = r'(</p>\s*)(<qti-choice-interaction)'
        replacement = f'</p>\n    <p><img src="{s3_url}" alt="Figura del enunciado: círculo con lana en su contorno"/></p>\n    \\2'
        xml_content = re.sub(pattern, replacement, xml_content, count=1)

    # Eliminar imágenes duplicadas del enunciado
    # Contar cuántas veces aparece Q50_enunciado
    enunciado_count = xml_content.count('Q50_enunciado')
    if enunciado_count > 1:
        # Mantener solo la primera, eliminar las demás
        parts = xml_content.split('Q50_enunciado')
        # Reconstruir manteniendo solo la primera ocurrencia
        xml_content = parts[0] + 'Q50_enunciado' + parts[1].split('Q50_enunciado')[0] + parts[-1]
        print(f"   ✅ Eliminadas {enunciado_count - 1} imagen(es) duplicada(s) del enunciado")

    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(xml_content)

    print("   ✅ Imagen del enunciado agregada")
    return {"success": True}


def main():
    """Corregir todos los problemas finales."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Fix final image issues"
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

    args = parser.parse_args()

    questions_dir = Path(args.questions_dir)
    output_dir = Path(args.output_dir)
    test_name = "Prueba-invierno-2025"

    print("=" * 60)
    print("🔧 CORRECCIÓN FINAL DE IMÁGENES")
    print("=" * 60)
    print()

    fixes = [
        (27, fix_q27_final, "Ajuste final bbox (cortar arriba, alargar izquierda)"),
        (38, fix_q38_swapped_and_extended, "Intercambiar imágenes y extender bbox"),
        (50, fix_q50_enunciado, "Agregar imagen del enunciado"),
        (53, fix_q53_map_only, "Recortar solo el mapa de coordenadas"),
    ]

    success_count = 0
    failed_count = 0

    for q_num, fix_func, description in fixes:
        question_id = f"Q{q_num}"
        pdf_path = questions_dir / f"{question_id}.pdf"
        question_dir = output_dir / question_id

        print(f"[{fixes.index((q_num, fix_func, description)) + 1}/{len(fixes)}] {question_id}: {description}")

        if not pdf_path.exists():
            print("   ❌ PDF no encontrado")
            failed_count += 1
            continue

        if not question_dir.exists():
            print("   ❌ Directorio no encontrado")
            failed_count += 1
            continue

        try:
            result = fix_func(question_dir, pdf_path, test_name)
            if result.get("success"):
                success_count += 1
            else:
                print(f"   ❌ Error: {result.get('error')}")
                failed_count += 1
        except Exception as e:
            print(f"   ❌ Excepción: {e}")
            import traceback
            traceback.print_exc()
            failed_count += 1

        print()

    print("=" * 60)
    print("📊 RESUMEN")
    print("=" * 60)
    print(f"✅ Exitosas: {success_count}")
    print(f"❌ Fallidas: {failed_count}")
    print(f"📊 Total: {len(fixes)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
