#!/usr/bin/env python3
"""
Script para migrar QTI con imágenes base64 a S3.

Este script:
1. Identifica QTI que tienen imágenes en base64
2. Extrae las imágenes base64
3. Las sube a S3
4. Reemplaza los data URIs con URLs S3
5. Guarda los QTI actualizados
"""

import base64
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.utils.s3_uploader import upload_image_to_s3

# Load environment variables
# Try multiple possible locations for .env
possible_env_locations = [
    Path(__file__).parent.parent.parent.parent / ".env",  # From scripts/ -> project root
    Path(__file__).parent.parent.parent.parent.parent / ".env",  # Alternative
    Path.cwd() / ".env",  # Current directory
]

env_file = None
for loc in possible_env_locations:
    if loc.exists():
        env_file = loc
        break
if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ Loaded environment variables from {env_file}")
else:
    print("⚠️  No .env file found")


def extract_base64_images(qti_xml: str) -> List[Dict[str, str]]:
    """
    Extrae todas las imágenes base64 de un QTI XML.

    Returns:
        Lista de diccionarios con 'data_uri', 'base64_data', 'mime_type'
    """
    images = []

    # Pattern para encontrar data URIs completos
    data_uri_pattern = r"data:image/([^;]+);base64,([A-Za-z0-9+/=]+)"

    matches = re.finditer(data_uri_pattern, qti_xml)
    for match in matches:
        mime_type = match.group(1)
        base64_data = match.group(2)
        full_data_uri = match.group(0)

        images.append(
            {
                "data_uri": full_data_uri,
                "base64_data": base64_data,
                "mime_type": mime_type,
            }
        )

    return images


def fix_base64_padding(base64_data: str) -> str:
    """
    Arregla el padding de base64 si es necesario.
    Base64 requiere que la longitud sea múltiplo de 4.
    """
    # Remover espacios y saltos de línea
    base64_data = base64_data.strip().replace(" ", "").replace("\n", "")

    # Agregar padding si es necesario
    missing_padding = len(base64_data) % 4
    if missing_padding:
        base64_data += "=" * (4 - missing_padding)

    return base64_data


def upload_images_to_s3(images: List[Dict[str, str]], question_id: str) -> Dict[str, Optional[str]]:
    """
    Sube imágenes a S3 y retorna un mapeo de data URI a URL S3.

    Args:
        images: Lista de imágenes con base64_data
        question_id: ID de la pregunta para nombrar las imágenes

    Returns:
        Diccionario mapeando data_uri -> s3_url
    """
    mapping = {}

    for i, image_info in enumerate(images):
        base64_data = image_info["base64_data"]
        data_uri = image_info["data_uri"]

        # Arreglar padding si es necesario
        try:
            base64_data = fix_base64_padding(base64_data)
            # Verificar que es válido intentando decodificarlo
            base64.b64decode(base64_data, validate=True)
        except Exception as e:
            print(f"   ⚠️  Base64 inválido para imagen {i + 1}: {str(e)}")
            print("   ⚠️  Saltando esta imagen (mantendrá base64)")
            continue

        # Generar ID único para esta imagen
        img_id = f"{question_id}_img{i}" if i > 0 else question_id

        print(f"   📤 Subiendo imagen {i + 1}/{len(images)} a S3...")

        # Subir a S3 (la función acepta base64 con o sin prefijo)
        s3_url = upload_image_to_s3(
            image_base64=base64_data,
            question_id=img_id,
        )

        if s3_url:
            mapping[data_uri] = s3_url
            print(f"   ✅ Subida exitosa: {s3_url}")
        else:
            print(f"   ❌ Error al subir imagen {i + 1} a S3")
            # Mantener el data URI original si falla

    return mapping


def replace_data_uris_with_s3(qti_xml: str, uri_mapping: Dict[str, str]) -> str:
    """
    Reemplaza data URIs con URLs S3 en el QTI XML.

    Args:
        qti_xml: XML del QTI
        uri_mapping: Mapeo de data_uri -> s3_url

    Returns:
        XML actualizado con URLs S3
    """
    updated_xml = qti_xml

    # Ordenar por longitud descendente para reemplazar los más largos primero
    # Esto evita reemplazos parciales
    sorted_mappings = sorted(uri_mapping.items(), key=lambda x: len(x[0]), reverse=True)

    for data_uri, s3_url in sorted_mappings:
        # Reemplazar el data URI completo con la URL S3
        # Usar replace con count=1 para evitar reemplazos múltiples del mismo patrón
        updated_xml = updated_xml.replace(data_uri, s3_url, 1)

        # Verificar si hay base64 residual después de la URL S3 (error de reemplazo parcial)
        # Buscar patrones como: s3_url + base64_data
        pattern = s3_url.replace(".", r"\.").replace("/", r"\/")
        # Buscar si hay base64 después de la URL S3 en el mismo atributo src
        residual_pattern = re.compile(rf"({pattern})([A-Za-z0-9+/=]{{50,}})")
        if residual_pattern.search(updated_xml):
            # Limpiar base64 residual después de URLs S3
            updated_xml = re.sub(rf"({pattern})([A-Za-z0-9+/=]{{50,}})", r"\1", updated_xml)

    return updated_xml


