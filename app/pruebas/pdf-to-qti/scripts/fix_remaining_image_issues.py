#!/usr/bin/env python3
"""
Script para corregir problemas restantes de imágenes en Prueba Invierno 2025.

Problemas a corregir:
1. Q27: Imagen cortada por izquierda y arriba - ajustar bbox
2. Q38: Faltan imágenes de alternativas (están en cuadrícula: A y B arriba, C y D abajo)
3. Q50: No procesada completamente - procesar desde cero
4. Q53: Imagen captura parte de la pregunta - ajustar bbox
5. Q65: Faltan imágenes de alternativas
"""

from __future__ import annotations

import json
import re
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
from main import process_single_question_pdf


def fix_q27_improved(question_dir: Path, pdf_path: Path, test_name: str) -> Dict[str, Any]:
    """
    Q27: Ajustar bbox para excluir pregunta de arriba y parte izquierda cortada.
    """
    print(f"\n🔧 Corrigiendo Q27: Ajustando bbox mejorado")
    
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
    
    # Ajustar más agresivamente: más hacia la derecha y más hacia abajo
    adjusted_bbox = original_bbox.copy()
    adjusted_bbox[0] = original_bbox[0] + 60  # Mover más hacia la derecha (excluir más de la izquierda)
    adjusted_bbox[1] = original_bbox[1] + 70  # Mover más hacia abajo (excluir más pregunta arriba)
    
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
        
        print(f"   ✅ Imagen actualizada con bbox mejorado")
    
    return {"success": True, "s3_url": s3_url}


def fix_q38_alternatives(question_dir: Path, pdf_path: Path, test_name: str) -> Dict[str, Any]:
    """
    Q38: Extraer 4 imágenes en cuadrícula (A y B arriba, C y D abajo) y colocarlas en alternativas.
    """
    print(f"\n🔧 Corrigiendo Q38: Agregando imágenes de alternativas en cuadrícula")
    
    xml_path = question_dir / "question.xml"
    if not xml_path.exists():
        return {"success": False, "error": "XML no encontrado"}
    
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    
    # Obtener estructura de la página
    structured_text = page.get_text("dict", sort=True)
    blocks = structured_text.get("blocks", [])
    
    # Buscar bloques de imagen (tipo 1)
    image_blocks = [b for b in blocks if b.get("type") == 1]
    
    if len(image_blocks) < 4:
        doc.close()
        return {"success": False, "error": f"Se esperaban 4 imágenes, se encontraron {len(image_blocks)}"}
    
    # Ordenar imágenes por posición (y primero, luego x)
    image_blocks.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))
    
    # Las primeras 2 deberían ser A y B (arriba), las siguientes 2 C y D (abajo)
    alternative_images = []
    for i, img_block in enumerate(image_blocks[:4]):
        bbox = img_block["bbox"]
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
    
    # Actualizar XML - agregar imágenes a las alternativas
    with open(xml_path, "r", encoding="utf-8") as f:
        xml_content = f.read()
    
    # Buscar cada alternativa y agregar imagen
    for i, choice_letter in enumerate(['A', 'B', 'C', 'D']):
        pattern = rf'(<qti-simple-choice identifier="Choice{choice_letter}">)([^<]+)(</qti-simple-choice>)'
        replacement = f'\\1<p><img src="{alternative_images[i]}" alt="Gráfico opción {choice_letter}"/></p>\\3'
        xml_content = re.sub(pattern, replacement, xml_content)
    
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(xml_content)
    
    print(f"   ✅ Imágenes agregadas a las 4 alternativas")
    return {"success": True}


