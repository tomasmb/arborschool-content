"""Atom validation module.

Provides functionality to validate generated atoms against standards using
external LLM evaluators (Gemini, OpenAI) or local checks.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.llm_clients import GeminiService, OpenAIClient
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
Contenido educativo matemático puro. Todos los términos ("cubo", "factor",
"producto", "raíz", etc.) son conceptos matemáticos estándar.
</educational_context>

<role>
Experto evaluador de diseño instruccional y granularidad de aprendizaje.
</role>

<context>
## Estándar Canónico

{json.dumps(standard, indent=2, ensure_ascii=False)}

## Átomos Generados

{json.dumps(atoms, indent=2, ensure_ascii=False)}
</context>

<task>
Evalúa los átomos generados en estas dimensiones:

1. **Fidelidad**: ¿Cubren el estándar sin agregar contenido de "no_incluye"?
2. **Granularidad**: ¿Cada átomo cumple los 6 criterios de granularidad atómica?
3. **Cobertura del estándar**: ¿Cada ítem de "incluye", cada
   "subcontenido_clave" y cada "habilidad_relacionada" está representado?
4. **Calidad del contenido**: ¿Descripciones, criterios y ejemplos son claros?
5. **Prerrequisitos**: ¿Correctamente identificados? ¿Exhaustivos en
   átomos integradores?
6. **Duplicaciones**: ¿Hay solapamientos significativos entre átomos?
</task>

<rules>
1. Evalúa cada átomo individualmente y luego el conjunto completo.
2. Identifica problemas específicos con ejemplos concretos.
3. Proporciona recomendaciones accionables.
4. Verifica separación correcta de: procedimientos con estrategias cognitivas
   distintas, versiones simples vs complejas, representaciones diferentes, y
   variantes con algoritmos fundamentalmente distintos.
5. Verifica consistencia entre habilidad_principal y criterios_atomicos.
6. Si un elemento del estándar NO está cubierto por ningún átomo, repórtalo
   en "missing_areas" y marca "coverage_completeness" como "incomplete".
</rules>

<constraints>
NO marques como problema ninguno de estos casos:

1. **Campo `en_alcance_m1`**: Ignorar completamente. Es una decisión de
   alcance de prueba, no de calidad. No mencionarlo en issues ni
   recomendaciones.
2. **Métodos matemáticamente equivalentes**: Si dos métodos en un átomo
   requieren la misma estrategia cognitiva (ej: "inverso multiplicativo" vs
   "multiplicación cruzada"), no es un problema. Solo marca si los algoritmos
   son fundamentalmente distintos. Ante la duda, asume equivalencia.
3. **Prerrequisitos transitivos**: Si A→B→C, entonces C solo necesita listar
   B, no A. Solo marca prerrequisitos DIRECTOS faltantes. Ante la duda,
   asume transitividad.
4. **Procedimientos limitados a casos específicos**: Cuando un átomo
   procedimental cubre solo casos simples (ej: ejes coordenados, origen)
   pero el átomo conceptual correspondiente cubre el caso general, es una
   decisión pedagógica válida.
5. **Estrategias integradas**: Cuando un átomo combina estrategias
   conceptualmente relacionadas, del mismo procedimiento general, evaluables
   en el mismo contexto, es válido.
</constraints>

<output_format>
Responde SOLO con un objeto JSON válido:

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
        "issues": []
      }},
      "granularity": {{
        "score": "pass" | "warning" | "fail",
        "issues": [],
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
        "issues": []
      }},
      "content_quality": {{
        "score": "pass" | "warning" | "fail",
        "issues": []
      }},
      "prerequisites": {{
        "score": "pass" | "warning" | "fail",
        "issues": []
      }},
      "recommendations": []
    }}
  ],
  "coverage_analysis": {{
    "standards_covered": [],
    "coverage_completeness": "complete" | "incomplete",
    "missing_areas": [],
    "duplication_issues": [],
    "conceptual_coverage": "present" | "missing",
    "procedural_coverage": "present" | "missing",
    "standard_items_coverage": {{
      "includes_covered": {{
        "<item de 'incluye'>": "covered" | "missing" | "partially_covered"
      }},
      "subcontenidos_covered": {{
        "<subcontenido>": "covered" | "missing" | "partially_covered"
      }},
      "habilidades_covered": {{
        "<habilidad_id>": "covered" | "missing" | "partially_covered"
      }}
    }}
  }},
  "global_recommendations": []
}}
</output_format>

<final_instruction>
Basándote en el estándar y los átomos anteriores, evalúa siguiendo estos pasos:

**Paso 1 — Cobertura del estándar (hacer primero)**:
Toma cada ítem de "incluye", cada "subcontenido_clave" y cada "habilidad_id"
del estándar. Verifica que haya al menos un átomo que lo cubra. Reporta
elementos no cubiertos en "missing_areas".

**Paso 2 — Evaluación individual y global**:
Evalúa cada átomo en las 5 dimensiones (fidelidad, granularidad, completitud,
calidad, prerrequisitos). Respeta las restricciones de `<constraints>`.
</final_instruction>
"""
    return prompt


# Reasoning effort for atom validation (complex multi-criteria evaluation).
_ATOM_VALIDATION_REASONING = "medium"


def validate_atoms_with_llm(
    client: OpenAIClient | GeminiService,
    standard: dict[str, Any],
    atoms: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate atoms using an LLM client.

    Args:
        client: OpenAIClient (GPT-5.1) or GeminiService instance.
        standard: The standard dictionary.
        atoms: List of atom dictionaries to validate.

    Returns:
        Validation result as dictionary.

    Raises:
        ValueError: If the LLM returns an empty or non-dict response.
    """
    prompt = build_validation_prompt(standard, atoms)

    logger.info(
        "Validating atoms with %s...",
        type(client).__name__,
    )

    # OpenAIClient supports reasoning_effort; GeminiService ignores it.
    # No max_tokens cap — the client lets the API use its model default.
    generate_kwargs: dict[str, Any] = {
        "response_mime_type": "application/json",
    }
    if isinstance(client, OpenAIClient):
        generate_kwargs["reasoning_effort"] = _ATOM_VALIDATION_REASONING

    raw_response = client.generate_text(prompt, **generate_kwargs)

    # Guard against empty responses (e.g. model returned nothing)
    if not raw_response or not raw_response.strip():
        raise ValueError(
            "LLM returned an empty response. Check API key, "
            "model availability, or try again."
        )

    # Parse JSON response
    result = parse_json_response(raw_response)

    if not isinstance(result, dict):
        raise ValueError(f"Expected dict, got {type(result)}")

    return result


# Backward-compat alias
validate_atoms_with_gemini = validate_atoms_with_llm


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
