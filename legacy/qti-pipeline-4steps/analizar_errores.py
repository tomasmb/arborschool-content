#!/usr/bin/env python3
"""Análisis automatizado de errores de notación matemática en preguntas.

Detecta posibles errores comunes que podrían requerir corrección manual.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# Patrones de posibles errores
SUSPICIOUS_PATTERNS = [
    {
        "name": "V seguida de números (posible raíz cuadrada mal parseada)",
        "pattern": re.compile(r'\bV\d{2,}'),
        "description": "V seguida de números puede indicar raíz cuadrada mal parseada",
        "severity": "alta"
    },
    {
        "name": "Números que podrían ser potencias concatenadas",
        "pattern": re.compile(r'\b\d{3,4}(?=\s*[+\-*/·]|\s*\[x\]|\s*$)'),
        "description": "Números de 3-4 dígitos en expresiones matemáticas podrían ser potencias",
        "severity": "media"
    },
    {
        "name": "[x] en contexto matemático",
        "pattern": re.compile(r'\d+\s*\[x\]'),
        "description": "[x] después de números puede indicar notación matemática, no respuesta correcta",
        "severity": "media"
    },
    {
        "name": "Números con formato sospechoso (ej: 2002, 1502)",
        "pattern": re.compile(r'\b(\d{3})(\d)\b(?=\s*[+\-*/·-])'),
        "description": "Números donde último dígito podría ser exponente (ej: 2002 → 200²)",
        "severity": "alta",
        "context_required": True
    },
    {
        "name": "Expresiones con operadores y números sospechosos",
        "pattern": re.compile(r'\d+\s*[+\-*/·]\s*\d{3,4}'),
        "description": "Expresiones matemáticas con números que podrían necesitar corrección",
        "severity": "baja"
    }
]


def analyze_question(question: dict[str, Any]) -> list[dict[str, Any]]:
    """Analiza una pregunta en busca de posibles errores."""
    issues = []
    content = question.get("content", "")
    qid = question.get("id", "unknown")
    
    for check in SUSPICIOUS_PATTERNS:
        pattern = check["pattern"]
        matches = pattern.findall(content) if isinstance(content, str) else []
        
        if matches:
            # Filtrar falsos positivos
            if check.get("context_required"):
                # Solo reportar si está en contexto matemático claro
                if not any(c in content for c in ["√", "²", "V", "-", "+", "*", "·"]):
                    continue
            
            # Evitar URLs
            filtered_matches = []
            for match in matches:
                if isinstance(match, tuple):
                    match_str = "".join(map(str, match))
                else:
                    match_str = str(match)
                # Filtrar si está en URL
                if "http" not in content[max(0, content.find(match_str)-50):content.find(match_str)+50]:
                    filtered_matches.append(match_str if not isinstance(match, tuple) else match)
            
            if filtered_matches:
                issues.append({
                    "question_id": qid,
                    "issue_type": check["name"],
                    "severity": check["severity"],
                    "description": check["description"],
                    "matches": list(set(filtered_matches))[:5],  # Limit to 5 unique matches
                    "snippet": _extract_snippet(content, pattern)
                })
    
    return issues


def _extract_snippet(content: str, pattern: re.Pattern, context: int = 50) -> str:
    """Extrae un snippet del contenido alrededor del match."""
    match = pattern.search(content)
    if not match:
        return ""
    
    start = max(0, match.start() - context)
    end = min(len(content), match.end() + context)
    snippet = content[start:end]
    
    # Marcar el match
    match_start = match.start() - start
    match_end = match.end() - start
    
    return (
        snippet[:match_start] +
        f"→→{snippet[match_start:match_end]}←←" +
        snippet[match_end:]
    )


def analyze_segmented_json(json_path: str) -> dict[str, Any]:
    """Analiza un archivo segmented.json en busca de errores."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    all_issues = []
    questions = data.get("validated_questions", []) + data.get("unvalidated_questions", [])
    
    for question in questions:
        issues = analyze_question(question)
        all_issues.extend(issues)
    
    # Organizar por severidad
    by_severity = {
        "alta": [i for i in all_issues if i["severity"] == "alta"],
        "media": [i for i in all_issues if i["severity"] == "media"],
        "baja": [i for i in all_issues if i["severity"] == "baja"]
    }
    
    return {
        "total_questions": len(questions),
        "questions_with_issues": len(set(i["question_id"] for i in all_issues)),
        "total_issues": len(all_issues),
        "issues_by_severity": by_severity,
        "all_issues": all_issues
    }


def print_report(analysis: dict[str, Any]) -> None:
    """Imprime un reporte de análisis."""
    print("=" * 70)
    print("REPORTE DE ANÁLISIS DE ERRORES POTENCIALES")
    print("=" * 70)
    print()
    print(f"Total preguntas analizadas: {analysis['total_questions']}")
    print(f"Preguntas con posibles errores: {analysis['questions_with_issues']}")
    print(f"Total de problemas detectados: {analysis['total_issues']}")
    print()
    
    for severity in ["alta", "media", "baja"]:
        issues = analysis["issues_by_severity"][severity]
        if issues:
            print(f"⚠️  SEVERIDAD {severity.upper()}: {len(issues)} problemas")
            print("-" * 70)
            
            # Agrupar por tipo de issue
            by_type = {}
            for issue in issues:
                issue_type = issue["issue_type"]
                if issue_type not in by_type:
                    by_type[issue_type] = []
                by_type[issue_type].append(issue)
            
            for issue_type, type_issues in by_type.items():
                print(f"\n  📋 {issue_type}: {len(type_issues)} casos")
                print(f"     {type_issues[0]['description']}")
                
                # Mostrar ejemplos
                for issue in type_issues[:3]:  # Mostrar solo primeros 3
                    print(f"\n     Pregunta {issue['question_id']}:")
                    print(f"       Matches: {', '.join(str(m) for m in issue['matches'][:3])}")
                    if issue.get('snippet'):
                        snippet = issue['snippet'].replace('\n', ' ')
                        if len(snippet) > 100:
                            snippet = snippet[:97] + "..."
                        print(f"       Contexto: ...{snippet}...")
                
                if len(type_issues) > 3:
                    print(f"     ... y {len(type_issues) - 3} casos más")
            
            print()


def main():
    """Función principal."""
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python analizar_errores.py <ruta_a_segmented.json>")
        print("\nEjemplo:")
        print("  python analizar_errores.py app/data/pruebas/procesadas/prueba-invierno-2026/segmented.json")
        sys.exit(1)
    
    json_path = sys.argv[1]
    
    if not Path(json_path).exists():
        print(f"Error: No se encontró el archivo {json_path}")
        sys.exit(1)
    
    print("Analizando...")
    analysis = analyze_segmented_json(json_path)
    print_report(analysis)
    
    # Guardar reporte JSON
    report_path = Path(json_path).parent / "reporte_errores.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Reporte completo guardado en: {report_path}")


if __name__ == "__main__":
    main()
