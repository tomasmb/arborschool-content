"""Prompt template for Phase 2 — Plan Generation.

Generates a diverse set of plan slots for an atom's question pool.
Uses GPT-5.1 with JSON response format.
"""

# Temperature: 0.0 (deterministic structured output)
# Response format: application/json

PLAN_GENERATION_PROMPT = """\
<role>
Eres un diseñador de ítems PAES M1 (Chile). Tu tarea es crear un PLAN
de generación de preguntas de opción múltiple para un átomo de aprendizaje.
NO generas las preguntas, solo el plan de especificaciones.
</role>

<context>
ÁTOMO:
- ID: {atom_id}
- Título: {atom_title}
- Descripción: {atom_description}
- Eje: {eje}
- Tipo atómico: {tipo_atomico}
- Criterios atómicos: {criterios_atomicos}

ENRIQUECIMIENTO DEL ÁTOMO:
{enrichment_section}

EJEMPLARES DISPONIBLES:
{exemplars_section}

INVENTARIO EXISTENTE: {existing_count} ítems ya generados para este átomo.
</context>

<task>
Genera un plan con exactamente {pool_size} slots. Cada slot especifica
un ítem a generar. El plan DEBE cumplir:

1. **Distribución de dificultad**: {difficulty_distribution}
2. **Diversidad de skeleton**: Cada `operation_skeleton_ast` puede aparecer
   MÁXIMO 2 veces en el plan total.
3. **Diversidad de contexto**: Varía `surface_context` entre los slots.
4. **Diversidad numérica**: Varía `numbers_profile` cuando sea posible.
5. **Anclaje a ejemplares**: Si hay ejemplares, cada slot DEBE tener
   `target_exemplar_id` y `distance_level`.
</task>

<rules>
- Cada slot DEBE tener: component_tag, difficulty_level, operation_skeleton_ast,
  surface_context, numbers_profile.
- operation_skeleton_ast es una representación canónica de la operación
  matemática (ej: "(= (+ (* a x) b) c) -> solve x").
- surface_context DEBE ser uno de: pure_math, real_world_money, real_world_time,
  real_world_measurement, real_world_science, geometric, statistical, tabular.
- numbers_profile DEBE ser uno de: small_integers, large_integers, fractions,
  decimals, mixed, negative_numbers.
- distance_level (si hay ejemplares): near, medium, far.
- SOLO responde en español cuando describes contextos.
</rules>

<output_format>
Responde con JSON puro (sin bloques markdown):
{{
  "plan": [
    {{
      "slot_index": 0,
      "component_tag": "EJE.CONCEPTO",
      "difficulty_level": "easy",
      "operation_skeleton_ast": "(operación canónica)",
      "surface_context": "pure_math",
      "numbers_profile": "small_integers",
      "target_exemplar_id": "Q1 o null",
      "distance_level": "medium o null"
    }}
  ]
}}
</output_format>

<final_instruction>
Basándote en toda la información anterior, genera el plan de {pool_size}
slots para el átomo {atom_id}. Responde SOLO con el JSON.
</final_instruction>
"""


def build_enrichment_section(enrichment: object | None) -> str:
    """Format enrichment data for the planning prompt.

    Args:
        enrichment: AtomEnrichment object or None.

    Returns:
        Formatted string with enrichment details.
    """
    if enrichment is None:
        return "No hay enriquecimiento disponible. Usa los datos del átomo."

    # AtomEnrichment is a Pydantic model, so use model_dump
    data = enrichment.model_dump()  # type: ignore[union-attr]
    lines = []

    rubric = data.get("difficulty_rubric", {})
    if rubric:
        lines.append("Rúbrica de dificultad:")
        for level, criteria in rubric.items():
            lines.append(f"  {level}: {', '.join(criteria)}")

    scope = data.get("scope_guardrails", {})
    if scope.get("in_scope"):
        lines.append(f"En alcance: {', '.join(scope['in_scope'])}")
    if scope.get("out_of_scope"):
        lines.append(f"Fuera de alcance: {', '.join(scope['out_of_scope'])}")

    errors = data.get("error_families", [])
    if errors:
        names = [e.get("name", "") for e in errors]
        lines.append(f"Familias de error: {', '.join(names)}")

    profiles = data.get("numbers_profiles", [])
    if profiles:
        lines.append(f"Perfiles numéricos: {', '.join(profiles)}")

    return "\n".join(lines) if lines else "Enriquecimiento vacío."


def build_difficulty_distribution(pool_size: int) -> str:
    """Build the expected difficulty distribution string.

    Default: equal split across easy/medium/hard.

    Args:
        pool_size: Total number of plan slots.

    Returns:
        Human-readable distribution string.
    """
    per_level = pool_size // 3
    remainder = pool_size % 3
    easy = per_level + (1 if remainder > 0 else 0)
    medium = per_level + (1 if remainder > 1 else 0)
    hard = per_level
    return f"{easy} easy, {medium} medium, {hard} hard"
