"""Prompt template for Phase 1 — Atom Enrichment.

Generates scope guardrails, difficulty rubric, and pedagogical guidance
for an atom. Uses GPT-5.1 with JSON response format.

Format placeholders:
- {image_type_catalog}: detailed catalog of available image types
- {not_images_description}: table prohibition text
Both injected by the enricher from image_types.py.
"""

# Temperature: 0.0 (deterministic structured output)
# Response format: application/json

ATOM_ENRICHMENT_PROMPT = """\
<role>
Eres un experto en diseño curricular para la prueba PAES M1 (Chile).
Tu tarea es enriquecer un átomo de aprendizaje con metadatos pedagógicos
que guiarán la generación de preguntas de opción múltiple.
</role>

<context>
ÁTOMO:
- ID: {atom_id}
- Título: {atom_title}
- Descripción: {atom_description}
- Eje: {eje}
- Tipo atómico: {tipo_atomico}
- Criterios atómicos: {criterios_atomicos}
- Ejemplos conceptuales: {ejemplos_conceptuales}
- Notas de alcance: {notas_alcance}
- Estándares asociados: {standard_ids}

EJEMPLARES DISPONIBLES (preguntas PAES reales taggeadas a este átomo):
{exemplars_section}
</context>

<task>
Genera un objeto de enriquecimiento para este átomo con los siguientes campos:

1. **scope_guardrails**: Qué está dentro y fuera del alcance de este átomo,
   prerrequisitos necesarios, y trampas comunes.
2. **difficulty_rubric**: Para cada nivel (easy, medium, hard), describe
   qué características hacen que un ítem sea de ese nivel DENTRO de este átomo.
3. **ambiguity_avoid**: Patrones de formulación o formato que deben evitarse
   para no crear ambigüedad.
4. **error_families**: Familias de errores comunes que los estudiantes cometen
   en este átomo (nombre, descripción, cómo abordar).
5. **future_targets**: Qué competencias futuras habilita dominar este átomo.
6. **representation_variants**: Tipos de representación relevantes
   (gráfica, tabular, simbólica, verbal, etc.).
7. **numbers_profiles**: Perfiles numéricos apropiados para los ítems
   (small_integers, fractions, mixed, decimals, etc.).
8. **required_image_types**: Tipos de imagen IMPRESCINDIBLES para evaluar
   este átomo. Devuelve [] salvo que sea IMPOSIBLE crear preguntas válidas
   sin contenido visual. Usa SOLO keys del catálogo más abajo.

PRINCIPIO DE MINIMALIDAD DE IMÁGENES:
Menos imágenes = mejor. La lista vacía [] es el valor por defecto.
Solo agrega un tipo si el átomo NO PUEDE evaluarse correctamente sin él.

NECESITAN imágenes (ejemplos de átomos):
- Interpretar o analizar gráficos de funciones → function_graph
- Transformaciones geométricas (reflexión, rotación) → geometric_figure
- Lectura de gráficos estadísticos (torta, barras, boxplot) → statistical_chart
- Ubicar o comparar valores en recta numérica → number_line

NO necesitan imágenes (devuelve []):
- Factorización, productos notables, expresiones algebraicas
- Resolución de ecuaciones e inecuaciones
- Probabilidades y combinatoria
- Porcentajes, razones y proporciones
- Potencias, raíces, logaritmos
- Sucesiones y series numéricas

CATÁLOGO DE TIPOS DE IMAGEN DISPONIBLES:
{image_type_catalog}

IMPORTANTE: {not_images_description}
</task>

<rules>
- Responde SOLO en español de Chile.
- Sé preciso y concreto: evita generalidades que apliquen a cualquier átomo.
- El rubric de dificultad debe ser específico a ESTE átomo, no genérico.
- Si hay ejemplares, úsalos para calibrar alcance y dificultad real.
- NO parafrasees ni reproduzcas los ejemplares.
</rules>

<output_format>
Responde con JSON puro (sin bloques markdown) con esta estructura:
{{
  "scope_guardrails": {{
    "in_scope": ["..."],
    "out_of_scope": ["..."],
    "prerequisites": ["A-M1-..."],
    "common_traps": ["..."]
  }},
  "difficulty_rubric": {{
    "easy": ["descripción de qué hace un ítem fácil..."],
    "medium": ["descripción de qué hace un ítem medio..."],
    "hard": ["descripción de qué hace un ítem difícil..."]
  }},
  "ambiguity_avoid": ["..."],
  "error_families": [
    {{"name": "...", "description": "...", "how_to_address": "..."}}
  ],
  "future_targets": ["..."],
  "representation_variants": ["..."],
  "numbers_profiles": ["small_integers", "fractions", ...],
  "required_image_types": []
}}
</output_format>

<final_instruction>
Basándote en toda la información anterior, genera el enriquecimiento
para el átomo {atom_id}. Responde SOLO con el JSON.
</final_instruction>
"""


def build_exemplars_section(exemplars: list) -> str:
    """Format exemplar data for the enrichment prompt.

    Args:
        exemplars: List of Exemplar objects.

    Returns:
        Formatted string describing available exemplars.
    """
    if not exemplars:
        return "No hay ejemplares disponibles para este átomo."

    lines = []
    for i, ex in enumerate(exemplars, 1):
        lines.append(
            f"Ejemplar {i}: [{ex.question_id}] "
            f"(test: {ex.test_id}, "
            f"dificultad: {ex.difficulty_level})\n"
            f"  Texto: {ex.question_text[:200]}..."
            if len(ex.question_text) > 200
            else f"Ejemplar {i}: [{ex.question_id}] "
            f"(test: {ex.test_id}, "
            f"dificultad: {ex.difficulty_level})\n"
            f"  Texto: {ex.question_text}",
        )
    return "\n".join(lines)
