#!/usr/bin/env python3
"""
Script para validar la calidad de los QTI generados.
Verifica estructura, elementos requeridos, y genera un reporte.
"""

import json
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict


def validate_qti_structure(xml_path: Path) -> Dict[str, Any]:
    """Valida la estructura básica de un QTI XML."""
    result = {"valid": False, "errors": [], "warnings": [], "elements": {}}

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Namespace QTI
        qti_ns = "http://www.imsglobal.org/xsd/imsqtiasi_v3p0"
        math_ns = "http://www.w3.org/1998/Math/MathML"

        # Función helper para buscar elementos (con prefijo qti- o namespace)
        # El XML usa prefijos qti- pero el namespace está definido en el root
        def find_qti(tag):
            # Buscar en todo el árbol con cualquier namespace o prefijo
            for elem in root.iter():
                # Verificar si el tag termina con el nombre que buscamos
                if elem.tag.endswith(tag) or elem.tag == f"qti-{tag}":
                    # Verificar que sea el elemento correcto (no un subelemento con nombre similar)
                    if tag in ["response-declaration", "outcome-declaration", "item-body", "choice-interaction", "correct-response"]:
                        if elem.tag.endswith(tag):
                            return elem
                    else:
                        return elem
            return None

        def findall_qti(tag):
            results = []
            for elem in root.iter():
                if elem.tag.endswith(tag) or elem.tag == f"qti-{tag}":
                    results.append(elem)
            return results

        # Verificar elemento raíz
        if root.tag.endswith("assessment-item") or root.tag == f"{{{qti_ns}}}assessment-item" or "assessment-item" in root.tag:
            result["valid"] = True
        else:
            result["errors"].append(f"Root element should be assessment-item, found: {root.tag}")
            return result

        # Verificar elementos requeridos
        required_elements = {
            "response_declaration": find_qti("response-declaration"),
            "outcome_declaration": find_qti("outcome-declaration"),
            "item_body": find_qti("item-body"),
            "choice_interaction": find_qti("choice-interaction"),
            "correct_response": find_qti("correct-response"),
        }

        for name, element in required_elements.items():
            if element is not None:
                result["elements"][name] = True
            else:
                result["errors"].append(f"Missing required element: {name}")

        # Verificar alternativas
        choices = findall_qti("simple-choice")
        result["elements"]["num_choices"] = len(choices)

        if len(choices) < 2:
            result["errors"].append(f"Too few choices: {len(choices)} (expected at least 2)")
        elif len(choices) > 6:
            result["warnings"].append(f"Many choices: {len(choices)} (expected 4 for PAES)")
        elif len(choices) != 4:
            result["warnings"].append(f"Unexpected number of choices: {len(choices)} (expected 4 for PAES)")

        # Verificar respuesta correcta
        correct_response = find_qti("correct-response")
        if correct_response is not None:
            # Buscar qti-value dentro de correct-response
            value_elem = None
            for child in correct_response.iter():
                if child.tag.endswith("value") or "value" in child.tag:
                    value_elem = child
                    break
            if value_elem is not None and value_elem.text:
                result["elements"]["correct_response"] = value_elem.text
            else:
                result["errors"].append("Missing correct response value")
        else:
            result["errors"].append("Missing correct response element")

        # Verificar MathML
        math_elements = root.findall(f".//{{{math_ns}}}math") or root.findall(".//math")
        result["elements"]["has_math"] = len(math_elements) > 0
        result["elements"]["num_math"] = len(math_elements)

        # Verificar imágenes (buscar en todo el árbol, incluyendo atributos src)
        images = []
        for elem in root.iter():
            tag_lower = elem.tag.lower()
            # Buscar elementos img
            if "img" in tag_lower:
                images.append(elem)
            # También buscar atributos src con data:image o http
            if "src" in elem.attrib:
                src = elem.attrib["src"]
                if src.startswith("data:image") or src.startswith("http") or "image" in src.lower():
                    images.append(elem)
        result["elements"]["has_images"] = len(images) > 0
        result["elements"]["num_images"] = len(images)

        # Verificar tablas (buscar en todo el árbol)
        tables = []
        for elem in root.iter():
            tag_lower = elem.tag.lower()
            if "table" in tag_lower:
                tables.append(elem)
        result["elements"]["has_tables"] = len(tables) > 0
        result["elements"]["num_tables"] = len(tables)

        # Verificar título
        title = root.get("title", "")
        result["elements"]["has_title"] = bool(title)
        result["elements"]["title"] = title[:50] if title else "No title"

        # Verificar identifier
        identifier = root.get("identifier", "")
        result["elements"]["has_identifier"] = bool(identifier)

    except ET.ParseError as e:
        result["errors"].append(f"XML parse error: {str(e)}")
    except Exception as e:
        result["errors"].append(f"Validation error: {str(e)}")

    return result


