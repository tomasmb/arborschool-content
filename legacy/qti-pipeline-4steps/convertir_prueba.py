#!/usr/bin/env python3
"""Helper script para convertir una prueba PAES M1 a QTI.

Facilita el proceso de conversión con comandos simplificados.
"""

from __future__ import annotations

import sys
import subprocess
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent.parent
PRUEBAS_RAW = REPO_ROOT / "app" / "data" / "pruebas" / "raw"
PRUEBAS_PROCESADAS = REPO_ROOT / "app" / "data" / "pruebas" / "procesadas"


def convertir_prueba(
    nombre_prueba: str,
    paso: str = "all",
    skip_validation: bool = False
) -> None:
    """
    Convierte una prueba de PDF a QTI.
    
    Args:
        nombre_prueba: Nombre de la prueba (ej: "prueba-001")
        paso: Paso a ejecutar (parse, segment, generate, validate, all)
        skip_validation: Si True, omite validación XSD/semántica
    """
    pdf_path = PRUEBAS_RAW / f"{nombre_prueba}.pdf"
    output_dir = PRUEBAS_PROCESADAS / nombre_prueba
    
    if not pdf_path.exists():
        print(f"❌ Error: No se encontró {pdf_path}")
        print(f"   Coloca el PDF en: {PRUEBAS_RAW}")
        sys.exit(1)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Determinar input según el paso
    if paso == "parse":
        input_file = str(pdf_path)
    elif paso == "segment":
        input_file = str(output_dir / "parsed.json")
        if not Path(input_file).exists():
            print(f"❌ Error: {input_file} no existe")
            print("   Ejecuta primero: --paso parse")
            sys.exit(1)
    elif paso == "generate":
        input_file = str(output_dir / "segmented.json")
        if not Path(input_file).exists():
            print(f"❌ Error: {input_file} no existe")
            print("   Ejecuta primero: --paso segment")
            sys.exit(1)
    elif paso == "validate":
        input_file = str(output_dir / "qti")
        if not Path(input_file).exists():
            print(f"❌ Error: {input_file} no existe")
            print("   Ejecuta primero: --paso generate")
            sys.exit(1)
    else:  # all
        input_file = str(pdf_path)
    
    # Construir comando
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "run.py"),
        input_file,
        "--output", str(output_dir),
        "--step", paso
    ]
    
    if skip_validation:
        cmd.append("--skip-validation")
    
    print("=" * 60)
    print(f"🔄 Convirtiendo: {nombre_prueba}")
    print(f"   Paso: {paso}")
    print(f"   Input: {input_file}")
    print(f"   Output: {output_dir}")
    print("=" * 60)
    print()
    
    # Ejecutar
    try:
        subprocess.run(cmd, check=True, cwd=str(SCRIPT_DIR))
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error durante la conversión: {e}")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Uso: python convertir_prueba.py <nombre_prueba> [--paso <paso>] [--skip-validation]")
        print()
        print("Ejemplos:")
        print("  python convertir_prueba.py prueba-001")
        print("  python convertir_prueba.py prueba-001 --paso parse")
        print("  python convertir_prueba.py prueba-001 --paso segment")
        print()
        print("Pasos: parse, segment, generate, validate, all (default: all)")
        sys.exit(1)
    
    nombre_prueba = sys.argv[1]
    paso = "all"
    skip_validation = False
    
    # Parsear argumentos
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--paso" and i + 1 < len(sys.argv):
            paso = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--skip-validation":
            skip_validation = True
            i += 1
        else:
            print(f"⚠️  Argumento desconocido: {sys.argv[i]}")
            i += 1
    
    convertir_prueba(nombre_prueba, paso, skip_validation)


if __name__ == "__main__":
    main()
