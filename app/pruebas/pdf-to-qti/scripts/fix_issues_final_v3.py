#!/usr/bin/env python3
"""
Script para corregir problemas finales - Versión 3.

Problemas a corregir:
1. Q27: Usar la imagen proporcionada por el usuario (verificar que se subió)
2. Q38: Verificar que las imágenes estén correctamente intercambiadas y con bbox extendido
3. Q53: Usar la imagen proporcionada por el usuario
"""

from __future__ import annotations

import json
import re
import base64
from pathlib import Path
from typing import Dict, Any

# Load environment variables
from dotenv import load_dotenv
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent.parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)

import fitz  # type: ignore

# Add modules to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.utils.s3_uploader import upload_image_to_s3
from modules.pdf_processor import render_image_area


def fix_q27_with_image(question_dir: Path, pdf_path: Path, test_name: str, image_path: Path) -> Dict[str, Any]:
    """
    Q27: Usar la imagen proporcionada por el usuario.
    """
    print(f"\n🔧 Corrigiendo Q27: Usando imagen proporcionada")
    
    if not image_path.exists():
        return {"success": False, "error": f"Imagen no encontrada: {image_path}"}
    
    print(f"   📸 Leyendo imagen de: {image_path}")
    
    # Leer imagen y convertir a base64
    with open(image_path, "rb") as f:
        image_data = f.read()
    
    image_base64 = base64.b64encode(image_data).decode("utf-8")
    
    # Subir a S3
    print(f"   📤 Subiendo imagen a S3...")
    s3_url = upload_image_to_s3(
        image_base64=image_base64,
        question_id="Q27_main",
        test_name=test_name,
    )
    
    if not s3_url:
        return {"success": False, "error": "No se pudo subir a S3"}
    
    print(f"   ✅ Imagen subida a: {s3_url}")
    
    # Actualizar XML
    xml_path = question_dir / "question.xml"
    with open(xml_path, "r", encoding="utf-8") as f:
        xml_content = f.read()
    
    # Buscar y reemplazar la URL de la imagen
    img_pattern = r'(<img[^>]+src=")([^"]+Q27_main[^"]*)(")'
    if re.search(img_pattern, xml_content):
        xml_content = re.sub(img_pattern, f'\\1{s3_url}\\3', xml_content)
        print(f"   ✅ URL actualizada en XML")
    else:
        # Buscar cualquier imagen en el XML
        img_pattern_generic = r'(<img[^>]+src=")([^"]+)(")'
        matches = list(re.finditer(img_pattern_generic, xml_content))
        if matches:
            old_url = matches[0].group(2)
            xml_content = xml_content.replace(old_url, s3_url, 1)
            print(f"   ✅ URL reemplazada (patrón genérico)")
        else:
            return {"success": False, "error": "No se encontró imagen en XML"}
    
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(xml_content)
    
    print(f"   ✅ Q27 corregida con imagen proporcionada")
    return {"success": True, "s3_url": s3_url}


def fix_q38_verify_and_fix(question_dir: Path, pdf_path: Path, test_name: str) -> Dict[str, Any]:
    """
    Q38: Verificar y corregir intercambio de imágenes y extender bbox.
    """
    print(f"\n🔧 Corrigiendo Q38: Intercambiar y extender bbox")
    
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
    # Mapeo: [1, 0, 3, 2] para obtener A, B, C, D
    
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
                print(f"   📸 Extrayendo alternativa {chr(65+i)} (original {chr(65+original_idx)}) con bbox extendido ±50px: {[round(x, 1) for x in bbox]}")
            else:  # C y D
                bbox[1] = max(0, bbox[1] - 30)  # Extender hacia arriba
                bbox[3] = min(page.rect.height, bbox[3] + 30)  # Extender hacia abajo
                print(f"   📸 Extrayendo alternativa {chr(65+i)} (original {chr(65+original_idx)}) con bbox extendido ±30px: {[round(x, 1) for x in bbox]}")
            
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
        # Buscar la URL actual de esta alternativa
        pattern = rf'(<qti-simple-choice identifier="Choice{choice_letter}">.*?<img[^>]+src=")([^"]+Q38_alt{choice_letter}[^"]*)(")'
        match = re.search(pattern, xml_content, flags=re.DOTALL)
        if match:
            old_url = match.group(2)
            xml_content = xml_content.replace(old_url, alternative_images[i])
            print(f"   ✅ Alternativa {choice_letter} actualizada: {old_url[:50]}... → {alternative_images[i][:50]}...")
        else:
            # Intentar patrón más simple: buscar cualquier URL en esa alternativa
            pattern_simple = rf'(<qti-simple-choice identifier="Choice{choice_letter}">.*?<img[^>]+src=")([^"]+)(")'
            match = re.search(pattern_simple, xml_content, flags=re.DOTALL)
            if match:
                old_url = match.group(2)
                xml_content = xml_content.replace(match.group(0), match.group(1) + alternative_images[i] + match.group(3))
                print(f"   ✅ Alternativa {choice_letter} actualizada (patrón simple)")
            else:
                print(f"   ⚠️  No se pudo encontrar alternativa {choice_letter} en XML")
    
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(xml_content)
    
    return {"success": True}


