"""Prompt for Phase 0: demand analysis.

Analyzes existing M1 atoms to identify missing prerequisite knowledge,
going as far back as 1° básico if needed.
"""

from __future__ import annotations

import json
from typing import Any

from app.prerequisites.constants import GRADE_LEVEL_LABELS


def build_demand_analysis_prompt(
    leaf_atoms: list[dict[str, Any]],
) -> str:
    """Build prompt that identifies prerequisite topics needed by M1 atoms.

    Args:
        leaf_atoms: M1 atoms that have no or few prerequisites — the
            "frontier" where students struggle.

    Returns:
        Complete prompt string for GPT-5.1.
    """
    atoms_json = json.dumps(leaf_atoms, ensure_ascii=False, indent=2)
    grade_labels = "\n".join(
        f"  - {k}: {v}" for k, v in GRADE_LEVEL_LABELS.items()
    )

    return f"""<role>
Eres un experto en diseño curricular de matemáticas del sistema educativo
chileno (Bases Curriculares, MINEDUC). Tu tarea es analizar átomos de
aprendizaje de nivel PAES M1 e identificar los conocimientos previos
fundamentales que un estudiante necesitaría dominar antes de abordarlos.
</role>

<context>
## Átomos M1 a analizar (átomos "frontera" — los más básicos del grafo M1)

{atoms_json}

## Niveles educativos disponibles

{grade_labels}

## Ejes temáticos válidos

- numeros
- algebra_y_funciones
- geometria
- probabilidad_y_estadistica
</context>

<task>
Para cada átomo M1 proporcionado, identifica los conocimientos previos
fundamentales que un estudiante necesitaría dominar ANTES de poder
abordar ese átomo. Sigue estas reglas:

1. Rastrea hacia atrás hasta el nivel más básico necesario (incluso 1°
   básico si aplica, por ejemplo: contar, sumar, restar).
2. Sé exhaustivo pero no redundante: si un prerequisito ya cubre otro
   transitivamente, no lo listes por separado.
3. Cada prerequisito debe ser un tema concreto y acotado (no "toda la
   aritmética de 3° básico").
4. Asigna el nivel educativo más apropiado según las Bases Curriculares
   chilenas.
5. Agrupa prerequisitos que son comunes a múltiples átomos M1 — evita
   repetir el mismo tema para cada átomo.
6. NO inventes niveles educativos — usa SOLO los prefijos listados.
</task>

<output_format>
Responde SOLO con un objeto JSON válido con esta estructura:

{{
  "prerequisite_topics": [
    {{
      "id": "PT-001",
      "grade_level": "EB3",
      "eje": "numeros",
      "titulo": "Título conciso del tema prerequisito",
      "descripcion": "Descripción breve (1-2 oraciones) de qué debe
        saber el estudiante.",
      "needed_by_m1_atoms": ["A-M1-NUM-01-01", "A-M1-ALG-01-02"],
      "justificacion": "Por qué este conocimiento es necesario."
    }}
  ],
  "dependency_chains": [
    {{
      "description": "Cadena ejemplo: contar → sumar → multiplicar",
      "chain": ["PT-001", "PT-005", "PT-012"]
    }}
  ],
  "summary": {{
    "total_topics": 0,
    "by_grade": {{"EB1": 0, "EB2": 0}},
    "by_eje": {{"numeros": 0}}
  }}
}}
</output_format>

<rules>
1. Todo en español.
2. Sé fiel a las Bases Curriculares chilenas para la asignación de niveles.
3. No omitas prerrequisitos fundamentales por parecerte "obvios" — si un
   estudiante de bajo rendimiento podría no saberlo, inclúyelo.
4. Prioriza temas que sean prerrequisito de MÚLTIPLES átomos M1.
5. Mantén las descripciones concisas pero específicas.
6. Cada topic ID debe ser único (PT-001, PT-002, ...).
7. Las cadenas de dependencia (dependency_chains) muestran el orden
   pedagógico — un tema más básico va primero.
</rules>

<final_instruction>
Analiza cada átomo M1 proporcionado y genera la lista completa de
prerequisite_topics necesarios. Piensa en un estudiante que llega con
lagunas desde educación básica: ¿qué necesitaría dominar paso a paso
para llegar a cada átomo M1?
</final_instruction>"""
