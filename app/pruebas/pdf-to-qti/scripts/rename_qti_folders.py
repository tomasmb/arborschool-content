#!/usr/bin/env python3
"""
Script para renombrar carpetas QTI según su posición en el archivo de selección.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

def main():
    """Renombrar carpetas QTI según posición en archivo."""
    # Cargar resultados de segmentación
    seg_file = Path(__file__).parent.parent.parent / "pdf-to-qti" / "splitter_output_regular_2026" / "part_1" / "segmentation_results.json"
    qti_dir = Path(__file__).parent.parent.parent.parent / "data" / "pruebas" / "procesadas" / "seleccion-regular-2026" / "qti"
    
    if not seg_file.exists():
        print(f"❌ Archivo de segmentación no encontrado: {seg_file}")
        sys.exit(1)
    
    with open(seg_file, 'r', encoding='utf-8') as f:
        seg_data = json.load(f)
    
    # Crear mapeo: número de pregunta -> posición en archivo (1-indexed)
    questions_list = seg_data.get('questions', [])
    qnum_to_position = {}
    for idx, q in enumerate(questions_list):
        q_id = q.get('id', '')
        if q_id.startswith('Q'):
            try:
                q_num = int(q_id[1:])
                qnum_to_position[q_num] = idx + 1  # Posición 1-indexed
            except:
                pass
    
    if not qti_dir.exists():
        print(f"❌ Directorio QTI no encontrado: {qti_dir}")
        sys.exit(1)
    
    # Encontrar carpetas a renombrar
    renames = []
    for item in os.listdir(qti_dir):
        item_path = qti_dir / item
        if item_path.is_dir() and item.startswith('Q'):
            try:
                # Extraer número actual
                if item.startswith('Q0'):
                    # Ya está en formato Q01, Q02, etc.
                    current_num = int(item[1:])
                    # Buscar qué pregunta es esta
                    for q_num, pos in qnum_to_position.items():
                        if pos == current_num:
                            # Ya está correcto
                            break
                    else:
                        # No encontrada, mantener
                        pass
                else:
                    # Formato Q1, Q2, Q11, etc.
                    current_num = int(item[1:])
                    if current_num in qnum_to_position:
                        pos = qnum_to_position[current_num]
                        new_name = f'Q{pos:02d}'
                        if item != new_name:
                            renames.append((item, new_name, current_num, pos))
            except ValueError:
                # No es un número válido, ignorar
                pass
    
    if not renames:
        print("✅ Todas las carpetas ya están correctamente nombradas")
        return
    
    print(f"🔄 Renombrando {len(renames)} carpetas...")
    print()
    
    # Renombrar en orden inverso para evitar conflictos
    renames.sort(key=lambda x: x[3], reverse=True)  # Ordenar por posición descendente
    
    for old_name, new_name, q_num, pos in renames:
        old_path = qti_dir / old_name
        new_path = qti_dir / new_name
        
        if new_path.exists():
            print(f"⚠️  {old_name} -> {new_name}: Ya existe, saltando")
            continue
        
        try:
            old_path.rename(new_path)
            print(f"✅ {old_name} -> {new_name} (pregunta {q_num}, posición {pos})")
        except Exception as e:
            print(f"❌ Error renombrando {old_name}: {e}")
    
    print()
    print(f"✅ Renombrado completado: {len(renames)} carpetas")


if __name__ == "__main__":
    main()
