#!/usr/bin/env python3
"""
Script para validar que cada pregunta tenga imágenes únicas.

Detecta problemas comunes:
- Múltiples preguntas compartiendo la misma imagen
- Imágenes duplicadas dentro de una misma pregunta
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List


def validate_image_uniqueness(test_name: str, output_dir: str) -> Dict[str, Any]:
    """
    Validar que cada pregunta tenga imágenes únicas.

    Returns:
        Dict con resultados de validación
    """
    output_path = Path(output_dir)
    if not output_path.exists():
        return {
            "success": False,
            "error": f"Output directory not found: {output_dir}"
        }

    # Encontrar todos los XMLs
    xml_files = list(output_path.glob("*/question.xml"))

    if not xml_files:
        return {
            "success": False,
            "error": "No XML files found"
        }

    # Mapear URLs de imágenes a preguntas
    image_to_questions: Dict[str, List[str]] = defaultdict(list)
    question_images: Dict[str, List[str]] = {}

    for xml_file in xml_files:
        question_id = xml_file.parent.name

        with open(xml_file, "r", encoding="utf-8") as f:
            xml_content = f.read()

        # Extraer todas las URLs de imágenes
        img_pattern = r'<img[^>]+src="([^"]+)"'
        matches = re.findall(img_pattern, xml_content)

        question_images[question_id] = matches

        for url in matches:
            image_to_questions[url].append(question_id)

    # Detectar problemas
    issues = []

    # Problema 1: Múltiples preguntas compartiendo la misma imagen
    for url, questions in image_to_questions.items():
        if len(questions) > 1:
            issues.append({
                "type": "duplicate_across_questions",
                "image_url": url,
                "shared_by": questions,
                "severity": "high"
            })

    # Problema 2: Imágenes duplicadas dentro de una pregunta
    for question_id, urls in question_images.items():
        seen = set()
        duplicates = []
        for url in urls:
            if url in seen:
                duplicates.append(url)
            seen.add(url)

        if duplicates:
            issues.append({
                "type": "duplicate_within_question",
                "question_id": question_id,
                "duplicate_urls": duplicates,
                "severity": "medium"
            })

    # Problema 3: Imágenes con nombres genéricos
    generic_patterns = [
        r'question\.png',
        r'pregunta\.png',
        r'main\.png',
    ]

    for question_id, urls in question_images.items():
        for url in urls:
            for pattern in generic_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    issues.append({
                        "type": "generic_image_name",
                        "question_id": question_id,
                        "image_url": url,
                        "severity": "low"
                    })
                    break

    return {
        "success": True,
        "total_questions": len(xml_files),
        "total_unique_images": len(image_to_questions),
        "issues": issues,
        "issue_count": len(issues),
        "high_severity_count": sum(1 for i in issues if i["severity"] == "high"),
        "medium_severity_count": sum(1 for i in issues if i["severity"] == "medium"),
        "low_severity_count": sum(1 for i in issues if i["severity"] == "low"),
    }


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate image uniqueness across questions"
    )
    parser.add_argument(
        "--test-name",
        required=True,
        help="Test name (e.g., prueba-invierno-2025)"
    )
    parser.add_argument(
        "--output-dir",
        default="../../data/pruebas/procesadas/{test_name}/qti",
        help="Output directory with QTI XMLs"
    )

    args = parser.parse_args()

    output_dir = args.output_dir.format(test_name=args.test_name)

    print("=" * 60)
    print("🔍 VALIDACIÓN DE UNICIDAD DE IMÁGENES")
    print("=" * 60)
    print(f"Test: {args.test_name}")
    print(f"Directorio: {output_dir}")
    print()

    result = validate_image_uniqueness(args.test_name, output_dir)

    if not result.get("success"):
        print(f"❌ Error: {result.get('error')}")
        return

    print("📊 Estadísticas:")
    print(f"   Total preguntas: {result['total_questions']}")
    print(f"   Total imágenes únicas: {result['total_unique_images']}")
    print(f"   Problemas encontrados: {result['issue_count']}")
    print()

    if result['issue_count'] > 0:
        print("⚠️  PROBLEMAS ENCONTRADOS:")
        print()

        high_issues = [i for i in result['issues'] if i['severity'] == 'high']
        if high_issues:
            print(f"🔴 Alta severidad ({len(high_issues)}):")
            for issue in high_issues:
                if issue['type'] == 'duplicate_across_questions':
                    print("   ❌ Imagen compartida por múltiples preguntas:")
                    print(f"      URL: {issue['image_url'][:80]}...")
                    print(f"      Compartida por: {', '.join(issue['shared_by'])}")
            print()

        medium_issues = [i for i in result['issues'] if i['severity'] == 'medium']
        if medium_issues:
            print(f"🟡 Media severidad ({len(medium_issues)}):")
            for issue in medium_issues:
                if issue['type'] == 'duplicate_within_question':
                    print(f"   ⚠️  Pregunta {issue['question_id']} tiene imágenes duplicadas:")
                    for url in issue['duplicate_urls']:
                        print(f"      {url[:80]}...")
            print()

        low_issues = [i for i in result['issues'] if i['severity'] == 'low']
        if low_issues:
            print(f"🟢 Baja severidad ({len(low_issues)}):")
            for issue in low_issues:
                print(f"   ℹ️  {issue['question_id']}: Nombre genérico - {issue['image_url'][:60]}...")
            print()
    else:
        print("✅ No se encontraron problemas de unicidad")

    print("=" * 60)

    # Guardar reporte
    report_file = Path(output_dir) / "image_uniqueness_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"📄 Reporte guardado en: {report_file}")


if __name__ == "__main__":
    main()
