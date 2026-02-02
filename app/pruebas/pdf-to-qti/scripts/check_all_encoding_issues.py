#!/usr/bin/env python3
"""
Script para verificar problemas de codificación en todos los QTI generados.
Detecta errores comunes de tildes, "ñ", y signos de interrogación.
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Importar ENCODING_FIXES desde el módulo principal para mantener consistencia
try:
    # Intentar importar desde el módulo qti_transformer
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from modules.qti_transformer import ENCODING_FIXES
    ENCODING_ISSUES = ENCODING_FIXES
except ImportError:
    # Fallback si no se puede importar
    print("⚠️  No se pudo importar ENCODING_FIXES, usando diccionario local")
    ENCODING_ISSUES = {
        'e1cido': 'ácido',
        'e1tomos': 'átomos',
        'af1o': 'año',
        'bfCue1l': '¿Cuál',
    }

# Patrones adicionales para detectar problemas
ENCODING_PATTERNS = [
    r'e[0-9][a-z]',  # e1, e2, e3, e9 seguido de letra
    r'f[0-9][a-z]',  # f1, f3 seguido de letra
    r'bf[a-z]',      # bf seguido de letra (¿ mal codificado)
    r'd[0-9]',       # d7, d9 (signos menos mal codificados)
]


def check_question_encoding(xml_path: Path) -> dict:
    """
    Verifica problemas de codificación en un QTI XML.

    Returns:
        Dict con información sobre problemas encontrados
    """
    if not xml_path.exists():
        return {"found": False, "error": "XML no encontrado"}

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        # Verificar en el XML completo (incluye atributos y contenido)
        xml_str = ET.tostring(root, encoding='unicode')

        issues_found = []
        patterns_checked = set()

        # Verificar patrones conocidos en el XML completo
        for wrong, correct in ENCODING_ISSUES.items():
            if wrong in xml_str and wrong not in patterns_checked:
                # Contar ocurrencias
                count = xml_str.count(wrong)
                issues_found.append({
                    'pattern': wrong,
                    'should_be': correct,
                    'count': count,
                    'type': 'known_pattern'
                })
                patterns_checked.add(wrong)

        # Verificar patrones genéricos
        import re
        for pattern in ENCODING_PATTERNS:
            matches = re.findall(pattern, xml_str)
            if matches:
                unique_matches = list(set(matches))
                issues_found.append({
                    'pattern': pattern,
                    'matches': unique_matches[:5],  # Primeros 5 únicos
                    'count': len(matches),
                    'type': 'generic_pattern'
                })

        return {
            "found": len(issues_found) > 0,
            "issues": issues_found,
            "total_issues": len(issues_found)
        }

    except ET.ParseError as e:
        return {"found": False, "error": f"Error parseando XML: {e}"}
    except Exception as e:
        return {"found": False, "error": f"Error: {e}"}


def main():
    """Main entry point."""
    script_dir = Path(__file__).parent.parent
    output_dir = script_dir / "output" / "paes-invierno-2026-new"

    if not output_dir.exists():
        print(f"❌ No se encontró el directorio: {output_dir}")
        sys.exit(1)

    print("🔍 Verificando problemas de codificación en todos los QTI generados...")
    print("=" * 70)
    print()

    # Buscar todas las preguntas
    question_dirs = sorted(
        [d for d in output_dir.iterdir() if d.is_dir() and d.name.startswith("question_")],
        key=lambda x: int(x.name.split("_")[1])
    )

    issues_found = []
    total_checked = 0

    for question_dir in question_dirs:
        question_num = question_dir.name.split("_")[1]
        xml_path = question_dir / "question.xml"

        total_checked += 1
        result = check_question_encoding(xml_path)

        if result.get("error"):
            print(f"⚠️  Pregunta {question_num}: {result['error']}")
            continue

        if result["found"]:
            issues_found.append((int(question_num), result))
            print(f"❌ Pregunta {question_num}: {result['total_issues']} problema(s) encontrado(s)")

            # Mostrar detalles de los primeros problemas
            for issue in result["issues"][:3]:  # Primeros 3
                if issue["type"] == "known_pattern":
                    print(f"   • '{issue['pattern']}' debería ser '{issue['should_be']}' ({issue['count']} vez/veces)")
                elif issue["type"] == "generic_pattern":
                    print(f"   • Patrón '{issue['pattern']}': {issue['matches']} ({issue['count']} ocurrencias)")
        else:
            print(f"✅ Pregunta {question_num}: Sin problemas")

    print()
    print("=" * 70)
    print("📊 Resumen:")
    print(f"   Total de preguntas verificadas: {total_checked}")
    print(f"   Preguntas con problemas: {len(issues_found)}")
    print(f"   Preguntas sin problemas: {total_checked - len(issues_found)}")

    if issues_found:
        print()
        print("📋 Preguntas con problemas de codificación:")
        for q_num, result in sorted(issues_found):
            print(f"   • Pregunta {q_num:03d}: {result['total_issues']} problema(s)")
            for issue in result["issues"]:
                if issue["type"] == "known_pattern":
                    print(f"     - '{issue['pattern']}' → '{issue['should_be']}' ({issue['count']}x)")

        print()
        print("💡 Sugerencia: Ejecuta el script de corrección automática:")
        print("   python3 scripts/fix_encoding_in_xml.py")
    else:
        print()
        print("✅ ¡Excelente! No se encontraron problemas de codificación.")


if __name__ == "__main__":
    main()
