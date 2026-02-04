#!/usr/bin/env python3
"""
Script para taggear la habilidad principal PAES a cada pregunta.

Las 4 habilidades PAES M1 son:
- RES: Resolver problemas (aplicar procedimientos, calcular)
- MOD: Modelar (plantear ecuación/expresión desde contexto)
- REP: Representar (interpretar/crear gráficos, tablas, diagramas)
- ARG: Argumentar (justificar, validar, detectar errores)

Usa Gemini con fallback a OpenAI.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.llm_clients import load_default_gemini_service

HABILIDADES_PROMPT = """Eres un experto en evaluación educativa PAES Chile.

Analiza la siguiente pregunta de matemáticas y determina cuál es la HABILIDAD PRINCIPAL que evalúa.

Las 4 habilidades PAES M1 son:

1. **RES (Resolver problemas)**: Aplicar procedimientos, calcular, resolver ecuaciones,
   operar numéricamente. El foco está en EJECUTAR operaciones o procedimientos conocidos.

2. **MOD (Modelar)**: Plantear una ecuación, expresión o modelo matemático a partir de
   un contexto. El foco está en TRADUCIR una situación real a lenguaje matemático.

3. **REP (Representar)**: Interpretar o construir gráficos, tablas, diagramas.
   El foco está en LEER o CREAR representaciones visuales de información.

4. **ARG (Argumentar)**: Justificar procedimientos, validar afirmaciones, detectar
   errores, elegir la opción correcta con fundamento. El foco está en EVALUAR la
   validez de algo.

## Pregunta a analizar:

{question_text}

## Opciones:
{choices}

## Análisis existente:
{general_analysis}

## Dificultad: {difficulty}

## Átomos identificados:
{atoms}

---

Responde SOLO con un JSON válido con la siguiente estructura:
{{
    "habilidad_principal": "RES" | "MOD" | "REP" | "ARG",
    "justificacion": "Explicación breve de por qué esta es la habilidad principal (max 50 palabras)"
}}

