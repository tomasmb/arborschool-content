#!/usr/bin/env python3
"""
Script para procesar Q50 manualmente extrayendo las 4 imágenes de alternativas correctamente.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

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


def process_q50_manual(question_dir: Path, pdf_path: Path, test_name: str) -> Dict[str, Any]:
    """
    Q50: Procesar manualmente extrayendo las 4 imágenes correctas.
    """
    print(f"\n🔧 Procesando Q50 manualmente")
    
    if not pdf_path.exists():
        return {"success": False, "error": "PDF no encontrado"}
    
    # Primero procesar normalmente para obtener el processed_content
    print(f"   📄 Procesando PDF para obtener estructura...")
    result = process_single_question_pdf(
        input_pdf_path=str(pdf_path),
        output_dir=str(question_dir),
        openai_api_key=None,
        paes_mode=True,
        skip_if_exists=False,
    )
    
    # Si falla, intentar extraer imágenes manualmente
    if not result.get("success"):
        print(f"   ⚠️  Procesamiento automático falló, extrayendo imágenes manualmente...")
        
        doc = fitz.open(str(pdf_path))
        page = doc[0]
        
        # Obtener todas las imágenes
        blocks = page.get_text("dict", sort=True)["blocks"]
        image_blocks = [b for b in blocks if b.get("type") == 1]
        
        # Ordenar por posición (y primero, luego x)
        image_blocks.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))
        
        print(f"   📸 Encontradas {len(image_blocks)} imágenes en el PDF")
        
        # Las 4 imágenes de alternativas deberían estar en las posiciones más bajas
        # Excluir la imagen más arriba (probablemente del enunciado) si hay 5
        if len(image_blocks) >= 4:
            # Usar las últimas 4 imágenes (más abajo en la página)
            alternative_images = image_blocks[-4:] if len(image_blocks) > 4 else image_blocks
            
            s3_urls = []
            for i, img_block in enumerate(alternative_images):
                bbox = img_block["bbox"]
                rendered = render_image_area(page, bbox, bbox, i)
                
                if rendered and rendered.get("image_base64"):
                    s3_url = upload_image_to_s3(
                        image_base64=rendered["image_base64"],
                        question_id=f"Q50_alt{chr(65+i)}",
                        test_name=test_name,
                    )
                    if s3_url:
                        s3_urls.append(s3_url)
                        print(f"   ✅ Imagen alternativa {chr(65+i)} extraída")
            
            doc.close()
            
            if len(s3_urls) == 4:
                # Crear XML básico con las imágenes
                xml_content = f'''<qti-assessment-item xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.imsglobal.org/xsd/imsqtiasi_v3p0 https://purl.imsglobal.org/spec/qti/v3p0/schema/xsd/imsqti_asiv3p0_v1p0.xsd" identifier="question-50" title="Verificación de relación perímetro-área círculos" adaptive="false" time-dependent="false">
  <qti-response-declaration identifier="RESPONSE" cardinality="single" base-type="identifier">
    <qti-correct-response>
      <qti-value>ChoiceA</qti-value>
    </qti-correct-response>
  </qti-response-declaration>
  <qti-outcome-declaration identifier="SCORE" cardinality="single" base-type="float">
    <qti-default-value>
      <qti-value>0</qti-value>
    </qti-default-value>
  </qti-outcome-declaration>
  <qti-item-body>
    <p>50. Para verificar la relación entre el perímetro y el área de un círculo, un grupo de estudiantes dibuja un círculo de radio r. Luego, dibujan varios círculos con el mismo radio r y observan que todos tienen el mismo perímetro y la misma área.</p>
    <p>¿Cuál de las siguientes imágenes representa mejor lo que los estudiantes deberían observar?</p>
    <qti-choice-interaction max-choices="1" response-identifier="RESPONSE">
      <qti-simple-choice identifier="ChoiceA">
        <p><img src="{s3_urls[0]}" alt="Opción A"/></p>
      </qti-simple-choice>
      <qti-simple-choice identifier="ChoiceB">
        <p><img src="{s3_urls[1]}" alt="Opción B"/></p>
      </qti-simple-choice>
      <qti-simple-choice identifier="ChoiceC">
        <p><img src="{s3_urls[2]}" alt="Opción C"/></p>
      </qti-simple-choice>
      <qti-simple-choice identifier="ChoiceD">
        <p><img src="{s3_urls[3]}" alt="Opción D"/></p>
      </qti-simple-choice>
    </qti-choice-interaction>
  </qti-item-body>
  <qti-response-processing template="https://purl.imsglobal.org/spec/qti/v3p0/rptemplates/match_correct.xml"/>
</qti-assessment-item>'''
                
                xml_path = question_dir / "question.xml"
                with open(xml_path, "w", encoding="utf-8") as f:
                    f.write(xml_content)
                
                print(f"   ✅ XML creado con 4 imágenes de alternativas")
                return {"success": True}
        
        doc.close()
        return {"success": False, "error": "No se pudieron extraer 4 imágenes"}
    
    # Si el procesamiento fue exitoso, verificar que tenga las 4 imágenes
    xml_path = question_dir / "question.xml"
    if xml_path.exists():
        with open(xml_path, "r", encoding="utf-8") as f:
            xml_content = f.read()
        
        # Contar imágenes en alternativas
        img_count = len(re.findall(r'<qti-simple-choice[^>]*>.*?<img', xml_content, re.DOTALL))
        if img_count == 4:
            print(f"   ✅ Q50 procesada exitosamente con 4 imágenes")
            return {"success": True}
        else:
            print(f"   ⚠️  Q50 procesada pero tiene {img_count} imágenes en alternativas (esperadas 4)")
            return {"success": False, "error": f"Solo {img_count} imágenes en alternativas"}
    
    return result

if __name__ == "__main__":
    questions_dir = Path("../../data/pruebas/procesadas/Prueba-invierno-2025/pdf")
    output_dir = Path("../../data/pruebas/procesadas/Prueba-invierno-2025/qti")
    test_name = "Prueba-invierno-2025"
    
    pdf_path = questions_dir / "Q50.pdf"
    question_dir = output_dir / "Q50"
    
    result = process_q50_manual(question_dir, pdf_path, test_name)
    if result.get("success"):
        print("✅ Q50 procesada exitosamente")
    else:
        print(f"❌ Error: {result.get('error')}")
