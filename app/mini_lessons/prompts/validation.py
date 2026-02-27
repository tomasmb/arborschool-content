"""Prompt templates for validation phases.

Provides prompts for:
- Section-level math/solve verification (Phase 3)
- Full-lesson quality gate: math + coverage + rubric (Phase 5)
"""

from __future__ import annotations

from app.mini_lessons.html_validator import FORBIDDEN_FILLER_PHRASES

# ------------------------------------------------------------------
# Section-level math verification (Phase 3)
# ------------------------------------------------------------------

SECTION_MATH_CHECK_PROMPT = """\
<role>
Experto en matemáticas PAES M1 (Chile). Verificas la corrección \
matemática de contenido educativo.
</role>

<context>
{section_html}
</context>

<task>
{task_description}
</task>

<output_format>
JSON puro:
{{
  "math_correct": true,
  "errors": [],
  "steps_verified": ["paso 1: OK", "paso 2: OK"]
}}
Si hay errores, "math_correct": false y describe cada error.
</output_format>
"""

WORKED_EXAMPLE_TASK = """\
1. Lee el ejemplo resuelto paso a paso.
2. Verifica cada paso matemático de forma independiente.
3. Comprueba que cada paso sigue lógicamente del anterior.
4. Verifica que la respuesta final es correcta.
5. Comprueba que el checklist PAES es coherente con los pasos."""


# ------------------------------------------------------------------
# Garbled / corrupted text check (Phase 3, all sections)
# ------------------------------------------------------------------

GARBLED_TEXT_CHECK_PROMPT = """\
<role>
Revisor de texto español educativo (HTML + MathML). Detectas \
cualquier texto corrupto, ilegible o con artefactos.
</role>

<context>
{section_html}
</context>

<task>
Revisa si hay CUALQUIER anomalía textual. Categorías:

ENCODING / CARACTERES:
1. Hex en lugar de letra: funcif3n → función
2. Letra eliminada: grfico → gráfico, nmero → número
3. Tilde faltante obligatoria: tamano, segun, Cual, numero, \
calculo, area, angulo, formula, ecuacion, grafico
4. Entidades HTML doble-codificadas: &amp;#xD7; en vez de ×
5. Caracteres de otro script (Devanagari, Cirílico, árabe) \
en texto español
6. Caracteres invisibles (soft hyphen, zero-width, BOM)
7. Espacios inusuales (NBSP, em-space) fuera de MathML

FORMATO / MARKUP:
8. LaTeX crudo en HTML: \\frac, \\sqrt, \\cdot, $...$
9. Markdown crudo en HTML: **texto**, _texto_, ```código```
10. HTML escapado visible: &lt;p&gt; en vez de <p>
11. MathML roto: tags <math>, <mrow>, <mi> sin cerrar o truncados

CONTENIDO / ARTEFACTOS:
12. Texto truncado a mitad de palabra u oración
13. Párrafo o frase duplicada textualmente
14. Placeholders: [TODO], {{variable}}, INSERT_HERE, PLACEHOLDER
15. Filtración de prompt/instrucciones del modelo en el contenido
16. Mezcla incoherente de idiomas en medio de oración española

Ignora contenido dentro de <math>...</math> al revisar tildes \
y espacios. Un <img> tag con src= es válido, no es artefacto.
</task>

<output_format>
JSON puro:
{{
  "text_clean": true,
  "issues": []
}}
Si hay problemas, "text_clean": false y lista cada issue con \
la categoría y el fragmento afectado.
</output_format>
"""


def build_garbled_text_prompt(section_html: str) -> str:
    """Build garbled-text detection prompt for a section."""
    return GARBLED_TEXT_CHECK_PROMPT.format(
        section_html=section_html,
    )


# ------------------------------------------------------------------
# Garbled text FIX prompt (used by fix_garbled_lessons script)
# ------------------------------------------------------------------