IMPORTANTE:
- Elige UNA SOLA habilidad principal
- Si hay duda entre dos, elige la que mejor describe lo que el estudiante DEBE HACER para resolver la pregunta
- No incluyas texto adicional fuera del JSON
"""


def load_metadata(metadata_path: str) -> Optional[Dict[str, Any]]:
    """Load existing metadata from file."""
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  ⚠️ Error loading {metadata_path}: {e}")
        return None


def save_metadata(metadata: Dict[str, Any], metadata_path: str) -> bool:
    """Save metadata back to file."""
    try:
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"  ❌ Error saving {metadata_path}: {e}")
        return False


def extract_question_info(metadata: Dict[str, Any]) -> Dict[str, str]:
    """Extract relevant question info from metadata for the prompt."""
    # Get atoms info
    atoms_info = []
    for atom in metadata.get("selected_atoms", []):
        atoms_info.append(f"- {atom.get('atom_id', 'N/A')}: {atom.get('atom_title', 'N/A')} ({atom.get('relevance', 'N/A')})")

    # Get difficulty
    difficulty = metadata.get("difficulty", {})
    difficulty_str = f"{difficulty.get('level', 'Unknown')} (score: {difficulty.get('score', 'N/A')})"

    return {
        "general_analysis": metadata.get("general_analysis", "No disponible"),
        "difficulty": difficulty_str,
        "atoms": "\n".join(atoms_info) if atoms_info else "No disponible",
    }


def load_question_text(qti_path: str) -> tuple[str, str]:
    """Load question text and choices from QTI XML file."""
    import xml.etree.ElementTree as ET

    try:
        tree = ET.parse(qti_path)
        root = tree.getroot()

        # Extract question text (simplified)
        question_parts = []
        for elem in root.iter():
            if elem.text and elem.text.strip():
                question_parts.append(elem.text.strip())

        question_text = " ".join(question_parts[:10])  # First parts usually contain question

        # Extract choices
        choices = []
        for choice in root.iter():
            if "simpleChoice" in choice.tag or "Choice" in choice.tag:
                choice_text = ET.tostring(choice, encoding="unicode", method="text").strip()
                if choice_text:
                    choices.append(choice_text)

        choices_str = "\n".join([f"- {c}" for c in choices[:5]]) if choices else "No disponibles"

        return question_text[:2000], choices_str  # Limit length

    except Exception as e:
        return f"Error loading question: {e}", "No disponibles"


def tag_habilidad(service, question_text: str, choices: str, metadata: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """Use LLM to tag the main skill."""
    info = extract_question_info(metadata)

    prompt = HABILIDADES_PROMPT.format(
        question_text=question_text, choices=choices, general_analysis=info["general_analysis"], difficulty=info["difficulty"], atoms=info["atoms"]
    )

    try:
        response = service.generate_text(prompt, response_mime_type="application/json", temperature=0.0)

        # Parse response
        result = json.loads(response)

        # Validate
        if result.get("habilidad_principal") not in ["RES", "MOD", "REP", "ARG"]:
            print(f"    ⚠️ Invalid habilidad: {result.get('habilidad_principal')}")
            return None

        return result

    except json.JSONDecodeError as e:
        print(f"    ❌ JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"    ❌ LLM error: {e}")
        return None


def process_all_questions(dry_run: bool = False):
    """Process all questions and add habilidad_principal field."""
    base_path = Path("app/data/pruebas/finalizadas")

    # Find all metadata files
    metadata_files = list(base_path.rglob("metadata_tags.json"))
    print(f"\n📊 Found {len(metadata_files)} metadata files\n")

    # Initialize service
    service = load_default_gemini_service()

    # Statistics - use separate typed variables to avoid union type issues
    processed = 0
    errors = 0
    already_tagged = 0
    by_habilidad: dict[str, int] = {"RES": 0, "MOD": 0, "REP": 0, "ARG": 0}

    for i, metadata_path in enumerate(metadata_files, 1):
        # Get question directory
        q_dir = metadata_path.parent
        qti_path = q_dir / "question.xml"

        print(f"[{i}/{len(metadata_files)}] Processing {q_dir.parent.name}/{q_dir.name}...", end=" ")

        # Load metadata
        metadata = load_metadata(str(metadata_path))
        if not metadata:
            errors += 1
            print("❌ Failed to load metadata")
            continue

        # Check if already tagged
        if "habilidad_principal" in metadata:
            already_tagged += 1
            hab = metadata["habilidad_principal"].get("habilidad", "?")
            by_habilidad[hab] = by_habilidad.get(hab, 0) + 1
            print(f"⏭️ Already tagged: {hab}")
            continue

        # Load question text
        if qti_path.exists():
            question_text, choices = load_question_text(str(qti_path))
        else:
            question_text = metadata.get("general_analysis", "")
            choices = "No disponibles"

        # Tag habilidad
        result = tag_habilidad(service, question_text, choices, metadata)

        if result:
            metadata["habilidad_principal"] = result

            if not dry_run:
                if save_metadata(metadata, str(metadata_path)):
                    processed += 1
                    hab = result["habilidad_principal"]
                    by_habilidad[hab] = by_habilidad.get(hab, 0) + 1
                    print(f"✅ {hab}")
                else:
                    errors += 1
                    print("❌ Save failed")
            else:
                processed += 1
                print(f"🔍 Would tag: {result['habilidad_principal']}")
        else:
            errors += 1
            print("❌ Tagging failed")

    # Print summary
    print("\n" + "=" * 50)
    print("📊 RESUMEN DE TAGGEO DE HABILIDADES")
    print("=" * 50)
    print(f"  Total archivos:     {len(metadata_files)}")
    print(f"  Procesados:         {processed}")
    print(f"  Ya taggeados:       {already_tagged}")
    print(f"  Errores:            {errors}")
    print("\n  Por habilidad:")
    for hab, count in sorted(by_habilidad.items()):
        pct = (count / max(1, processed + already_tagged)) * 100
        print(f"    {hab}: {count} ({pct:.1f}%)")
    print("=" * 50)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Tag PAES skills to questions")
    parser.add_argument("--dry-run", action="store_true", help="Don't save changes")
    args = parser.parse_args()

    process_all_questions(dry_run=args.dry_run)
