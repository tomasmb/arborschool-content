"""Prompt for Phase 4: combined graph validation.

Validates prerequisite atoms for quality, and the combined prerequisite +
M1 graph for structural integrity.
"""

from __future__ import annotations

import json
from typing import Any


def build_prereq_validation_prompt(
    standard: dict[str, Any],
    atoms: list[dict[str, Any]],
) -> str:
    """Build validation prompt for prerequisite atoms against a standard.

    Mirrors the M1 validation prompt structure but adapted for prereqs.

    Args:
        standard: Prerequisite standard dict.
        atoms: Prerequisite atom dicts for this standard.

    Returns:
        Complete prompt string for GPT-5.1.
    """
    return f"""<educational_context>
Contenido educativo matemático para nivel escolar chileno. Todos los
términos son conceptos matemáticos estándar.
</educational_context>

<role>
Experto evaluador de diseño instruccional y granularidad de aprendizaje
para contenido matemático de nivel escolar.
</role>

<context>
## Estándar Prerequisito

{json.dumps(standard, indent=2, ensure_ascii=False)}

## Átomos Generados

{json.dumps(atoms, indent=2, ensure_ascii=False)}
</context>

<task>
Evalúa los átomos generados en estas dimensiones:

1. **Fidelidad**: ¿Cubren el estándar sin agregar contenido de
   "no_incluye"?
2. **Granularidad**: ¿Cada átomo cumple los 6 criterios de
   granularidad atómica (una intención cognitiva, carga razonable,
   independencia de prerrequisitos, independencia de evaluación,
   límite de generalización, validez de integrador)?
3. **Cobertura del estándar**: ¿Cada "subcontenido_clave" y cada
   ítem de "incluye" está representado por al menos un átomo?
4. **Calidad del contenido**: ¿Descripciones, criterios y ejemplos
   son claros y apropiados para el nivel educativo (grade_level)?
5. **Prerrequisitos**: ¿Correctamente identificados? ¿Exhaustivos en
   átomos integradores?
6. **Consistencia**: ¿habilidad_principal se refleja en los
   criterios_atomicos de cada átomo?
7. **Duplicaciones**: ¿Hay solapamientos significativos entre átomos?
</task>

<constraints>
NO marques como problema estos casos:
1. Campo "en_alcance_m1": Ignorar — es decisión de alcance.
2. Prerrequisitos transitivos: Si A→B→C, C solo lista B. Solo marca
   prerrequisitos DIRECTOS faltantes.
3. Estrategias integradas del mismo procedimiento: es válido.
</constraints>

<output_format>
Responde SOLO con un objeto JSON:

{{
  "evaluation_summary": {{
    "total_atoms": 0,
    "atoms_passing_all_checks": 0,
    "atoms_with_issues": 0,
    "overall_quality": "excellent" | "good" | "needs_improvement",
    "coverage_assessment": "complete" | "incomplete",
    "granularity_assessment": "appropriate" | "too_coarse" | "too_fine"
  }},
  "atoms_evaluation": [
    {{
      "atom_id": "<id>",
      "overall_score": "excellent" | "good" | "needs_improvement",
      "fidelity": {{"score": "pass" | "warning" | "fail", "issues": []}},
      "granularity": {{
        "score": "pass" | "warning" | "fail",
        "issues": [],
        "checks": {{
          "single_cognitive_intention": true,
          "reasonable_working_memory": true,
          "prerequisite_independence": true,
          "assessment_independence": true
        }}
      }},
      "content_quality": {{"score": "pass" | "warning" | "fail", "issues": []}},
      "prerequisites": {{"score": "pass" | "warning" | "fail", "issues": []}},
      "recommendations": []
    }}
  ],
  "coverage_analysis": {{
    "coverage_completeness": "complete" | "incomplete",
    "missing_areas": [],
    "duplication_issues": [],
    "standard_items_coverage": {{
      "subcontenidos_covered": {{
        "<subcontenido>": "covered" | "missing" | "partially_covered"
      }}
    }}
  }},
  "global_recommendations": []
}}
</output_format>

<rules>
1. Evalúa considerando el nivel educativo del estándar (grade_level).
2. Prerrequisitos transitivos no son un problema.
3. Sé estricto con granularidad: un átomo = una intención cognitiva.
4. Sé específico en issues y recommendations.
5. Verifica consistencia habilidad_principal vs criterios_atomicos.
6. Si un subcontenido_clave NO está cubierto, repórtalo en
   "missing_areas" y marca "coverage_completeness" como "incomplete".
</rules>

<final_instruction>
Evalúa siguiendo estos pasos:

**Paso 1 — Cobertura** (primero): Toma cada subcontenido_clave y cada
ítem de "incluye". Verifica que al menos un átomo lo cubra. Reporta
faltantes en "missing_areas".

**Paso 2 — Evaluación individual**: Evalúa cada átomo en fidelidad,
granularidad, calidad, prerrequisitos. Respeta las restricciones.
</final_instruction>"""
