"""Prompt for Phase 1: prerequisite standards generation.

Converts demand-analysis topics into full canonical standards, using
Chilean Bases Curriculares as the authoritative reference.
"""

from __future__ import annotations

import json
from typing import Any

from app.prerequisites.constants import GRADE_LEVEL_LABELS


def build_standards_generation_prompt(
    topics: list[dict[str, Any]],
    grade_level: str,
    existing_standard_ids: list[str],
) -> str:
    """Build prompt to generate prerequisite standards for one grade level.

    Args:
        topics: Prerequisite topics for this grade from demand analysis.
        grade_level: Grade prefix (e.g. "EB5").
        existing_standard_ids: IDs of standards already generated for
            lower grades, so the LLM avoids duplication.

    Returns:
        Complete prompt string for GPT-5.1.
    """
    topics_json = json.dumps(topics, ensure_ascii=False, indent=2)
    grade_label = GRADE_LEVEL_LABELS.get(grade_level, grade_level)
    existing_ids_str = ", ".join(existing_standard_ids) if existing_standard_ids else "(ninguno)"

    return f"""<role>
Eres un experto en currículo de matemáticas chileno (Bases Curriculares,
MINEDUC). Tu tarea es generar estándares canónicos de aprendizaje para
contenidos prerequisito de nivel {grade_label}.
</role>

<context>
## Temas prerequisito identificados para {grade_label}

{topics_json}

## Estándares ya generados en niveles anteriores

{existing_ids_str}

## Convención de IDs

- Formato: {grade_level}-{{EJE}}-{{NN}}
  donde EJE es NUM, ALG, GEO o PROB, y NN es un número de dos dígitos.
- Ejemplo: {grade_level}-NUM-01, {grade_level}-ALG-01

## Ejes temáticos y sus prefijos

- numeros → NUM
- algebra_y_funciones → ALG
- geometria → GEO
- probabilidad_y_estadistica → PROB
</context>

<task>
Genera un estándar canónico para CADA tema prerequisito listado. Cada
estándar debe:

1. Ser fiel a las Bases Curriculares chilenas para {grade_label}.
2. Ser autocontenido — legible sin contexto adicional.
3. Incluir campos "incluye" y "no_incluye" explícitos para acotar alcance.
4. Tener "subcontenidos_clave" que sugieran descomposición natural en
   átomos de aprendizaje.
5. Usar IDs únicos que no colisionen con los estándares ya existentes.
6. Tener el campo "grade_level" con valor "{grade_level}".
</task>

<output_format>
Responde SOLO con un array JSON de estándares:

[
  {{
    "id": "{grade_level}-NUM-01",
    "grade_level": "{grade_level}",
    "eje": "numeros",
    "titulo": "Título del estándar",
    "descripcion_general": "Descripción detallada (min 50 chars)...",
    "incluye": ["Qué cubre este estándar..."],
    "no_incluye": ["Qué NO cubre..."],
    "subcontenidos_clave": ["Subtema 1", "Subtema 2"],
    "ejemplos_conceptuales": ["Ejemplo 1"],
    "habilidades_relacionadas": [
      {{
        "habilidad_id": "resolver_problemas",
        "criterios_relevantes": ["Criterio relevante"]
      }}
    ]
  }}
]
</output_format>

<rules>
1. Todo en español.
2. NO generes estándares para temas ya cubiertos en niveles anteriores.
3. Mantén el alcance estrictamente dentro de {grade_label} — no incluyas
   contenido de niveles superiores.
4. "habilidades_relacionadas" usa SOLO: resolver_problemas, modelar,
   representar, argumentar.
5. Los "subcontenidos_clave" deben ser lo suficientemente granulares
   para generar 2-6 átomos de aprendizaje por estándar.
6. "no_incluye" debe ser explícito sobre límites de complejidad.
</rules>

<final_instruction>
Basándote en los temas prerequisito proporcionados arriba, genera los
estándares canónicos. Antes de finalizar cada estándar, verifica:
1. ¿El alcance es fiel a las Bases Curriculares de {grade_label}?
2. ¿"incluye" y "no_incluye" son explícitos y no ambiguos?
3. ¿Los "subcontenidos_clave" sugieren descomposición natural en
   átomos evaluables independientemente?
4. ¿El ID es único y no colisiona con estándares ya existentes?
</final_instruction>"""
