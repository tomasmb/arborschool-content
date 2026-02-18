"""Prompt templates for Phase 4 — Base QTI Generation.

Provides two prompts and helper builders for per-slot generation:
- SINGLE_QTI_GENERATION_PROMPT: generates exactly 1 QTI item per slot.
- XSD_RETRY_PROMPT: re-generates an item after XSD validation failure,
  passing the specific errors back to the model.

Helper functions:
- build_context_section: shared atom+enrichment text (built once).
- build_single_slot_section: formats one PlanSlot for the prompt.
"""

from __future__ import annotations

from app.question_generation.prompts.planning import (
    build_enrichment_section,
)
from app.question_generation.prompts.reference_examples import (
    BASE_QTI_REFERENCE,
    BASE_QTI_WITH_IMAGE_REFERENCE,
)

# ------------------------------------------------------------------
# QTI structural rules — shared by both generation and retry prompts.
# Defined once to avoid redundancy / contradictions (DRY).
# ------------------------------------------------------------------

_QTI_RULES = """\
- El ítem DEBE tener identifier: "{atom_id}_Q{slot_index}"
- Opción múltiple (MCQ) con EXACTAMENTE 4 opciones (A-D), 1 correcta
- En español de Chile, notación PAES (separadores decimales chilenos)
- Usa MathML nativo para TODA expresión matemática. NUNCA uses LaTeX.
  Cada <math> DEBE llevar xmlns explícito:
  <math xmlns="http://www.w3.org/1998/Math/MathML"><mrow>...</mrow></math>
  Sin este atributo, el XSD rechaza el elemento.
- xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0"
- Estructura: qti-assessment-item > qti-response-declaration +
  qti-outcome-declaration + qti-item-body > (prompt +
  qti-choice-interaction > qti-simple-choice identifier="A","B","C","D")
  + qti-response-processing
- Distractores DEBEN representar errores plausibles, NO valores aleatorios
- NO incluyas feedback ni solución trabajada (se agregan después)
- NO incluyas <modalFeedback> ni <feedbackInline>
- Contexto real (real_world_*): intégralo naturalmente en el enunciado
- Respeta el numbers_profile del slot para los valores numéricos
- Dificultad: sigue la rúbrica del ENRIQUECIMIENTO en el contexto
- El XML DEBE ser well-formed y parseable
- NO uses caracteres de control (Unicode < 0x20 excepto tab/newline).
  Solo texto imprimible estándar en contenido y atributos."""

# ------------------------------------------------------------------
# Image placeholder rules — appended to _QTI_RULES when
# the slot has image_required=True. Defined once (DRY).
# ------------------------------------------------------------------

_IMAGE_PLACEHOLDER_RULES = """\
- Este slot REQUIERE una imagen. Incluye EXACTAMENTE un tag <img>
  dentro de <qti-item-body>, envuelto en un <p>:
  <p><img src="IMAGE_PLACEHOLDER" alt="BREVE DESCRIPCION"
    style="max-width:100%;height:auto;" /></p>
- El alt DEBE describir brevemente el contenido visual (accesibilidad).
- El enunciado DEBE referenciar la imagen de forma natural:
  "La siguiente figura muestra...", "A partir del grafico...", etc.
- NO inventes datos que no sean visibles en la imagen.
  La pregunta depende de lo que el estudiante VE en la imagen.
- Ademas del QTI XML, responde con "image_description": una
  descripcion DETALLADA del contenido visual que se debe generar.
  Incluye: elementos matematicos, posiciones, etiquetas, valores
  numericos, dominio/rango, puntos notables. Esta descripcion
  sera usada para generar la imagen automaticamente."""

# ------------------------------------------------------------------
# JSON output spec — shared by both prompts
# ------------------------------------------------------------------

_JSON_OUTPUT = """\
Responde con JSON puro (sin bloques markdown):
{{
  "slot_index": {slot_index},
  "qti_xml": "<qti-assessment-item ...>...</qti-assessment-item>"
}}"""

_JSON_OUTPUT_WITH_IMAGE = """\
Responde con JSON puro (sin bloques markdown):
{{
  "slot_index": {slot_index},
  "qti_xml": "<qti-assessment-item ...>...</qti-assessment-item>",
  "image_description": "Descripcion detallada del contenido visual..."
}}"""

# ------------------------------------------------------------------
# Prompt 1: Single-slot generation
# ------------------------------------------------------------------

SINGLE_QTI_GENERATION_PROMPT = """\
<role>
Eres un generador de ítems PAES M1 (Chile) en formato QTI 3.0 XML.
Tu tarea es materializar UNA especificación de ítem en XML válido.
</role>

<context>
{context_section}
</context>

<slot>
{slot_section}
</slot>

<reference_example>
El siguiente es un ejemplo de QTI 3.0 válido. Tu output DEBE seguir
esta misma estructura XML (namespaces, elementos, atributos).
El contenido será distinto.
{reference_example}
</reference_example>

<rules>
{rules}
</rules>

<output_format>
{json_output}
</output_format>

<final_instruction>
Genera 1 ítem base QTI 3.0 para el slot indicado. Responde SOLO con JSON.
</final_instruction>
"""

# ------------------------------------------------------------------
# Prompt 2: XSD retry (includes failed XML + errors)
# ------------------------------------------------------------------