def validate_all_questions(output_dir: str) -> Dict[str, Any]:
    """Valida todas las preguntas en el directorio de output."""
    output_path = Path(output_dir)

    if not output_path.exists():
        return {"success": False, "error": f"Output directory not found: {output_dir}"}

    # Encontrar todos los XMLs
    question_xmls = sorted(output_path.glob("question_*/question.xml"))

    if not question_xmls:
        return {"success": False, "error": f"No question XMLs found in {output_dir}"}

    print(f"📋 Validando {len(question_xmls)} preguntas...")
    print()

    results = {
        "total": len(question_xmls),
        "valid": 0,
        "invalid": 0,
        "questions": {},
        "summary": {
            "with_math": 0,
            "with_images": 0,
            "with_tables": 0,
            "correct_choices": 0,
            "missing_correct_response": 0,
            "errors": defaultdict(int),
            "warnings": defaultdict(int),
        },
    }

    for xml_path in question_xmls:
        question_id = xml_path.parent.name  # e.g., "question_001"
        question_num = question_id.replace("question_", "")

        print(f"Validando {question_id}...", end=" ")

        validation = validate_qti_structure(xml_path)
        results["questions"][question_num] = validation

        if validation["valid"] and not validation["errors"]:
            results["valid"] += 1
            print("✅")
        else:
            results["invalid"] += 1
            print("❌")
            if validation["errors"]:
                print(f"   Errores: {', '.join(validation['errors'])}")

        # Actualizar resumen
        if validation["elements"].get("has_math"):
            results["summary"]["with_math"] += 1
        if validation["elements"].get("has_images"):
            results["summary"]["with_images"] += 1
        if validation["elements"].get("has_tables"):
            results["summary"]["with_tables"] += 1

        num_choices = validation["elements"].get("num_choices", 0)
        if num_choices == 4:
            results["summary"]["correct_choices"] += 1

        if not validation["elements"].get("correct_response"):
            results["summary"]["missing_correct_response"] += 1

        for error in validation["errors"]:
            results["summary"]["errors"][error] += 1

        for warning in validation["warnings"]:
            results["summary"]["warnings"][warning] += 1

    # Calcular estadísticas
    results["success_rate"] = f"{(results['valid'] / results['total'] * 100):.1f}%"

    return results


def print_report(results: Dict[str, Any]):
    """Imprime un reporte detallado de la validación."""
    print()
    print("=" * 70)
    print("REPORTE DE VALIDACIÓN QTI")
    print("=" * 70)
    print()

    print("📊 RESUMEN GENERAL")
    print(f"   Total preguntas: {results['total']}")
    print(f"   ✅ Válidas: {results['valid']}")
    print(f"   ❌ Inválidas: {results['invalid']}")
    print(f"   Tasa de éxito: {results['success_rate']}")
    print()

    print("📈 ESTADÍSTICAS DE CONTENIDO")
    print(f"   Con MathML: {results['summary']['with_math']} ({results['summary']['with_math'] / results['total'] * 100:.1f}%)")
    print(f"   Con imágenes: {results['summary']['with_images']} ({results['summary']['with_images'] / results['total'] * 100:.1f}%)")
    print(f"   Con tablas: {results['summary']['with_tables']} ({results['summary']['with_tables'] / results['total'] * 100:.1f}%)")
    print(f"   Con 4 alternativas: {results['summary']['correct_choices']} ({results['summary']['correct_choices'] / results['total'] * 100:.1f}%)")
    print()

    if results["summary"]["errors"]:
        print("❌ ERRORES ENCONTRADOS")
        for error, count in sorted(results["summary"]["errors"].items(), key=lambda x: x[1], reverse=True):
            print(f"   - {error}: {count} veces")
        print()

    if results["summary"]["warnings"]:
        print("⚠️  ADVERTENCIAS")
        for warning, count in sorted(results["summary"]["warnings"].items(), key=lambda x: x[1], reverse=True):
            print(f"   - {warning}: {count} veces")
        print()

    # Preguntas con problemas
    problematic = []
    for qnum, validation in results["questions"].items():
        if validation["errors"]:
            problematic.append({"question": qnum, "errors": validation["errors"]})

    if problematic:
        print(f"🔍 PREGUNTAS CON PROBLEMAS ({len(problematic)}):")
        for item in problematic[:10]:  # Mostrar solo las primeras 10
            print(f"   Q{item['question']}: {', '.join(item['errors'][:2])}")
        if len(problematic) > 10:
            print(f"   ... y {len(problematic) - 10} más")
        print()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Validar calidad de QTI generados")
    parser.add_argument("--output-dir", default="./output/paes-invierno-2026-new", help="Directorio con los QTI generados")
    parser.add_argument("--json", help="Guardar resultados en JSON")

    args = parser.parse_args()

    print("=" * 70)
    print("VALIDACIÓN DE QTI GENERADOS")
    print("=" * 70)
    print()

    results = validate_all_questions(args.output_dir)

    if not results.get("success", True):
        print(f"❌ Error: {results.get('error')}")
        sys.exit(1)

    print_report(results)

    # Guardar JSON si se solicita
    if args.json:
        output_path = Path(args.json)
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"📄 Resultados guardados en: {output_path}")
        print()

    # Exit code basado en resultados
    if results["invalid"] > 0:
        print("⚠️  Se encontraron problemas en algunas preguntas")
        sys.exit(1)
    else:
        print("✅ Todas las preguntas son válidas")
        sys.exit(0)


if __name__ == "__main__":
    main()
