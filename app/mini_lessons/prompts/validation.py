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
4. Verifica que la respuesta final es correcta."""

QUICK_CHECK_TASK = """\
1. Lee el enunciado y las 4 opciones (A-D).
2. Resuelve el problema paso a paso desde cero.
3. Compara tu respuesta con la opción marcada como correcta.
4. Verifica que el feedback de cada distractor es matemáticamente \
correcto.
5. Verifica que hay feedback para la correcta + 3 distractores."""


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
- Verifica cada paso de los ejemplos resueltos.
- Resuelve cada quick-check desde cero y compara con la clave.
- Busca contradicciones entre explicación y clave de respuesta.

**2. COBERTURA** (auto-fail si hay gaps):
- ¿Cada ítem in_scope está cubierto en alguna sección?
- ¿Cada familia de error está abordada en alguna sección?
- ¿Ejemplo 1 usa criterios easy? ¿Ejemplo 2 sube a medium/hard?

**3. RÚBRICA PEDAGÓGICA** (0-2 cada dimensión, umbral >= 12/14):
1. objective_clarity: Objetivo claro y medible.
2. brevity_cognitive_load: Sin relleno, sin decoración, cada \
oración enseña o estructura. 0=verbose, 1=algo exceso, 2=limpio.
3. worked_example_correctness: Matemática verificada.
4. step_rationale_clarity: Pasos explican "por qué", no solo \
"cómo". Sin sobre-explicar.
5. quick_check_quality: Distractores plausibles, no triviales.
6. feedback_quality: Explicativo, accionable, conciso.
7. transition_readiness: Transición explícita al set adaptativo con \
acción clara. 0=sin transición, 1=genérica, 2=específica y motivante.
</task>

<rules>
- AUTO-FAIL: matemática incorrecta, contradicción explicación vs \
clave, feedback vago, ejemplos resueltos faltantes, ítem in_scope \
no cubierto, familia de error no abordada, sección que excede 2x \
presupuesto, frases relleno prohibidas.
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
    "step_rationale_clarity": 2,
    "quick_check_quality": 2,
    "feedback_quality": 2,
    "transition_readiness": 2
  }}}},
  "total_score": 14,
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
        "quick-check": QUICK_CHECK_TASK,
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
) -> str:
    """Build the full quality gate prompt for Phase 5."""
    return QUALITY_GATE_PROMPT.format(
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
