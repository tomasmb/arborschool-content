"""Prompts for auditing Chilean PAES notation and text quality.

Prompt families:
- scan-only (Pass 1, low reasoning): detect issues per item.
- confirm (Pass 2, medium reasoning): validate flagged issues,
  eliminate false positives, and categorise confirmed issues.
"""

from __future__ import annotations

# -- Shared notation and quality standard sections ----------------

_NOTATION_STANDARD = """\
<chilean_notation_standard>
Chile usa formato numérico PAES, distinto al anglosajón:

SEPARADOR DECIMAL = coma (,)
  Correcto: 3,14  |  0,5  |  1,75  |  Incorrecto: 3.14  |  0.5

SEPARADOR DE MILES = espacio (NO punto)
  Correcto: 10 000  |  25 000  |  1 250 000
  Incorrecto: 10.000  |  25.000  |  10,000  |  25,000

COMBINADO: 1 250,5 (correcto)  |  1.250,5 / 1,250.5 (incorrecto)

ENTEROS DE 4 DÍGITOS: sin separador es válido (1000, 1500, 2025).

Dentro de MathML, los valores en <mn> siguen la misma convención. \
El espacio de miles DEBE ser &#160; (espacio de no separación):
  Correcto: <mn>3,14</mn>  |  <mn>10&#160;000</mn>
  Incorrecto: <mn>3.14</mn>  |  <mn>10.000</mn>
  Incorrecto: un espacio normal dentro de <mn> (se puede cortar)

En texto plano, usa también &#160; como separador de miles.

NÚMEROS GRANDES en MathML DEBEN estar en UN SOLO <mn>:
  Correcto: <mn>25&#160;000</mn>
  Incorrecto: <mn>25</mn><mspace width="..."/><mn>000</mn>

EXCEPCIONES — NO son errores de notación:
- Enteros sin separador de miles (e.g. "250", "15") son válidos.
- Números en atributos XML, URLs, identificadores, hashes SHA.
- Coordenadas (x, y) donde la coma separa componentes.
- Exponentes y subíndices (e.g. x², a₁).
</chilean_notation_standard>

"""

_QUALITY_STANDARD = """\
<text_quality_standard>
CODIFICACIÓN: solo caracteres del español, símbolos matemáticos, \
puntuación y emojis pedagógicos (❌ ✔ ✅ ❗ etc.). \
Sin secuencias hex, bytes sueltos, caracteres de control, ni \
scripts no latinos (excepto griegas en MathML). Entidades HTML \
correctamente codificadas (no doble-codificadas). En QTI XML, \
no debe haber entidades HTML con nombre (&oacute;, &minus;) — \
solo Unicode directo o numéricas. EXCEPCIÓN: las 5 entidades \
predefinidas de XML (&amp; &lt; &gt; &quot; &apos;) SÍ son \
válidas y NO deben reportarse.

NOTACIÓN MATEMÁTICA: MathML válido y bien formado. Sin LaTeX \
crudo (\\frac, \\sqrt, $...$). Sin Markdown crudo. Números \
grandes no deben estar divididos en múltiples <mn> separados \
por <mspace>.

INTEGRIDAD: sin texto truncado, placeholders, duplicados, ni \
filtraciones de instrucciones del modelo.

NO reportar como problema:
- Emojis (❌, ✔, ✅, ❗) — son intencionales.
- Gramática, ortografía, estilo o redacción.
- Números en atributos XML, URLs, identificadores, hashes SHA.
- Coordenadas tipo (x, y) donde la coma separa componentes.
- xmlns, xsi:schemaLocation, src="...".
- Entidades XML predefinidas (&amp; &lt; &gt; &quot; &apos;).
- Operadores (−, +, ×) dentro de <mn>: es cosmético, no afecta \
al estudiante.
</text_quality_standard>

"""

_STANDARDS = _NOTATION_STANDARD + _QUALITY_STANDARD

# -- Scan-only prompt — Pass 1: detect, no corrections -----------

