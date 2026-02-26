"""Prompt template for Phase 1 — Lesson Planning.

Generates a structured LessonPlan for an atom's mini-class.
Uses GPT-5.1 with JSON response format.
"""

from __future__ import annotations

from app.mini_lessons.prompts.shared import _TONE_RULES

LESSON_PLAN_PROMPT = """\
<role>
Eres un diseñador instruccional experto en PAES M1 (Chile). \
Tu tarea es crear un PLAN detallado para una mini-clase de un \
átomo de aprendizaje. NO generas la clase, solo el plan.
</role>

<context>
{context_section}
</context>

<task>
Genera un plan JSON para la mini-clase del átomo {atom_id} \
(template {template_type}).

El plan DEBE cumplir:

1. **Cobertura total de in_scope**: Cada ítem de "En alcance" del \
enriquecimiento debe estar asignado a al menos una sección.
2. **Cobertura total de error_families**: Cada familia de error \
debe estar asignada a ejemplos resueltos (rationale de pasos), \
feedback de quick-checks, o sección de errores.
3. **Progresión de dificultad**: Ejemplo 1 usa criterios del nivel \
"easy" de la rúbrica. Ejemplo 2 sube a criterios "medium"/"hard".
4. **Contextos diferentes**: Los dos ejemplos resueltos usan \
contextos matemáticos distintos.
5. **Quick-checks por template**:
  - P-template: EXACTAMENTE 2 quick-checks. \
QC1 = rápido, un solo concepto (20-30s). \
QC2 = integrador, combina conceptos (45-60s).
  - C-template: 1-2 quick-checks.
  - M-template: 2 quick-checks (1 procedimental + 1 conceptual).
  NUNCA 3 o más quick-checks.
6. **Complejidad gradual**: WE2 agrega máximo UNA dimensión de \
dificultad nueva vs WE1. \
Dimensiones: tipo de número, número de variables, tipo de \
expresión, presencia de potencias. NO 3+ cambios de golpe.
7. **Brevedad**: El plan debe producir una clase de 4-7 minutos. \
Cada sección tiene un presupuesto de palabras indicado.
8. **Prerequisitos**: Decide si incluir bloque de repaso de \
prerequisitos basándote en la lista de prerrequisitos.
</task>

<rules>
{tone_rules}
- Responde SOLO en español cuando describes contenido pedagógico.
- NO copies preguntas generadas; úsalas solo como referencia de \
estilo y nivel.
- Secciones opcionales SOLO si el tipo de átomo lo justifica.
</rules>

<output_format>
JSON puro (sin bloques markdown):
{{
  "template_type": "{template_type}",
  "objective_spec": "descripción del objetivo medible",
  "concept_spec": "qué explicar en la sección concepto",
  "concept_in_scope_items": ["in_scope item 1", "..."],
  "worked_example_1": {{
    "topic": "tema del ejemplo",
    "mathematical_context": "contexto matemático",
    "step_count": 4,
    "numbers_to_use": "descripción de números",
    "fading_level": "full",
    "in_scope_items_covered": ["..."],
    "error_families_addressed": ["nombre_familia"]
  }},
  "worked_example_2": {{
    "topic": "tema diferente",
    "mathematical_context": "contexto diferente",
    "step_count": 3,
    "numbers_to_use": "números más complejos",
    "fading_level": "faded",
    "in_scope_items_covered": ["..."],
    "error_families_addressed": ["nombre_familia"]
  }},
  "quick_checks": [  // MÁXIMO 2 elementos en esta lista
    {{
      "stem_topic": "tema del quick check",
      "correct_answer_theme": "qué evalúa",
      "distractor_themes": ["error 1", "error 2", "error 3"],
      "error_families_addressed": ["nombre_familia"],
      "difficulty": "simple"  // "simple" o "integrative"
    }}
  ],
  "error_patterns_spec": "qué errores cubrir + tip PAES",
  "error_patterns_families": ["familias restantes"],
  "optional_sections": [],
  "include_prerequisite_refresh": false,
  "justifications": {{
    "prerequisite_decision": "razón",
    "optional_sections": "razón o vacío"
  }}
}}
</output_format>

<final_instruction>
Genera el plan para la mini-clase del átomo {atom_id}. \
Asegúrate de que TODOS los ítems in_scope y TODAS las familias \
de error estén asignados a alguna sección. \
Responde SOLO con el JSON.
</final_instruction>
"""


PLAN_COHERENCE_PROMPT = """\
<role>
Revisor de planes de mini-clase PAES M1.
</role>

<context>
PLAN:
{plan_json}

ÁTOMO:
{atom_summary}
</context>

<task>
Revisa el plan y responde con JSON:
1. ¿El Ejemplo 2 es una progresión coherente desde el Ejemplo 1 \
(fading)?
2. ¿El contenido está dentro del alcance del átomo?
3. ¿Los quick-checks evalúan habilidades vistas en los ejemplos?
4. ¿La cobertura de error_families es completa?
</task>

<output_format>
JSON puro:
{{
  "coherent": true,
  "issues": []
}}
Si hay problemas, "coherent": false y lista los issues.
</output_format>
"""


def build_plan_prompt(
    context_section: str,
    atom_id: str,
    template_type: str,
) -> str:
    """Assemble the full lesson planning prompt."""
    return LESSON_PLAN_PROMPT.format(
        context_section=context_section,
        atom_id=atom_id,
        template_type=template_type,
        tone_rules=_TONE_RULES,
    )


def build_coherence_prompt(
    plan_json: str,
    atom_summary: str,
) -> str:
    """Assemble the plan coherence check prompt."""
    return PLAN_COHERENCE_PROMPT.format(
        plan_json=plan_json,
        atom_summary=atom_summary,
    )
