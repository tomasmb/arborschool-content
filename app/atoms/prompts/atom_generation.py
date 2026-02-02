"""Atom generation prompt builder.

Builds prompts for generating learning atoms from curriculum standards.
Follows Gemini best practices: context first, clear task, explicit output format.
"""

from __future__ import annotations

import json
from typing import Any

from app.models.constants import EJE_PREFIX_MAP
from app.utils.prompt_helpers import format_habilidades_context

from .atom_final_instruction import build_final_instruction
from .atom_guidelines import ATOM_GRANULARITY_GUIDELINES
from .atom_rules import ATOM_GENERATION_RULES
from .atom_schema import format_atom_schema_example


def build_atom_generation_prompt(
    standard: dict[str, Any],
    habilidades: dict[str, Any],
    atom_counter: int,
) -> str:
    """
    Build a prompt for generating atoms from a single standard.

    Follows Gemini best practices: context first, clear task, explicit output format.

    Args:
        standard: The curriculum standard to decompose into atoms
        habilidades: Dictionary of curriculum skills/abilities
        atom_counter: Counter for generating unique atom IDs

    Returns:
        Complete prompt string for the LLM
    """
    standard_id = standard["id"]
    eje_key = standard["eje"]
    eje_prefix = EJE_PREFIX_MAP[eje_key]
    standard_number = standard_id.split("-")[2]

    habilidades_context = format_habilidades_context(habilidades)
    standard_json = json.dumps(standard, ensure_ascii=False, indent=2)
    atom_schema_example = format_atom_schema_example()
    final_instruction = build_final_instruction()

    return f"""<role>
Eres un experto en diseño de aprendizaje granular.
Tu tarea es descomponer estándares curriculares en átomos de aprendizaje atómicos.
</role>

<context>
## Habilidades del currículo

{habilidades_context}

## Estándar canónico a procesar

{standard_json}

## Guías de granularidad atómica

{ATOM_GRANULARITY_GUIDELINES}

## Ejemplo de átomo canónico

{atom_schema_example}

**IMPORTANTE sobre campos (CRÍTICO - NO CONFUNDIR):**
- "habilidad_principal" y "habilidades_secundarias" SOLO pueden contener
  habilidades válidas del contexto proporcionado (revisa la sección "Habilidades
  del currículo" en el contexto). Estas habilidades son las que aparecen en el
  contexto de habilidades proporcionado, no valores de "tipo_atomico".
- "tipo_atomico" es un campo COMPLETAMENTE DIFERENTE y puede ser:
  concepto, procedimiento, representacion, argumentacion, modelizacion, concepto_procedimental
- **CRÍTICO**: "tipo_atomico" NO es lo mismo que "habilidad_principal".
  - "tipo_atomico" describe el TIPO de contenido del átomo (concepto, procedimiento, etc.)
  - "habilidad_principal" describe la HABILIDAD del currículo que el átomo desarrolla
  - NO uses valores de "tipo_atomico" (como "procedimiento", "concepto", "representacion",
    "argumentacion", "modelizacion") en "habilidad_principal" o "habilidades_secundarias"
  - NO uses valores de "habilidad_principal" (las habilidades del contexto) en "tipo_atomico"
- Son campos completamente independientes y con propósitos diferentes.
</context>

<task>
Genera una lista de átomos de aprendizaje (JSON array) que descompongan este estándar.
Cada átomo debe:

1. Tener exactamente UNA intención cognitiva
2. Ser evaluable independientemente
3. Estar vinculado a una habilidad principal (y opcionalmente secundarias)
4. Tener un ID único: A-M1-{eje_prefix}-{standard_number}-MM (MM = contador 01, 02, ...)
5. Incluir "standard_ids": ["{standard_id}"]
6. Respetar los criterios de granularidad atómica

IMPORTANTE: Asegúrate de cubrir tanto aspectos CONCEPTUALES (qué es, cómo se
define, cómo se reconoce) como PROCEDIMENTALES (cómo se hace, qué pasos seguir)
del estándar. No te enfoques solo en procedimientos; incluye también átomos
conceptuales cuando el estándar lo requiera.
</task>

<rules>
{ATOM_GENERATION_RULES}
</rules>

<output_format>
Responde SOLO con un array JSON de átomos. Sin markdown, sin explicaciones.
Cada átomo debe seguir exactamente el schema del ejemplo.
</output_format>

<final_instruction>
{final_instruction}
</final_instruction>"""
