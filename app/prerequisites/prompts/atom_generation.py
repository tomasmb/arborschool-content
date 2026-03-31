"""Prompt for Phase 2: prerequisite atom generation.

Generates learning atoms from prerequisite standards. Imports the same
comprehensive rules and final-instruction checklist used by the M1 atom
generation pipeline (DRY) and wraps them with prereq-specific context
(grade level, available lower-grade atoms, en_alcance_m1=false).
"""

from __future__ import annotations

import json
from typing import Any

from app.atoms.prompts.atom_final_instruction import build_final_instruction
from app.atoms.prompts.atom_guidelines import ATOM_GRANULARITY_GUIDELINES
from app.atoms.prompts.atom_rules import ATOM_GENERATION_RULES
from app.atoms.prompts.atom_schema import format_atom_schema_example
from app.models.constants import EJE_PREFIX_MAP
from app.prerequisites.constants import GRADE_LEVEL_LABELS


def _format_available_prereqs(
    atoms_below: list[dict[str, Any]],
) -> str:
    """Format atoms from lower grade levels as available prerequisites."""
    if not atoms_below:
        return "(Ninguno — este es el nivel más básico.)"
    lines: list[str] = []
    for a in atoms_below:
        lines.append(
            f"  - {a['id']}: {a['titulo']} "
            f"[{a.get('grade_level', '?')}]"
        )
    return "\n".join(lines)


def build_prereq_atom_generation_prompt(
    standard: dict[str, Any],
    grade_level: str,
    atoms_below: list[dict[str, Any]],
) -> str:
    """Build prompt for generating prerequisite atoms from one standard.

    Uses the same ATOM_GENERATION_RULES and build_final_instruction()
    as M1 generation, wrapped with prereq-specific context (grade,
    available lower-grade atoms, en_alcance_m1=false).

    Args:
        standard: Prerequisite standard dict.
        grade_level: Grade prefix (e.g. "EB5").
        atoms_below: Atoms already generated for lower grade levels,
            available as prerequisites.

    Returns:
        Complete prompt string for GPT-5.1.
    """
    grade_label = GRADE_LEVEL_LABELS.get(grade_level, grade_level)
    std_json = json.dumps(standard, ensure_ascii=False, indent=2)
    eje_key = standard.get("eje", "numeros")
    eje_prefix = EJE_PREFIX_MAP.get(eje_key, "NUM")
    std_number = standard["id"].split("-")[2]
    available_prereqs = _format_available_prereqs(atoms_below)
    schema_example = format_atom_schema_example(grade_level=grade_level)
    final_instruction = build_final_instruction()

    return f"""<role>
Eres un experto en diseño de aprendizaje granular para matemáticas de
nivel {grade_label} (sistema educativo chileno).
Tu tarea es descomponer estándares curriculares en átomos de aprendizaje.
</role>

<context>
## Estándar prerequisito a procesar

{std_json}

## Átomos de niveles anteriores disponibles como prerrequisitos

{available_prereqs}

## Guías de granularidad atómica

{ATOM_GRANULARITY_GUIDELINES}

## Ejemplo de átomo canónico

{schema_example}

## Campos (CRÍTICO — NO CONFUNDIR)

- "habilidad_principal" y "habilidades_secundarias" SOLO pueden ser:
  resolver_problemas, modelar, representar, argumentar.
- "tipo_atomico" es un campo COMPLETAMENTE DIFERENTE: concepto,
  procedimiento, representacion, argumentacion, modelizacion,
  concepto_procedimental.
- NO uses valores de "tipo_atomico" en "habilidad_principal" ni
  viceversa. Son campos independientes.
</context>

<task>
Genera una lista de átomos de aprendizaje (JSON array) que descompongan
este estándar de nivel {grade_label}. Cada átomo debe:

1. Tener exactamente UNA intención cognitiva.
2. Ser evaluable independientemente.
3. Tener ID único: A-{grade_level}-{eje_prefix}-{std_number}-MM
   (MM = 01, 02, ...).
4. Incluir "standard_ids": ["{standard['id']}"].
5. Incluir "grade_level": "{grade_level}".
6. Respetar los criterios de granularidad atómica.
7. Usar átomos de niveles anteriores como prerrequisitos cuando aplique
   (referenciándolos por su ID exacto de la lista proporcionada).
8. Tener "en_alcance_m1": false (estos son átomos prerequisito).

IMPORTANTE: Asegúrate de cubrir tanto aspectos CONCEPTUALES (qué es,
cómo se define, cómo se reconoce) como PROCEDIMENTALES (cómo se hace,
qué pasos seguir) del estándar. No te enfoques solo en procedimientos;
incluye también átomos conceptuales cuando el estándar lo requiera.

Adapta la complejidad al nivel educativo:
- EB1-EB4: lenguaje simple, ejemplos concretos y manipulativos.
- EB5-EB8, EM1-EM2: lenguaje técnico gradual, siempre claro.
</task>

<rules>
{ATOM_GENERATION_RULES}
</rules>

<output_format>
Responde SOLO con un array JSON de átomos. Sin markdown, sin explicaciones.
Cada átomo debe seguir exactamente el schema del ejemplo, con estos campos:
  id, grade_level, eje, standard_ids, habilidad_principal,
  habilidades_secundarias, tipo_atomico, titulo, descripcion,
  criterios_atomicos, ejemplos_conceptuales, prerrequisitos,
  notas_alcance, en_alcance_m1
</output_format>

<final_instruction>
{final_instruction}
</final_instruction>"""
