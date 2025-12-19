#!/usr/bin/env python3
"""
Script para corregir problemas de imágenes en Prueba Invierno 2025 SIN llamar a la API.
Extrae imágenes del PDF y actualiza el XML directamente.
"""

from __future__ import annotations

import json
import base64
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List, Optional

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


def extract_main_image_from_pdf(
    pdf_path: Path,
    question_id: str,
    test_name: str = "Prueba-invierno-2025"
) -> Optional[str]:
    """
    Extrae la imagen principal del PDF y la sube a S3.
    
    Returns:
        S3 URL de la imagen o None si falla
    """
    try:
        doc = fitz.open(str(pdf_path))
        if doc.page_count == 0:
            return None
        
        page = doc[0]
        
        # Obtener estructura de la página
        structured_text = page.get_text("dict", sort=True)
        blocks = structured_text.get("blocks", [])
        
        # Buscar bloques de imagen (tipo 1)
        image_blocks = [b for b in blocks if b.get("type") == 1]
        
        if not image_blocks:
            print(f"   ⚠️  No se encontraron imágenes en el PDF")
            doc.close()
            return None
        
        # Usar la imagen más grande (probablemente la principal)
        largest_image = max(
            image_blocks,
            key=lambda b: (b["bbox"][2] - b["bbox"][0]) * (b["bbox"][3] - b["bbox"][1])
        )
        
        bbox = largest_image["bbox"]
        print(f"   📸 Extrayendo imagen de bbox: {[round(x, 1) for x in bbox]}")
        
        # Renderizar imagen
        rendered = render_image_area(page, bbox, bbox, 0)
        if not rendered or not rendered.get("image_base64"):
            print(f"   ❌ No se pudo renderizar la imagen")
            doc.close()
            return None
        
        image_base64 = rendered["image_base64"]
        
        # Subir a S3 con nombre único por pregunta
        s3_url = upload_image_to_s3(
            image_base64=image_base64,
            question_id=f"{question_id}_main",
            test_name=test_name,
        )
        
        doc.close()
        return s3_url
        
    except Exception as e:
        print(f"   ❌ Error extrayendo imagen: {e}")
        return None


def extract_all_images_from_pdf(
    pdf_path: Path,
    question_id: str,
    test_name: str = "Prueba-invierno-2025"
) -> List[Dict[str, Any]]:
    """
    Extrae todas las imágenes del PDF y las sube a S3.
    
    Returns:
        Lista de dicts con 's3_url' y 'bbox'
    """
    results = []
    try:
        doc = fitz.open(str(pdf_path))
        if doc.page_count == 0:
            return results
        
        page = doc[0]
        structured_text = page.get_text("dict", sort=True)
        blocks = structured_text.get("blocks", [])
        
        # Buscar bloques de imagen (tipo 1)
        image_blocks = [b for b in blocks if b.get("type") == 1]
        
        for i, img_block in enumerate(image_blocks):
            bbox = img_block["bbox"]
            rendered = render_image_area(page, bbox, bbox, i)
            
            if rendered and rendered.get("image_base64"):
                s3_url = upload_image_to_s3(
                    image_base64=rendered["image_base64"],
                    question_id=f"{question_id}_img{i}",
                    test_name=test_name,
                )
                if s3_url:
                    results.append({
                        "s3_url": s3_url,
                        "bbox": bbox,
                        "index": i
                    })
        
        doc.close()
        return results
        
    except Exception as e:
        print(f"   ❌ Error extrayendo imágenes: {e}")
        return results


def update_xml_image_url(
    xml_path: Path,
    old_url: str,
    new_url: str,
    description: str = ""
) -> bool:
    """
    Actualiza una URL de imagen en el XML.
    """
    try:
        with open(xml_path, "r", encoding="utf-8") as f:
            xml_content = f.read()
        
        # Reemplazar la URL
        if old_url in xml_content:
            xml_content = xml_content.replace(old_url, new_url)
            print(f"   ✅ {description}: URL actualizada")
            
            with open(xml_path, "w", encoding="utf-8") as f:
                f.write(xml_content)
            return True
        else:
            print(f"   ⚠️  {description}: URL no encontrada en XML")
            return False
            
    except Exception as e:
        print(f"   ❌ Error actualizando XML: {e}")
        return False


