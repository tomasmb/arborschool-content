"""Prompts for full QA validation over syncable questions and lessons.

Design goals:
- non-contradictory: one consistency rule per phase
- non-redundant: shared templates with source-specific inserts
- structured: role/context/task/output blocks for every prompt
"""

from __future__ import annotations

ISSUE_CATEGORIES = (
    "deterministic_thousands_sep",
    "deterministic_encoding",
    "deterministic_spacing",
    "manual_fix",
    "ignore",
)

QUESTION_CHECKS = (
    "correct_answer_check",
    "feedback_check",
    "content_quality_check",
    "math_validity_check",
)

LESSON_CHECKS = (
    "lesson_math_check",
    "lesson_content_quality_check",
    "lesson_pedagogy_check",
    "lesson_format_check",
)


_NOTATION_STANDARD = """\
<chilean_notation_standard>
Formato PAES:
- Decimal: coma (,)
- Miles: espacio en texto y &#160; dentro de MathML <mn>
- Enteros de 4 dígitos sin separador son válidos (1000, 1500)

Errores objetivos:
- Punto decimal (3.14)
- Punto de miles (10.000)
- Espacio normal dentro de <mn> para miles
- Número de 5+ dígitos sin separador de miles
</chilean_notation_standard>
"""

_ENCODING_STANDARD = """\
<encoding_standard>
Errores objetivos:
- Mojibake, bytes sueltos, caracteres de control
- Entidades HTML con nombre en QTI XML (&oacute;, &minus;)
- Doble codificación (&amp;amp;)
- Texto truncado o placeholders
</encoding_standard>
"""

_SCAN_SHARED_RULES = """\
<rules>
- Evalúa cada check de forma independiente.
- Marca "blocking" solo para errores que invalidan corrección matemática
  o sincronización segura del contenido.
- No reportes estilo/redacción si no afecta corrección.
- No inventes hallazgos: cada issue debe tener evidencia textual.
</rules>
"""

_CONFIRM_SHARED_RULES = """\
<rules>
- Confirma solo hallazgos demostrables.
- Si hay duda razonable, rechaza (falso positivo).
- Usa SOLO categorías legacy permitidas.
- Incluye decision explícita: confirm/reject.
</rules>
"""

_SCAN_TEMPLATE = """\
<role>
{role}
</role>

{standards}
<content_type>{content_type}</content_type>
<content_label>{label}</content_label>
<content>
{content}
</content>

<checks>
{checks_block}
</checks>

<task>
{task_body}
</task>

{scan_rules}
<consistency_rule>
- Si no hay hallazgos demostrables: status="OK" e issues=[].
- Si status="HAS_ISSUES": cada issue debe incluir issue/check_name/severity/evidence.
</consistency_rule>

<output_format_confirm>
JSON puro:
{{
  "status":"OK" | "HAS_ISSUES",
  "issues":[
    {{
      "issue":"descripción concreta",
      "check_name":"uno de los checks permitidos",
      "severity":"blocking|non_blocking",
      "evidence":"fragmento o referencia concreta"
    }}
  ]
}}
</output_format_confirm>
"""

_CONFIRM_TEMPLATE = """\
<role>
{role}
</role>

<phase>confirm</phase>
{standards}
<content_type>{content_type}</content_type>
<content>
{content}
</content>

<flagged_issues>
{issues_list}
</flagged_issues>

<task>
Para cada hallazgo en flagged_issues:
1) decide si es real (confirm) o falso positivo (reject)
2) si confirmas, asigna category legacy EXACTA:
   - deterministic_thousands_sep
   - deterministic_encoding
   - deterministic_spacing
   - manual_fix
3) preserva o corrige:
   - check_name (debe ser uno permitido)
   - severity (blocking|non_blocking)
   - evidence (texto concreto)
</task>

{confirm_rules}
<consistency_rule>
- confirmed contiene SOLO hallazgos reales con decision="confirm"
- rejected contiene SOLO falsos positivos con decision="reject"
- no uses "ignore" en confirmed
</consistency_rule>

<output_format>
JSON puro:
{{
  "confirmed":[
    {{
      "issue":"...",
      "category":"manual_fix",
      "check_name":"{sample_check}",
      "severity":"non_blocking",
      "evidence":"...",
      "decision":"confirm"
    }}
  ],
  "rejected":[
    {{
      "original_issue":"...",
      "reason":"...",
      "decision":"reject"
    }}
  ]
}}
</output_format>
"""


def _format_issue_line(issue: str | dict) -> str:
    if isinstance(issue, dict):
        issue_text = str(issue.get("issue", "")).strip()
        check_name = str(issue.get("check_name", "")).strip()
        severity = str(issue.get("severity", "")).strip()
        evidence = str(issue.get("evidence", "")).strip()
        parts = [p for p in (issue_text, check_name, severity, evidence) if p]
        return " | ".join(parts) if parts else str(issue)
    return str(issue)


