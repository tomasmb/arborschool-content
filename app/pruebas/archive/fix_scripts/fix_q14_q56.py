#!/usr/bin/env python3
"""
Script para corregir Q14 y Q56 extrayendo solo la página correcta (tercera página).
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("❌ PyMuPDF (fitz) no está instalado. Instala con: pip install pymupdf")
    sys.exit(1)


def extract_page_from_pdf(input_pdf_path: str, page_num: int, output_pdf_path: str) -> bool:
    """Extrae una página específica de un PDF y la guarda como nuevo PDF."""
    try:
        doc = fitz.open(input_pdf_path)
        if page_num < 1 or page_num > doc.page_count:
            print(f"   ❌ Página {page_num} no existe en el PDF (tiene {doc.page_count} páginas)")
            doc.close()
            return False

        # Crear nuevo documento con solo esa página
        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=page_num - 1, to_page=page_num - 1)
        new_doc.save(output_pdf_path)
        new_doc.close()
        doc.close()
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        if 'doc' in locals():
            doc.close()
        return False


def main():
    """Punto de entrada principal."""
    base_dir = Path(__file__).parent
    project_root = base_dir.parent.parent.parent

    pdf_dir = project_root / "app" / "data" / "pruebas" / "procesadas" / "Prueba-invierno-2025" / "pdf"

    print("=" * 60)
    print("Corrigiendo Q14 y Q56 - Extrayendo solo la página correcta")
    print("=" * 60)
    print()

    # Corregir Q14 (tercera página = página 3)
    q14_path = pdf_dir / "Q14.pdf"
    if q14_path.exists():
        print("📄 Corrigiendo Q14...")
        print(f"   Archivo original: {q14_path}")

        # Crear backup
        backup_path = pdf_dir / "Q14.pdf.backup"
        import shutil
        shutil.copy2(q14_path, backup_path)
        print(f"   ✅ Backup creado: {backup_path}")

        # Extraer página 3
        if extract_page_from_pdf(str(q14_path), 3, str(q14_path)):
            print("   ✅ Q14 corregida (extraída página 3)")
        else:
            print("   ❌ Error corrigiendo Q14")
            # Restaurar backup
            shutil.move(backup_path, q14_path)
    else:
        print("   ⚠️  Q14.pdf no encontrado")

    print()

    # Corregir Q56 (tercera página = página 3)
    q56_path = pdf_dir / "Q56.pdf"
    if q56_path.exists():
        print("📄 Corrigiendo Q56...")
        print(f"   Archivo original: {q56_path}")

        # Crear backup
        backup_path = pdf_dir / "Q56.pdf.backup"
        import shutil
        shutil.copy2(q56_path, backup_path)
        print(f"   ✅ Backup creado: {backup_path}")

        # Extraer página 3
        if extract_page_from_pdf(str(q56_path), 3, str(q56_path)):
            print("   ✅ Q56 corregida (extraída página 3)")
        else:
            print("   ❌ Error corrigiendo Q56")
            # Restaurar backup
            shutil.move(backup_path, q56_path)
    else:
        print("   ⚠️  Q56.pdf no encontrado")

    print()
    print("✅ Corrección completada")


if __name__ == "__main__":
    main()