def fix_q53_with_image(question_dir: Path, pdf_path: Path, test_name: str, image_path: Path) -> Dict[str, Any]:
    """
    Q53: Usar la imagen proporcionada por el usuario.
    """
    print(f"\n🔧 Corrigiendo Q53: Usando imagen proporcionada")
    
    if not image_path.exists():
        return {"success": False, "error": f"Imagen no encontrada: {image_path}"}
    
    print(f"   📸 Leyendo imagen de: {image_path}")
    
    # Leer imagen y convertir a base64
    with open(image_path, "rb") as f:
        image_data = f.read()
    
    image_base64 = base64.b64encode(image_data).decode("utf-8")
    
    # Subir a S3
    print(f"   📤 Subiendo imagen a S3...")
    s3_url = upload_image_to_s3(
        image_base64=image_base64,
        question_id="Q53_main",
        test_name=test_name,
    )
    
    if not s3_url:
        return {"success": False, "error": "No se pudo subir a S3"}
    
    print(f"   ✅ Imagen subida a: {s3_url}")
    
    # Actualizar XML
    xml_path = question_dir / "question.xml"
    with open(xml_path, "r", encoding="utf-8") as f:
        xml_content = f.read()
    
    # Buscar y reemplazar la URL de la imagen
    img_pattern = r'(<img[^>]+src=")([^"]+Q53_main[^"]*)(")'
    if re.search(img_pattern, xml_content):
        xml_content = re.sub(img_pattern, f'\\1{s3_url}\\3', xml_content)
        print(f"   ✅ URL actualizada en XML")
    else:
        # Buscar cualquier imagen en el XML
        img_pattern_generic = r'(<img[^>]+src=")([^"]+)(")'
        matches = list(re.finditer(img_pattern_generic, xml_content))
        if matches:
            old_url = matches[0].group(2)
            xml_content = xml_content.replace(old_url, s3_url, 1)
            print(f"   ✅ URL reemplazada (patrón genérico)")
        else:
            return {"success": False, "error": "No se encontró imagen en XML"}
    
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(xml_content)
    
    print(f"   ✅ Q53 corregida con imagen proporcionada")
    return {"success": True, "s3_url": s3_url}


def main():
    """Corregir todos los problemas finales."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Fix final image issues v3"
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
    parser.add_argument(
        "--q53-image",
        default="~/.cursor/projects/Users-francosolari-Arbor-arborschool-content/assets/Captura_de_pantalla_2025-12-19_a_la_s__00.25.15-d29fc468-976c-4e98-bca8-ca03159d55a6.png",
        help="Path to Q53 image provided by user"
    )
    
    args = parser.parse_args()
    
    questions_dir = Path(args.questions_dir)
    output_dir = Path(args.output_dir)
    q27_image_path = Path(args.q27_image).expanduser()
    q53_image_path = Path(args.q53_image).expanduser()
    test_name = "Prueba-invierno-2025"
    
    print("=" * 60)
    print("🔧 CORRECCIÓN FINAL DE IMÁGENES - VERSIÓN 3")
    print("=" * 60)
    print()
    
    fixes = [
        (27, fix_q27_with_image, "Usar imagen proporcionada", q27_image_path),
        (38, fix_q38_verify_and_fix, "Intercambiar y extender bbox", None),
        (53, fix_q53_with_image, "Usar imagen proporcionada", q53_image_path),
    ]
    
    success_count = 0
    failed_count = 0
    
    for q_num, fix_func, description, extra_arg in fixes:
        question_id = f"Q{q_num}"
        pdf_path = questions_dir / f"{question_id}.pdf"
        question_dir = output_dir / question_id
        
        print(f"[{fixes.index((q_num, fix_func, description, extra_arg)) + 1}/{len(fixes)}] {question_id}: {description}")
        
        if not pdf_path.exists():
            print(f"   ❌ PDF no encontrado: {pdf_path}")
            failed_count += 1
            continue
        
        if not question_dir.exists():
            print(f"   ❌ Directorio no encontrado: {question_dir}")
            failed_count += 1
            continue
        
        if extra_arg is not None and not extra_arg.exists():
            print(f"   ❌ Imagen no encontrada: {extra_arg}")
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
                print(f"   ✅ {question_id} corregida exitosamente")
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
