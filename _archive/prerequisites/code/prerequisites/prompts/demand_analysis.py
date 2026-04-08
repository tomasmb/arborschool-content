"""Prompts for Phase 0: demand analysis.

Analyzes existing M1 leaf atoms to identify missing prerequisite knowledge.
Split into two steps:
  1. Per-eje analysis — focused prerequisite identification per domain
  2. Merge — cross-eje deduplication and dependency chain building
"""

from __future__ import annotations

import json
from typing import Any

from app.prerequisites.constants import GRADE_LEVEL_LABELS

EJE_DISPLAY_NAMES: dict[str, str] = {
    "numeros": "Números",
    "algebra_y_funciones": "Álgebra y Funciones",
    "geometria": "Geometría",
    "probabilidad_y_estadistica": "Probabilidad y Estadística",
}


def build_eje_demand_prompt(
    leaf_atoms: list[dict[str, Any]],
    eje: str,
) -> str:
    """Build prompt for prerequisite analysis of ONE eje's leaf atoms.

    Args:
        leaf_atoms: Compact M1 leaf atoms filtered to this eje.
        eje: Eje key (e.g. "numeros").

    Returns:
        Complete prompt string for GPT-5.1.
    """
    eje_label = EJE_DISPLAY_NAMES.get(eje, eje)
    atoms_json = json.dumps(leaf_atoms, ensure_ascii=False, indent=2)
    grade_labels = "\n".join(
        f"  - {k}: {v}" for k, v in GRADE_LEVEL_LABELS.items()
    )

    return f"""<role>
Eres un experto en diseño curricular de matemáticas del sistema educativo
chileno (Bases Curriculares, MINEDUC). Tu especialidad es el eje de
{eje_label}.
</role>

<context>
## Átomos M1 a analizar — eje {eje_label}

Estos son los átomos "frontera" (sin prerrequisitos M1) del eje
{eje_label}. Representan el punto de entrada al conocimiento M1 en
este dominio.

{atoms_json}

## Niveles educativos disponibles

{grade_labels}
</context>

<task>
Para CADA átomo proporcionado, identifica los conocimientos previos
fundamentales que un estudiante necesita dominar ANTES de abordar ese
átomo. Concéntrate exclusivamente en el dominio de {eje_label} y sus
dependencias naturales.

Reglas:
1. Rastrea hacia atrás hasta el nivel más básico necesario (incluso 1°
   básico si aplica).
2. Sé exhaustivo pero no redundante: si un prerrequisito cubre otro
   transitivamente, lista solo el más directo.
3. Cada prerrequisito debe ser un tema concreto y acotado (no "toda la
   aritmética de 3° básico").
4. Asigna el nivel educativo según las Bases Curriculares chilenas.
5. Agrupa prerrequisitos comunes a múltiples átomos — evita repetir el
   mismo tema para cada átomo.
6. NO inventes niveles educativos — usa SOLO los prefijos listados.
7. Incluye dependencias de OTROS ejes si son estrictamente necesarias
   (por ejemplo, {eje_label} puede depender de conceptos numéricos
   básicos). Márcalas claramente con su eje correcto.
</task>

<output_format>
Responde SOLO con un objeto JSON válido:

{{
  "eje": "{eje}",
  "prerequisite_topics": [
    {{
      "temp_id": "PT-{eje[:3].upper()}-001",
      "grade_level": "EB3",
      "eje": "{eje}",
      "titulo": "Título conciso del tema prerrequisito",
      "descripcion": "Descripción breve (1-2 oraciones).",
      "needed_by_m1_atoms": ["A-M1-...-01-01"],
      "justificacion": "Por qué este conocimiento es necesario."
    }}
  ],
  "internal_chains": [
    {{
      "description": "Cadena dentro del eje: tema A → tema B → tema C",
      "chain": ["PT-{eje[:3].upper()}-001", "PT-{eje[:3].upper()}-005"]
    }}
  ]
}}
</output_format>

<rules>
1. Todo en español.
2. Sé fiel a las Bases Curriculares chilenas para la asignación de niveles.
3. No omitas prerrequisitos fundamentales por ser "obvios" — si un
   estudiante de bajo rendimiento podría no saberlo, inclúyelo.
4. Prioriza temas prerrequisito de MÚLTIPLES átomos M1.
5. Descripciones concisas pero específicas.
6. Los temp_id deben ser únicos dentro de este eje.
</rules>

<final_instruction>
Analiza cada átomo M1 de {eje_label} y genera la lista completa de
prerrequisitos. Piensa en un estudiante con lagunas desde educación
básica: ¿qué necesita dominar paso a paso para llegar a cada átomo?
</final_instruction>"""


