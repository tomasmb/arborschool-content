"""Prompt templates for Phase 4b — Image Generation & Validation.

Two prompts with separated concerns:
1. GEMINI_IMAGE_GENERATION_PROMPT — wraps a content description with
   HOW to draw it (visual style, background, contrast). The content
   description itself comes from Phase 4 (image_description field).
2. IMAGE_VALIDATION_PROMPT — GPT-5.1 (vision) judges whether the
   generated image matches the expected description and question.

The description-generation step that previously lived here was removed:
Phase 4 now produces the image_description as part of the QTI JSON
response, so the question and image are designed together.
"""

# ---------------------------------------------------------------------------
# Gemini image generation (visual style wrapper)
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

# ---------------------------------------------------------------------------
# Image validation (GPT-5.1 with vision)
# Concern: Does the generated image match the question?
# ---------------------------------------------------------------------------

IMAGE_VALIDATION_PROMPT = """\
<role>
Eres un validador de imagenes educativas para preguntas PAES M1 (Chile).
Tu tarea es verificar que la imagen generada coincide con lo esperado.
</role>

<context>
DESCRIPCION ESPERADA:
{image_description}

ENUNCIADO DE LA PREGUNTA (extracto del QTI):
{stem_context}
</context>

<task>
Analiza la imagen adjunta y determina si cumple con la descripcion
esperada. Verifica:
1. Los elementos matematicos correctos estan presentes (ejes, curvas,
   figuras, puntos, etiquetas).
2. Los valores numericos y etiquetas son correctos y legibles.
3. La imagen es coherente con el enunciado de la pregunta.
4. No hay errores matematicos visibles (intersecciones incorrectas,
   escalas erroneas, ángulos mal dibujados).
</task>

<rules>
- Tolera variaciones estilisticas menores (grosor de linea, sombreado).
- NO toleres errores matematicos (valores incorrectos, elementos
  faltantes, funciones mal graficadas).
- Si la imagen es generica o no contiene los elementos especificos
  descritos, marca como "fail".
</rules>

<output_format>
Responde con JSON puro:
{{
  "result": "pass" o "fail",
  "reason": "explicacion breve del veredicto"
}}
</output_format>

<final_instruction>
Basandote en la imagen adjunta y la descripcion esperada, emite
tu veredicto. Responde SOLO con el JSON.
</final_instruction>
"""
