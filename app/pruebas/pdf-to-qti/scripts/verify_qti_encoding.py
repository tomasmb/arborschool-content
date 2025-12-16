#!/usr/bin/env python3
"""
Script para verificar problemas de codificación en QTI XML.
Confirma si los problemas están en el XML o solo en el HTML.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
import sys

def check_question(question_num: int, output_dir: Path) -> dict:
    """Verifica una pregunta específica."""
    question_num_str = f"{question_num:03d}"
    xml_path = output_dir / f"question_{question_num_str}" / "question.xml"
    
    if not xml_path.exists():
        return {
            "exists": False,
            "encoding_issues": [],
            "missing_content": [],
            "mathml_issues": []
        }
    
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Extraer todo el texto del item-body
        item_body = None
        for elem in root.iter():
            if 'item-body' in elem.tag.lower():
                item_body = elem
                break
        
        if item_body is None:
            return {
                "exists": True,
                "encoding_issues": [],
                "missing_content": ["No se encontró item-body"],
                "mathml_issues": []
            }
        
        # Extraer texto completo
        text = ET.tostring(item_body, encoding='unicode', method='text')
        
        # Verificar problemas de codificación comunes
        encoding_issues = []
        problematic_patterns = [
            ('e1', 'á'), ('f3', 'ó'), ('e9', 'é'), ('ed', 'í'), ('fa', 'ú'),
            ('f1', 'ñ'), ('bfCue1l', '¿Cuál'), ('af1o', 'año'),
            ('bfcue1ntos', '¿cuántos'), ('bfcue1les', '¿cuáles'),
            ('producif3n', 'producción'), ('tecnolf3gica', 'tecnológica'),
            ('sere1', 'será'), ('produciredan', 'producirían'),
            ('cumplif3', 'cumplió'), ('me1s', 'más'), ('d1a', 'día'),
            ('d1as', 'días'), ('Mi1rcoles', 'Miércoles'),
            ('reflexif3n', 'reflexión'), ('traslacif3n', 'traslación'),
            ('isome9tricas', 'isométricas'), ('ve9rtice', 'vértice'),
            ('Gr1fico', 'Gráfico'), ('c1cido', 'ácido'), ('c1tomo', 'átomo'),
            ('e1tomo', 'átomo'), ('oxedgeno', 'oxígeno'), ('hidrf3geno', 'hidrógeno'),
            ('azufre', 'azufre'), ('sulffarico', 'sulfúrico')
        ]
        
        for pattern, correct in problematic_patterns:
            if pattern in text:
                encoding_issues.append(f"'{pattern}' debería ser '{correct}'")
        
        # Verificar problemas de MathML
        mathml_issues = []
        math_elements = item_body.findall('.//{http://www.w3.org/1998/Math/MathML}math')
        math_elements.extend(item_body.findall('.//math'))
        
        # Verificar si hay sistemas de ecuaciones mal estructurados (pregunta 35)
        if question_num == 35:
            math_count = len(math_elements)
            if math_count > 1:
                # Verificar si están en un mtable
                mtable_found = False
                for math in math_elements:
                    if math.find('.//{http://www.w3.org/1998/Math/MathML}mtable') is not None:
                        mtable_found = True
                        break
                    if math.find('.//mtable') is not None:
                        mtable_found = True
                        break
                if not mtable_found and math_count >= 2:
                    mathml_issues.append("Sistema de ecuaciones no está en un mtable (debería estar agrupado)")
        
        # Verificar contenido faltante específico
        missing_content = []
        if question_num == 7:
            if 'paso' not in text.lower() and 'step' not in text.lower():
                missing_content.append("No se encontraron referencias a 'paso' o 'step'")
        
        if question_num == 9:
            # Verificar si hay imagen
            img_elements = item_body.findall('.//img')
            if len(img_elements) == 0:
                missing_content.append("No se encontró imagen (gráfico)")
        
        if question_num == 36:
            # Verificar pasos
            paso_count = text.lower().count('paso')
            if paso_count < 4:
                missing_content.append(f"Solo se encontraron {paso_count} referencias a 'paso' (deberían ser 4)")
        
        if question_num == 63:
            # Verificar instrucciones del juego
            if 'instrucc' not in text.lower() and 'regla' not in text.lower():
                missing_content.append("No se encontraron instrucciones o reglas del juego")
        
        return {
            "exists": True,
            "encoding_issues": encoding_issues,
            "missing_content": missing_content,
            "mathml_issues": mathml_issues
        }
        
    except Exception as e:
        return {
            "exists": True,
            "encoding_issues": [],
            "missing_content": [f"Error al procesar: {str(e)}"],
            "mathml_issues": []
        }

def main():
    """Main entry point."""
    # Obtener el directorio base del script
    script_dir = Path(__file__).parent.parent
    output_dir = script_dir / "output" / "paes-invierno-2026-new"
    
    # Preguntas a verificar según el reporte del usuario
    questions_to_check = [7, 9, 11, 15, 25, 31, 35, 36, 41, 44, 49, 52, 54, 63]
    
    print("=" * 80)
    print("VERIFICACIÓN DE PROBLEMAS EN QTI XML")
    print("=" * 80)
    print()
    
    qti_issues = []
    html_only_issues = []
    
    for q_num in questions_to_check:
        result = check_question(q_num, output_dir)
        
        if not result["exists"]:
            print(f"❌ Pregunta {q_num}: Archivo no encontrado")
            continue
        
        has_qti_issues = (
            len(result["encoding_issues"]) > 0 or
            len(result["missing_content"]) > 0 or
            len(result["mathml_issues"]) > 0
        )
        
        if has_qti_issues:
            qti_issues.append(q_num)
            print(f"⚠️  Pregunta {q_num}: PROBLEMAS EN EL QTI XML")
            if result["encoding_issues"]:
                print(f"   - Codificación: {len(result['encoding_issues'])} problemas")
                for issue in result["encoding_issues"][:3]:  # Mostrar solo los primeros 3
                    print(f"     • {issue}")
                if len(result["encoding_issues"]) > 3:
                    print(f"     ... y {len(result['encoding_issues']) - 3} más")
            if result["missing_content"]:
                print(f"   - Contenido faltante:")
                for issue in result["missing_content"]:
                    print(f"     • {issue}")
            if result["mathml_issues"]:
                print(f"   - MathML:")
                for issue in result["mathml_issues"]:
                    print(f"     • {issue}")
        else:
            html_only_issues.append(q_num)
            print(f"✅ Pregunta {q_num}: Sin problemas en QTI XML (problema solo en HTML)")
        
        print()
    
    print("=" * 80)
    print("RESUMEN")
    print("=" * 80)
    print(f"Problemas en QTI XML: {len(qti_issues)} preguntas")
    if qti_issues:
        print(f"  Preguntas: {', '.join(map(str, qti_issues))}")
    print()
    print(f"Problemas solo en HTML: {len(html_only_issues)} preguntas")
    if html_only_issues:
        print(f"  Preguntas: {', '.join(map(str, html_only_issues))}")
    print()
    
    if qti_issues:
        print("⚠️  IMPORTANTE: Las preguntas con problemas en QTI XML necesitan corrección")
        print("   en el pipeline de generación de QTI, no solo en el renderizado HTML.")
    else:
        print("✅ Todos los problemas reportados son solo de renderizado HTML.")

if __name__ == "__main__":
    main()
