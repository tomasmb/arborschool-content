"""Prompt builders for standards generation and validation.

Follows Gemini best practices from
`docs/gemini-3-pro-prompt-engineering-best-practices.md` for `gemini-3-pro-preview`:
- Context first, then instructions
- Explicit output format with JSON schema
- Clear task description
- Negative constraints (what NOT to do)
- Anchor phrases like "Based on the information above..."
"""

from __future__ import annotations

import json
from typing import Any

from app.models.constants import EJE_PREFIX_MAP
from app.utils.prompt_helpers import format_habilidades_context

# Example standard for few-shot learning (from standards-paes-m1-full-GPT.md)
EXAMPLE_STANDARD = {
    "id": "M1-NUM-02",
    "eje": "numeros",
    "unidad_temario": "Porcentaje",
    "titulo": "Porcentajes",
    "descripcion_general": (
        "Este contenido aborda la comprensión conceptual y procedimental de los "
        "porcentajes como una forma de expresar razones y proporciones. Incluye su "
        "interpretación como 'parte de un total', su relación con fracciones y decimales, "
        "y su utilización para describir cambios relativos, comparaciones y distribuciones."
    ),
    "incluye": [
        "Interpretación de un porcentaje como fracción de denominador 100.",
        "Conversión entre porcentaje, fracción y número decimal.",
        "Cálculo de un porcentaje de una cantidad.",
        "Aplicación en situaciones reales: descuentos, aumentos, impuestos.",
    ],
    "no_incluye": [
        "Cálculo de intereses compuestos (no aparece en PAES M1).",
        "Ecuaciones con porcentajes como incógnitas (corresponde a Álgebra).",
        "Probabilidad o conteo combinatorio.",
    ],
    "subcontenidos_clave": [
        "Relación porcentaje ↔ fracción ↔ decimal.",
        "Porcentaje de una cantidad.",
        "Porcentajes de cambio (aumento/disminución).",
    ],
    "ejemplos_conceptuales": [
        "Interpretar '35% de los estudiantes' como una fracción del total.",
        "Comparar dos descuentos distintos en términos de proporción.",
    ],
    "habilidades_relacionadas": [
        {
            "habilidad_id": "resolver_problemas",
            "criterios_relevantes": ["Resuelve situaciones rutinarias con operatoria básica."],
        },
    ],
    "fuentes_temario": {
        "conocimientos_path": "conocimientos.numeros.unidades[1]",
        "descripciones_originales": [
            "Concepto y cálculo de porcentaje.",
            "Problemas que involucren porcentaje en diversos contextos.",
        ],
    },
}


# -----------------------------------------------------------------------------
# Generation prompt
# -----------------------------------------------------------------------------


def build_generation_prompt(
    unidad_data: dict[str, Any],
    eje_key: str,
    unidad_index: int,
    habilidades: dict[str, Any],
    standard_number: int,
) -> str:
    """
    Build a prompt for generating a single standard from one temario unidad.

    Follows Gemini best practices: context first, clear task, explicit output format.
    """
    eje_prefix = EJE_PREFIX_MAP[eje_key]
    standard_id = f"M1-{eje_prefix}-{standard_number:02d}"
    conocimientos_path = f"conocimientos.{eje_key}.unidades[{unidad_index}]"

    habilidades_context = format_habilidades_context(habilidades)
    unidad_json = json.dumps(unidad_data, ensure_ascii=False, indent=2)
    example_json = json.dumps(EXAMPLE_STANDARD, ensure_ascii=False, indent=2)

    return f"""<role>
Eres un experto en diseño curricular de matemáticas para la PAES de Chile.
</role>

<context>
## Habilidades DEMRE

{habilidades_context}

## Unidad temática a procesar

Eje: {eje_key}
Datos:

{unidad_json}

## Ejemplo de estándar canónico

{example_json}
</context>

<task>
Genera UN estándar canónico en JSON que cubra la unidad temática. Requisitos:

1. ID exacto: "{standard_id}"
2. Eje: "{eje_key}"
3. Copiar nombre exacto en "unidad_temario"
4. "descripcion_general" rica y narrativa (mínimo 100 caracteres)
5. "subcontenidos_clave" con granularidad atómica (una intención cognitiva cada uno)
6. "ejemplos_conceptuales" descriptivos, NO ejercicios completos
7. "fuentes_temario.conocimientos_path": "{conocimientos_path}"
8. "habilidades_relacionadas": revisa TODAS las 4 habilidades y selecciona las relevantes
</task>

<rules>
1. Todo en español.
2. FIEL AL TEMARIO: no agregar contenido más allá de las descripciones originales.
3. Más explícito, no más amplio.
4. Mínimo 3 items en "incluye", "no_incluye", "subcontenidos_clave".
5. Mínimo 2 items en "ejemplos_conceptuales".
6. NO usar LaTeX; usar texto plano para notación matemática.
7. "subcontenidos_clave": cada item debe ser específico y atómico (ej: "Suma de números
   enteros con mismo signo" en vez de "Operaciones con enteros").
8. "habilidades_relacionadas": revisa exhaustivamente las 4 habilidades (resolver_problemas,
   modelar, representar, argumentar) e incluye TODAS las que sean relevantes. Para cada
   habilidad incluida, selecciona TODOS los criterios de evaluación que apliquen.
</rules>

<output_format>
Responde SOLO con el objeto JSON del estándar. Sin markdown, sin explicaciones.
</output_format>

<final_instruction>
Basándote en la unidad y habilidades del contexto, genera el estándar canónico en JSON.
Revisa cuidadosamente todas las habilidades para identificar las relevantes y sus
criterios aplicables.
</final_instruction>"""


