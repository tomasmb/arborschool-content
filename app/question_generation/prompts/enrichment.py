"""Prompt template for Phase 1 — Atom Enrichment.

Generates scope guardrails, difficulty rubric, and pedagogical guidance
for an atom. Uses GPT-5.1 with JSON response format.

Format placeholders:
- {image_type_catalog}: full catalog of available image types
    (generatable + non-generatable, grouped and labeled)
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
Genera un JSON de enriquecimiento con estos campos:

1. **scope_guardrails**: Alcance (in/out), prerrequisitos y trampas.
2. **difficulty_rubric**: Qué hace un ítem easy/medium/hard EN ESTE átomo.
3. **ambiguity_avoid**: Patrones a evitar para no crear ambigüedad.
4. **error_families**: Errores comunes (nombre, descripción, cómo abordar).
5. **future_targets**: Competencias futuras que habilita este átomo.
6. **representation_variants**: Representaciones relevantes.
7. **numbers_profiles**: Perfiles numéricos apropiados.
8. **required_image_types**: Ver sección ANÁLISIS DE IMÁGENES.
</task>

<image_analysis>
CRITERIO: ¿Un conjunto representativo de buenas preguntas PAES para
este átomo incluiría contenido visual (gráficos, figuras, diagramas)
como parte ESENCIAL del enunciado?

Pregúntate: "¿Puedo diseñar preguntas PAES completas y representativas
para este átomo sin ninguna imagen, o la mayoría necesitaría un
gráfico, figura o diagrama como parte del problema?"

NECESITAN imágenes:
- Interpretar, comparar o graficar funciones → function_graph
- Analizar efecto visual de parámetros en gráficos → function_graph
- Figuras 2D: triángulos, polígonos, con medidas/ángulos → geometric_figure
- Transformaciones isométricas de figuras en el plano → geometric_figure
- Coordenadas, vectores, puntos en plano cartesiano → geometric_figure
- Lectura de gráficos estadísticos (barras, histograma, torta,
  boxplot, dispersión) → statistical_chart
- Ubicar o comparar valores en la recta numérica → number_line
- Visualizar cuerpos 3D (prismas, cilindros, pirámides) → complex_3d

NO necesitan imágenes (devuelve []):
- Factorización, productos notables
- Resolución algebraica de ecuaciones (sin gráficos)
- Probabilidad y combinatoria sin diagramas
- Porcentajes, razones, proporciones
- Potencias, raíces, logaritmos
- Cálculos numéricos puros

CATÁLOGO COMPLETO DE TIPOS DE IMAGEN:
{image_type_catalog}

NOTA: {not_images_description}
</image_analysis>

<rules>
- Responde SOLO en español de Chile.
- Sé preciso y concreto: evita generalidades que apliquen a cualquier átomo.
- El rubric de dificultad debe ser específico a ESTE átomo, no genérico.
- Si hay ejemplares, úsalos para calibrar alcance y dificultad real.
- NO parafrasees ni reproduzcas los ejemplares.
</rules>

<output_format>
JSON puro (sin bloques markdown):
{{
  "scope_guardrails": {{
    "in_scope": ["..."],
    "out_of_scope": ["..."],
    "prerequisites": ["A-M1-..."],
    "common_traps": ["..."]
  }},
  "difficulty_rubric": {{
    "easy": ["..."],
    "medium": ["..."],
    "hard": ["..."]
  }},
  "ambiguity_avoid": ["..."],
  "error_families": [
    {{"name": "...", "description": "...", "how_to_address": "..."}}
  ],
  "future_targets": ["..."],
  "representation_variants": ["..."],
  "numbers_profiles": ["small_integers", "fractions", ...],
  "required_image_types": ["key_del_catalogo", ...]
}}
Para required_image_types: usa keys exactas del catálogo.
Si el átomo no necesita imágenes, devuelve [].
</output_format>

<final_instruction>
Genera el enriquecimiento para el átomo {atom_id}.
Responde SOLO con el JSON.
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
