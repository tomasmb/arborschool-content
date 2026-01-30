#!/usr/bin/env python3
"""
Script para preparar imágenes subiéndolas a S3 antes de regenerar QTI.
Esto permite trabajar sin cuota de API - solo sube imágenes que tienen placeholders.
"""

from __future__ import annotations

# CRITICAL: Load environment variables FIRST, before ANY other imports
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Calculate root: scripts/ -> pdf-to-qti/ -> pruebas/ -> app/ -> root
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent.parent.parent
env_file = project_root / ".env"
if env_file.exists():
    # Load using dotenv
    load_dotenv(env_file, override=True)

    # Also manually parse and set to ensure they're available
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                os.environ[key] = value

    print(f"✅ Loaded environment variables from {env_file}")
else:
    print(f"⚠️  .env file not found at {env_file}")

# Verificar que las credenciales se cargaron
aws_access = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
aws_bucket = os.getenv("AWS_S3_BUCKET")

print(f"🔑 AWS_ACCESS_KEY_ID: {'SET (' + aws_access[:10] + '...)' if aws_access else 'NOT SET'}")
print(f"🔑 AWS_SECRET_ACCESS_KEY: {'SET' if aws_secret else 'NOT SET'}")
print(f"🪣 AWS_S3_BUCKET: {aws_bucket}")

if not aws_access or not aws_secret:
    print("⚠️  WARNING: AWS credentials not found in environment. S3 uploads will fail.")

# NOW add modules to path and import
sys.path.insert(0, str(script_dir.parent))

import base64
import hashlib
import json
import re

# Import boto3 directly to avoid import issues
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    print("❌ boto3 no está instalado. Instala con: pip install boto3")


def upload_image_to_s3_direct(
    image_base64: str,
    question_id: str | None = None,
    bucket_name: str | None = None,
    test_name: str | None = None,
) -> str | None:
    """Sube una imagen a S3 directamente usando boto3."""
    if not BOTO3_AVAILABLE:
        return None

    if not bucket_name:
        bucket_name = os.getenv("AWS_S3_BUCKET", "paes-question-images")

    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_REGION", "us-east-1")

    if not aws_access_key or not aws_secret_key:
        print("   ❌ Credenciales AWS no encontradas")
        return None

    try:
        # Clean base64 data
        if image_base64.startswith("data:"):
            header, encoded = image_base64.split(",", 1)
            mime_type = header.split(":")[1].split(";")[0]
            image_data = base64.b64decode(encoded)
        else:
            image_data = base64.b64decode(image_base64)
            mime_type = "image/png"

        # Generate filename
        if question_id:
            safe_id = "".join(c for c in question_id if c.isalnum() or c in "-_")
            filename = f"{safe_id}.png"
        else:
            image_hash = hashlib.md5(image_data).hexdigest()[:12]
            filename = f"img_{image_hash}.png"

        # Build path
        path_prefix = "images/"
        if test_name:
            safe_test_name = "".join(c for c in test_name if c.isalnum() or c in "-_")
            path_prefix = f"{path_prefix}{safe_test_name}/"

        s3_key = f"{path_prefix}{filename}"

        # Create S3 client and upload
        session = boto3.Session(
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region,
        )
        s3_client = session.client("s3")

        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=image_data,
            ContentType=mime_type,
        )

        s3_url = f"https://{bucket_name}.s3.{aws_region}.amazonaws.com/{s3_key}"
        return s3_url

    except Exception as e:
        print(f"   ❌ Error al subir a S3: {e}")
        return None


