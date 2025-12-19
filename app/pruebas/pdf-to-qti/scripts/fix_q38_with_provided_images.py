#!/usr/bin/env python3
"""
Script para usar las imágenes proporcionadas por el usuario para Q38.
"""

from __future__ import annotations

import base64
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

# Add modules to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.utils.s3_uploader import upload_image_to_s3


def fix_q38_with_images(question_dir: Path, test_name: str, image_paths: Dict[str, Path]) -> Dict[str, Any]:
    """
    Q38: Usar las imágenes proporcionadas por el usuario.
    """
    print(f"\n🔧 Corrigiendo Q38: Usando imágenes proporcionadas")
    
    xml_path = question_dir / "question.xml"
    if not xml_path.exists():
        return {"success": False, "error": "XML no encontrado"}
    
    timestamp = int(time.time())
    uploaded_urls = {}
    
    # Subir cada imagen
    for choice_letter in ['A', 'B', 'C', 'D']:
        image_path = image_paths.get(choice_letter)
        if not image_path or not image_path.exists():
            return {"success": False, "error": f"Imagen {choice_letter} no encontrada: {image_path}"}
        
        print(f"   📸 Leyendo imagen {choice_letter} de: {image_path}")
        
        with open(image_path, "rb") as f:
            image_data = f.read()
        
        image_base64 = base64.b64encode(image_data).decode("utf-8")
        
        question_id = f"Q38_alt{choice_letter}_{timestamp}"
        s3_url = upload_image_to_s3(
            image_base64=image_base64,
            question_id=question_id,
            test_name=test_name,
        )
        
        if not s3_url:
            return {"success": False, "error": f"No se pudo subir imagen {choice_letter} a S3"}
        
        uploaded_urls[choice_letter] = s3_url
        print(f"   ✅ Imagen {choice_letter} subida: {s3_url[:80]}...")
    
    # Actualizar XML
    with open(xml_path, "r", encoding="utf-8") as f:
        xml_content = f.read()
    
    for choice_letter in ['A', 'B', 'C', 'D']:
        pattern = rf'(<qti-simple-choice identifier="Choice{choice_letter}">.*?<img[^>]+src=")([^"]+Q38_alt{choice_letter}[^"]*)(")'
        match = re.search(pattern, xml_content, flags=re.DOTALL)
        if match:
            old_url = match.group(2)
            xml_content = xml_content.replace(old_url, uploaded_urls[choice_letter])
            print(f"   ✅ Alternativa {choice_letter} actualizada en XML")
        else:
            print(f"   ⚠️  No se pudo encontrar alternativa {choice_letter} en XML")
    
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(xml_content)
    
    return {"success": True, "urls": uploaded_urls}


def main():
    """Usar imágenes proporcionadas para Q38."""
    output_dir = Path("../../data/pruebas/procesadas/Prueba-invierno-2025/qti")
    test_name = "Prueba-invierno-2025"
    
    # Rutas de las imágenes proporcionadas (en orden A, B, C, D)
    base_path = Path.home() / ".cursor/projects/Users-francosolari-Arbor-arborschool-content/assets"
    image_paths = {
        'A': base_path / "Captura_de_pantalla_2025-12-19_a_la_s__00.46.06-2ca41694-cff6-4318-89ff-549ac3b6241b.png",
        'B': base_path / "Captura_de_pantalla_2025-12-19_a_la_s__00.46.15-c088312e-9250-4b09-92b0-e62b3591f2d5.png",
        'C': base_path / "Captura_de_pantalla_2025-12-19_a_la_s__00.46.31-dd975e58-343c-4dc2-9a20-f2df5efae07f.png",
        'D': base_path / "Captura_de_pantalla_2025-12-19_a_la_s__00.46.38-9e0a20ea-95c3-4959-8ce3-9299f444ad51.png",
    }
    
    print("=" * 60)
    print("🔧 Q38: USANDO IMÁGENES PROPORCIONADAS")
    print("=" * 60)
    
    question_dir = output_dir / "Q38"
    result = fix_q38_with_images(question_dir, test_name, image_paths)
    
    if result.get("success"):
        print("\n✅ Q38 corregida exitosamente con imágenes proporcionadas")
    else:
        print(f"\n❌ Error: {result.get('error')}")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