def _format_issues(issues: list[str | dict]) -> str:
    if issues:
        return "\n".join(f"- {_format_issue_line(i)}" for i in issues)
    return "(ninguna)"


def _checks_block(checks: tuple[str, ...]) -> str:
    return "\n".join(f"- {c}" for c in checks)


_STANDARDS = _NOTATION_STANDARD + "\n" + _ENCODING_STANDARD

_QUESTION_SCAN_TASK = """\
Resuelve de forma breve el problema para verificar:
- corrección de respuesta marcada
- que la pregunta sea respondible con la información dada
- que feedback/cálculos (si existen) no contradigan la solución
- validez matemática PAES M1
Reporta solo errores concretos."""

_LESSON_SCAN_TASK = """\
Verifica:
- corrección matemática de ejemplos/pasos
- contenido sin corrupción de texto/encoding/notación
- coherencia pedagógica (objetivo, foco, progresión)
- estructura HTML/MathML utilizable
Reporta solo errores concretos."""


def build_scan_question_prompt(label: str, content: str) -> str:
    """Build scan prompt for a question item."""
    return _SCAN_TEMPLATE.format(
        role="Auditor QA senior de preguntas PAES M1 (Chile).",
        standards=_STANDARDS,
        content_type="question",
        label=label,
        content=content,
        checks_block=_checks_block(QUESTION_CHECKS),
        task_body=_QUESTION_SCAN_TASK,
        scan_rules=_SCAN_SHARED_RULES,
    )


def build_scan_lesson_prompt(label: str, content: str) -> str:
    """Build scan prompt for a lesson item."""
    return _SCAN_TEMPLATE.format(
        role="Auditor QA senior de mini-lecciones PAES M1 (Chile).",
        standards=_STANDARDS,
        content_type="lesson",
        label=label,
        content=content,
        checks_block=_checks_block(LESSON_CHECKS),
        task_body=_LESSON_SCAN_TASK,
        scan_rules=_SCAN_SHARED_RULES,
    )


def build_scan_prompt(
    source: str,
    label: str,
    content: str,
) -> str:
    """Source-routed scan builder for DRY call sites."""
    if source in {"lesson", "mini-class"}:
        return build_scan_lesson_prompt(label, content)
    return build_scan_question_prompt(label, content)


# Backward-compatible wrappers
def build_scan_mini_class_prompt(label: str, html: str) -> str:
    return build_scan_lesson_prompt(label, html)


def build_scan_xml_file_prompt(label: str, xml: str) -> str:
    return build_scan_question_prompt(label, xml)


def build_confirm_question_prompt(
    content: str,
    issues: list[str | dict],
) -> str:
    """Build confirm prompt for question findings."""
    return _CONFIRM_TEMPLATE.format(
        role="Revisor QA de confirmación para preguntas PAES M1.",
        standards=_STANDARDS,
        content_type="question",
        content=content,
        issues_list=_format_issues(issues),
        confirm_rules=_CONFIRM_SHARED_RULES,
        sample_check="content_quality_check",
    )


def build_confirm_lesson_prompt(
    content: str,
    issues: list[str | dict],
) -> str:
    """Build confirm prompt for lesson findings."""
    return _CONFIRM_TEMPLATE.format(
        role="Revisor QA de confirmación para mini-lecciones PAES M1.",
        standards=_STANDARDS,
        content_type="lesson",
        content=content,
        issues_list=_format_issues(issues),
        confirm_rules=_CONFIRM_SHARED_RULES,
        sample_check="lesson_content_quality_check",
    )


def build_confirm_prompt(
    content: str,
    issues: list[str | dict],
    *,
    source: str | None = None,
) -> str:
    """Source-routed confirm builder for DRY call sites."""
    if source in {"lesson", "mini-class"}:
        return build_confirm_lesson_prompt(content, issues)
    return build_confirm_question_prompt(content, issues)


_LLM_FIX_PROMPT = """\
<role>
Corrector experto de contenido educativo PAES M1 (Chile).
Corrige SOLO issues explícitos, sin cambios colaterales.
</role>

{standards}
<content>
{content}
</content>

<issues_to_fix>
{issues_list}
</issues_to_fix>

<task>
1) Aplica correcciones mínimas y localizadas.
2) No alteres respuesta correcta ni significado matemático.
3) Mantén estructura y formato salvo donde el issue lo requiera.
4) Si no hay cambios necesarios, devuelve UNCHANGED.
</task>

<output_fix_format>
JSON puro:
{{"status":"UNCHANGED"}}
o
{{
  "status":"FIXED",
  "changes":["..."],
  "corrected_content":"<contenido completo>"
}}
</output_fix_format>
"""


# Fix prompt public builder
def build_llm_fix_prompt(content: str, issues: list[str]) -> str:
    """Build an LLM fix prompt for encoding/manual issues."""
    return _LLM_FIX_PROMPT.format(
        standards=_STANDARDS,
        content=content,
        issues_list=_format_issues(issues),
    )
