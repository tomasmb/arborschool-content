"""Shared prompt constants and context builders for mini-lessons.

All shared rule constants live here so they are defined ONCE and
reused by generation, retry, and validation prompts (DRY).
"""

from __future__ import annotations

from typing import Any

from app.mini_lessons.html_validator import FORBIDDEN_FILLER_PHRASES
from app.mini_lessons.models import SECTION_WORD_BUDGETS

# ------------------------------------------------------------------
# HTML structural rules (injected into every generation prompt)
# ------------------------------------------------------------------

_HTML_RULES = """\
- Genera HTML semántico SIN estilos inline, sin <style>, sin <script>.
- Tags permitidos: section, header, h1-h4, p, ul, ol, li, table, \
thead, tbody, tr, th, td, strong, em, code, math, details, summary, \
blockquote, hr, img (requiere atributo alt).
- Usa MathML nativo con xmlns explícito para toda expresión \
matemática:
  <math xmlns="http://www.w3.org/1998/Math/MathML"><mrow>...</mrow>\
</math>
- NO uses LaTeX. SOLO MathML.
- Atributos semánticos requeridos: data-block, data-role, \
data-option, data-correct-option, data-feedback-type según la \
sección.
- Caracteres UTF-8 directos: é, ó, á, ú, í, ñ, ü, ¿, ¡. \
NUNCA entidades Latin-1.
- Todo decimal usa COMA (convención chilena): 1,5 y NO 1.5. \
Punto decimal está PROHIBIDO. Aplica a texto y a <mn> en MathML.
- NO cubras temas listados como "Fuera de alcance" en el \
enriquecimiento. Limítate estrictamente a los ítems "En alcance"."""

# ------------------------------------------------------------------
# Scope gate (injected into concept, WE, and QC prompts)
# ------------------------------------------------------------------

_SCOPE_GATE_RULES = """\
- SCOPE GATE: No enseñes reglas generales de fracciones, decimales, \
simplificación algebraica ni otros prerrequisitos salvo lo mínimo \
para completar el cálculo en curso (máximo 1 línea).
- Si aparece un prerrequisito, resuélvelo directamente sin explicar \
la técnica general.
- Frases como "denominador común", "invierte la fracción", \
"simplifica la fracción", "mínimo común múltiplo", "convierte a \
decimal", "alinea la coma" deben aparecer como máximo 1 vez en \
toda la mini-clase. Si necesitas más, comprime."""

# ------------------------------------------------------------------
# Tone rules (injected into every generation prompt)
# ------------------------------------------------------------------

def _build_filler_list() -> str:
    """Build the PROHIBIDO filler list from the canonical constant."""
    quoted = [f'"{p.capitalize()}..."' for p in FORBIDDEN_FILLER_PHRASES]
    return ", ".join(quoted)


_TONE_RULES = (
    "- Español de Chile, tuteo natural, directo y respetuoso.\n"
    "- Audiencia: estudiantes de 17 años preparando la PAES.\n"
    "- Cada oración debe enseñar algo o cumplir un rol estructural.\n"
    "- Si se puede eliminar una oración sin perder significado, "
    "elimínala.\n"
    "- Voz activa, oraciones cortas, listas sobre párrafos largos.\n"
    f"- PROHIBIDO: {_build_filler_list()}.\n"
    '- USA: dirección directa ("Factoriza sacando el factor común", '
    'no "Se debe factorizar sacando...").'
)

# ------------------------------------------------------------------
# Quick-check rules (shared by generation and validation)
# ------------------------------------------------------------------

_QUICK_CHECK_RULES = """\
- Exactamente 4 opciones (A-D), 1 correcta.
- Distractores representan errores plausibles, NO valores al azar.
- Cada distractor DEBE corresponder a una familia de error del \
enriquecimiento del átomo.
- Estructura HTML: ol[data-role="options"] > li[data-option="A|B|C|D"].
- Feedback dentro de <details><summary>Ver explicación</summary>.
- El <p data-correct-option> DEBE terminar con \
"Regla: Si [situación], entonces [acción]."
- Cada <li> de distractor-rationale DEBE incluir el atributo \
data-error-id="nombre_de_la_familia_de_error" indicando qué \
error representa.
- Cada <li> de distractor-rationale cierra con qué revisar \
la próxima vez.
- Estructura feedback: \
div[data-role="feedback"] > details > summary + \
p[data-correct-option] + ul[data-role="distractor-rationale"] \
> li[data-option][data-error-id]."""

