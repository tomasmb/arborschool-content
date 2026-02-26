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
- NO cubras temas listados como "Fuera de alcance" en el \
enriquecimiento. Limítate estrictamente a los ítems "En alcance"."""

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
- Feedback obligatorio: por qué la correcta es correcta, por qué \
cada distractor es tentador pero incorrecto, y un "next-step cue".
- Estructura HTML: ol[data-role="options"] > li[data-option="A|B|C|D"].
- Feedback: div[data-role="feedback"] > p[data-correct-option] + \
ul[data-role="distractor-rationale"] > li[data-option]."""

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
    "- Mínima teoría necesaria: definiciones y notación solo si "
    "son imprescindibles.\n"
    f"- ~{_CON_BUDGET} palabras máximo.\n"
    "- Una idea por párrafo. Sin repetir lo que los ejemplos "
    "mostrarán."
)

_WE_BUDGET = SECTION_WORD_BUDGETS["worked-example"]
_WORKED_EXAMPLE_RULES = (
    "- Pasos numerados con etiquetas (Paso 1, Paso 2...).\n"
    "- Cada paso: 1-2 oraciones máximo.\n"
    f"- ~{_WE_BUDGET} palabras por ejemplo.\n"
    '- Incluir un "por qué" en cada paso clave, no solo el '
    '"cómo".'
)

_ERR_BUDGET = SECTION_WORD_BUDGETS["error-patterns"]
_ERROR_PATTERNS_RULES = (
    "- Cubre TODAS las familias de error asignadas en el plan.\n"
    "- ~1-2 oraciones por error.\n"
    "- Incluir un tip PAES al final.\n"
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


def build_generation_rules(section_type: str) -> str:
    """Build the full rules block for a section generation prompt.

    Composes shared HTML rules + tone rules + section-specific rules
    into a single string. Defined once per section type (DRY).
    """
    section_rules_map: dict[str, str] = {
        "objective": _OBJECTIVE_RULES,
        "concept": _CONCEPT_RULES,
        "worked-example": _WORKED_EXAMPLE_RULES,
        "quick-check": _QUICK_CHECK_RULES,
        "error-patterns": _ERROR_PATTERNS_RULES,
        "transition-to-adaptive": _TRANSITION_RULES,
    }

    specific = section_rules_map.get(section_type, "")
    parts = [_HTML_RULES, _TONE_RULES]
    if specific:
        parts.append(specific)
    return "\n".join(parts)
