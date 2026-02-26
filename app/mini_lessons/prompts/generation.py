"""Prompt templates for Phase 2 — Section-by-Section Generation.

Provides one generation prompt per section type and a retry prompt
for sections that fail validation. All prompts share the same
rule constants from shared.py (DRY).

Builder functions compose: context + plan + rules + reference.
"""

from __future__ import annotations

from app.mini_lessons.prompts.reference_examples import (
    extract_section_reference,
)
from app.mini_lessons.prompts.shared import build_generation_rules

# ------------------------------------------------------------------
# Generic section generation prompt (all section types)
# ------------------------------------------------------------------

SECTION_GENERATION_PROMPT = """\
<role>
Eres un redactor de mini-clases PAES M1 (Chile). Tu tarea es \
generar UNA sección de una mini-clase en HTML semántico.
</role>

<context>
{context_section}

PLAN DE LA MINI-CLASE:
{plan_section}
</context>

<reference_example>
El siguiente es un ejemplo de sección "{block_name}" válida. \
Tu output DEBE seguir esta misma estructura HTML. \
El contenido será distinto.
{reference_html}
</reference_example>

<task>
Genera la sección "{block_name}"{index_label} de la mini-clase \
para el átomo {atom_id}.
{task_details}
</task>

<rules>
{rules}
</rules>

<output_format>
Responde con JSON puro (sin bloques markdown):
{{
  "block_name": "{block_name}",
  "index": {index_json},
  "html": "<section data-block=\\"{block_name}\\"...>...</section>"
}}
</output_format>

<final_instruction>
Genera SOLO la sección "{block_name}" como HTML semántico. \
Respeta el presupuesto de palabras. Responde SOLO con JSON.
</final_instruction>
"""

# ------------------------------------------------------------------
# Retry prompt (includes failed HTML + specific errors)
# ------------------------------------------------------------------

SECTION_RETRY_PROMPT = """\
<role>
Eres un redactor de mini-clases PAES M1 (Chile). La sección que \
generaste anteriormente NO pasó la validación. Corrígela.
</role>

<context>
{context_section}

PLAN DE LA MINI-CLASE:
{plan_section}
</context>

<task>
{task_details}

La versión anterior falló por los errores listados abajo. \
Corrige todos los problemas manteniendo la estructura correcta.
</task>

<failed_html>
{failed_html}
</failed_html>

<validation_errors>
{validation_errors}
</validation_errors>

<reference_example>
{reference_html}
</reference_example>

<rules>
{rules}
</rules>

<output_format>
JSON puro:
{{
  "block_name": "{block_name}",
  "index": {index_json},
  "html": "<section ...>...</section>"
}}
</output_format>

<final_instruction>
Corrige los errores y genera la sección válida. \
Responde SOLO con JSON.
</final_instruction>
"""


# ------------------------------------------------------------------
# Task details per section type
# ------------------------------------------------------------------

_TASK_DETAILS: dict[str, str] = {
    "objective": (
        "Genera el header con objetivo medible + relevancia PAES. "
        "Usa <header data-block=\"objective\">."
    ),
    "concept": (
        "Genera la explicación conceptual mínima. "
        "Cubre los ítems in_scope asignados en el plan. "
        "Una idea por párrafo, sin repetir lo que el ejemplo "
        "resuelto mostrará."
    ),
    "worked-example": (
        "Genera el ejemplo resuelto con pasos en "
        "<details>/<summary>. "
        "Aborda las familias de error asignadas en el plan "
        "mostrando por qué el enfoque correcto funciona. "
        "Cierra con micro-refuerzo y Checklist PAES (3 ítems)."
    ),
    "prerequisite-refresh": (
        "Micro-bloque de repaso de prerrequisitos. "
        "Solo los conceptos estrictamente necesarios."
    ),
}


# ------------------------------------------------------------------
# Builder functions
# ------------------------------------------------------------------


def build_section_prompt(
    context_section: str,
    plan_section: str,
    block_name: str,
    atom_id: str,
    template_type: str,
    index: int | None = None,
) -> str:
    """Assemble a section generation prompt.

    Args:
        context_section: Pre-built atom+enrichment text.
        plan_section: Relevant portion of the plan for this section.
        block_name: Section data-block name.
        atom_id: Atom identifier.
        template_type: P, C, or M.
        index: Section index (for worked-example).
    """
    reference_html = extract_section_reference(
        template_type, block_name, index,
    )
    if not reference_html:
        reference_html = "(No hay ejemplo de referencia disponible)"

    rules = build_generation_rules(block_name, index)
    task_details = _TASK_DETAILS.get(block_name, "")
    index_label = f" (índice {index})" if index else ""
    index_json = str(index) if index else "null"

    return SECTION_GENERATION_PROMPT.format(
        context_section=context_section,
        plan_section=plan_section,
        reference_html=reference_html,
        block_name=block_name,
        index_label=index_label,
        index_json=index_json,
        atom_id=atom_id,
        task_details=task_details,
        rules=rules,
    )


def build_retry_prompt(
    context_section: str,
    plan_section: str,
    block_name: str,
    template_type: str,
    failed_html: str,
    validation_errors: str,
    index: int | None = None,
) -> str:
    """Assemble a section retry prompt with error feedback."""
    reference_html = extract_section_reference(
        template_type, block_name, index,
    )
    if not reference_html:
        reference_html = "(No hay ejemplo de referencia disponible)"

    rules = build_generation_rules(block_name, index)
    task_details = _TASK_DETAILS.get(block_name, "")
    index_json = str(index) if index else "null"

    return SECTION_RETRY_PROMPT.format(
        context_section=context_section,
        plan_section=plan_section,
        reference_html=reference_html,
        block_name=block_name,
        index_json=index_json,
        failed_html=failed_html,
        validation_errors=validation_errors,
        task_details=task_details,
        rules=rules,
    )


def extract_plan_section_for_block(
    plan_data: dict,
    block_name: str,
    index: int | None = None,
) -> str:
    """Extract the relevant portion of the plan for a section.

    Returns a concise string with only the plan fields relevant
    to the section being generated.
    """
    if block_name == "objective":
        return f"Objetivo: {plan_data.get('objective_spec', '')}"

    if block_name == "concept":
        items = plan_data.get("concept_in_scope_items", [])
        return (
            f"Concepto: {plan_data.get('concept_spec', '')}\n"
            f"Ítems in_scope a cubrir: {', '.join(items)}"
        )

    if block_name == "worked-example":
        we = plan_data.get("worked_example", {})
        canonical = plan_data.get("canonical_steps", [])
        checklist = plan_data.get("checklist_items", [])
        canonical_line = ""
        if canonical:
            canonical_line = (
                f"\n  Pasos canónicos: "
                f"{', '.join(canonical)}"
            )
        checklist_line = ""
        if checklist:
            checklist_line = (
                f"\n  Checklist PAES: "
                f"{'; '.join(checklist)}"
            )
        if isinstance(we, dict):
            return (
                f"Ejemplo resuelto:\n"
                f"  Tema: {we.get('topic', '')}\n"
                f"  Contexto: {we.get('mathematical_context', '')}\n"
                f"  Pasos: {we.get('step_count', 4)}\n"
                f"  Números: {we.get('numbers_to_use', '')}\n"
                f"  In_scope: "
                f"{', '.join(we.get('in_scope_items_covered', []))}\n"
                f"  Errores: "
                f"{', '.join(we.get('error_families_addressed', []))}"
                f"{canonical_line}"
                f"{checklist_line}"
            )
        return str(we)

    return ""
