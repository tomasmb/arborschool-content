"""Atom validation module.

Provides functionality to validate generated atoms against standards using
external LLM evaluators (Gemini, OpenAI) or local checks.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.llm_clients import GeminiService
from app.standards.helpers import parse_json_response

logger = logging.getLogger(__name__)


def build_validation_prompt(standard: dict[str, Any], atoms: list[dict[str, Any]]) -> str:
    """Build the validation prompt for atom quality evaluation.

    Args:
        standard: The standard dictionary
        atoms: List of atom dictionaries to validate

    Returns:
        Complete validation prompt as string
    """
    prompt = f"""<educational_context>
Este es contenido educativo matemático puro para evaluación curricular. Todos los términos
("cubo", "factor", "producto", "raíz", etc.) se refieren exclusivamente a conceptos matemáticos
estándar de álgebra y aritmética. No hay contenido inapropiado, solo matemáticas educativas.
</educational_context>

<role>
Eres un experto evaluador de diseño instruccional y granularidad de aprendizaje.
Tu tarea es evaluar la calidad de átomos de aprendizaje generados a partir de un estándar curricular.
</role>

<context>
## Estándar Canónico

{json.dumps(standard, indent=2, ensure_ascii=False)}

## Átomos Generados

{json.dumps(atoms, indent=2, ensure_ascii=False)}
</context>

<task>
Evalúa la calidad de los átomos generados considerando:

1. **Fidelidad**: ¿Los átomos cubren completamente el estándar sin agregar contenido fuera de alcance?
2. **Granularidad**: ¿Cada átomo cumple los 6 criterios de granularidad atómica?
3. **Completitud y Cobertura del Estándar (CRÍTICO)**:
   - Verifica punto por punto que CADA elemento del estándar esté representado en los átomos:
     * Revisa cada ítem en "incluye" del estándar y verifica que haya átomos que lo cubran
     * Revisa cada "subcontenidos_clave" y verifica que esté representado
     * Revisa las "habilidades_relacionadas" y verifica que se reflejen en los átomos
     * Verifica que los "ejemplos_conceptuales" del estándar puedan ser abordados con los átomos generados
   - Identifica específicamente qué elementos del estándar NO están cubiertos por ningún átomo
   - Verifica que no haya contenido en los átomos que esté explícitamente en "no_incluye" del estándar
4. **Calidad del contenido**: ¿Las descripciones, criterios y ejemplos son claros y apropiados?
5. **Prerrequisitos**: ¿Los prerrequisitos están correctamente identificados y son exhaustivos en átomos integradores?
6. **Cobertura**: ¿No hay duplicaciones ni áreas faltantes?
</task>

<rules>
1. Evalúa cada átomo individualmente y luego el conjunto completo.
2. Identifica problemas específicos con ejemplos concretos.
3. Proporciona recomendaciones accionables.
4. Usa el formato JSON estructurado especificado.
</rules>

<output_format>
Responde SOLO con un objeto JSON válido con esta estructura:

{{
  "evaluation_summary": {{
    "total_atoms": <número>,
    "atoms_passing_all_checks": <número>,
    "atoms_with_issues": <número>,
    "overall_quality": "excellent" | "good" | "needs_improvement",
    "coverage_assessment": "complete" | "incomplete",
    "granularity_assessment": "appropriate" | "too_coarse" | "too_fine"
  }},
  "atoms_evaluation": [
    {{
      "atom_id": "<id>",
      "overall_score": "excellent" | "good" | "needs_improvement",
      "fidelity": {{
        "score": "pass" | "warning" | "fail",
        "issues": ["<problema 1>", "<problema 2>"]
      }},
      "granularity": {{
        "score": "pass" | "warning" | "fail",
        "issues": ["<problema 1>", "<problema 2>"],
        "checks": {{
          "single_cognitive_intention": true | false,
          "reasonable_working_memory": true | false,
          "prerequisite_independence": true | false,
          "assessment_independence": true | false,
          "generalization_boundary": true | false,
          "integrator_validity": true | false
        }}
      }},
      "completeness": {{
        "score": "pass" | "warning" | "fail",
        "issues": ["<problema 1>", "<problema 2>"]
      }},
      "content_quality": {{
        "score": "pass" | "warning" | "fail",
        "issues": ["<problema 1>", "<problema 2>"]
      }},
      "prerequisites": {{
        "score": "pass" | "warning" | "fail",
        "issues": ["<problema 1>", "<problema 2>"]
      }},
      "recommendations": ["<recomendación 1>", "<recomendación 2>"]
    }}
  ],
  "coverage_analysis": {{
    "standards_covered": ["<standard_id>"],
    "coverage_completeness": "complete" | "incomplete",
    "missing_areas": ["<área faltante 1>", "<área faltante 2>"],
    "duplication_issues": ["<problema 1>", "<problema 2>"],
    "conceptual_coverage": "present" | "missing",
    "procedural_coverage": "present" | "missing",
    "standard_items_coverage": {{
      "includes_covered": {{
        "<item del campo 'incluye'>": "covered" | "missing" | "partially_covered",
        "<item del campo 'incluye'>": "covered" | "missing" | "partially_covered"
      }},
      "subcontenidos_covered": {{
        "<subcontenido clave>": "covered" | "missing" | "partially_covered",
        "<subcontenido clave>": "covered" | "missing" | "partially_covered"
      }},
      "habilidades_covered": {{
        "<habilidad_id>": "covered" | "missing" | "partially_covered",
        "<habilidad_id>": "covered" | "missing" | "partially_covered"
      }}
    }}
  }},
  "global_recommendations": [
    "<recomendación global 1>",
    "<recomendación global 2>"
  ]
}}
</output_format>

