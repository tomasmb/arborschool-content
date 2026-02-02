#!/usr/bin/env python3
"""
Script para forzar la subida de imágenes a S3 con nombres únicos (timestamp).
"""

from __future__ import annotations

import base64
import time
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


def force_upload_q27(image_path: Path, test_name: str) -> Dict[str, Any]:
    """Forzar subida de Q27 con nombre único."""
    print("\n🔧 Forzando subida de Q27")

    if not image_path.exists():
        return {"success": False, "error": f"Imagen no encontrada: {image_path}"}

    with open(image_path, "rb") as f:
        image_data = f.read()

    image_base64 = base64.b64encode(image_data).decode("utf-8")

    # Usar timestamp para forzar nueva subida
    timestamp = int(time.time())
    question_id = f"Q27_main_{timestamp}"

    s3_url = upload_image_to_s3(
        image_base64=image_base64,
        question_id=question_id,
        test_name=test_name,
    )

    if not s3_url:
        return {"success": False, "error": "No se pudo subir a S3"}

    print(f"   ✅ Imagen subida: {s3_url}")
    return {"success": True, "s3_url": s3_url, "question_id": question_id}


def force_upload_q38(pdf_path: Path, test_name: str) -> Dict[str, Any]:
    """Forzar subida de Q38 con nombres únicos."""
    print("\n🔧 Forzando subida de Q38")

    doc = fitz.open(str(pdf_path))
    page = doc[0]

    blocks = page.get_text("dict", sort=True)["blocks"]
    image_blocks = [b for b in blocks if b.get("type") == 1]
    image_blocks.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))

    if len(image_blocks) < 4:
        doc.close()
        return {"success": False, "error": f"Se esperaban 4 imágenes, se encontraron {len(image_blocks)}"}

    timestamp = int(time.time())
    order_map = [1, 0, 3, 2]  # B→A, A→B, D→C, C→D
    alternative_images = []

    for i, original_idx in enumerate(order_map):
        if original_idx < len(image_blocks):
            img_block = image_blocks[original_idx]
            bbox = list(img_block["bbox"])

            # Extender bbox
            if i < 2:  # A y B
                bbox[1] = max(0, bbox[1] - 50)
                bbox[3] = min(page.rect.height, bbox[3] + 50)
            else:  # C y D
                bbox[1] = max(0, bbox[1] - 30)
                bbox[3] = min(page.rect.height, bbox[3] + 30)

            rendered = render_image_area(page, bbox, bbox, i)

            if rendered and rendered.get("image_base64"):
                question_id = f"Q38_alt{chr(65+i)}_{timestamp}"
                s3_url = upload_image_to_s3(
                    image_base64=rendered["image_base64"],
                    question_id=question_id,
                    test_name=test_name,
                )
                if s3_url:
                    alternative_images.append(s3_url)
                    print(f"   ✅ Alternativa {chr(65+i)} subida: {s3_url}")

    doc.close()

    if len(alternative_images) != 4:
        return {"success": False, "error": f"Se esperaban 4 imágenes, se procesaron {len(alternative_images)}"}

    return {"success": True, "urls": alternative_images, "timestamp": timestamp}


def force_upload_q53(image_path: Path, test_name: str) -> Dict[str, Any]:
    """Forzar subida de Q53 con nombre único."""
    print("\n🔧 Forzando subida de Q53")

    if not image_path.exists():
        return {"success": False, "error": f"Imagen no encontrada: {image_path}"}

    with open(image_path, "rb") as f:
        image_data = f.read()

    image_base64 = base64.b64encode(image_data).decode("utf-8")

    timestamp = int(time.time())
    question_id = f"Q53_main_{timestamp}"

    s3_url = upload_image_to_s3(
        image_base64=image_base64,
        question_id=question_id,
        test_name=test_name,
    )

    if not s3_url:
        return {"success": False, "error": "No se pudo subir a S3"}

    print(f"   ✅ Imagen subida: {s3_url}")
    return {"success": True, "s3_url": s3_url, "question_id": question_id}