def process_q50(question_dir: Path, pdf_path: Path, test_name: str) -> Dict[str, Any]:
    """
    Q50: Procesar completamente desde cero.
    El problema es que detecta 4 choices pero solo extrae 3 imágenes.
    Vamos a procesar manualmente extrayendo las 4 imágenes correctamente.
    """
    print(f"\n🔧 Procesando Q50 completamente")
    
    if not pdf_path.exists():
        return {"success": False, "error": "PDF no encontrado"}
    
    # Primero intentar procesamiento normal
    result = process_single_question_pdf(
        input_pdf_path=str(pdf_path),
        output_dir=str(question_dir),
        openai_api_key=None,
        paes_mode=True,
        skip_if_exists=False,
    )
    
    # Si falla por mismatch de imágenes, intentar corregir manualmente
    if not result.get("success") and "Mismatch" in str(result.get("error", "")):
        print(f"   ⚠️  Procesamiento falló por mismatch, intentando corrección manual...")
        
        # El processed_content debería tener información útil
        processed_file = question_dir / "processed_content.json"
        if processed_file.exists():
            # Intentar regenerar desde processed_content
            from scripts.regenerate_qti_from_processed import regenerate_qti_from_processed
            import os
            
            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")
            if api_key:
                result = regenerate_qti_from_processed(
                    question_dir=question_dir,
                    api_key=api_key,
                    paes_mode=True,
                    test_name=test_name,
                )
                if result.get("success"):
                    print(f"   ✅ Q50 regenerada exitosamente desde processed_content")
                    return {"success": True}
    
    if result.get("success"):
        print(f"   ✅ Q50 procesada exitosamente")
        return {"success": True}
    else:
        error = result.get("error", "Unknown error")
        print(f"   ❌ Error: {error}")
        return {"success": False, "error": error}


def fix_q53_improved(question_dir: Path, pdf_path: Path, test_name: str) -> Dict[str, Any]:
    """
    Q53: Ajustar bbox para excluir texto de la pregunta.
    El mapa cartesiano está en la página completa, necesitamos recortar solo el área del gráfico.
    """
    print(f"\n🔧 Corrigiendo Q53: Ajustando bbox para excluir pregunta")
    
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
    
    # Encontrar dónde termina la pregunta - buscar el último bloque de texto antes de y=200
    question_end_y = 0
    for block in text_blocks:
        bbox = block.get("bbox", [])
        if len(bbox) == 4:
            block_text = ""
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    block_text += span.get("text", "")
            
            # Si contiene "circunferencia R" o está antes de y=200, es parte de la pregunta
            if bbox[3] < 200 and ("circunferencia" in block_text.lower() or "refleja" in block_text.lower() or "eje Y" in block_text):
                question_end_y = max(question_end_y, bbox[3])
    
    # Agregar margen generoso
    question_end_y += 30
    print(f"   📐 Fin de pregunta estimado en y={round(question_end_y, 1)}")
    
    # Extraer imagen del PDF - usar image_base64 del processed_content pero recortar
    image_base64 = processed_data.get("image_base64")
    if image_base64 and not image_base64.startswith("CONTENT_PLACEHOLDER"):
        # Decodificar y recortar la imagen
        import base64
        from PIL import Image
        import io
        
        # Decodificar base64
        if image_base64.startswith("data:"):
            header, encoded = image_base64.split(",", 1)
            image_data = base64.b64decode(encoded)
        else:
            image_data = base64.b64decode(image_base64)
        
        # Abrir imagen
        img = Image.open(io.BytesIO(image_data))
        width, height = img.size
        
        # Calcular qué porcentaje de la imagen corresponde a la pregunta
        # La pregunta ocupa más espacio, recortar más agresivamente
        crop_top = int(height * 0.25)  # Recortar 25% superior para excluir más pregunta
        
        # Recortar imagen
        cropped_img = img.crop((0, crop_top, width, height))
        
        # Convertir a base64
        buffer = io.BytesIO()
        cropped_img.save(buffer, format="PNG")
        cropped_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Subir a S3
        map_image_url = upload_image_to_s3(
            image_base64=cropped_base64,
            question_id="Q53_main",
            test_name=test_name,
        )
        
        if map_image_url:
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
                
                print(f"   ✅ Imagen recortada y actualizada (recortado {crop_top}px del top)")
                return {"success": True}
    
    return {"success": False, "error": "No se pudo procesar image_base64"}


