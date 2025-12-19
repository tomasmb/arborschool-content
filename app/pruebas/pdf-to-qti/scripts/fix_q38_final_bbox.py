#!/usr/bin/env python3
"""
Script para ajustar los bbox finales de Q38 según especificaciones del usuario.
"""

from __future__ import annotations

import re
import time
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


def fix_q38_final_bbox(question_dir: Path, pdf_path: Path, test_name: str) -> Dict[str, Any]:
    """
    Q38: Ajustar bbox según especificaciones:
    - A: agrandar a la derecha, cortar muy poco abajo, agrandar muy poco a la izquierda
    - B: cortar un poco arriba, cortar como una línea y media abajo
    - C: cortar muy poquito por la izquierda
    - D: cortar muy poquito por la izquierda
    """
    print(f"\n🔧 Ajustando bbox finales de Q38")
    
    xml_path = question_dir / "question.xml"
    if not xml_path.exists():
        return {"success": False, "error": "XML no encontrado"}
    
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    page_rect = page.rect
    
    # Obtener todas las imágenes
    blocks = page.get_text("dict", sort=True)["blocks"]
    image_blocks = [b for b in blocks if b.get("type") == 1]
    image_blocks.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))
    
    if len(image_blocks) < 4:
        doc.close()
        return {"success": False, "error": f"Se esperaban 4 imágenes, se encontraron {len(image_blocks)}"}
    
    # Orden actual en PDF: [0]=B, [1]=A, [2]=D, [3]=C
    # Necesitamos: A, B, C, D
    # Mapeo: [1, 0, 3, 2] para obtener A, B, C, D
    order_map = [1, 0, 3, 2]
    
    alternative_images = []
    timestamp = int(time.time())
    
    for i, original_idx in enumerate(order_map):
        if original_idx < len(image_blocks):
            img_block = image_blocks[original_idx]
            bbox = list(img_block["bbox"])
            
            choice_letter = chr(65 + i)  # A, B, C, D
            
            # Ajustes específicos según la alternativa
            if choice_letter == 'A':
                # A: agrandar a la derecha, cortar muy poco abajo, agrandar muy poco a la izquierda
                bbox[0] = max(0, bbox[0] - 5)  # Agrandar muy poco a la izquierda
                bbox[2] = min(page_rect.width, bbox[2] + 15)  # Agrandar a la derecha
                bbox[3] = bbox[3] - 3  # Cortar muy poco abajo
                print(f"   📐 Alternativa A: bbox ajustado = {[round(x, 1) for x in bbox]}")
            elif choice_letter == 'B':
                # B: cortar un poco arriba, cortar como una línea y media abajo
                bbox[1] = bbox[1] + 8  # Cortar un poco arriba
                bbox[3] = bbox[3] - 20  # Cortar como una línea y media abajo (~20px)
                print(f"   📐 Alternativa B: bbox ajustado = {[round(x, 1) for x in bbox]}")
            elif choice_letter == 'C':
                # C: cortar muy poquito por la izquierda
                bbox[0] = bbox[0] + 3  # Cortar muy poquito por la izquierda
                print(f"   📐 Alternativa C: bbox ajustado = {[round(x, 1) for x in bbox]}")
            elif choice_letter == 'D':
                # D: cortar muy poquito por la izquierda
                bbox[0] = bbox[0] + 3  # Cortar muy poquito por la izquierda
                print(f"   📐 Alternativa D: bbox ajustado = {[round(x, 1) for x in bbox]}")
            
            # Asegurar que el bbox esté dentro de los límites de la página
            bbox[0] = max(0, bbox[0])
            bbox[1] = max(0, bbox[1])
            bbox[2] = min(page_rect.width, bbox[2])
            bbox[3] = min(page_rect.height, bbox[3])
            
            rendered = render_image_area(page, bbox, bbox, i)
            
            if rendered and rendered.get("image_base64"):
                question_id = f"Q38_alt{choice_letter}_{timestamp}"
                s3_url = upload_image_to_s3(
                    image_base64=rendered["image_base64"],
                    question_id=question_id,
                    test_name=test_name,
                )
                if s3_url:
                    alternative_images.append(s3_url)
                    print(f"   ✅ Alternativa {choice_letter} extraída y subida: {s3_url[:80]}...")
    
    doc.close()
    
    if len(alternative_images) != 4:
        return {"success": False, "error": f"Se esperaban 4 imágenes, se procesaron {len(alternative_images)}"}
    
    # Actualizar XML con las nuevas URLs
    with open(xml_path, "r", encoding="utf-8") as f:
        xml_content = f.read()
    
    for i, choice_letter in enumerate(['A', 'B', 'C', 'D']):
        pattern = rf'(<qti-simple-choice identifier="Choice{choice_letter}">.*?<img[^>]+src=")([^"]+Q38_alt{choice_letter}[^"]*)(")'
        match = re.search(pattern, xml_content, flags=re.DOTALL)
        if match:
            old_url = match.group(2)
            xml_content = xml_content.replace(old_url, alternative_images[i])
            print(f"   ✅ Alternativa {choice_letter} actualizada en XML")
        else:
            print(f"   ⚠️  No se pudo encontrar alternativa {choice_letter} en XML")
    
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(xml_content)
    
    return {"success": True, "urls": alternative_images}


def main():
    """Ajustar bbox finales de Q38."""
    questions_dir = Path("../../data/pruebas/procesadas/Prueba-invierno-2025/pdf")
    output_dir = Path("../../data/pruebas/procesadas/Prueba-invierno-2025/qti")
    test_name = "Prueba-invierno-2025"
    
    pdf_path = questions_dir / "Q38.pdf"
    question_dir = output_dir / "Q38"
    
    print("=" * 60)
    print("🔧 AJUSTE FINAL DE BBOX - Q38")
    print("=" * 60)
    
    if not pdf_path.exists():
        print(f"❌ PDF no encontrado: {pdf_path}")
        return
    
    if not question_dir.exists():
        print(f"❌ Directorio no encontrado: {question_dir}")
        return
    
    result = fix_q38_final_bbox(question_dir, pdf_path, test_name)
    
    if result.get("success"):
        print("\n✅ Q38 corregida exitosamente")
        print(f"   URLs actualizadas: {len(result.get('urls', []))} imágenes")
    else:
        print(f"\n❌ Error: {result.get('error')}")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
