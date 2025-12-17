#!/usr/bin/env python3
"""Script para corregir preguntas problemáticas en segmented.json"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SEGMENTED_JSON = Path(__file__).parent.parent / "data" / "pruebas" / "procesadas" / "prueba-invierno-2026" / "segmented.json"


def load_segmented() -> dict:
    """Cargar segmented.json"""
    with open(SEGMENTED_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_segmented(data: dict) -> None:
    """Guardar segmented.json"""
    # Hacer backup
    backup = SEGMENTED_JSON.with_suffix('.json.backup')
    if not backup.exists():
        with open(SEGMENTED_JSON, 'r', encoding='utf-8') as f:
            backup.write_text(f.read(), encoding='utf-8')
        print(f"✅ Backup creado: {backup}")
    
    # Guardar nuevo
    with open(SEGMENTED_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Guardado: {SEGMENTED_JSON}")


def corregir_q3(data: dict, contenido_corregido: str) -> None:
    """Corregir Q3"""
    unvalidated = data.get('unvalidated_questions', [])
    for i, q in enumerate(unvalidated):
        if q['id'] == 'Q3':
            q['content'] = contenido_corregido
            # Mover a validated
            data.setdefault('validated_questions', []).append(q)
            unvalidated.pop(i)
            print("✅ Q3 corregida y movida a validated")
            return
    print("❌ Q3 no encontrada")


def corregir_q7(data: dict, contenido_corregido: str) -> None:
    """Corregir Q7"""
    unvalidated = data.get('unvalidated_questions', [])
    for i, q in enumerate(unvalidated):
        if q['id'] == 'Q7':
            q['content'] = contenido_corregido
            # Mover a validated
            data.setdefault('validated_questions', []).append(q)
            unvalidated.pop(i)
            print("✅ Q7 corregida y movida a validated")
            return
    print("❌ Q7 no encontrada")


def corregir_q32(data: dict, contenido_corregido: str) -> None:
    """Corregir Q32"""
    unvalidated = data.get('unvalidated_questions', [])
    for i, q in enumerate(unvalidated):
        if q['id'] == 'Q32':
            q['content'] = contenido_corregido
            # Mover a validated
            data.setdefault('validated_questions', []).append(q)
            unvalidated.pop(i)
            print("✅ Q32 corregida y movida a validated")
            return
    print("❌ Q32 no encontrada")


def limpiar_errores(data: dict) -> None:
    """Limpiar errores relacionados con preguntas corregidas"""
    errors = data.get('errors', [])
    # Remover errores de Q3, Q7, Q32
    data['errors'] = [e for e in errors if not any(q in e for q in ['Q3', 'Q7', 'Q32'])]
    print(f"✅ Errores limpiados: {len(errors) - len(data['errors'])} errores removidos")


def main():
    """Main function"""
    if len(sys.argv) < 3:
        print("Uso: python corregir_preguntas.py <Q3|Q7|Q32> <archivo_con_contenido.txt>")
        print("\nEjemplo:")
        print("  python corregir_preguntas.py Q7 contenido_q7.txt")
        sys.exit(1)
    
    pregunta_id = sys.argv[1].upper()
    archivo_contenido = Path(sys.argv[2])
    
    if pregunta_id not in ['Q3', 'Q7', 'Q32']:
        print(f"❌ Pregunta inválida: {pregunta_id}. Debe ser Q3, Q7 o Q32")
        sys.exit(1)
    
    if not archivo_contenido.exists():
        print(f"❌ Archivo no encontrado: {archivo_contenido}")
        sys.exit(1)
    
    # Leer contenido corregido
    contenido_corregido = archivo_contenido.read_text(encoding='utf-8').strip()
    
    # Cargar y modificar
    data = load_segmented()
    
    if pregunta_id == 'Q3':
        corregir_q3(data, contenido_corregido)
    elif pregunta_id == 'Q7':
        corregir_q7(data, contenido_corregido)
    elif pregunta_id == 'Q32':
        corregir_q32(data, contenido_corregido)
    
    # Limpiar errores
    limpiar_errores(data)
    
    # Guardar
    save_segmented(data)
    
    # Mostrar resumen
    validated = len(data.get('validated_questions', []))
    unvalidated = len(data.get('unvalidated_questions', []))
    print(f"\n📊 Resumen:")
    print(f"   Validadas: {validated}")
    print(f"   Sin validar: {unvalidated}")


if __name__ == '__main__':
    main()