GARBLED_FIX_PROMPT = """\
<role>
Editor técnico de HTML educativo español con MathML. \
Corriges SOLO los problemas reportados sin alterar nada más.
</role>

<html>
{html}
</html>

<issues>
{issues}
</issues>

<task>
Corrige SOLO los problemas listados en <issues>. Reglas:
1. Cambia lo mínimo posible — cada cambio debe resolver un \
issue reportado.
2. NO reescribas, reformules ni reorganices contenido sano.
3. NO toques atributos data-*, xmlns, <img src="...">, ni URLs.
4. NO agregues tags <html>, <head>, <body> ni ningún wrapper. \
El documento es un fragmento <article>...</article>, devuélvelo \
exactamente así.
5. Para MathML roto: reconstruye la estructura mínima correcta \
(e.g. <msup><mi>x</mi><mn>2</mn></msup> en vez de <msup/>).
6. Para control chars / bytes garbled: identifica qué carácter \
debería ser (típicamente +, −, ×, =, →) y reemplaza por el \
carácter correcto o su entidad HTML.
7. Para tildes faltantes: agrega la tilde correcta en español.
8. Para guiones bajos en títulos de pasos: reemplaza _ por \
espacios y agrega tildes correctas.
9. Devuelve el HTML COMPLETO corregido, no un fragmento.
</task>

<output_format>
JSON puro:
{{
  "fixed_html": "<article ...>...</article>"
}}
</output_format>
"""

GARBLED_FIX_VERIFY_PROMPT = """\
<role>
Verificador QA de mini-clases PAES en HTML + MathML español.
</role>

<task>
Abajo hay un diff de cambios aplicados a una mini-clase. \
Cada línea cambiada muestra la versión antigua (-) y nueva (+).

Verifica SOLO estos problemas reales:
1. Un reemplazo produjo español INCORRECTO (e.g. "ccómo" en \
vez de "cómo", "tampocó" en vez de "tampoco").
2. Un reemplazo ALTERÓ expresiones matemáticas o MathML de \
forma que cambió su significado.
3. Un reemplazo ELIMINÓ contenido que no debía eliminarse.
4. Un reemplazo ROMPIÓ la estructura HTML (tags sin cerrar, \
atributos perdidos).

NO marques:
- Correcciones de tildes/acentos que son correctas en español.
- Eliminación de caracteres invisibles o de control.
- Reconstrucción de MathML roto a MathML válido.
</task>

<diff>
{diff_text}
</diff>

<output_format>
JSON puro:
{{"verdict": "PASS"}} o {{"verdict": "FAIL", "issues": ["..."]}}
</output_format>
"""


def build_garbled_fix_prompt(
    html: str, issues: list[str],
) -> str:
    """Build prompt to fix garbled text issues in a lesson."""
    issues_text = "\n".join(f"- {i}" for i in issues)
    return GARBLED_FIX_PROMPT.format(
        html=html, issues=issues_text,
    )


def build_garbled_fix_verify_prompt(diff_text: str) -> str:
    """Build prompt to verify a garbled-text fix didn't break content."""
    return GARBLED_FIX_VERIFY_PROMPT.format(
        diff_text=diff_text,
    )


# ------------------------------------------------------------------
# Full quality gate prompt (Phase 5)
# ------------------------------------------------------------------

def _build_quality_filler_list() -> str:
    """Build filler phrase list for the quality gate prompt."""
    return ", ".join(
        f'"{p.capitalize()}..."' for p in FORBIDDEN_FILLER_PHRASES
    )


