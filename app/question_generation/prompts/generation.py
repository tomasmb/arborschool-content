"""Prompt template for Phase 4 — Base QTI Generation.

Materializes plan slots into base QTI 3.0 XML items (stem + options +
correct response). Does NOT add feedback or worked solutions.
"""

# Temperature: 0.0 (deterministic XML output)
# Response format: text (XML output, not JSON)

BASE_QTI_GENERATION_PROMPT = """\
<role>
Eres un generador de ítems PAES M1 (Chile) en formato QTI 3.0 XML.
Tu tarea es materializar especificaciones de ítems en XML válido.
</role>

<context>
ÁTOMO:
- ID: {atom_id}
- Título: {atom_title}
- Descripción: {atom_description}
- Eje: {eje}
- Criterios atómicos: {criterios_atomicos}

ENRIQUECIMIENTO:
{enrichment_section}
</context>

<task>
Genera exactamente {num_items} ítems QTI 3.0 XML BASE (sin feedback ni
solución trabajada) a partir de las siguientes especificaciones de slots:

{slots_section}

Cada ítem DEBE ser:
- Opción múltiple (MCQ) con EXACTAMENTE 4 opciones (A-D)
- EXACTAMENTE 1 respuesta correcta
- En español de Chile
- Con notación PAES (separadores decimales, convenciones chilenas)
- QTI 3.0 XML válido con namespace correcto
</task>

<rules>
- Cada ítem DEBE tener un identifier único: "{atom_id}_Q{{slot_index}}"
- Usa MathML para TODA expresión matemática (fracciones, ecuaciones, etc.)
- Incluye MathML completo: <math>, <mrow>, <mfrac>, <msup>, etc.
- Los distractores DEBEN representar errores plausibles, NO valores aleatorios
- NO incluyas feedback por opción ni solución trabajada (se agrega después)
- NO incluyas etiquetas <modalFeedback> ni <feedbackInline>
- Si el slot especifica un contexto real (real_world_*), integra el contexto
  de forma natural en el enunciado
- Respeta el numbers_profile del slot para elegir valores numéricos
- Respeta la dificultad: easy = procedimiento directo, medium = 2-3 pasos,
  hard = razonamiento compuesto o representaciones múltiples
</rules>

<output_format>
Responde con un JSON con esta estructura (sin bloques markdown):
{{
  "items": [
    {{
      "slot_index": 0,
      "qti_xml": "<qti-assessment-item ...>...</qti-assessment-item>"
    }}
  ]
}}

El XML de cada ítem DEBE:
- Usar xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0"
- Tener la estructura: qti-assessment-item > qti-item-body > (prompt +
  qti-choice-interaction con qti-simple-choice) + qti-response-declaration +
  qti-outcome-declaration + qti-response-processing
- Cada qti-simple-choice debe tener identifier="A", "B", "C", "D"
</output_format>

<restricciones_criticas>
CRÍTICO:
- Si la pregunta requiere ecuaciones o tablas, INCLUYE MathML completo
  (<mtable>, <mtr>, <mtd> para sistemas; <mfrac> para fracciones)
- NUNCA uses LaTeX — solo MathML nativo dentro del XML
- El XML debe ser well-formed y parseable
</restricciones_criticas>

<final_instruction>
Basándote en las especificaciones anteriores, genera los {num_items}
ítems base QTI 3.0 para el átomo {atom_id}. Responde SOLO con el JSON.
</final_instruction>
"""


def build_slots_section(plan_slots: list) -> str:
    """Format plan slots for the generation prompt.

    Args:
        plan_slots: List of PlanSlot objects.

    Returns:
        Formatted string describing each slot specification.
    """
    lines = []
    for slot in plan_slots:
        lines.append(
            f"Slot {slot.slot_index}:\n"
            f"  - Dificultad: {slot.difficulty_level.value}\n"
            f"  - Componente: {slot.component_tag}\n"
            f"  - Skeleton: {slot.operation_skeleton_ast}\n"
            f"  - Contexto: {slot.surface_context}\n"
            f"  - Perfil numérico: {slot.numbers_profile}",
        )
    return "\n\n".join(lines)
