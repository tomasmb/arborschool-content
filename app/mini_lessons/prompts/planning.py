"""Prompt template for Phase 1 — Lesson Planning.

Generates a structured LessonPlan for an atom's mini-class.
Uses GPT-5.1 with JSON response format.
"""

from __future__ import annotations

from app.mini_lessons.prompts.shared import _TONE_RULES
from app.question_generation.image_types import (
    ALL_SPECS,
    NOT_IMAGES_DESCRIPTION,
)

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
Si incluyes Trampa PAES, elige la ÚNICA confusión más peligrosa \
de las familias de error seleccionadas (las demás se cubren en \
el ejemplo resuelto y las preguntas adaptativas).
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
9. **Specs son directivas, NO borradores**: Los campos *_spec son \
instrucciones concisas para el redactor de cada sección. Describe \
QUÉ cubrir, no CÓMO redactarlo. El redactor decidirá la prosa \
final. Límites: objective_spec max 30 palabras (1 oración), \
concept_spec max 40 palabras (1-2 oraciones), \
mathematical_context max 30 palabras (1 oración).

{image_instruction}
</task>

<rules>
{tone_rules}
- Responde SOLO en español cuando describes contenido pedagógico.
- NO copies preguntas generadas; úsalas solo como referencia de \
estilo y nivel.
</rules>

<output_format>
JSON puro (sin bloques markdown). Los *_spec son directivas breves:
{{
  "template_type": "{template_type}",
  "objective_spec": "Evaluar expresiones sustituyendo racionales con jerarquía de operaciones.",
  "concept_spec": "Definir evaluación, resumir jerarquía, Trampa: confusión signo negativo en potencias.",
  "concept_in_scope_items": ["in_scope item 1", "..."],
  "canonical_steps": ["Sustituye", "Reescribe", "Calcula", "Chequeo"],
  "worked_example": {{
    "topic": "tema del ejemplo",
    "mathematical_context": "Expresión racional con x negativo fraccionario y potencia cuadrada.",
    "step_count": 4,
    "numbers_to_use": "x=-3/2, y=0,5, coeficientes 2 y 3",
    "in_scope_items_covered": ["..."],
    "error_families_addressed": ["nombre_familia"]
  }},
  "checklist_items": [
    "¿Verificación 1?",
    "¿Verificación 2?",
    "¿Verificación 3?"
  ],
  "image_plan": [
    {{
      "target_section": "concept",
      "image_type": "function_graph",
      "image_description_hint": "Parábola y=x²-4 con interceptos"
    }}
  ],
  "include_prerequisite_refresh": false,
  "justifications": {{
    "prerequisite_decision": "razón breve",
    "image_decision": "razón breve"
  }}
}}
Si el átomo NO necesita imágenes, "image_plan" debe ser [].
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
    required_image_types: list[str] | None = None,
) -> str:
    """Assemble the full lesson planning prompt."""
    image_instruction = build_image_instruction_for_lessons(
        required_image_types,
    )
    return LESSON_PLAN_PROMPT.format(
        context_section=context_section,
        atom_id=atom_id,
        template_type=template_type,
        tone_rules=_TONE_RULES,
        image_instruction=image_instruction,
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


# ------------------------------------------------------------------
# Image instruction builder
# ------------------------------------------------------------------

_VALID_IMAGE_SECTIONS = frozenset({
    "concept", "worked-example", "prerequisite-refresh",
})


def build_image_instruction_for_lessons(
    required_image_types: list[str] | None,
) -> str:
    """Build the image planning instruction for the lesson planner.

    When the atom has ``required_image_types`` from enrichment, the
    planner decides which sections need images and what type.
    The section generator later produces the detailed description.
    """
    if not required_image_types:
        return (
            "10. **Imágenes**: Este átomo NO necesita imágenes. "
            '"image_plan" debe ser [].'
        )

    spec_map = {s.key: s for s in ALL_SPECS}
    type_lines: list[str] = []
    keys: list[str] = []
    for t in required_image_types:
        spec = spec_map.get(t)
        if spec:
            type_lines.append(
                f"  - `{spec.key}`: {spec.description}\n"
                f"    Usar cuando: {spec.when_to_use}"
            )
            keys.append(spec.key)

    types_catalog = "\n".join(type_lines)
    sections_str = ", ".join(sorted(_VALID_IMAGE_SECTIONS))

    return (
        f"10. **Imágenes**: Este átomo puede usar estos tipos "
        f"de imagen:\n{types_catalog}\n"
        f"Decide qué secciones ({sections_str}) se benefician "
        f"genuinamente de una imagen. Agrega una entrada en "
        f'"image_plan" por cada imagen necesaria.\n'
        f"- target_section: sección que recibe la imagen.\n"
        f"- image_type: SOLO valores de: "
        f"{', '.join(keys)}.\n"
        f"- image_description_hint: directiva breve (1 oración) "
        f"del contenido visual. El redactor refinará la "
        f"descripción junto con el HTML.\n"
        f"- NO agregues imagen si no aporta comprensión real.\n"
        f"- IMPORTANTE: {NOT_IMAGES_DESCRIPTION}"
    )
