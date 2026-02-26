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

La mini-clase tiene SOLO 3 secciones: objetivo, concepto y \
un ejemplo resuelto (con checklist PAES al final). \
Toda la práctica ocurre después en un set de preguntas adaptativo.

El plan DEBE cumplir:

1. **Cobertura total de in_scope**: Cada ítem de "En alcance" del \
enriquecimiento debe estar asignado al concepto o al ejemplo resuelto.
2. **Selección de error_families**: Selecciona máximo 5 familias \
de error (las más relevantes del enriquecimiento). Usa los NOMBRES \
EXACTOS del enriquecimiento. El ejemplo resuelto debe abordar al \
menos 2 de ellas en sus pasos.
3. **Brevedad extrema**: La clase entera debe tomar 3-4 minutos. \
Cada sección tiene un presupuesto de palabras indicado. Prioriza \
densidad sobre exhaustividad.
4. **Concepto**: Máximo 3 bloques <h3>. Mínima teoría necesaria. \
Si hay una confusión frecuente, incluye Trampa PAES como uno de \
los 3 bloques.
5. **Ejemplo resuelto**: Contexto matemático de dificultad easy/medium \
(no hard — eso lo cubre el set adaptativo). 3-4 pasos con \
verificación. Cierra con Checklist PAES de 3 ítems.
6. **Pasos canónicos (P-template)**: Si el template es P, define \
3-5 pasos con nombres fijos que forman el procedimiento repetible \
del átomo.
7. **Checklist PAES**: Exactamente 3 ítems cortos (1 línea cada uno) \
que el estudiante puede aplicar en 10 segundos bajo presión. \
Deben cubrir las verificaciones más críticas del procedimiento.
8. **Prerrequisitos**: Decide si incluir bloque de repaso de \
prerrequisitos basándote en la lista de prerrequisitos.
</task>

<rules>
{tone_rules}
- Responde SOLO en español cuando describes contenido pedagógico.
- NO copies preguntas generadas; úsalas solo como referencia de \
estilo y nivel.
</rules>

<output_format>
JSON puro (sin bloques markdown):
{{
  "template_type": "{template_type}",
  "objective_spec": "descripción del objetivo medible",
  "concept_spec": "qué explicar en la sección concepto",
  "concept_in_scope_items": ["in_scope item 1", "..."],
  "canonical_steps": ["Sustituye", "Reescribe", "Calcula", "Chequeo"],
  "worked_example": {{
    "topic": "tema del ejemplo",
    "mathematical_context": "contexto matemático",
    "step_count": 4,
    "numbers_to_use": "descripción de números",
    "in_scope_items_covered": ["..."],
    "error_families_addressed": ["nombre_familia"]
  }},
  "checklist_items": [
    "¿Verificación 1?",
    "¿Verificación 2?",
    "¿Verificación 3?"
  ],
  "include_prerequisite_refresh": false,
  "justifications": {{
    "prerequisite_decision": "razón"
  }}
}}
</output_format>

<final_instruction>
Genera el plan para la mini-clase del átomo {atom_id}. \
Asegúrate de que TODOS los ítems in_scope estén asignados a \
concepto o ejemplo resuelto. Para familias de error, selecciona \
hasta 5 usando sus NOMBRES EXACTOS del enriquecimiento. \
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
1. ¿El contenido está dentro del alcance del átomo?
2. ¿El ejemplo resuelto cubre al menos 2 familias de error?
3. ¿Los 3 ítems de checklist son accionables y relevantes?
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