def build_demand_merge_prompt(
    per_eje_results: dict[str, list[dict[str, Any]]],
) -> str:
    """Build prompt to merge and deduplicate per-eje demand results.

    Args:
        per_eje_results: Dict mapping eje name to its prerequisite
            topics list (from per-eje analysis calls).

    Returns:
        Complete prompt string for GPT-5.1.
    """
    per_eje_json = json.dumps(
        per_eje_results, ensure_ascii=False, indent=2,
    )
    grade_labels = "\n".join(
        f"  - {k}: {v}" for k, v in GRADE_LEVEL_LABELS.items()
    )

    return f"""<role>
Eres un experto en diseño curricular de matemáticas chileno. Tu tarea
es unificar y deduplicar listas de prerrequisitos provenientes de
análisis independientes por eje temático.
</role>

<context>
## Prerrequisitos identificados por eje

{per_eje_json}

## Niveles educativos

{grade_labels}
</context>

<task>
Toma las listas de prerrequisitos de los 4 ejes y produce UNA lista
unificada. Pasos:

1. **Deduplicación**: Si el mismo tema aparece en múltiples ejes (por
   ejemplo, "fracciones" necesario tanto para Números como para
   Geometría), únelos en UN solo tema. Consolida needed_by_m1_atoms.
2. **IDs unificados**: Asigna IDs finales PT-001, PT-002, ... en orden
   de grade_level (EB1 primero, EM2 al final).
3. **Cadenas de dependencia globales**: Construye cadenas que crucen
   ejes cuando aplique (por ejemplo: contar → sumar → fracciones →
   razones).
4. **Resumen**: Genera conteos por grade_level y por eje.

Reglas de deduplicación:
- Dos temas son duplicados si cubren el MISMO conocimiento en el MISMO
  grade_level. No importa que tengan títulos ligeramente distintos.
- Ante duda, conserva el tema con descripción más completa.
- Si un tema fue listado con diferentes grade_levels en distintos ejes,
  conserva el grade_level más bajo (donde se enseña por primera vez).
</task>

<output_format>
Responde SOLO con un objeto JSON válido:

{{
  "prerequisite_topics": [
    {{
      "id": "PT-001",
      "grade_level": "EB1",
      "eje": "numeros",
      "titulo": "Título conciso",
      "descripcion": "Descripción breve.",
      "needed_by_m1_atoms": ["A-M1-NUM-01-01", "A-M1-ALG-01-02"],
      "justificacion": "Por qué este conocimiento es necesario."
    }}
  ],
  "dependency_chains": [
    {{
      "description": "Cadena: tema A → tema B → tema C",
      "chain": ["PT-001", "PT-005", "PT-012"]
    }}
  ],
  "deduplication_log": [
    {{
      "merged_into": "PT-003",
      "original_ids": ["PT-NUM-005", "PT-GEO-002"],
      "reason": "Ambos cubren fracciones en EB4"
    }}
  ],
  "summary": {{
    "total_topics": 0,
    "topics_before_dedup": 0,
    "topics_removed": 0,
    "by_grade": {{"EB1": 0, "EB2": 0}},
    "by_eje": {{"numeros": 0}}
  }}
}}
</output_format>

<rules>
1. Todo en español.
2. Conserva TODOS los needed_by_m1_atoms al fusionar — no pierdas refs.
3. Los IDs finales deben ser secuenciales: PT-001, PT-002, etc.
4. Ordena por grade_level ascendente (EB1 → EB2 → ... → EM2).
5. Sé agresivo con la deduplicación: mejor un tema bien definido que
   dos solapados.
6. Las dependency_chains deben cubrir las cadenas pedagógicas más
   importantes (las que conectan EB1 con EM2).
</rules>

<final_instruction>
Unifica las 4 listas en una sola lista limpia, deduplicada y ordenada.
Prioriza la calidad sobre la cantidad: menos temas bien definidos es
mejor que muchos temas solapados.
</final_instruction>"""
