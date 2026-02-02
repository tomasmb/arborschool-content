"""Script para extraer el mapeo pregunta→átomo de los metadata_tags.json.

Genera un JSON con el mapeo de cada pregunta del MST a los átomos que evalúa.

Usage:
    python -m app.diagnostico.scripts.extract_question_atoms
"""

import json
from pathlib import Path

# Las 32 preguntas del MST
MST_QUESTIONS = {
    "R1": [
        ("seleccion-regular-2025", "Q32"),
        ("seleccion-regular-2026", "Q33"),
        ("prueba-invierno-2026", "Q7"),
        ("prueba-invierno-2026", "Q23"),
        ("seleccion-regular-2026", "Q41"),
        ("prueba-invierno-2026", "Q48"),
        ("seleccion-regular-2026", "Q62"),
        ("seleccion-regular-2026", "Q61"),
    ],
    "A2": [
        ("prueba-invierno-2026", "Q37"),
        ("seleccion-regular-2026", "Q40"),
        ("seleccion-regular-2026", "Q30"),
        ("prueba-invierno-2026", "Q19"),
        ("prueba-invierno-2026", "Q18"),
        ("prueba-invierno-2026", "Q22"),
        ("prueba-invierno-2026", "Q53"),
        ("seleccion-regular-2026", "Q54"),
    ],
    "B2": [
        ("prueba-invierno-2025", "Q11"),
        ("prueba-invierno-2026", "Q6"),
        ("seleccion-regular-2026", "Q47"),
        ("prueba-invierno-2025", "Q18"),
        ("seleccion-regular-2026", "Q5"),
        ("seleccion-regular-2026", "Q45"),
        ("prueba-invierno-2026", "Q54"),
        ("prueba-invierno-2026", "Q57"),
    ],
    "C2": [
        ("seleccion-regular-2026", "Q27"),
        ("seleccion-regular-2026", "Q48"),
        ("prueba-invierno-2026", "Q36"),
        ("seleccion-regular-2025", "Q23"),
        ("prueba-invierno-2025", "Q56"),
        ("seleccion-regular-2025", "Q65"),
        ("prueba-invierno-2025", "Q61"),
        ("seleccion-regular-2026", "Q53"),
    ],
}


def extract_question_atoms():
    """Extrae los átomos asociados a cada pregunta del MST."""
    base_path = Path("app/data/pruebas/finalizadas")

    question_atoms = {}
    missing = []

    for module, questions in MST_QUESTIONS.items():
        for exam, qid in questions:
            key = f"{exam}/{qid}"
            metadata_path = base_path / exam / "qti" / qid / "metadata_tags.json"

            if not metadata_path.exists():
                print(f"⚠️  No encontrado: {metadata_path}")
                missing.append(key)
                continue

            with metadata_path.open() as f:
                metadata = json.load(f)

            atoms = []
            for atom in metadata.get("selected_atoms", []):
                atoms.append({
                    "atom_id": atom["atom_id"],
                    "relevance": atom.get("relevance", "primary"),
                })

            question_atoms[key] = {
                "module": module,
                "exam": exam,
                "question_id": qid,
                "atoms": atoms,
                "habilidad": metadata.get("habilidad_principal", {}).get("habilidad_principal"),
                "difficulty": metadata.get("difficulty", {}).get("level"),
            }

    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN DE MAPEO PREGUNTA → ÁTOMO")
    print("=" * 60)
    print(f"Total preguntas: {len(question_atoms)}")
    print(f"Preguntas faltantes: {len(missing)}")

    total_atoms = sum(len(q["atoms"]) for q in question_atoms.values())
    print(f"Total asociaciones pregunta-átomo: {total_atoms}")

    unique_atoms = set()
    for q in question_atoms.values():
        for a in q["atoms"]:
            unique_atoms.add(a["atom_id"])
    print(f"Átomos únicos cubiertos: {len(unique_atoms)}")

    # Por módulo
    print("\nPor módulo:")
    for module in ["R1", "A2", "B2", "C2"]:
        module_questions = [q for q in question_atoms.values() if q["module"] == module]
        module_atoms = set()
        for q in module_questions:
            for a in q["atoms"]:
                module_atoms.add(a["atom_id"])
        print(f"  {module}: {len(module_questions)} preguntas, {len(module_atoms)} átomos únicos")

    print("=" * 60)

    # Guardar
    output = {
        "metadata": {
            "total_questions": len(question_atoms),
            "total_atom_associations": total_atoms,
            "unique_atoms_covered": len(unique_atoms),
            "missing_questions": missing,
        },
        "question_atoms": question_atoms,
        "atom_to_questions": {},  # Reverse mapping
    }

    # Crear reverse mapping (átomo → preguntas)
    for key, q in question_atoms.items():
        for a in q["atoms"]:
            atom_id = a["atom_id"]
            if atom_id not in output["atom_to_questions"]:
                output["atom_to_questions"][atom_id] = []
            output["atom_to_questions"][atom_id].append({
                "question_key": key,
                "module": q["module"],
                "relevance": a["relevance"],
            })

    output_path = Path("app/diagnostico/config/question_atoms.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Guardado en: {output_path}")

    return output


if __name__ == "__main__":
    extract_question_atoms()