def fix_question_with_wrong_image(
    question_id: str,
    question_dir: Path,
    pdf_path: Path,
    test_name: str
) -> Dict[str, Any]:
    """
    Corrige una pregunta que tiene la imagen incorrecta (de Q14).
    """
    print(f"\n🔧 Corrigiendo {question_id}: Reemplazando imagen incorrecta")
    
    xml_path = question_dir / "question.xml"
    if not xml_path.exists():
        return {"success": False, "error": "XML no encontrado"}
    
    # Leer XML para encontrar la URL incorrecta
    with open(xml_path, "r", encoding="utf-8") as f:
        xml_content = f.read()
    
    # Buscar URLs de imágenes
    img_pattern = r'<img[^>]+src="([^"]+)"[^>]*>'
    matches = re.findall(img_pattern, xml_content)
    
    if not matches:
        return {"success": False, "error": "No se encontraron imágenes en XML"}
    
    # Extraer imagen correcta del PDF
    new_url = extract_main_image_from_pdf(pdf_path, question_id, test_name)
    if not new_url:
        return {"success": False, "error": "No se pudo extraer imagen del PDF"}
    
    # Reemplazar todas las URLs de imágenes en el body (no en alternativas)
    # Primero reemplazar la primera imagen (que está en el body)
    old_url = matches[0]
    if old_url != new_url:
        xml_content = xml_content.replace(old_url, new_url, 1)  # Solo la primera ocurrencia
        
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(xml_content)
        
        print(f"   ✅ Imagen del body actualizada")
    
    return {"success": True, "new_url": new_url}


def fix_q38(question_dir: Path, pdf_path: Path, test_name: str) -> Dict[str, Any]:
    """
    Q38: Eliminar imagen del enunciado, solo mantener en alternativas.
    """
    print(f"\n🔧 Corrigiendo Q38: Eliminando imagen del enunciado")
    
    xml_path = question_dir / "question.xml"
    if not xml_path.exists():
        return {"success": False, "error": "XML no encontrado"}
    
    # Leer XML como texto para trabajar con regex (más simple que namespaces)
    with open(xml_path, "r", encoding="utf-8") as f:
        xml_content = f.read()
    
    # Buscar imágenes en el body (antes del choice-interaction)
    # Patrón para encontrar <p><img> antes de <qti-choice-interaction>
    pattern = r'(<p>\s*<img[^>]+/>\s*</p>\s*)(?=.*?<qti-choice-interaction)'
    
    # Eliminar imágenes del enunciado
    xml_content = re.sub(pattern, '', xml_content, flags=re.DOTALL)
    
    # Extraer y actualizar imágenes de alternativas
    all_images = extract_all_images_from_pdf(pdf_path, "Q38", test_name)
    if len(all_images) >= 4:
        # Buscar imágenes en alternativas y reemplazarlas
        choice_pattern = r'(<qti-simple-choice[^>]*>.*?<img[^>]+src=")([^"]+)(")'
        matches = list(re.finditer(choice_pattern, xml_content, re.DOTALL))
        
        for i, match in enumerate(matches[:4]):
            if i < len(all_images):
                old_url = match.group(2)
                new_url = all_images[i]["s3_url"]
                xml_content = xml_content.replace(old_url, new_url, 1)
                print(f"   ✅ Alternativa {chr(65+i)} actualizada")
    
    # Guardar XML
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(xml_content)
    
    print(f"   ✅ Imágenes del enunciado eliminadas")
    return {"success": True}


def fix_q27(question_dir: Path, pdf_path: Path, test_name: str) -> Dict[str, Any]:
    """
    Q27: Imagen cortada - ajustar bbox para recortar correctamente.
    """
    print(f"\n🔧 Corrigiendo Q27: Ajustando bbox de imagen cortada")
    
    # Leer processed_content para ver el bbox actual
    processed_file = question_dir / "processed_content.json"
    if not processed_file.exists():
        return {"success": False, "error": "processed_content.json no encontrado"}
    
    with open(processed_file, "r", encoding="utf-8") as f:
        processed_data = json.load(f)
    
    all_images = processed_data.get("all_images", [])
    if not all_images:
        return {"success": False, "error": "No hay imágenes en processed_content"}
    
    # Obtener bbox de la primera imagen
    original_bbox = all_images[0].get("bbox", [])
    if len(original_bbox) != 4:
        return {"success": False, "error": "Bbox inválido"}
    
    # Ajustar bbox: mover x0 hacia la derecha para excluir parte izquierda cortada
    # y ajustar y0 hacia abajo para excluir pregunta de arriba
    adjusted_bbox = original_bbox.copy()
    adjusted_bbox[0] = original_bbox[0] + 20  # Mover izquierda hacia la derecha
    adjusted_bbox[1] = original_bbox[1] + 30  # Mover arriba hacia abajo
    
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
    
    # Buscar y reemplazar la URL de la imagen
    img_pattern = r'(<img[^>]+src=")([^"]+)(")'
    matches = list(re.finditer(img_pattern, xml_content))
    if matches:
        old_url = matches[0].group(2)
        xml_content = xml_content.replace(old_url, s3_url, 1)
        
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(xml_content)
        
        print(f"   ✅ Imagen actualizada con bbox ajustado")
    
    return {"success": True, "s3_url": s3_url}