def prepare_images_for_question(
    question_dir: Path,
    test_name: str | None = None,
) -> dict[str, any]:
    """
    Prepara imágenes para una pregunta subiéndolas a S3.
    
    Args:
        question_dir: Directorio de la pregunta (ej: Q23/)
        test_name: Nombre del test para organizar imágenes en S3
        
    Returns:
        Resultado del procesamiento con mapeo de placeholders a URLs
    """
    processed_json = question_dir / "processed_content.json"
    extracted_json = question_dir / "extracted_content.json"

    if not processed_json.exists():
        return {
            "success": False,
            "error": f"processed_content.json no encontrado en {question_dir}"
        }

    if not extracted_json.exists():
        return {
            "success": False,
            "error": f"extracted_content.json no encontrado en {question_dir}"
        }

    # Cargar archivos
    print("📖 Cargando processed_content.json...")
    with open(processed_json, "r", encoding="utf-8") as f:
        processed_content = json.load(f)

    print("📖 Cargando extracted_content.json...")
    with open(extracted_json, "r", encoding="utf-8") as f:
        extracted_content = json.load(f)

    question_id = question_dir.name
    placeholder_to_s3_url: dict[str, str] = {}
    uploaded_count = 0

    # Procesar image_base64 si tiene placeholder
    if processed_content.get('image_base64') and processed_content['image_base64'].startswith('CONTENT_PLACEHOLDER_'):
        placeholder = processed_content['image_base64']
        print(f"\n🔄 Procesando placeholder: {placeholder}")

        match = re.search(r'P(\d+)', placeholder)
        if match:
            idx = int(match.group(1))
            base64_data = None

            # Buscar en all_images del extracted_content
            if 'all_images' in extracted_content and idx < len(extracted_content['all_images']):
                extracted_img = extracted_content['all_images'][idx]
                if extracted_img.get('image_base64') and not extracted_img['image_base64'].startswith('CONTENT_PLACEHOLDER'):
                    base64_data = extracted_img['image_base64']

            # También intentar en image_base64 raíz del extracted_content si es P0
            if not base64_data and idx == 0 and extracted_content.get('image_base64'):
                if not extracted_content['image_base64'].startswith('CONTENT_PLACEHOLDER'):
                    base64_data = extracted_content['image_base64']

            if base64_data:
                # Asegurar formato data URI
                if not base64_data.startswith('data:'):
                    base64_data = f"data:image/png;base64,{base64_data}"

                print("   📤 Subiendo imagen principal a S3...")
                s3_url = upload_image_to_s3_direct(
                    image_base64=base64_data,
                    question_id=question_id or "main",
                    bucket_name=os.getenv("AWS_S3_BUCKET"),
                    test_name=test_name,
                )

                if s3_url:
                    placeholder_to_s3_url[placeholder] = s3_url
                    placeholder_to_s3_url['main_image'] = s3_url
                    uploaded_count += 1
                    print(f"   ✅ Subida exitosa: {s3_url}")
                else:
                    print("   ❌ Error al subir imagen principal")
            else:
                print("   ⚠️  No se encontró la imagen correspondiente en extracted_content")

    # Procesar all_images
    if processed_content.get('all_images'):
        print(f"\n🔄 Procesando {len(processed_content['all_images'])} imagen(es) adicional(es)...")
        for i, img_info in enumerate(processed_content['all_images']):
            placeholder = img_info.get('image_base64', '')
            if placeholder.startswith('CONTENT_PLACEHOLDER_'):
                print(f"\n   📌 Imagen {i}: {placeholder}")

                match = re.search(r'P(\d+)', placeholder)
                if match:
                    idx = int(match.group(1))
                    base64_data = None

                    # Buscar en all_images del extracted_content
                    if 'all_images' in extracted_content and idx < len(extracted_content['all_images']):
                        extracted_img = extracted_content['all_images'][idx]
                        if extracted_img.get('image_base64') and not extracted_img['image_base64'].startswith('CONTENT_PLACEHOLDER'):
                            base64_data = extracted_img['image_base64']

                    # Si no encontramos y es P0, buscar en image_base64 raíz
                    if not base64_data and idx == 0 and extracted_content.get('image_base64'):
                        if not extracted_content['image_base64'].startswith('CONTENT_PLACEHOLDER'):
                            base64_data = extracted_content['image_base64']

                    if base64_data:
                        # Asegurar formato data URI
                        if not base64_data.startswith('data:'):
                            base64_data = f"data:image/png;base64,{base64_data}"

                        img_id = f"{question_id}_img{i}" if question_id else f"img{i}"
                        print(f"   📤 Subiendo imagen {i} a S3...")
                        s3_url = upload_image_to_s3_direct(
                            image_base64=base64_data,
                            question_id=img_id,
                            bucket_name=os.getenv("AWS_S3_BUCKET"),
                            test_name=test_name,
                        )

                        if s3_url:
                            placeholder_to_s3_url[placeholder] = s3_url
                            placeholder_to_s3_url[f"image_{i}"] = s3_url
                            uploaded_count += 1
                            print(f"   ✅ Subida exitosa: {s3_url}")
                        else:
                            print(f"   ❌ Error al subir imagen {i}")
                    else:
                        print("   ⚠️  No se encontró la imagen correspondiente en extracted_content")

    # Guardar mapeo en un archivo JSON para uso futuro
    if placeholder_to_s3_url:
        mapping_file = question_dir / "s3_image_mapping.json"
        with open(mapping_file, "w", encoding="utf-8") as f:
            json.dump(placeholder_to_s3_url, f, indent=2)
        print(f"\n✅ Mapeo guardado en: {mapping_file}")

    return {
        "success": True,
        "uploaded_count": uploaded_count,
        "mapping": placeholder_to_s3_url,
        "mapping_file": str(question_dir / "s3_image_mapping.json") if placeholder_to_s3_url else None
    }


def main():
    """Función principal."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Preparar imágenes subiéndolas a S3 antes de regenerar QTI"
    )
    parser.add_argument(
        "--question-numbers",
        nargs="+",
        type=int,
        required=True,
        help="Números de pregunta a procesar (ej: 23)"
    )
    parser.add_argument(
        "--output-dir",
        default="../../data/pruebas/procesadas/seleccion-regular-2026/qti",
        help="Directorio base con las carpetas de preguntas"
    )
    parser.add_argument(
        "--test-name",
        default="seleccion-regular-2026",
        help="Nombre del test para organizar imágenes en S3"
    )

    args = parser.parse_args()

    output_base_dir = Path(args.output_dir)

    print("=" * 60)
    print("Preparación de imágenes para regeneración")
    print("=" * 60)
    print(f"📁 Directorio: {output_base_dir}")
    print(f"📋 Preguntas: {len(args.question_numbers)}")
    print(f"📦 Test: {args.test_name}")
    print()

    success_count = 0
    failed_count = 0

    for i, q_num in enumerate(args.question_numbers, 1):
        question_dir = output_base_dir / f"Q{q_num}"

        print(f"[{i}/{len(args.question_numbers)}] Procesando Q{q_num}...")

        if not question_dir.exists():
            print(f"   ❌ Carpeta no encontrada: {question_dir}")
            failed_count += 1
            continue

        try:
            result = prepare_images_for_question(
                question_dir=question_dir,
                test_name=args.test_name,
            )

            if result.get("success"):
                print(f"   ✅ Éxito: {result.get('uploaded_count', 0)} imagen(es) subida(s)")
                success_count += 1
            else:
                print(f"   ❌ Falló: {result.get('error', 'Unknown')}")
                failed_count += 1
        except Exception as e:
            print(f"   ❌ Excepción: {e}")
            failed_count += 1

        print()

    print("=" * 60)
    print(f"✅ Exitosas: {success_count}")
    print(f"❌ Fallidas: {failed_count}")
    print(f"📊 Total: {len(args.question_numbers)}")
    print("=" * 60)


if __name__ == "__main__":
    main()