<final_instruction>
Basándote en el estándar y los átomos generados, realiza una evaluación exhaustiva.

**PASO 1 - Verificación de Cobertura Completa del Estándar (HACER PRIMERO)**:
1. Toma cada elemento del campo "incluye" del estándar y verifica que haya al menos un átomo que lo cubra
2. Toma cada "subcontenidos_clave" y verifica que esté representado en los átomos
3. Toma cada "habilidad_id" en "habilidades_relacionadas" y verifica que haya átomos que la desarrollen
4. Identifica específicamente qué elementos del estándar NO están cubiertos (si los hay)
5. Verifica que ningún átomo incluya contenido explícitamente mencionado en "no_incluye"

**PASO 2 - Evaluación de Calidad Individual y Global**:
Identifica problemas específicos, especialmente relacionados con:
- Separación de procedimientos con estrategias cognitivas diferentes
- Separación de versiones simples vs complejas del mismo procedimiento
- Prerrequisitos exhaustivos en átomos integradores (tanto conceptuales como procedimentales)
- Uso de métodos estándar preferentes (evitar métodos alternativos inusuales o confusos)
- Separación de representaciones diferentes que requieren estrategias cognitivas distintas
- Consistencia entre habilidad_principal y criterios_atomicos
- Separación correcta de variantes con algoritmos fundamentalmente distintos (ej: decimal finito vs periódico)

**VERIFICACIÓN CRÍTICA - MÉTODOS EQUIVALENTES**:
Antes de marcar como problema que un átomo menciona "múltiples métodos", DEBES
verificar si son realmente métodos distintos o el mismo método explicado de
forma diferente:
- Si dos métodos mencionados son matemáticamente equivalentes y requieren la
  misma estrategia cognitiva, NO es un problema
- Ejemplos de métodos equivalentes (NO son problemas):
  * "Multiplicar por el inverso multiplicativo" vs "Multiplicación cruzada"
    (división de fracciones) → Son el mismo método
  * "Sumar opuestos" vs "Restar" (en enteros) → Pueden ser equivalentes según
    el contexto
- Solo marca como problema si los métodos requieren algoritmos o estrategias
  cognitivas fundamentalmente distintos
- Si tienes duda, asume que son equivalentes y NO marques como problema

**VERIFICACIÓN CRÍTICA - TRANSITIVIDAD DE PRERREQUISITOS**:
Los prerrequisitos son TRANSITIVOS. Si A es prerrequisito de B, y B es
prerrequisito de C, entonces C solo necesita listar B como prerrequisito,
NO necesita listar A explícitamente.
- **REGLA DE ORO**: NO marques como problema si un átomo no lista un
  prerrequisito transitivo
- Ejemplo: Si A-01 → A-04 → A-17, entonces A-17 solo necesita listar A-04,
  NO A-01
- Solo marca como problema si falta un prerrequisito DIRECTO (no transitivo)
- Si un átomo requiere operar con enteros pero ya tiene un prerrequisito que
  a su vez requiere enteros, NO es un problema
- Si tienes duda sobre si un prerrequisito es directo o transitivo, asume que
  es transitivo y NO marques como problema

**PRINCIPIOS PEDAGÓGICOS GENERALES - NO MARCAR COMO PROBLEMAS**:
Los siguientes casos representan decisiones pedagógicas válidas que pueden
aplicarse a cualquier conjunto de átomos. NO los marques como problemas:

1. **Limitaciones intencionales de procedimientos**:
   - Cuando los procedimientos están limitados a casos específicos (ej: ejes
     coordenados, origen, casos simples) pero los conceptos correspondientes
     cubren el caso general, esto es una decisión pedagógica válida: conceptos
     generales, procedimientos específicos para el nivel educativo.
   - **NO marques como problema** si un átomo procedimental está limitado a
     casos específicos mientras el átomo conceptual correspondiente cubre el
     caso general.

2. **Estrategias integradas válidas**:
   - Cuando un átomo integra múltiples estrategias o niveles de complejidad
     que son conceptualmente relacionados, parte de un mismo procedimiento
     general, y pueden evaluarse en el mismo contexto, esto es una decisión
     pedagógica válida.
   - **NO marques como problema** si un átomo integra múltiples estrategias
     válidas para el mismo objetivo cognitivo, siempre que puedan evaluarse
     coherentemente en el mismo contexto.

3. **Métodos equivalentes**:
   - Si un átomo menciona métodos que son matemáticamente equivalentes
     (ej: "multiplicación cruzada" vs "inverso multiplicativo" en división de
     fracciones), NO marques como problema. Los métodos equivalentes son
     válidos y la elección puede ser pedagógica.

**IMPORTANTE**: Si encuentras elementos del estándar que NO están cubiertos
por ningún átomo, esto es un problema crítico que debe reportarse en
"missing_areas" y debe afectar el "coverage_completeness" a "incomplete".
</final_instruction>
"""
    return prompt


def validate_atoms_with_gemini(
    gemini: GeminiService,
    standard: dict[str, Any],
    atoms: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate atoms using Gemini.

    Args:
        gemini: Gemini service instance
        standard: The standard dictionary
        atoms: List of atom dictionaries to validate

    Returns:
        Validation result as dictionary
    """
    prompt = build_validation_prompt(standard, atoms)

    logger.info("Validating atoms with Gemini...")
    # Try with high thinking level first, fallback to medium if safety filters trigger
    try:
        raw_response = gemini.generate_text(
            prompt,
            thinking_level="high",
            response_mime_type="application/json",
            temperature=0.0,
            timeout=1200,  # 20 minutes
        )
    except ValueError as e:
        if "Finish reason: 2" in str(e) or "safety filters" in str(e).lower():
            logger.warning("High thinking level blocked by safety filters, retrying with medium...")
            raw_response = gemini.generate_text(
                prompt,
                thinking_level="medium",  # Try with less restrictive thinking level
                response_mime_type="application/json",
                temperature=0.0,
                timeout=1200,
            )
        else:
            raise

    # Parse JSON response
    result = parse_json_response(raw_response)

    if not isinstance(result, dict):
        raise ValueError(f"Expected dict, got {type(result)}")

    return result


def validate_atoms_from_files(
    gemini: GeminiService,
    standard_path: str | Path,
    atoms_path: str | Path,
    standard_id: str | None = None,
) -> dict[str, Any]:
    """Validate atoms from JSON files.

    Args:
        gemini: Gemini service instance
        standard_path: Path to standards JSON file
        atoms_path: Path to atoms JSON file
        standard_id: Optional standard ID to filter (if standards file contains multiple)

    Returns:
        Validation result as dictionary
    """
    # Load standard
    with open(standard_path, "r", encoding="utf-8") as f:
        standards_data = json.load(f)

    if isinstance(standards_data, list):
        if standard_id:
            standard = next((s for s in standards_data if s.get("id") == standard_id), None)
            if not standard:
                raise ValueError(f"Standard {standard_id} not found in {standard_path}")
        else:
            if len(standards_data) != 1:
                raise ValueError(f"Multiple standards in file, must specify standard_id. Found: {[s.get('id') for s in standards_data]}")
            standard = standards_data[0]
    else:
        if "standards" in standards_data:
            standards_list = standards_data["standards"]
            if standard_id:
                standard = next((s for s in standards_list if s.get("id") == standard_id), None)
                if not standard:
                    raise ValueError(f"Standard {standard_id} not found in {standard_path}")
            else:
                if len(standards_list) != 1:
                    raise ValueError(f"Multiple standards in file, must specify standard_id. Found: {[s.get('id') for s in standards_list]}")
                standard = standards_list[0]
        else:
            standard = standards_data

    # Load atoms
    with open(atoms_path, "r", encoding="utf-8") as f:
        atoms = json.load(f)

    if not isinstance(atoms, list):
        raise ValueError(f"Expected list of atoms, got {type(atoms)}")

    return validate_atoms_with_gemini(gemini, standard, atoms)