def fix_q65_alternatives(question_dir: Path, pdf_path: Path, test_name: str) -> Dict[str, Any]:
    """
    Q65: Verificar y corregir imágenes de alternativas.
    """
    print(f"\n🔧 Corrigiendo Q65: Verificando imágenes de alternativas")
    
    xml_path = question_dir / "question.xml"
    if not xml_path.exists():
        return {"success": False, "error": "XML no encontrado"}
    
    # Leer XML para ver qué imágenes hay
    with open(xml_path, "r", encoding="utf-8") as f:
        xml_content = f.read()
    
    # Buscar imágenes en alternativas
    choice_pattern = r'<qti-simple-choice[^>]*>.*?<img[^>]+src="([^"]+)"'
    matches = re.findall(choice_pattern, xml_content, re.DOTALL)
    
    if len(matches) == 4:
        # Verificar si las URLs son válidas (no son placeholders)
        valid_urls = [url for url in matches if "s3" in url or "http" in url]
        if len(valid_urls) == 4:
            print(f"   ✅ Las 4 alternativas ya tienen imágenes válidas")
            return {"success": True}
    
    # Si faltan imágenes, extraerlas del PDF
    print(f"   📸 Extrayendo imágenes de alternativas del PDF")
    
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    
    structured_text = page.get_text("dict", sort=True)
    blocks = structured_text.get("blocks", [])
    image_blocks = [b for b in blocks if b.get("type") == 1]
    
    if len(image_blocks) < 4:
        doc.close()
        return {"success": False, "error": f"Se esperaban 4 imágenes, se encontraron {len(image_blocks)}"}
    
    # Ordenar por posición
    image_blocks.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))
    
    alternative_images = []
    for i, img_block in enumerate(image_blocks[:4]):
        bbox = img_block["bbox"]
        rendered = render_image_area(page, bbox, bbox, i)
        
        if rendered and rendered.get("image_base64"):
            s3_url = upload_image_to_s3(
                image_base64=rendered["image_base64"],
                question_id=f"Q65_alt{chr(65+i)}",
                test_name=test_name,
            )
            if s3_url:
                alternative_images.append(s3_url)
                print(f"   ✅ Imagen alternativa {chr(65+i)} extraída")
    
    doc.close()
    
    if len(alternative_images) != 4:
        return {"success": False, "error": f"Se esperaban 4 imágenes, se procesaron {len(alternative_images)}"}
    
    # Actualizar XML
    choice_pattern = r'(<qti-simple-choice[^>]*>.*?<img[^>]+src=")([^"]+)(")'
    matches = list(re.finditer(choice_pattern, xml_content, re.DOTALL))
    
    for i, match in enumerate(matches[:4]):
        if i < len(alternative_images):
            old_url = match.group(2)
            xml_content = xml_content.replace(old_url, alternative_images[i], 1)
            print(f"   ✅ Alternativa {chr(65+i)} actualizada")
    
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(xml_content)
    
    return {"success": True}


def main():
    """Corregir todos los problemas restantes."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Fix remaining image issues in Prueba Invierno 2025"
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
    print("🔧 CORRECCIÓN DE PROBLEMAS RESTANTES")
    print("=" * 60)
    print()
    
    fixes = [
        (27, fix_q27_improved, "Ajustar bbox imagen cortada"),
        (38, fix_q38_alternatives, "Agregar imágenes de alternativas"),
        (50, process_q50, "Procesar completamente"),
        (53, fix_q53_improved, "Ajustar bbox para excluir pregunta"),
        (65, fix_q65_alternatives, "Corregir imágenes de alternativas"),
    ]
    
    success_count = 0
    failed_count = 0
    
    for q_num, fix_func, description in fixes:
        question_id = f"Q{q_num}"
        pdf_path = questions_dir / f"{question_id}.pdf"
        question_dir = output_dir / question_id
        
        print(f"[{fixes.index((q_num, fix_func, description)) + 1}/{len(fixes)}] {question_id}: {description}")
        
        if not pdf_path.exists():
            print(f"   ❌ PDF no encontrado")
            failed_count += 1
            continue
        
        if not question_dir.exists() and q_num != 50:
            print(f"   ❌ Directorio no encontrado")
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
