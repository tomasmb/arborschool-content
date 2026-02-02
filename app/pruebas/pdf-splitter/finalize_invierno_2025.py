#!/usr/bin/env python3
"""
Script para finalizar la organización de PDFs de prueba-invierno-2025.

Copia todos los PDFs generados correctamente y los organiza en el directorio final.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


def main():
    """Punto de entrada principal."""
    base_dir = Path(__file__).parent
    project_root = base_dir.parent.parent.parent

    source_dir = project_root / "app" / "data" / "pruebas" / "procesadas" / "prueba-invierno-2025" / "pdf-splitter-output-fixed" / "questions"
    output_dir = project_root / "app" / "data" / "pruebas" / "procesadas" / "prueba-invierno-2025" / "pdf"

    # Crear directorio de salida
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Finalizando organización de PDFs de prueba-invierno-2025")
    print("=" * 60)
    print()

    # Verificar que el directorio source existe
    if not source_dir.exists():
        print(f"❌ Directorio source no encontrado: {source_dir}")
        sys.exit(1)

    # Copiar todos los PDFs y renombrarlos de question_XXX.pdf a QXXX.pdf
    print("📋 Copiando y renombrando PDFs...")
    copied = 0

    for source_file in sorted(source_dir.glob("question_*.pdf")):
        # Extraer número de pregunta
        q_num = source_file.stem.replace("question_", "")
        try:
            q_num_int = int(q_num)
            dest_file = output_dir / f"Q{q_num_int}.pdf"
            shutil.copy2(source_file, dest_file)
            copied += 1
            if copied % 10 == 0:
                print(f"   ✅ Copiadas {copied} preguntas...")
        except ValueError:
            print(f"   ⚠️  No se pudo extraer número de: {source_file.name}")

    print(f"   ✅ Total copiadas: {copied}")
    print()

    # Verificar cuántas preguntas tenemos
    pdf_files = sorted(output_dir.glob("Q*.pdf"))
    print("📊 Resumen:")
    print(f"   Total PDFs en destino: {len(pdf_files)}")
    if pdf_files:
        first_num = int(pdf_files[0].stem[1:])
        last_num = int(pdf_files[-1].stem[1:])
        print(f"   Rango: Q{first_num} - Q{last_num}")

    print()
    print(f"📁 PDFs organizados en: {output_dir}")
    print()
    print("✅ Proceso completado!")


if __name__ == "__main__":
    main()
