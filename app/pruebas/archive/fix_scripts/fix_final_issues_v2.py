#!/usr/bin/env python3
"""
Script para corregir problemas finales de imágenes - Versión 2.

Problemas a corregir:
1. Q27: Usar la imagen proporcionada por el usuario
2. Q38: Intercambiar correctamente (A↔B, C↔D) y extender más bbox para A y B
3. Q50: Agregar texto faltante y reposicionar imagen del enunciado
4. Q53: Recortar más agresivamente para mostrar solo el mapa
"""

from __future__ import annotations

import base64
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


def fix_q27_with_provided_image(question_dir: Path, pdf_path: Path, test_name: str, image_path: Path) -> Dict[str, Any]:
    """
    Q27: Usar la imagen proporcionada por el usuario.
    """
    print("\n🔧 Corrigiendo Q27: Usando imagen proporcionada")

    if not image_path.exists():
        return {"success": False, "error": f"Imagen no encontrada: {image_path}"}

    # Leer imagen y convertir a base64
    with open(image_path, "rb") as f:
        image_data = f.read()

    image_base64 = base64.b64encode(image_data).decode("utf-8")

    # Subir a S3
    s3_url = upload_image_to_s3(
        image_base64=image_base64,
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

        print("   ✅ Imagen actualizada con la proporcionada por el usuario")

    return {"success": True, "s3_url": s3_url}


def fix_q38_correct_swap_and_extend(question_dir: Path, pdf_path: Path, test_name: str) -> Dict[str, Any]:
    """
    Q38: Intercambiar correctamente (A↔B, C↔D) y extender más bbox para A y B.
    """
    print("\n🔧 Corrigiendo Q38: Intercambiar correctamente y extender bbox")

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

    # Orden actual en PDF: [0]=B, [1]=A, [2]=D, [3]=C
    # Necesitamos: A, B, C, D
    # Mapeo correcto: [1, 0, 3, 2] para obtener A, B, C, D

    alternative_images = []
    order_map = [1, 0, 3, 2]  # B→A, A→B, D→C, C→D

    for i, original_idx in enumerate(order_map):
        if original_idx < len(image_blocks):
            img_block = image_blocks[original_idx]
            bbox = list(img_block["bbox"])

            # Extender bbox más agresivamente para A y B (primeras dos)
            if i < 2:  # A y B
                bbox[1] = max(0, bbox[1] - 50)  # Extender más hacia arriba
                bbox[3] = min(page.rect.height, bbox[3] + 50)  # Extender más hacia abajo
            else:  # C y D
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


def fix_q50_text_and_position(question_dir: Path, pdf_path: Path, test_name: str) -> Dict[str, Any]:
    """
    Q50: Agregar texto faltante y reposicionar imagen del enunciado.
    """
    print("\n🔧 Corrigiendo Q50: Agregar texto faltante y reposicionar imagen")

    xml_path = question_dir / "question.xml"
    if not xml_path.exists():
        return {"success": False, "error": "XML no encontrado"}

    # Leer el PDF para obtener el texto completo
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    full_text = page.get_text()
    doc.close()

    # Buscar el texto completo de la pregunta
    # El texto debería incluir "cómo se representa en la siguiente forma:"
    print("   📝 Texto completo del PDF (primeros 500 caracteres):")
    print(f"   {full_text[:500]}")

    # Actualizar XML
    with open(xml_path, "r", encoding="utf-8") as f:
        xml_content = f.read()

    # Extraer el texto completo del PDF
    # Buscar el texto que contiene "cómo se representa" o similar
    lines = full_text.split('\n')
    question_text = ""
    for i, line in enumerate(lines):
        if '50' in line or 'Para verificar' in line:
            # Capturar desde aquí hasta encontrar las alternativas
            question_lines = []
            for j in range(i, min(i+10, len(lines))):
                question_lines.append(lines[j].strip())
                if 'A)' in lines[j] or 'B)' in lines[j]:
                    break
            question_text = ' '.join(question_lines)
            break

    print(f"   📝 Texto extraído del PDF: {question_text[:200]}...")

    # Buscar en el texto si hay "cómo se representa" o similar
    if 'cómo se representa' in question_text.lower() or 'como se representa' in question_text.lower():
        # El texto ya contiene la frase, extraerla
        # Buscar el patrón en el XML y actualizar
        current_pattern = r'(<p>)(¿Cuál de las siguientes imágenes[^<]*</p>)'
        if re.search(current_pattern, xml_content):
            # Insertar el texto antes de "¿Cuál de las siguientes imágenes..."
            xml_content = re.sub(
                current_pattern,
                r'\1¿Cómo se representa en la siguiente forma: \2',
                xml_content
            )
            print("   ✅ Texto actualizado con frase faltante")
        else:
            print("   ⚠️  No se encontró el patrón de pregunta en XML")
    else:
        print("   ⚠️  No se encontró 'cómo se representa' en el texto del PDF")

    # Reposicionar la imagen: debe ir después de "cómo se representa en la siguiente forma:"
    # Buscar la imagen del enunciado y moverla después del texto correcto
    img_pattern = r'(<p><img[^>]+Q50_enunciado[^>]+></p>)'
    img_match = re.search(img_pattern, xml_content)

    if img_match:
        img_tag = img_match.group(1)
        # Eliminar la imagen de donde está
        xml_content = re.sub(img_pattern, '', xml_content, count=1)

        # Insertar después de "cómo se representa en la siguiente forma:"
        insertion_pattern = r'(¿Cómo se representa en la siguiente forma:[^<]*</p>)'
        if re.search(insertion_pattern, xml_content):
            xml_content = re.sub(
                insertion_pattern,
                f'\\1\n    {img_tag}',
                xml_content
            )
            print("   ✅ Imagen reposicionada")
        else:
            # Si no encontramos el patrón, insertar después de la pregunta
            question_pattern = r'(¿Cuál de las siguientes imágenes representa mejor lo que los estudiantes deberían observar\?</p>)'
            if re.search(question_pattern, xml_content):
                xml_content = re.sub(
                    question_pattern,
                    f'\\1\n    {img_tag}',
                    xml_content
                )
                print("   ✅ Imagen reposicionada (patrón alternativo)")

    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(xml_content)

    return {"success": True}


def fix_q53_aggressive_crop(question_dir: Path, pdf_path: Path, test_name: str) -> Dict[str, Any]:
    """
    Q53: Recortar más agresivamente para mostrar solo el mapa de coordenadas.
    """
    print("\n🔧 Corrigiendo Q53: Recortar más agresivamente")

    doc = fitz.open(str(pdf_path))

    # El mapa está en la página 1
    if doc.page_count < 2:
        doc.close()
        return {"success": False, "error": "El PDF no tiene página 1"}

    page = doc[1]  # Página 1 (índice 1)
    page_rect = page.rect

    # Recortar más agresivamente: márgenes más grandes
    map_bbox = [
        60,  # x0: margen izquierdo más grande
        35,  # y0: margen superior más grande
        page_rect.width - 60,  # x1: margen derecho más grande
        page_rect.height - 15  # y1: margen inferior pequeño
    ]

    print(f"   📐 Bbox del mapa (recorte agresivo): {[round(x, 1) for x in map_bbox]}")

    rendered = render_image_area(page, map_bbox, map_bbox, 0)
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

        print("   ✅ Mapa recortado agresivamente y actualizado")

    return {"success": True, "s3_url": map_image_url}


def main():
    """Corregir todos los problemas finales."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Fix final image issues v2"
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
        "--q27-image",
        default="~/.cursor/projects/Users-francosolari-Arbor-arborschool-content/assets/Captura_de_pantalla_2025-12-19_a_la_s__00.13.58-d378b019-baa7-41ec-9838-77558d6b9e79.png",
        help="Path to Q27 image provided by user"
    )

    args = parser.parse_args()

    questions_dir = Path(args.questions_dir)
    output_dir = Path(args.output_dir)
    q27_image_path = Path(args.q27_image).expanduser()
    test_name = "Prueba-invierno-2025"

    print("=" * 60)
    print("🔧 CORRECCIÓN FINAL DE IMÁGENES - VERSIÓN 2")
    print("=" * 60)
    print()

    fixes = [
        (27, fix_q27_with_provided_image, "Usar imagen proporcionada", q27_image_path),
        (38, fix_q38_correct_swap_and_extend, "Intercambiar correctamente y extender bbox", None),
        (50, fix_q50_text_and_position, "Agregar texto faltante y reposicionar imagen", None),
        (53, fix_q53_aggressive_crop, "Recortar más agresivamente", None),
    ]

    success_count = 0
    failed_count = 0

    for q_num, fix_func, description, extra_arg in fixes:
        question_id = f"Q{q_num}"
        pdf_path = questions_dir / f"{question_id}.pdf"
        question_dir = output_dir / question_id

        print(f"[{fixes.index((q_num, fix_func, description, extra_arg)) + 1}/{len(fixes)}] {question_id}: {description}")

        if not pdf_path.exists():
            print("   ❌ PDF no encontrado")
            failed_count += 1
            continue

        if not question_dir.exists():
            print("   ❌ Directorio no encontrado")
            failed_count += 1
            continue

        try:
            # Pasar argumento extra si existe
            if extra_arg is not None:
                result = fix_func(question_dir, pdf_path, test_name, extra_arg)
            else:
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
