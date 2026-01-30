#!/usr/bin/env python3
"""Script to mark uncovered atoms as out of M1 scope.

This script adds the 'en_alcance_m1' field to all atoms in the JSON file,
setting it to False for the 31 atoms identified as having no question coverage.
"""

import json
from pathlib import Path

# 31 atoms without coverage (from docs/analisis_cobertura_atomos.md)
ATOMS_FUERA_DE_ALCANCE = {
    # Álgebra y Funciones (11)
    "A-M1-ALG-01-11",  # Desarrollo de cubo de binomio
    "A-M1-ALG-02-07",  # Concepto de Proporcionalidad Inversa
    "A-M1-ALG-02-08",  # Constante de Proporcionalidad Inversa
    "A-M1-ALG-02-09",  # Representación Tabular de Proporcionalidad Inversa
    "A-M1-ALG-02-10",  # Representación Gráfica de Proporcionalidad Inversa
    "A-M1-ALG-02-11",  # Modelado Algebraico de Proporcionalidad Inversa
    "A-M1-ALG-02-12",  # Resolución de Problemas de Proporción Inversa
    "A-M1-ALG-02-13",  # Distinción entre Proporcionalidad Directa e Inversa
    "A-M1-ALG-04-03",  # Clasificación de Sistemas por Cantidad de Soluciones
    "A-M1-ALG-05-03",  # Distinción entre Función Lineal y Afín
    "A-M1-ALG-05-09",  # Graficación mediante Tabla de Valores
    # Números (8)
    "A-M1-NUM-01-14",  # Conversión de decimal periódico a fracción
    "A-M1-NUM-03-07",  # División de potencias de igual exponente
    "A-M1-NUM-03-08",  # Conversión de potencia de exponente racional a raíz
    "A-M1-NUM-03-09",  # Conversión de raíz enésima a potencia de exponente racional
    "A-M1-NUM-03-10",  # Existencia de raíces enésimas en los números reales
    "A-M1-NUM-03-12",  # División de raíces de igual índice
    "A-M1-NUM-03-13",  # Propiedad de raíz de una raíz
    "A-M1-NUM-03-16",  # Racionalización de denominadores con raíz enésima no cuadrada
    # Probabilidad y Estadística (11)
    "A-M1-PROB-01-06",  # Construcción de gráficos de barras
    "A-M1-PROB-01-12",  # Cálculo de ángulos para construcción de gráficos circulares
    "A-M1-PROB-01-13",  # Selección del gráfico adecuado
    "A-M1-PROB-02-10",  # Selección y justificación de la medida adecuada
    "A-M1-PROB-03-02",  # Concepto de Percentiles
    "A-M1-PROB-03-04",  # Cálculo de Percentiles en datos no agrupados
    "A-M1-PROB-03-06",  # Interpretación de Percentiles en contexto
    "A-M1-PROB-03-09",  # Comparación de distribuciones mediante Diagramas de Cajón
    "A-M1-PROB-04-06",  # Aplicación de la regla aditiva para eventos no mutuamente excluyentes
    "A-M1-PROB-04-08",  # Aplicación de la regla multiplicativa para eventos independientes
    "A-M1-PROB-04-11",  # Cálculo de probabilidad condicional por fórmula algebraica
}


def main():
    """Mark uncovered atoms as out of scope."""
    # Path relative to project root
    project_root = Path(__file__).parent.parent.parent.parent
    atoms_path = project_root / "app" / "data" / "atoms" / "paes_m1_2026_atoms.json"

    print(f"Loading atoms from: {atoms_path}")
    with open(atoms_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    marked_count = 0
    in_scope_count = 0

    for atom in data["atoms"]:
        atom_id = atom["id"]
        if atom_id in ATOMS_FUERA_DE_ALCANCE:
            atom["en_alcance_m1"] = False
            marked_count += 1
            print(f"  ❌ {atom_id}: {atom['titulo'][:50]}...")
        else:
            atom["en_alcance_m1"] = True
            in_scope_count += 1

    # Update metadata version
    data["metadata"]["version"] = "2025-12-29"

    print("\nSummary:")
    print(f"  - Total atoms: {len(data['atoms'])}")
    print(f"  - In scope (en_alcance_m1=True): {in_scope_count}")
    print(f"  - Out of scope (en_alcance_m1=False): {marked_count}")

    if marked_count != len(ATOMS_FUERA_DE_ALCANCE):
        print(f"\n⚠️  WARNING: Expected {len(ATOMS_FUERA_DE_ALCANCE)} atoms to mark, but found {marked_count}")
        missing = ATOMS_FUERA_DE_ALCANCE - {a["id"] for a in data["atoms"]}
        if missing:
            print(f"  Missing atom IDs: {missing}")

    # Write back
    with open(atoms_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Updated {atoms_path}")


if __name__ == "__main__":
    main()