def update_xml_with_new_urls(question_dir: Path, urls: Dict[str, str]) -> bool:
    """Actualizar XML con nuevas URLs."""
    xml_path = question_dir / "question.xml"
    if not xml_path.exists():
        return False

    import re
    with open(xml_path, "r", encoding="utf-8") as f:
        xml_content = f.read()

    # Reemplazar URLs
    for old_pattern, new_url in urls.items():
        if old_pattern == "Q27_main":
            # Buscar cualquier URL de Q27_main
            pattern = r'(<img[^>]+src=")([^"]+Q27_main[^"]*)(")'
            match = re.search(pattern, xml_content)
            if match:
                xml_content = xml_content.replace(match.group(2), new_url)
        elif old_pattern.startswith("Q38_alt"):
            letter = old_pattern[-1]
            # Buscar la alternativa específica
            pattern = rf'(<qti-simple-choice identifier="Choice{letter}">.*?<img[^>]+src=")([^"]+Q38_alt{letter}[^"]*)(")'
            match = re.search(pattern, xml_content, flags=re.DOTALL)
            if match:
                xml_content = xml_content.replace(match.group(2), new_url)
        elif old_pattern == "Q53_main":
            # Buscar cualquier URL de Q53_main
            pattern = r'(<img[^>]+src=")([^"]+Q53_main[^"]*)(")'
            match = re.search(pattern, xml_content)
            if match:
                xml_content = xml_content.replace(match.group(2), new_url)

    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(xml_content)

    return True


def main():
    """Forzar subida de imágenes con nombres únicos."""
    import argparse

    parser = argparse.ArgumentParser(description="Force upload images to S3")
    parser.add_argument("--output-dir", default="../../data/pruebas/procesadas/prueba-invierno-2025/qti")
    parser.add_argument("--questions-dir", default="../../data/pruebas/procesadas/prueba-invierno-2025/pdf")
    parser.add_argument("--q27-image", default="~/.cursor/projects/Users-francosolari-Arbor-arborschool-content/assets/Captura_de_pantalla_2025-12-19_a_la_s__00.13.58-d378b019-baa7-41ec-9838-77558d6b9e79.png")
    parser.add_argument("--q53-image", default="~/.cursor/projects/Users-francosolari-Arbor-arborschool-content/assets/Captura_de_pantalla_2025-12-19_a_la_s__00.25.15-d29fc468-976c-4e98-bca8-ca03159d55a6.png")

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    questions_dir = Path(args.questions_dir)
    q27_image = Path(args.q27_image).expanduser()
    q53_image = Path(args.q53_image).expanduser()
    test_name = "prueba-invierno-2025"

    print("=" * 60)
    print("🔄 FORZANDO SUBIDA DE IMÁGENES CON NOMBRES ÚNICOS")
    print("=" * 60)

    # Q27
    result27 = force_upload_q27(q27_image, test_name)
    if result27.get("success"):
        urls = {"Q27_main": result27["s3_url"]}
        if update_xml_with_new_urls(output_dir / "Q27", urls):
            print("   ✅ XML actualizado con nueva URL")

    # Q38
    result38 = force_upload_q38(questions_dir / "Q38.pdf", test_name)
    if result38.get("success"):
        urls = {
            "Q38_altA": result38["urls"][0],
            "Q38_altB": result38["urls"][1],
            "Q38_altC": result38["urls"][2],
            "Q38_altD": result38["urls"][3],
        }
        if update_xml_with_new_urls(output_dir / "Q38", urls):
            print("   ✅ XML actualizado con nuevas URLs")

    # Q53
    result53 = force_upload_q53(q53_image, test_name)
    if result53.get("success"):
        urls = {"Q53_main": result53["s3_url"]}
        if update_xml_with_new_urls(output_dir / "Q53", urls):
            print("   ✅ XML actualizado con nueva URL")

    print("=" * 60)
    print("✅ PROCESO COMPLETADO")
    print("=" * 60)


if __name__ == "__main__":
    main()
