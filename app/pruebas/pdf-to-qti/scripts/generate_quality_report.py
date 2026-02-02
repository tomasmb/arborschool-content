#!/usr/bin/env python3
"""
Script para generar un reporte completo de calidad de los QTI XMLs generados.
Ejecuta múltiples validaciones sin necesidad de llamadas API.

Uso:
    python scripts/generate_quality_report.py <test_name> [--output OUTPUT_FILE.json]

Ejemplo:
    python scripts/generate_quality_report.py seleccion-regular-2026
    python scripts/generate_quality_report.py seleccion-regular-2026 --output report.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def check_xml_structure(xml_file: Path) -> Dict[str, Any]:
    """Valida estructura básica del XML."""
    result = {"valid": False, "errors": [], "warnings": [], "elements": {}}

    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        xml_content = xml_file.read_text(encoding="utf-8")

        # Check root element
        if root.tag.endswith("assessment-item"):
            result["valid"] = True
        else:
            result["errors"].append(f"Root element should be assessment-item, found: {root.tag}")

        # Check namespace
        if "http://www.imsglobal.org/xsd/imsqtiasi_v3p0" not in xml_content:
            result["errors"].append("Missing QTI 3.0 namespace")

        # Check required elements
        required = {
            "response_declaration": "response-declaration",
            "item_body": "item-body",
            "choice_interaction": "choice-interaction",
            "correct_response": "correct-response",
        }

        for name, tag in required.items():
            found = any(tag in elem.tag for elem in root.iter())
            result["elements"][name] = found
            if not found:
                result["errors"].append(f"Missing required element: {name}")

        # Check number of choices
        choices = [e for e in root.iter() if "simple-choice" in e.tag]
        result["elements"]["num_choices"] = len(choices)

        if len(choices) != 4:
            result["warnings"].append(f"Expected 4 choices for PAES, found {len(choices)}")

        # Check for base64
        if "data:image" in xml_content and "base64" in xml_content:
            result["errors"].append("XML still contains base64 (should use S3 URLs)")

        # Check for S3 URLs
        s3_urls = re.findall(r'https://[^/]+\.s3\.[^/]+/[^"\']+', xml_content)
        result["elements"]["s3_images"] = len(s3_urls)

    except ET.ParseError as e:
        result["errors"].append(f"XML parsing error: {e}")
    except Exception as e:
        result["errors"].append(f"Error: {e}")

    return result


def check_encoding_issues(xml_file: Path) -> Dict[str, Any]:
    """Verifica problemas de codificación comunes."""
    result = {"has_issues": False, "issues": []}

    try:
        xml_content = xml_file.read_text(encoding="utf-8")

        # Known encoding patterns
        encoding_patterns = [
            (r"\be1\w*", "á (tildes mal codificados)"),
            (r"\bf3\w*", "ó (tildes mal codificados)"),
            (r"\bf1\w*", "ñ (letra ñ mal codificada)"),
            (r"\bbf\w*", "¿ (signo de interrogación mal codificado)"),
        ]

        for pattern, description in encoding_patterns:
            matches = re.findall(pattern, xml_content)
            if matches:
                unique_matches = list(set(matches))[:5]
                result["has_issues"] = True
                result["issues"].append({"pattern": pattern, "description": description, "matches": unique_matches, "count": len(matches)})

    except Exception as e:
        result["issues"].append({"error": str(e)})

    return result


def check_correct_answer(xml_file: Path, expected_answer: str | None) -> Dict[str, Any]:
    """Verifica que la respuesta correcta coincida con el answer key."""
    result = {"has_answer": False, "matches": False, "found": None, "expected": expected_answer}

    if not expected_answer:
        return result

    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Find correct-response
        correct_response = None
        for elem in root.iter():
            if "correct-response" in elem.tag:
                correct_response = elem
                break

        if correct_response:
            # Find qti-value
            for child in correct_response.iter():
                if "value" in child.tag and child.text:
                    result["has_answer"] = True
                    result["found"] = child.text.strip()

                    # Normalize for comparison
                    found_norm = child.text.strip().upper()
                    expected_norm = expected_answer.strip().upper()
                    result["matches"] = found_norm == expected_norm
                    break

    except Exception:
        pass

    return result


def generate_report(test_name: str, output_file: Path | None = None) -> Dict[str, Any]:
    """Genera reporte completo de calidad."""
    qti_dir = Path(f"app/data/pruebas/procesadas/{test_name}/qti")
    answer_key_path = Path(f"app/data/pruebas/procesadas/{test_name}/respuestas_correctas.json")

    if not qti_dir.exists():
        print(f"❌ Directory not found: {qti_dir}")
        return {}

    # Load answer key if available
    answer_key = {}
    if answer_key_path.exists():
        with open(answer_key_path, "r") as f:
            answer_key_data = json.load(f)
            answer_key = answer_key_data.get("answers", {})

    report = {
        "test_name": test_name,
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_xmls": 0,
            "valid_xmls": 0,
            "xmls_with_errors": 0,
            "xmls_with_warnings": 0,
            "encoding_issues": 0,
            "answer_mismatches": 0,
            "missing_xmls": [],
        },
        "details": [],
    }

    # Find all question folders
    question_folders = sorted(
        [f for f in qti_dir.iterdir() if f.is_dir() and f.name.startswith("Q")], key=lambda x: int(x.name[1:]) if x.name[1:].isdigit() else 999
    )

    for folder in question_folders:
        q_name = folder.name
        q_num = q_name[1:] if q_name[1:].isdigit() else None

        xml_file = folder / "question.xml"

        if not xml_file.exists():
            report["summary"]["missing_xmls"].append(q_name)
            continue

        report["summary"]["total_xmls"] += 1

        detail = {"question": q_name, "xml_file": str(xml_file)}

        # Check structure
        structure_check = check_xml_structure(xml_file)
        detail["structure"] = structure_check

        if structure_check["valid"] and not structure_check["errors"]:
            report["summary"]["valid_xmls"] += 1
        if structure_check["errors"]:
            report["summary"]["xmls_with_errors"] += 1
        if structure_check["warnings"]:
            report["summary"]["xmls_with_warnings"] += 1

        # Check encoding
        encoding_check = check_encoding_issues(xml_file)
        detail["encoding"] = encoding_check
        if encoding_check["has_issues"]:
            report["summary"]["encoding_issues"] += 1

        # Check correct answer
        expected = answer_key.get(q_num) if q_num else None
        answer_check = check_correct_answer(xml_file, expected)
        detail["correct_answer"] = answer_check
        if expected and answer_check["has_answer"] and not answer_check["matches"]:
            report["summary"]["answer_mismatches"] += 1

        report["details"].append(detail)

    # Print summary
    print("\n" + "=" * 60)
    print("📊 REPORTE DE CALIDAD QTI")
    print("=" * 60)
    print(f"Test: {test_name}")
    print(f"Generado: {report['generated_at']}")
    print()
    print(f"✅ XMLs válidos: {report['summary']['valid_xmls']}/{report['summary']['total_xmls']}")
    print(f"❌ XMLs con errores: {report['summary']['xmls_with_errors']}")
    print(f"⚠️  XMLs con warnings: {report['summary']['xmls_with_warnings']}")
    print(f"🔤 XMLs con problemas de encoding: {report['summary']['encoding_issues']}")
    print(f"📝 Respuestas incorrectas: {report['summary']['answer_mismatches']}")
    print(f"📄 XMLs faltantes: {len(report['summary']['missing_xmls'])}")

    if report["summary"]["missing_xmls"]:
        print("\n📋 Preguntas sin XML:")
        print(f"   {', '.join(report['summary']['missing_xmls'])}")

    # Show issues
    xmls_with_issues = [
        d
        for d in report["details"]
        if d["structure"]["errors"] or d["encoding"]["has_issues"] or (d["correct_answer"]["has_answer"] and not d["correct_answer"]["matches"])
    ]

    if xmls_with_issues:
        print(f"\n⚠️  XMLs con problemas ({len(xmls_with_issues)}):")
        for detail in xmls_with_issues[:10]:
            print(f"\n   {detail['question']}:")
            if detail["structure"]["errors"]:
                for error in detail["structure"]["errors"]:
                    print(f"      ❌ {error}")
            if detail["encoding"]["has_issues"]:
                print("      🔤 Problemas de encoding encontrados")
                for issue in detail["encoding"]["issues"][:2]:
                    print(f"         - {issue['description']}: {issue['count']} ocurrencias")
            if detail["correct_answer"]["has_answer"] and not detail["correct_answer"]["matches"]:
                print("      📝 Respuesta incorrecta:")
                print(f"         Esperado: {detail['correct_answer']['expected']}")
                print(f"         Encontrado: {detail['correct_answer']['found']}")

        if len(xmls_with_issues) > 10:
            print(f"\n   ... y {len(xmls_with_issues) - 10} más")

    # Save to file if requested
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Reporte guardado en: {output_file}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Generate quality report for QTI XMLs")
    parser.add_argument("test_name", help="Test name (e.g., 'seleccion-regular-2026')")
    parser.add_argument("--output", help="Output JSON file path (optional)")

    args = parser.parse_args()

    output_path = Path(args.output) if args.output else None
    report = generate_report(args.test_name, output_path)

    return 0 if report["summary"]["xmls_with_errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
