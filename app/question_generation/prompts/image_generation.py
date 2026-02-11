"""Prompt templates for Phase 4b — Image Generation.

Two prompts with separated concerns:
1. IMAGE_DESCRIPTION_PROMPT — GPT-5.1 generates a detailed description
   of WHAT to draw (elements, positions, labels, mathematical content).
2. GEMINI_IMAGE_GENERATION_PROMPT — wraps the description with HOW to
   draw it (visual style, background, contrast).

This separation avoids redundancy and potential contradictions.
"""

# ---------------------------------------------------------------------------
# Step 1: Content description (GPT-5.1, reasoning_effort="low")
# Concern: WHAT to draw — elements, layout, labels, data
# ---------------------------------------------------------------------------

IMAGE_DESCRIPTION_PROMPT = """\
<role>
Eres un diseñador de contenido visual para preguntas PAES M1 (Chile).
Tu tarea es describir QUÉ debe contener una imagen educativa.
</role>

<context>
TIPO DE IMAGEN: {image_type}
DESCRIPCIÓN DEL PLAN: {plan_description}
CONTEXTO DE LA PREGUNTA (enunciado QTI):
{stem_context}
</context>

<task>
Describe el CONTENIDO de la imagen. La descripción DEBE incluir:
1. Qué elementos matemáticos deben aparecer (ejes, curvas, figuras, puntos)
2. Cómo deben estar posicionados entre sí
3. Qué etiquetas textuales incluir (nombres de ejes, valores, ángulos)
4. Valores numéricos específicos si los hay

NO incluyas instrucciones de estilo visual (colores, fondo, contraste).
Esas reglas se aplican por separado.
</task>

<rules>
- Para gráficos de funciones: especifica dominio, rango, puntos notables,
  intersecciones y ecuación visible si corresponde.
- Para figuras geométricas: especifica medidas, ángulos, nombres de vértices.
- Para gráficos estadísticos: especifica tipo (barra, histograma, etc.),
  categorías, valores y etiquetas de ejes.
- Para rectas numéricas: especifica rango, puntos marcados y sus valores.
- Solo etiquetas esenciales. Sin texto explicativo ni títulos.
</rules>

<output_format>
Responde con JSON puro:
{{
  "generation_prompt": "descripción detallada del contenido visual...",
  "alt_text": "texto alternativo breve para accesibilidad"
}}
</output_format>

<final_instruction>
Basándote en el tipo de imagen y contexto, describe el contenido.
Responde SOLO con el JSON.
</final_instruction>
"""


# ---------------------------------------------------------------------------
# Step 2: Gemini image generation (visual style wrapper)
# Concern: HOW to draw — style, background, contrast, quality
# ---------------------------------------------------------------------------

GEMINI_IMAGE_GENERATION_PROMPT = """\
Generate a clean, educational image for a math exam question.

CONTENT (what to draw):
{generation_prompt}

STYLE (how to draw it):
- Clean white background
- Black lines with subtle color accents where needed
- High contrast, easy to read at small sizes
- Minimal labels only (axis labels, point names, measurements)
- No title, header text, or explanatory text
- No watermarks or logos
- Professional, exam-quality visual
"""