_QUALITY_GATE_TEMPLATE = """\
<role>
Revisor experto de mini-clases PAES M1 (Chile). Evalúas \
corrección matemática, cobertura pedagógica, brevedad y tono.
</role>

<context>
MINI-CLASE COMPLETA:
{{full_html}}

ENRIQUECIMIENTO DEL ÁTOMO:
Ítems in_scope: {{in_scope_items}}
Familias de error: {{error_families}}
Rúbrica de dificultad:
  easy: {{rubric_easy}}
  medium: {{rubric_medium}}
  hard: {{rubric_hard}}
</context>

<task>
Evalúa la mini-clase en tres dimensiones:

**1. CORRECCIÓN MATEMÁTICA** (auto-fail si hay error):
- Verifica cada paso del ejemplo resuelto.
- Busca contradicciones entre explicación y resultado.

**2. COBERTURA** (auto-fail si hay gaps):
- ¿Cada ítem in_scope está cubierto en concepto o ejemplo resuelto?
- ¿El ejemplo resuelto aborda al menos 2 familias de error?

**3. RÚBRICA PEDAGÓGICA** (0-2 cada dimensión, umbral >= 6/8):
1. objective_clarity: Objetivo claro y medible. 0=vago o sin verbo \
medible, 1=claro pero sin relevancia PAES, 2=verbo medible + \
relevancia PAES en 2 oraciones.
2. brevity_cognitive_load: Sin relleno, sin decoración, cada \
oración enseña o estructura. 0=concepto sin h3 sub-bloques O \
Trampa PAES lista más de 1 error, 1=h3 sub-bloques pero algún \
bloque excede 3 oraciones, 2=cada h3 tiene 1-2 oraciones + \
opcional mini-ejemplo de 1 línea.
3. worked_example_correctness: Matemática verificada y checklist \
PAES coherente con el procedimiento. 0=error matemático o \
checklist incongruente, 1=correcto pero checklist genérica, \
2=correcto + checklist específica al procedimiento.
4. step_rationale_clarity: Pasos explican "por qué", no solo \
"cómo". 0=pasos sin explicación del por qué, 1=algunos pasos \
explican, 2=TODOS los pasos explican por qué + la verificación \
usa un método alternativo.
</task>

<rules>
- AUTO-FAIL: matemática incorrecta, contradicción explicación vs \
resultado, ejemplo resuelto faltante, ítem in_scope no cubierto, \
sección que excede 2x presupuesto, frases relleno prohibidas.
- AUTO-FAIL SCOPE GATE: si la mini-clase enseña reglas generales \
de fracciones, decimales o álgebra que no son el tema del átomo \
(frases como "denominador común", "invierte la fracción", \
"simplifica la fracción", "mínimo común múltiplo"), es auto-fail.
- AUTO-FAIL NOTACIÓN: si hay decimales con punto en vez de coma \
(1.5 en vez de 1,5), o miles con punto en vez de espacio \
(10.000 en vez de 10 000), es auto-fail.
- AUTO-FAIL TRAMPA: si el bloque Trampa PAES lista más de 1 \
patrón de error en lugar de un contraste enfocado \
(1 línea ❌ + 1 línea ✔), score brevity_cognitive_load = 0.
- AUTO-FAIL OBJECTIVE TAG: si el bloque objective usa <section> \
en vez de <header>, es auto-fail.
- Para P-template: si el ejemplo no respeta los pasos canónicos, \
penalizar step_rationale_clarity.
- Frases relleno prohibidas: {filler_list}
</rules>

<output_format>
JSON puro:
{{{{
  "math_correct": true,
  "math_errors": [],
  "coverage_pass": true,
  "coverage_gaps": [],
  "dimension_scores": {{{{
    "objective_clarity": 2,
    "brevity_cognitive_load": 2,
    "worked_example_correctness": 2,
    "step_rationale_clarity": 2
  }}}},
  "total_score": 8,
  "auto_fail_triggered": false,
  "auto_fail_reasons": [],
  "publishable": true,
  "improvement_suggestions": []
}}}}
</output_format>

<final_instruction>
Evalúa la mini-clase completa. Sé estricto con la matemática \
y la cobertura. Sé exigente con la brevedad: si una oración no \
enseña nada, penaliza. Responde SOLO con JSON.
</final_instruction>
"""

QUALITY_GATE_PROMPT = _QUALITY_GATE_TEMPLATE.format(
    filler_list=_build_quality_filler_list(),
)


# ------------------------------------------------------------------
# Builder functions
# ------------------------------------------------------------------


def build_section_math_prompt(
    section_html: str,
    section_type: str,
) -> str:
    """Build a math verification prompt for a single section."""
    task_map = {
        "worked-example": WORKED_EXAMPLE_TASK,
    }
    task = task_map.get(
        section_type,
        "Verifica la corrección del contenido matemático.",
    )
    return SECTION_MATH_CHECK_PROMPT.format(
        section_html=section_html,
        task_description=task,
    )


def build_quality_gate_prompt(
    full_html: str,
    in_scope_items: list[str],
    error_families: list[str],
    rubric: dict[str, list[str]],
    image_failures: list[str] | None = None,
) -> str:
    """Build the full quality gate prompt for Phase 5.

    When ``image_failures`` is non-empty, appends a note so the
    gate knows which planned images are missing and can score
    accordingly (e.g. penalize dangling figure references).
    """
    prompt = QUALITY_GATE_PROMPT.format(
        full_html=full_html,
        in_scope_items="\n  ".join(
            f"- {item}" for item in in_scope_items
        ),
        error_families="\n  ".join(
            f"- {fam}" for fam in error_families
        ),
        rubric_easy="; ".join(rubric.get("easy", [])),
        rubric_medium="; ".join(rubric.get("medium", [])),
        rubric_hard="; ".join(rubric.get("hard", [])),
    )
    if image_failures:
        note = (
            "\n\nNOTA: Las siguientes secciones tenían imágenes "
            "planificadas pero la generación falló: "
            f"{', '.join(image_failures)}. "
            "Si el texto referencia figuras inexistentes, "
            "penaliza en brevity_cognitive_load."
        )
        prompt += note
    return prompt