def fix_q53(question_dir: Path, pdf_path: Path, test_name: str) -> Dict[str, Any]:
    """
    Q53: Agregar imagen del mapa cartesiano en el enunciado.
    """
    print(f"\n🔧 Corrigiendo Q53: Agregando imagen del mapa cartesiano")
    
    xml_path = question_dir / "question.xml"
    if not xml_path.exists():
        return {"success": False, "error": "XML no encontrado"}
    
    # Intentar extraer imagen directamente del PDF
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    
    # Obtener estructura de la página
    structured_text = page.get_text("dict", sort=True)
    blocks = structured_text.get("blocks", [])
    
    # Buscar bloques de imagen (tipo 1) - el mapa cartesiano debería ser una imagen
    image_blocks = [b for b in blocks if b.get("type") == 1]
    
    # Si no hay bloques de imagen tipo 1, intentar usar image_base64 del processed_content
    if not image_blocks:
        processed_file = question_dir / "processed_content.json"
        if processed_file.exists():
            with open(processed_file, "r", encoding="utf-8") as f:
                processed_data = json.load(f)
            
            image_base64 = processed_data.get("image_base64")
            if image_base64 and not image_base64.startswith("CONTENT_PLACEHOLDER"):
                print(f"   📸 Usando image_base64 del processed_content")
                map_image_url = upload_image_to_s3(
                    image_base64=image_base64,
                    question_id="Q53_main",
                    test_name=test_name,
                )
                doc.close()
                
                if map_image_url:
                    # Leer XML como texto
                    with open(xml_path, "r", encoding="utf-8") as f:
                        xml_content = f.read()
                    
                    # Verificar si ya existe una imagen antes del choice-interaction
                    choice_pos = xml_content.find("<qti-choice-interaction")
                    img_before_choice = xml_content.find("<img", 0, choice_pos) if choice_pos > 0 else -1
                    
                    if img_before_choice == -1:
                        # No hay imagen antes del choice-interaction, agregar una
                        pattern = r'(</p>\s*)(<qti-choice-interaction)'
                        replacement = f'</p>\n    <p><img src="{map_image_url}" alt="Mapa cartesiano con circunferencia T y transformaciones"/></p>\n    \\2'
                        xml_content = re.sub(pattern, replacement, xml_content, count=1)
                        
                        with open(xml_path, "w", encoding="utf-8") as f:
                            f.write(xml_content)
                        
                        print(f"   ✅ Imagen del mapa cartesiano agregada")
                        return {"success": True}
    
    if image_blocks:
        # Usar la imagen más grande (probablemente el mapa cartesiano)
        largest_image = max(
            image_blocks,
            key=lambda b: (b["bbox"][2] - b["bbox"][0]) * (b["bbox"][3] - b["bbox"][1])
        )
        
        bbox = largest_image["bbox"]
        print(f"   📸 Extrayendo imagen del mapa cartesiano de bbox: {[round(x, 1) for x in bbox]}")
        
        rendered = render_image_area(page, bbox, bbox, 0)
        doc.close()
        
        if rendered and rendered.get("image_base64"):
            map_image_url = upload_image_to_s3(
                image_base64=rendered["image_base64"],
                question_id="Q53_main",
                test_name=test_name,
            )
            
            if map_image_url:
                # Leer XML como texto
                with open(xml_path, "r", encoding="utf-8") as f:
                    xml_content = f.read()
                
                # Verificar si ya existe una imagen antes del choice-interaction
                # Buscar la posición del choice-interaction
                choice_pos = xml_content.find("<qti-choice-interaction")
                img_before_choice = xml_content.find("<img", 0, choice_pos) if choice_pos > 0 else -1
                
                if img_before_choice == -1:
                    # No hay imagen antes del choice-interaction, agregar una
                    # Buscar el último párrafo antes del choice-interaction
                    pattern = r'(</p>\s*)(<qti-choice-interaction)'
                    replacement = f'</p>\n    <p><img src="{map_image_url}" alt="Mapa cartesiano con circunferencia T y transformaciones"/></p>\n    \\2'
                    xml_content = re.sub(pattern, replacement, xml_content, count=1)
                    
                    with open(xml_path, "w", encoding="utf-8") as f:
                        f.write(xml_content)
                    
                    print(f"   ✅ Imagen del mapa cartesiano agregada")
                    return {"success": True}
                else:
                    # Actualizar URL existente
                    img_pattern = r'(<img[^>]+src=")([^"]+)(")'
                    matches = list(re.finditer(img_pattern, xml_content))
                    if matches and matches[0].start() < choice_pos:
                        old_url = matches[0].group(2)
                        xml_content = xml_content.replace(old_url, map_image_url, 1)
                        
                        with open(xml_path, "w", encoding="utf-8") as f:
                            f.write(xml_content)
                        
                        print(f"   ✅ URL de imagen existente actualizada")
                        return {"success": True}
    else:
        doc.close()
    
    return {"success": False, "error": "No se encontraron imágenes en el PDF"}