# -----------------------------------------------------------------------------
# Per-unidad validation prompt
# -----------------------------------------------------------------------------


def build_single_standard_validation_prompt(
    standard_dict: dict[str, Any],
    unidad_data: dict[str, Any],
    habilidades: dict[str, Any],
) -> str:
    """
    Build a focused validation prompt for a single standard.

    Used immediately after generation to catch issues early.
    """
    habilidades_context = format_habilidades_context(habilidades)
    standard_json = json.dumps(standard_dict, ensure_ascii=False, indent=2)
    unidad_json = json.dumps(unidad_data, ensure_ascii=False, indent=2)

    return f"""<role>
Eres un revisor experto en estándares curriculares de matemáticas PAES.
</role>

<context>
## Habilidades DEMRE

{habilidades_context}

## Unidad original del temario

{unidad_json}

## Estándar candidato

{standard_json}
</context>

<task>
Revisa el estándar contra la unidad original usando este checklist.
</task>

<checklist>
1. FIDELIDAD: NO introduce temas fuera de las descripciones del temario.
2. COMPLETITUD: Todos los campos requeridos presentes y no vacíos.
3. COBERTURA: Cubre todas las descripciones de la unidad.
4. GRANULARIDAD: "subcontenidos_clave" tienen granularidad atómica.
5. EXCLUSIONES: "no_incluye" son razonables.
6. COHERENCIA: "titulo" y "descripcion_general" coherentes con la unidad.
</checklist>

<output_format>
JSON con esta estructura:

{{
  "is_valid": true/false,
  "issues": [
    {{
      "issue_type": "fidelity|completeness|coverage|granularity|exclusions|coherence",
      "description": "Descripción del problema",
      "severity": "error|warning"
    }}
  ],
  "corrected_standard": null o estándar corregido si hay errores
}}
</output_format>

<constraints>
- NUNCA ignores problemas de fidelidad (crítico).
- "error" = debe corregirse; "warning" = sugerencia.
- Corrección debe mantener el mismo ID.
</constraints>

<final_instruction>
Revisa el estándar contra el checklist. Reporta problemas y corrige si hay errores.
</final_instruction>"""


# -----------------------------------------------------------------------------
# Per-eje validation prompt
# -----------------------------------------------------------------------------


def build_eje_validation_prompt(
    standards: list[dict[str, Any]],
    eje_key: str,
    original_unidades: list[dict[str, Any]],
    habilidades: dict[str, Any],
) -> str:
    """
    Build a prompt for validating a batch of standards (cross-standard checks).

    Used after all standards for an eje are generated.
    """
    habilidades_context = format_habilidades_context(habilidades)
    standards_json = json.dumps(standards, ensure_ascii=False, indent=2)
    unidades_json = json.dumps(original_unidades, ensure_ascii=False, indent=2)
    eje_prefix = EJE_PREFIX_MAP[eje_key]

    return f"""<role>
Eres un revisor experto en estándares curriculares PAES.
</role>

<context>
## Habilidades DEMRE

{habilidades_context}

## Unidades originales (eje: {eje_key})

{unidades_json}

## Estándares candidatos

{standards_json}
</context>

<task>
Revisa los estándares contra el temario usando este checklist.
</task>

<checklist>
1. COBERTURA: Cada unidad está cubierta por al menos un estándar.
2. FIDELIDAD: Ningún estándar introduce temas fuera del temario.
3. COMPLETITUD: Todos los campos requeridos presentes.
4. CONSISTENCIA: IDs siguen patrón M1-{eje_prefix}-NN.
5. NO DUPLICADOS: Sin contenido duplicado entre estándares.
</checklist>

<output_format>
JSON con esta estructura:

{{
  "is_valid": true/false,
  "issues": [
    {{
      "standard_id": "M1-XXX-NN o null si general",
      "issue_type": "coverage|fidelity|completeness|consistency|duplicate",
      "description": "Descripción del problema",
      "severity": "error|warning"
    }}
  ],
  "corrected_standards": null o lista de estándares corregidos
}}
</output_format>

<constraints>
- NUNCA ignores problemas de fidelidad o cobertura.
- "error" = debe corregirse; "warning" = sugerencia.
</constraints>

<final_instruction>
Revisa los estándares contra el checklist. Reporta problemas y corrige si hay errores.
</final_instruction>"""
