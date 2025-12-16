#!/usr/bin/env python3
"""
Script para extraer las imágenes de las alternativas de Q7 del PDF
y subir la imagen faltante de B a S3.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
import os

# Cargar .env
project_root = Path(__file__).parent.parent.parent
env_paths = [
    project_root / ".env",
    Path(".env"),
    Path("../../.env"),
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break

sys.path.insert(0, str(Path(__file__).parent.parent))

import fitz  # PyMuPDF
import boto3
import base64
from modules.pdf_processor import extract_pdf_content
from modules.image_processing.llm_analyzer import analyze_visual_content_with_llm

def main():
    """Extraer imágenes de alternativas de Q7."""
    pdf_path = Path("../../../data/pruebas/raw/prueba-invierno-2026.pdf")
    if not pdf_path.exists():
        print(f"❌ PDF no encontrado: {pdf_path}")
        return
    
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ No se encontró API key")
        return
    
    print("📄 Abriendo PDF...")
    doc = fitz.open(str(pdf_path))
    
    # Encontrar página de Q7
    target_text = "12 huevos"
    found_page_num = None
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text()
        if target_text.lower() in text.lower() and "aparta" in text.lower():
            found_page_num = page_num
            break
    
    if found_page_num is None:
        print("❌ Q7 no encontrada")
        doc.close()
        return
    
    page = doc.load_page(found_page_num)
    print(f"✅ Q7 encontrada en página {found_page_num + 1}")
    print()
    
    # Extraer contenido con AI para obtener las imágenes de alternativas
    print("🔍 Extrayendo imágenes de alternativas con AI...")
    structured_text = page.get_text("dict", sort=True)
    question_text = page.get_text()
    
    # Analizar con LLM para encontrar las imágenes de alternativas
    analysis = analyze_visual_content_with_llm(
        page=page,
        text_blocks=structured_text.get("blocks", []),
        question_text=question_text,
        openai_api_key=api_key
    )
    
    # Procesar choice_bboxes si existen
    prompt_choice_analysis = analysis.get("prompt_choice_analysis", {})
    if prompt_choice_analysis.get("has_choice_visuals") and prompt_choice_analysis.get("choice_bboxes"):
        choice_bboxes = prompt_choice_analysis["choice_bboxes"]
        print(f"✅ Encontradas {len(choice_bboxes)} imágenes de alternativas")
        print()
        
        # Configurar S3
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        bucket_name = os.getenv('S3_BUCKET_NAME', 'paes-question-images')
        
        # Extraer y subir cada imagen
        for i, choice_info in enumerate(choice_bboxes):
            choice_letter = choice_info.get('choice_letter', f'Choice{i+1}')
            choice_bbox = choice_info['bbox']
            
            print(f"📸 Procesando {choice_letter}...")
            
            # Renderizar la imagen
            try:
                render_rect = fitz.Rect(choice_bbox)
                scale = 2.0
                matrix = fitz.Matrix(scale, scale)
                pix = page.get_pixmap(matrix=matrix, clip=render_rect, alpha=False)
                img_bytes = pix.tobytes("png")
                img_base64 = base64.b64encode(img_bytes).decode('utf-8')
                
                # Determinar nombre del archivo
                if choice_letter.upper() == 'A':
                    img_id = "Q7"
                elif choice_letter.upper() == 'B':
                    img_id = "Q7_img3"  # Nueva imagen para B
                elif choice_letter.upper() == 'C':
                    img_id = "Q7_img2"
                elif choice_letter.upper() == 'D':
                    img_id = "Q7_img1"
                else:
                    img_id = f"Q7_img{i+1}"
                
                # Subir a S3
                s3_key = f"images/{img_id}.png"
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=s3_key,
                    Body=img_bytes,
                    ContentType="image/png"
                )
                
                s3_url = f"https://{bucket_name}.s3.{os.getenv('AWS_REGION', 'us-east-1')}.amazonaws.com/{s3_key}"
                print(f"  ✅ Subida: {s3_url}")
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
        
        print()
        print("✅ Imágenes extraídas y subidas a S3")
        print()
        print("📝 Próximo paso: Actualizar Q7.xml para que B use Q7_img3.png")
    
    doc.close()

if __name__ == "__main__":
    main()