_SCAN_ONLY_SINGLE = """\
<role>
Revisor experto de contenido educativo matemático PAES M1 \
(Chile). Tu tarea es DETECTAR problemas de notación numérica \
y calidad de texto. NO corrijas nada.
</role>

{standards}\
<content>
{content}
</content>

<task>
Revisa el contenido buscando SOLO estos tipos de problema:

NOTACIÓN NUMÉRICA PAES:
- Punto como separador de miles (10.000 → 10 000).
- Punto como separador decimal (3.14 → 3,14).
- Falta separador de miles en números ≥ 5 dígitos (25000 → \
25 000 o 25&#160;000 en MathML).

MATHML ESTRUCTURAL:
- Número grande dividido en múltiples <mn> con <mspace> \
(debe ser un solo <mn>).
- Espacio normal dentro de <mn> (debe ser &#160;).
- NO reportar operadores (−, ×, +) dentro de <mn>: es \
cosmético y no afecta la visualización.

CODIFICACIÓN Y ENTIDADES:
- Texto corrupto/garbled (mojibake, bytes hex, caracteres \
de control, tabulaciones).
- Entidades HTML con nombre en QTI XML (&oacute;, &minus;) \
que deberían ser Unicode directo o numéricas. NO reportar \
las 5 predefinidas XML (&amp; &lt; &gt; &quot; &apos;).
- Doble-codificación de entidades (&amp;amp;).

INTEGRIDAD:
- LaTeX crudo (\\frac, $...$) o Markdown crudo en HTML/XML.
- Texto truncado, placeholders, instrucciones del modelo.

Solo REPORTA los problemas encontrados. NO generes contenido \
corregido. Sé PRECISO: indica qué texto o fragmento tiene \
el problema.
</task>

<output_format>
JSON puro (sin markdown):

Si no hay problemas:
{{"status": "OK"}}

Si hay problemas:
{{"status": "HAS_ISSUES", "issues": ["Descripción breve"]}}

- Cada string en issues describe un problema encontrado.
- NO incluyas contenido corregido.
</output_format>
"""


# -- Confirm-issues prompt — Pass 2: validate + categorise --------

ISSUE_CATEGORIES = (
    "deterministic_thousands_sep",
    "deterministic_encoding",
    "deterministic_spacing",
    "manual_fix",
    "ignore",
)

_CONFIRM_ISSUES_PROMPT = """\
<role>
Auditor QA senior de contenido educativo matemático PAES M1 \
(Chile). Un escaneo automático previo (modelo de baja capacidad) \
marcó los problemas listados abajo. Tu tarea es:
1. Confirmar cuáles son problemas REALES.
2. Descartar falsos positivos.
3. Clasificar cada problema real en una categoría de corrección.
</role>

{standards}\
<content>
{content}
</content>

<flagged_issues>
{issues_list}
</flagged_issues>

<task>
Para CADA problema en flagged_issues:
1. Revisa si es un problema REAL en el contenido.
2. Si es real, clasifícalo en UNA de estas categorías:
   - "deterministic_thousands_sep": punto como separador de \
miles, o número de 5+ dígitos sin separador de miles en texto \
plano o MathML (montos en pesos, cantidades enteras).
   - "deterministic_encoding": texto con bytes corruptos, \
caracteres de control, tabulaciones, hex incrustado, tildes \
faltantes por corrupción (NO tildes gramaticales).
   - "deterministic_spacing": espacio normal dentro de <mn> \
(debe ser &#160;), o espacio normal como separador de miles \
en texto plano (debe ser &#160;).
   - "manual_fix": problemas reales que requieren juicio humano \
(texto en inglés, contenido duplicado, errores semánticos).
   - "ignore": NO es un problema real, o es un cambio de estilo \
/ gramática que no debe tocarse.
3. Si el modelo previo sugirió algo INCORRECTO (falso positivo), \
clasifícalo como "ignore" y explica brevemente por qué.

Sé CONSERVADOR: ante la duda, clasifica como "manual_fix" o \
"ignore". NO inventes problemas que no estén en flagged_issues.
</task>

<output_format>
JSON puro (sin markdown):
{{
  "confirmed": [
    {{
      "issue": "Descripción del problema real",
      "category": "deterministic_thousands_sep"
    }}
  ],
  "rejected": [
    {{
      "original_issue": "Lo que reportó el escaneo previo",
      "reason": "Por qué es falso positivo"
    }}
  ]
}}

- "confirmed" contiene SOLO problemas reales con su categoría.
- "rejected" contiene los falsos positivos descartados.
- Si TODO es falso positivo: {{"confirmed": [], "rejected": [...]}}
- Si TODO es real: {{"confirmed": [...], "rejected": []}}
</output_format>
"""