def migrate_qti_file(qti_path: Path, dry_run: bool = False) -> Dict[str, any]:
    """
    Migra un QTI de base64 a S3.

    Args:
        qti_path: Ruta al archivo QTI
        dry_run: Si True, solo muestra lo que haría sin hacer cambios

    Returns:
        Diccionario con resultados de la migración
    """
    question_id = qti_path.stem  # Q10, Q12, etc.

    print(f"\n📄 Procesando {question_id}...")

    # Leer QTI
    try:
        qti_xml = qti_path.read_text(encoding="utf-8")
    except Exception as e:
        return {
            "success": False,
            "error": f"Error leyendo archivo: {e}",
            "question_id": question_id,
        }

    # Verificar si tiene base64
    if "data:image" not in qti_xml:
        return {
            "success": True,
            "skipped": True,
            "reason": "No tiene imágenes base64",
            "question_id": question_id,
        }

    # Extraer imágenes base64
    images = extract_base64_images(qti_xml)

    if not images:
        return {
            "success": True,
            "skipped": True,
            "reason": "No se encontraron imágenes base64 válidas",
            "question_id": question_id,
        }

    print(f"   🔍 Encontradas {len(images)} imagen(es) base64")

    if dry_run:
        print(f"   🔍 [DRY RUN] Subiría {len(images)} imagen(es) a S3")
        return {
            "success": True,
            "dry_run": True,
            "images_count": len(images),
            "question_id": question_id,
        }

    # Subir imágenes a S3
    uri_mapping = upload_images_to_s3(images, question_id)

    if not uri_mapping:
        return {
            "success": False,
            "error": "No se pudo subir ninguna imagen a S3",
            "question_id": question_id,
            "images_count": len(images),
        }

    # Reemplazar data URIs con URLs S3
    updated_xml = replace_data_uris_with_s3(qti_xml, uri_mapping)

    # Verificar que se reemplazaron
    if "data:image" in updated_xml:
        remaining = len(re.findall(r"data:image/[^;]+;base64,", updated_xml))
        if remaining > 0:
            print(f"   ⚠️  Advertencia: {remaining} data URI(s) no fueron reemplazados")

    # Guardar QTI actualizado
    try:
        qti_path.write_text(updated_xml, encoding="utf-8")
        print("   ✅ QTI actualizado guardado")

        return {
            "success": True,
            "images_uploaded": len(uri_mapping),
            "images_total": len(images),
            "question_id": question_id,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error guardando archivo: {e}",
            "question_id": question_id,
        }


def main():
    """Función principal."""
    import argparse

    parser = argparse.ArgumentParser(description="Migrar QTI con imágenes base64 a S3")
    parser.add_argument(
        "--qti-dir", type=str, default="../../../data/pruebas/procesadas/prueba-invierno-2026/qti", help="Directorio con los QTI a migrar"
    )
    parser.add_argument("--questions", type=str, nargs="+", help="IDs específicos de preguntas a migrar (ej: Q10 Q12 Q13)")
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar lo que haría sin hacer cambios")

    args = parser.parse_args()

    # Resolver ruta del directorio
    qti_dir = Path(__file__).parent / args.qti_dir
    if not qti_dir.exists():
        qti_dir = Path(args.qti_dir)

    if not qti_dir.exists():
        print(f"❌ Directorio no encontrado: {qti_dir}")
        return 1

    print("=" * 60)
    print("Migración de Base64 a S3")
    print("=" * 60)
    print(f"Directorio: {qti_dir}")
    print(f"Modo: {'DRY RUN (sin cambios)' if args.dry_run else 'MIGRACIÓN REAL'}")
    print()

    # Verificar credenciales AWS
    aws_key = os.environ.get("AWS_ACCESS_KEY_ID")
    aws_secret = os.environ.get("AWS_SECRET_ACCESS_KEY")

    if not args.dry_run and (not aws_key or not aws_secret):
        print("❌ Credenciales AWS no encontradas")
        print("   Configura AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY en .env")
        return 1

    if args.dry_run:
        print("⚠️  MODO DRY RUN: No se harán cambios reales")
    else:
        print("✅ Credenciales AWS encontradas")

    print()

    # Encontrar QTI con base64
    if args.questions:
        # Procesar preguntas específicas
        qti_files = []
        for q_id in args.questions:
            # Aceptar Q10 o Q10.xml
            q_id = q_id.replace(".xml", "")
            qti_file = qti_dir / f"{q_id}.xml"
            if qti_file.exists():
                qti_files.append(qti_file)
            else:
                print(f"⚠️  Archivo no encontrado: {qti_file}")
    else:
        # Encontrar todos los QTI con base64
        qti_files = []
        for xml_file in sorted(qti_dir.glob("Q*.xml")):
            content = xml_file.read_text(encoding="utf-8")
            if "data:image" in content:
                qti_files.append(xml_file)

    if not qti_files:
        print("✅ No se encontraron QTI con imágenes base64")
        return 0

    print(f"📋 Encontrados {len(qti_files)} QTI con imágenes base64")
    print()

    # Procesar cada QTI
    results = {
        "successful": [],
        "failed": [],
        "skipped": [],
    }

    for qti_file in qti_files:
        result = migrate_qti_file(qti_file, dry_run=args.dry_run)

        if result.get("skipped"):
            results["skipped"].append(result)
        elif result.get("success"):
            results["successful"].append(result)
        else:
            results["failed"].append(result)

    # Resumen
    print()
    print("=" * 60)
    print("Resumen de Migración")
    print("=" * 60)
    print(f"✅ Exitosos: {len(results['successful'])}")
    print(f"❌ Fallidos: {len(results['failed'])}")
    print(f"⏭️  Omitidos: {len(results['skipped'])}")
    print()

    if results["failed"]:
        print("Errores:")
        for result in results["failed"]:
            print(f"  - {result['question_id']}: {result.get('error', 'Error desconocido')}")
        print()

    if args.dry_run:
        print("⚠️  Este fue un DRY RUN. Ejecuta sin --dry-run para hacer la migración real.")

    return 0 if not results["failed"] else 1


if __name__ == "__main__":
    sys.exit(main())
