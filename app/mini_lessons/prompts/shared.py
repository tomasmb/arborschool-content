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
- CADA variable o símbolo en texto corrido DEBE estar dentro de \
un bloque <math>. NUNCA escribas <mi>, <mn>, <mo>, <msup>, \
<mfrac> u otro tag MathML suelto fuera de <math>. \
Incorrecto: "donde <mi>x</mi> es..." \
Correcto: "donde <math xmlns=\\"...\\"><mi>x</mi></math> es..."
- Tags MathML NUNCA auto-cerrados: NO <msup/>, NO <mfrac/>. \
Cada tag debe tener apertura y cierre con contenido válido.
- NO uses LaTeX. SOLO MathML.
- Atributos semánticos requeridos: data-block, data-role según la \
sección.
- Caracteres UTF-8 directos: é, ó, á, ú, í, ñ, ü, ¿, ¡. \
NUNCA entidades Latin-1.
- Todo decimal usa COMA (convención PAES): 1,5 y NO 1.5. \
Punto decimal está PROHIBIDO. Aplica a texto y a <mn> en MathML.
- Separador de miles es ESPACIO (convención PAES): 10 000 y NO \
10.000. Usar espacio no separable \\u00A0 dentro de <mn>. \
Enteros de 4 dígitos pueden ir sin separador (1000, 1500).
- NO cubras temas listados como "Fuera de alcance" en el \
enriquecimiento. Limítate estrictamente a los ítems "En alcance"."""

# ------------------------------------------------------------------
# Scope gate (injected into concept and WE prompts)
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
    'no "Se debe factorizar sacando...").\n'
    "- Errores: normalízalos como patrones comunes, no fallas "
    'personales. Usa "Es común que..." o "Muchos confunden..." '
    'en vez de "Cambias mal..." o "Confundes...". '
    "Esto reduce la respuesta defensiva y mejora el aprendizaje."
)

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
    "- MÁXIMO 3 bloques <h3> (incluyendo Trampa PAES si aplica). "
    "Fusiona ideas relacionadas en un solo bloque.\n"
    "- Cada <h3> cubre UNA sola idea o regla.\n"
    "- Formato: <h3>título corto</h3> seguido de 1-2 oraciones "
    "+ opcional mini-ejemplo de 1 línea.\n"
    "- Si alguna familia de error describe una confusión frecuente, "
    "incluye un bloque <h3>Trampa PAES</h3> con UNA SOLA confusión "
    "(la más peligrosa). Formato estricto: 1 línea ❌ incorrecto + "
    "1 línea ✔ correcto. NO listes múltiples errores — eso lo "
    "cubre el ejemplo resuelto y las preguntas adaptativas.\n"
    "- Mínima teoría necesaria: definiciones y notación solo si "
    "son imprescindibles.\n"
    f"- ~{_CON_BUDGET} palabras total entre todos los bloques.\n"
    "- Sin repetir lo que el ejemplo resuelto mostrará."
)

_WE_BUDGET = SECTION_WORD_BUDGETS["worked-example"]
_WE_RULES = (
    "- Pasos numerados dentro de <details>/<summary>.\n"
    '- <summary> tiene "Paso N:" + 1 frase corta del objetivo '
    "(español normal con espacios y tildes, NUNCA identificadores "
    'con guiones bajos como "Elige_y_despeja").\n'
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
    "- Después del micro-refuerzo, incluye un Checklist PAES:\n"
    '  <ul data-role="paes-checklist">\n'
    "    <li>✅ [verificación 1]</li>\n"
    "    <li>✅ [verificación 2]</li>\n"
    "    <li>✅ [verificación 3]</li>\n"
    "  </ul>\n"
    "- Usa EXACTAMENTE los 3 ítems de checklist_items del plan.\n"
    "- Cada ítem de checklist es 1 línea que el estudiante puede "
    "aplicar en 10 segundos bajo presión de examen.\n"
    f"- ~{_WE_BUDGET} palabras."
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
    "concept", "worked-example",
})


def build_generation_rules(
    section_type: str,
    index: int | None = None,
) -> str:
    """Build the full rules block for a section generation prompt.

    Composes shared HTML rules + tone rules + scope gate (for
    concept / WE) + section-specific rules into a single string.
    """
    section_rules_map: dict[str, str] = {
        "objective": _OBJECTIVE_RULES,
        "concept": _CONCEPT_RULES,
        "worked-example": _WE_RULES,
    }
    specific = section_rules_map.get(section_type, "")

    parts = [_HTML_RULES, _TONE_RULES]
    if section_type in _SCOPE_GATE_SECTIONS:
        parts.append(_SCOPE_GATE_RULES)
    if specific:
        parts.append(specific)
    return "\n".join(parts)
