"""Prompt for Phase 2: prerequisite atom generation.

Generates learning atoms from prerequisite standards. Reuses the same
granularity guidelines as M1 atom generation and includes the critical
generation rules that ensure high-quality, non-overlapping atoms.
"""

from __future__ import annotations

import json
from typing import Any

from app.atoms.prompts.atom_guidelines import ATOM_GRANULARITY_GUIDELINES
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
    schema_example = format_atom_schema_example()

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

## Ejemplo de átomo canónico (adaptar IDs al nivel {grade_level})

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

Adapta la complejidad al nivel educativo:
- EB1-EB4: lenguaje simple, ejemplos concretos y manipulativos.
- EB5-EB8, EM1-EM2: lenguaje técnico gradual, siempre claro.
</task>

<rules>
1. Todo en español.
2. FIEL AL ESTÁNDAR: no agregar contenido fuera de su alcance.
   Antes de finalizar cada átomo, verifica que descripcion,
   criterios_atomicos y notas_alcance estén dentro de "incluye" y
   "no_incluye" del estándar.
3. Granularidad: cada átomo = una sola intención cognitiva.
4. Mínimo 1 criterio_atomico por átomo.
5. 1-4 ejemplos_conceptuales (NO ejercicios completos).
6. NO usar LaTeX; usar texto plano para notación matemática.
7. "prerrequisitos": solo IDs de átomos de niveles anteriores o del
   mismo estándar. Los prerrequisitos son TRANSITIVOS — si A→B→C,
   C solo necesita B, no A.
8. "notas_alcance": acotar complejidad con rangos, límites y
   exclusiones apropiados para {grade_label}.
9. INDEPENDENCIA DE EVALUACIÓN (más importante): si dos conceptos
   o procedimientos pueden evaluarse por separado, son átomos
   separados — incluso si están relacionados o comparten reglas.
10. Incluir átomos CONCEPTUALES y PROCEDIMENTALES según requiera el
    estándar.
11. CONSISTENCIA habilidad_principal / criterios_atomicos: la
    habilidad declarada DEBE reflejarse en los criterios. Si los
    criterios son puramente procedimentales, la habilidad no debería
    ser "argumentar". Si son conceptuales, no debería ser
    "resolver_problemas".
12. CORRESPONDENCIA CON subcontenidos_clave: cada subcontenido del
    estándar debe tener al menos un átomo correspondiente. Antes de
    finalizar, verifica que no haya subcontenidos sin cubrir.
13. Si el título contiene "y" conectando dos conceptos evaluables por
    separado, divídelos en átomos separados.
14. Procedimientos con versiones simple y compleja deben ser átomos
    separados si requieren diferente carga cognitiva.
15. Átomos integradores deben listar TODOS sus prerrequisitos
    exhaustivamente (conceptuales y procedimentales).
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
Basándote en el estándar anterior, genera los átomos. ANTES de
finalizar, aplica este checklist a cada átomo:

1. ¿Una sola intención cognitiva? Si no, dividir.
2. ¿Evaluable independientemente? Si no, dividir.
3. ¿≤4 piezas novedosas de información? Si no, dividir.
4. ¿Título con "y" entre conceptos separables? Si sí, dividir.
5. ¿Múltiples algoritmos distintos? Si sí, elegir uno preferente o
   dividir según estrategia cognitiva.
6. ¿habilidad_principal se refleja en criterios_atomicos? Si no,
   ajustar.
7. ¿notas_alcance acotan complejidad? Si no, agregar.
8. ¿Cada subcontenido_clave del estándar está cubierto? Si no,
   agregar átomos faltantes.
9. ¿Prerrequisitos son directos (no transitivos)? Verificar.
10. ¿Átomos integradores tienen prerrequisitos exhaustivos?
</final_instruction>"""