# ------------------------------------------------------------------
# Section-specific rules (appended per section type)
# ------------------------------------------------------------------

_OBJ_BUDGET = SECTION_WORD_BUDGETS["objective"]
_OBJECTIVE_RULES = (
    "- Exactamente 2 oraciones: qué aprenderás + relevancia PAES.\n"
    "- Verbo medible (\"podrás identificar\", \"podrás resolver\").\n"
    f"- ~{_OBJ_BUDGET} palabras máximo."
)

_CON_BUDGET = SECTION_WORD_BUDGETS["concept"]
_CONCEPT_RULES = (
    "- Divide el concepto en micro-bloques con <h3> subtítulos.\n"
    "- Cada <h3> cubre UNA sola idea o regla.\n"
    "- Formato: <h3>título corto</h3> seguido de 1-2 oraciones "
    "+ opcional mini-ejemplo de 1 línea.\n"
    "- Si las familias de error incluyen confusiones de signos o "
    "notación, incluye un bloque <h3>Trampa PAES</h3> con "
    "ejemplo correcto vs incorrecto (2 líneas).\n"
    "- Mínima teoría necesaria: definiciones y notación solo si "
    "son imprescindibles.\n"
    f"- ~{_CON_BUDGET} palabras total entre todos los bloques.\n"
    "- Sin repetir lo que los ejemplos mostrarán."
)

_WE_BUDGET = SECTION_WORD_BUDGETS["worked-example"]

_WE1_RULES = (
    "- Pasos numerados dentro de <details>/<summary>.\n"
    '- <summary> tiene "Paso N:" + 1 frase corta del objetivo.\n'
    "- Si el plan incluye canonical_steps, usa EXACTAMENTE esos "
    "nombres en cada <summary> de paso.\n"
    "- Contenido del <details>: 1-2 oraciones con cálculo + "
    '"por qué".\n'
    "- Último paso: verificación (comprobar resultado por otro "
    "camino).\n"
    "- Lista de pasos en <ol data-role=\"steps\">.\n"
    "- Cierra con micro-refuerzo: "
    '<p data-role="micro-reinforcement">"Si obtuviste [X], '
    'vas bien — el punto clave fue [Y]."</p>\n'
    f"- ~{_WE_BUDGET} palabras."
)

_WE2_RULES = (
    "- Misma estructura <details>/<summary> que WE1.\n"
    "- Lista de pasos en <ol data-role=\"steps\">.\n"
    "- Si el plan incluye canonical_steps, usa EXACTAMENTE los "
    "mismos nombres de paso que WE1 (sin paso de verificación).\n"
    '- Menos anotaciones "por qué" — solo en el paso clave.\n'
    "- Incluye 1-2 cues de predicción: "
    '<p data-role="prediction-cue">"¿Cuánto da [subcálculo]? '
    'Piénsalo antes de abrir el siguiente paso."</p>\n'
    "- SIN paso de verificación (el estudiante lo hace solo).\n"
    "- Cierra con micro-refuerzo: "
    '<p data-role="micro-reinforcement">"Si obtuviste [X], '
    'vas bien."</p>\n'
    f"- ~{_WE_BUDGET} palabras."
)

_ERR_BUDGET = SECTION_WORD_BUDGETS["error-patterns"]
_ERROR_PATTERNS_RULES = (
    "- Cubre TODAS las familias de error asignadas en el plan.\n"
    "- Errores en <ul><li> (1-2 oraciones por error).\n"
    "- Reemplaza el Tip PAES en prosa por un Checklist PAES:\n"
    "  <p><strong>Checklist PAES</strong></p>\n"
    '  <ul data-role="paes-checklist">\n'
    "    <li>✅ [verificación 1]</li>\n"
    "    <li>✅ [verificación 2]</li>\n"
    "    <li>✅ [verificación 3]</li>\n"
    "  </ul>\n"
    "- Exactamente 3 ítems de checklist. Cada uno es 1 línea que "
    "el estudiante puede aplicar en 10 segundos bajo presión.\n"
    f"- ~{_ERR_BUDGET} palabras total."
)

_TR_BUDGET = SECTION_WORD_BUDGETS["transition-to-adaptive"]
_TRANSITION_RULES = (
    f"- Máximo 2 oraciones (~{_TR_BUDGET} palabras).\n"
    "- Transición explícita al set adaptativo."
)


# ------------------------------------------------------------------
# Context builder (built once per atom, reused in all prompts)
# ------------------------------------------------------------------