def fix_q65(question_dir: Path, pdf_path: Path, test_name: str) -> Dict[str, Any]:
    """
    Q65: Corregir imágenes incorrectas en alternativas.
    """
    print(f"\n🔧 Corrigiendo Q65: Reorganizando imágenes en alternativas")
    
    xml_path = question_dir / "question.xml"
    if not xml_path.exists():
        return {"success": False, "error": "XML no encontrado"}
    
    # Extraer todas las imágenes del PDF
    all_images = extract_all_images_from_pdf(pdf_path, "Q65", test_name)
    if len(all_images) < 4:
        return {"success": False, "error": f"Se esperaban 4 imágenes, se encontraron {len(all_images)}"}
    
    # Leer XML como texto
    with open(xml_path, "r", encoding="utf-8") as f:
        xml_content = f.read()
    
    # Buscar todas las imágenes en alternativas
    choice_pattern = r'(<qti-simple-choice[^>]*>.*?<img[^>]+src=")([^"]+)(")'
    matches = list(re.finditer(choice_pattern, xml_content, re.DOTALL))
    
    if len(matches) != 4:
        return {"success": False, "error": f"Se esperaban 4 imágenes en alternativas, se encontraron {len(matches)}"}
    
    # Reemplazar cada imagen
    for i, match in enumerate(matches):
        if i < len(all_images):
            old_url = match.group(2)
            new_url = all_images[i]["s3_url"]
            xml_content = xml_content.replace(old_url, new_url, 1)
            print(f"   ✅ Alternativa {chr(65+i)} actualizada")
    
    # Guardar XML
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(xml_content)
    
    return {"success": True}


def main():
    """Corregir todas las preguntas con problemas de imágenes."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Fix image issues in Prueba Invierno 2025 questions (local, no API)"
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
    
    # Preguntas con problemas
    questions_with_wrong_image = [6, 7, 8, 9, 29, 31, 33, 35, 43, 45, 46, 48, 51, 54, 56]
    special_cases = {
        27: fix_q27,
        38: fix_q38,
        53: fix_q53,
        65: fix_q65,
    }
    
    print("=" * 60)
    print("🔧 CORRECCIÓN LOCAL DE IMÁGENES - Prueba Invierno 2025")
    print("=" * 60)
    print(f"📋 Preguntas a corregir: {len(questions_with_wrong_image) + len(special_cases)}")
    print()
    
    success_count = 0
    failed_count = 0
    
    # Corregir preguntas con imagen incorrecta
    for q_num in sorted(questions_with_wrong_image):
        question_id = f"Q{q_num}"
        pdf_path = questions_dir / f"{question_id}.pdf"
        question_dir = output_dir / question_id
        
        print(f"[{questions_with_wrong_image.index(q_num) + 1}/{len(questions_with_wrong_image)}] {question_id}...")
        
        if not pdf_path.exists():
            print(f"   ❌ PDF no encontrado")
            failed_count += 1
            continue
        
        if not question_dir.exists():
            print(f"   ❌ Directorio de pregunta no encontrado")
            failed_count += 1
            continue
        
        result = fix_question_with_wrong_image(question_id, question_dir, pdf_path, test_name)
        if result.get("success"):
            success_count += 1
        else:
            print(f"   ❌ Error: {result.get('error')}")
            failed_count += 1
    
    # Corregir casos especiales
    for q_num, fix_func in sorted(special_cases.items()):
        question_id = f"Q{q_num}"
        pdf_path = questions_dir / f"{question_id}.pdf"
        question_dir = output_dir / question_id
        
        print(f"\n[{list(special_cases.keys()).index(q_num) + 1}/{len(special_cases)}] {question_id} (caso especial)...")
        
        if not pdf_path.exists() or not question_dir.exists():
            print(f"   ❌ Archivos no encontrados")
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
            failed_count += 1
    
    print("\n" + "=" * 60)
    print("📊 RESUMEN")
    print("=" * 60)
    print(f"✅ Exitosas: {success_count}")
    print(f"❌ Fallidas: {failed_count}")
    print(f"📊 Total: {len(questions_with_wrong_image) + len(special_cases)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
