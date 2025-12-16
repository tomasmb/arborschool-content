#!/usr/bin/env python3
"""
Script para corregir problemas de codificación en QTI XML generados.
Corrige automáticamente los errores comunes de codificación de caracteres.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
import re
import sys

# Importar ENCODING_FIXES desde el módulo principal para mantener consistencia
try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from modules.qti_transformer import ENCODING_FIXES
except ImportError:
    # Fallback si no se puede importar
    print("⚠️  No se pudo importar ENCODING_FIXES, usando diccionario local")
    ENCODING_FIXES = {
        'e1cido': 'ácido',
        'e1tomos': 'átomos',
        'af1o': 'año',
        'bfCue1l': '¿Cuál',
    }

def fix_encoding_in_xml(xml_content: str) -> str:
    """Corrige problemas de codificación en el XML."""
    fixed_content = xml_content
    
    # Aplicar correcciones en orden (más específicas primero)
    for wrong, correct in sorted(ENCODING_FIXES.items(), key=lambda x: -len(x[0])):
        fixed_content = fixed_content.replace(wrong, correct)
        # También buscar en mayúsculas/minúsculas
        fixed_content = fixed_content.replace(wrong.capitalize(), correct.capitalize())
        fixed_content = fixed_content.replace(wrong.upper(), correct.upper())
    
    return fixed_content

def fix_xml_file(xml_path: Path) -> bool:
    """Corrige un archivo XML y lo guarda."""
    try:
        # Leer XML
        with open(xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        # Verificar si tiene problemas
        has_issues = any(wrong in xml_content for wrong in ENCODING_FIXES.keys())
        if not has_issues:
            return False  # No necesita corrección
        
        # Corregir
        fixed_content = fix_encoding_in_xml(xml_content)
        
        # Validar que el XML sigue siendo válido
        try:
            ET.fromstring(fixed_content)
        except ET.ParseError as e:
            print(f"  ⚠️  Error al validar XML corregido: {e}")
            return False
        
        # Guardar
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        return True
    except Exception as e:
        print(f"  ❌ Error procesando {xml_path}: {e}")
        return False

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Corregir problemas de codificación en QTI XML"
    )
    parser.add_argument(
        "--question",
        type=int,
        help="Número de pregunta específica a corregir"
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directorio con los QTI generados"
    )
    
    args = parser.parse_args()
    
    # Obtener directorio base del script
    script_dir = Path(__file__).parent.parent
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = script_dir / "output" / "paes-invierno-2026-new"
    if not output_dir.exists():
        print(f"❌ No se encontró el directorio: {output_dir}")
        sys.exit(1)
    
    if args.question:
        questions = [args.question]
    else:
        # Corregir todas las preguntas con problemas conocidos
        # Basado en el último escaneo: 7, 47, 49, 54, 57
        questions = [7, 47, 49, 54, 57]
    
    print(f"🔧 Corrigiendo problemas de codificación...")
    print()
    
    fixed_count = 0
    for q_num in questions:
        q_str = f"{q_num:03d}"
        xml_path = output_dir / f"question_{q_str}" / "question.xml"
        
        if not xml_path.exists():
            print(f"⚠️  Pregunta {q_num}: XML no encontrado")
            continue
        
        print(f"📄 Pregunta {q_num}...", end=" ")
        if fix_xml_file(xml_path):
            print("✅ Corregida")
            fixed_count += 1
        else:
            print("ℹ️  Sin problemas o no se pudo corregir")
    
    print()
    print("=" * 60)
    print(f"📊 Resumen: {fixed_count} archivo(s) corregido(s)")

if __name__ == "__main__":
    main()