def build_lesson_context_section(ctx: Any) -> str:
    """Build the shared atom+enrichment context for all prompts.

    Built once per atom and injected identically into every
    per-section LLM call to prevent contradictions.

    Args:
        ctx: LessonContext dataclass.

    Returns:
        Formatted context string.
    """
    enrichment_text = _format_enrichment(ctx.enrichment)
    questions_text = _format_sample_questions(ctx.sample_questions)

    return (
        f"ÁTOMO:\n"
        f"- ID: {ctx.atom_id}\n"
        f"- Título: {ctx.atom_title}\n"
        f"- Descripción: {ctx.atom_description}\n"
        f"- Eje: {ctx.eje}\n"
        f"- Tipo atómico: {ctx.tipo_atomico}\n"
        f"- Template: {ctx.template_type}\n"
        f"- Criterios atómicos: "
        f"{', '.join(ctx.criterios_atomicos)}\n"
        f"- Notas de alcance: "
        f"{', '.join(ctx.notas_alcance) or 'ninguna'}\n"
        f"- Prerrequisitos: "
        f"{', '.join(ctx.prerequisites) or 'ninguno'}\n"
        f"\nENRIQUECIMIENTO:\n{enrichment_text}\n"
        f"\nEJEMPLOS DE PREGUNTAS GENERADAS:\n{questions_text}"
    )


def _format_enrichment(enrichment: Any | None) -> str:
    """Format enrichment data for prompt injection."""
    if enrichment is None:
        return "No hay enriquecimiento disponible."

    data = enrichment.model_dump()
    lines: list[str] = []

    scope = data.get("scope_guardrails", {})
    if scope.get("in_scope"):
        lines.append("En alcance:")
        for item in scope["in_scope"]:
            lines.append(f"  - {item}")
    if scope.get("out_of_scope"):
        lines.append("Fuera de alcance:")
        for item in scope["out_of_scope"]:
            lines.append(f"  - {item}")

    rubric = data.get("difficulty_rubric", {})
    if rubric:
        lines.append("Rúbrica de dificultad:")
        for level, criteria in rubric.items():
            lines.append(f"  {level}: {'; '.join(criteria)}")

    errors = data.get("error_families", [])
    if errors:
        lines.append("Familias de error:")
        for e in errors:
            name = e.get("name", "")
            desc = e.get("description", "")
            how = e.get("how_to_address", "")
            lines.append(f"  - {name}: {desc}")
            if how:
                lines.append(f"    Abordar: {how}")

    profiles = data.get("numbers_profiles", [])
    if profiles:
        lines.append(f"Perfiles numéricos: {', '.join(profiles)}")

    variants = data.get("representation_variants", [])
    if variants:
        lines.append(
            f"Variantes de representación: {', '.join(variants)}",
        )

    return "\n".join(lines) if lines else "Enriquecimiento vacío."


def _format_sample_questions(
    samples: dict[str, list[str]],
) -> str:
    """Format sample question stems for prompt injection."""
    if not samples or not any(samples.values()):
        return "No hay preguntas generadas disponibles."

    lines: list[str] = []
    for difficulty in ("easy", "medium", "hard"):
        stems = samples.get(difficulty, [])
        if stems:
            lines.append(f"{difficulty.upper()}:")
            for i, stem in enumerate(stems, 1):
                lines.append(f"  {i}. {stem}")
    return "\n".join(lines)


_SCOPE_GATE_SECTIONS = frozenset({
    "concept", "worked-example", "quick-check",
})


def build_generation_rules(
    section_type: str,
    index: int | None = None,
) -> str:
    """Build the full rules block for a section generation prompt.

    Composes shared HTML rules + tone rules + scope gate (for
    concept / WE / QC) + section-specific rules into a single
    string. For worked-examples, selects WE1 (full scaffolding)
    or WE2 (faded) rules based on index.
    """
    section_rules_map: dict[str, str] = {
        "objective": _OBJECTIVE_RULES,
        "concept": _CONCEPT_RULES,
        "quick-check": _QUICK_CHECK_RULES,
        "error-patterns": _ERROR_PATTERNS_RULES,
        "transition-to-adaptive": _TRANSITION_RULES,
    }

    if section_type == "worked-example":
        specific = _WE2_RULES if index == 2 else _WE1_RULES
    else:
        specific = section_rules_map.get(section_type, "")

    parts = [_HTML_RULES, _TONE_RULES]
    if section_type in _SCOPE_GATE_SECTIONS:
        parts.append(_SCOPE_GATE_RULES)
    if specific:
        parts.append(specific)
    return "\n".join(parts)