# -- Preambles ----------------------------------------------------

_MINI_CLASS_PREAMBLE = """\
Mini-clase HTML educativa del átomo {label}.\
"""

_XML_FILE_PREAMBLE = """\
Pregunta QTI XML individual ({label}).\
"""

# -- Helpers ------------------------------------------------------


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


# -- Builders: scan-only (Pass 1) ---------------------------------


def build_scan_mini_class_prompt(
    label: str, html: str,
) -> str:
    """Build a scan-only prompt for a single mini-class."""
    preamble = _MINI_CLASS_PREAMBLE.format(label=label)
    return preamble + "\n\n" + _SCAN_ONLY_SINGLE.format(
        standards=_STANDARDS, content=html,
    )


def build_scan_xml_file_prompt(
    label: str, xml: str,
) -> str:
    """Build a scan-only prompt for a single QTI XML item."""
    preamble = _XML_FILE_PREAMBLE.format(label=label)
    return preamble + "\n\n" + _SCAN_ONLY_SINGLE.format(
        standards=_STANDARDS, content=xml,
    )


# -- Compatibility wrappers used by scripts.qa_scan --------------


def build_scan_question_prompt(label: str, content: str) -> str:
    """Compatibility wrapper for question scan prompt."""
    return build_scan_xml_file_prompt(label, content)


def build_scan_lesson_prompt(label: str, content: str) -> str:
    """Compatibility wrapper for lesson scan prompt."""
    return build_scan_mini_class_prompt(label, content)


def build_scan_prompt(source: str, label: str, content: str) -> str:
    """Source-routed scan builder used by QA scripts."""
    if source in {"lesson", "mini-class"}:
        return build_scan_lesson_prompt(label, content)
    return build_scan_question_prompt(label, content)


# -- Builders: confirm-issues (Pass 2) ----------------------------


def build_confirm_prompt(
    content: str,
    issues: list[str | dict],
    *,
    source: str | None = None,
) -> str:
    """Build a confirm-issues prompt for a single item.

    *content*: the original HTML / QTI XML of the item.
    *issues*: the issue descriptions from the scan pass.
    """
    _ = source
    return _CONFIRM_ISSUES_PROMPT.format(
        standards=_STANDARDS,
        content=content,
        issues_list=_format_issues(issues),
    )


# -- LLM fix prompt — for encoding + manual_fix -------------------

_LLM_FIX_PROMPT = """\
<role>
Corrector experto de contenido educativo PAES M1 (Chile). \
Tu tarea es corregir SOLO los problemas específicos listados \
abajo. NO cambies NADA más.
</role>

{standards}\
<content>
{content}
</content>

<issues_to_fix>
{issues_list}
</issues_to_fix>

<task>
Corrige EXCLUSIVAMENTE los problemas listados en issues_to_fix.
Reglas estrictas:
1. Correcciones MÍNIMAS: solo lo necesario para cada problema.
2. NO cambies formato numérico, separadores, ni MathML.
3. NO elimines contenido, símbolos ($, %, °), ni alternativas.
4. NO cambies la respuesta correcta ni el orden de opciones.
5. Devuelve el contenido COMPLETO corregido.
Si los problemas no son reales o no requieren cambios, \
devuelve el original sin modificar.
</task>

<output_format>
JSON puro (sin markdown):
Si no hay cambios necesarios:
{{"status": "UNCHANGED"}}

Si hay correcciones:
{{
  "status": "FIXED",
  "changes": ["Descripción breve de cada cambio"],
  "corrected_content": "<contenido completo corregido>"
}}
</output_format>
"""


def build_llm_fix_prompt(
    content: str, issues: list[str],
) -> str:
    """Build an LLM fix prompt for encoding/manual issues."""
    return _LLM_FIX_PROMPT.format(
        standards=_STANDARDS,
        content=content,
        issues_list=_format_issues(issues),
    )