XSD_RETRY_PROMPT = """\
<role>
Eres un generador de ítems PAES M1 (Chile) en formato QTI 3.0 XML.
El XML que generaste anteriormente NO pasó la validación XSD.
Tu tarea es corregir los errores y generar XML válido.
</role>

<context>
{context_section}
</context>

<slot>
{slot_section}
</slot>

<failed_xml>
{failed_xml}
</failed_xml>

<xsd_errors>
{xsd_errors}
</xsd_errors>

<reference_example>
El siguiente es un ejemplo de QTI 3.0 válido. Compáralo con tu XML
fallido para identificar diferencias estructurales.
{reference_example}
</reference_example>

<rules>
{rules}
</rules>

<output_format>
{json_output}
</output_format>

<final_instruction>
Corrige los errores XSD del XML anterior y genera el ítem válido.
Responde SOLO con JSON.
</final_instruction>
"""


# ------------------------------------------------------------------
# Builder helpers
# ------------------------------------------------------------------


def build_context_section(
    ctx: object,
    enrichment: object | None,
) -> str:
    """Build the shared atom+enrichment context text.

    Built once and reused across all per-slot LLM calls so that
    the model has full atom context without repeating it.

    Args:
        ctx: AtomContext with atom metadata.
        enrichment: AtomEnrichment or None.

    Returns:
        Formatted context string for prompt injection.
    """
    enrichment_text = build_enrichment_section(enrichment)
    return (
        f"ÁTOMO:\n"
        f"- ID: {ctx.atom_id}\n"
        f"- Título: {ctx.atom_title}\n"
        f"- Descripción: {ctx.atom_description}\n"
        f"- Eje: {ctx.eje}\n"
        f"- Criterios atómicos: {', '.join(ctx.criterios_atomicos)}\n"
        f"\n"
        f"ENRIQUECIMIENTO:\n"
        f"{enrichment_text}"
    )


def build_single_slot_section(slot: object) -> str:
    """Format a single PlanSlot for the generation prompt.

    Conditionally appends image metadata when the slot
    requires an image (Open/Closed via composition).

    Args:
        slot: PlanSlot object.

    Returns:
        Formatted string describing the slot specification.
    """
    base = (
        f"Slot {slot.slot_index}:\n"
        f"  - Dificultad: {slot.difficulty_level.value}\n"
        f"  - Componente: {slot.component_tag}\n"
        f"  - Skeleton: {slot.operation_skeleton_ast}\n"
        f"  - Contexto: {slot.surface_context}\n"
        f"  - Perfil numérico: {slot.numbers_profile}"
    )
    if getattr(slot, "image_required", False):
        img_type = getattr(slot, "image_type", None) or "general"
        img_desc = getattr(slot, "image_description", None) or ""
        base += (
            f"\n  - Imagen requerida: Sí"
            f"\n  - Tipo de imagen: {img_type}"
            f"\n  - Descripción del plan: {img_desc}"
        )
    return base


def _format_slot_rules_and_output(
    slot: object,
    atom_id: str,
) -> tuple[str, str]:
    """Build the rules and JSON output blocks for a slot.

    Shared by both generation and XSD-retry prompts (DRY).
    Conditionally appends image placeholder rules when the
    slot requires an image.

    Args:
        slot: PlanSlot with slot_index.
        atom_id: Atom identifier for the item ID.

    Returns:
        Tuple of (rules_text, json_output_text).
    """
    rules = _QTI_RULES.format(
        atom_id=atom_id, slot_index=slot.slot_index,
    )
    needs_image = getattr(slot, "image_required", False)
    if needs_image:
        rules += "\n" + _IMAGE_PLACEHOLDER_RULES
    json_tpl = _JSON_OUTPUT_WITH_IMAGE if needs_image else _JSON_OUTPUT
    json_output = json_tpl.format(slot_index=slot.slot_index)
    return rules, json_output


def build_single_generation_prompt(
    context_section: str,
    slot: object,
    atom_id: str,
) -> str:
    """Assemble the full single-slot generation prompt.

    When the slot needs an image, injects the image reference
    example alongside the base reference (Open/Closed).

    Args:
        context_section: Pre-built atom+enrichment text.
        slot: PlanSlot to generate.
        atom_id: Atom identifier for the item ID.

    Returns:
        Complete prompt string ready for LLM call.
    """
    rules, json_output = _format_slot_rules_and_output(
        slot, atom_id,
    )
    ref_example = BASE_QTI_REFERENCE
    if getattr(slot, "image_required", False):
        ref_example += (
            "\n\n--- Ejemplo con imagen (placeholder) ---\n\n"
            + BASE_QTI_WITH_IMAGE_REFERENCE
        )
    return SINGLE_QTI_GENERATION_PROMPT.format(
        context_section=context_section,
        slot_section=build_single_slot_section(slot),
        reference_example=ref_example,
        rules=rules,
        json_output=json_output,
    )


def build_xsd_retry_prompt(
    context_section: str,
    slot: object,
    failed_xml: str,
    xsd_errors: str,
    atom_id: str,
) -> str:
    """Assemble the XSD-retry prompt with error feedback.

    Args:
        context_section: Pre-built atom+enrichment text.
        slot: Original PlanSlot specification.
        failed_xml: The QTI XML that failed XSD validation.
        xsd_errors: Specific XSD error messages.
        atom_id: Atom identifier for the item ID.

    Returns:
        Complete retry prompt string ready for LLM call.
    """
    rules, json_output = _format_slot_rules_and_output(
        slot, atom_id,
    )
    ref_example = BASE_QTI_REFERENCE
    if getattr(slot, "image_required", False):
        ref_example += (
            "\n\n--- Ejemplo con imagen (placeholder) ---\n\n"
            + BASE_QTI_WITH_IMAGE_REFERENCE
        )
    return XSD_RETRY_PROMPT.format(
        context_section=context_section,
        slot_section=build_single_slot_section(slot),
        failed_xml=failed_xml,
        xsd_errors=xsd_errors,
        reference_example=ref_example,
        rules=rules,
        json_output=json_output,
    )
