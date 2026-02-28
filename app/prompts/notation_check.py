"""Prompts for auditing Chilean PAES notation and text quality.

Prompt families: scan-only (Pass 1), fix-only (Pass 2),
validate (Pass 3), revalidate (Pass 4), retry.
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
puntuación. Sin secuencias hex, bytes sueltos, caracteres de \
control, ni scripts no latinos (excepto griegas en MathML). \
Entidades HTML correctamente codificadas (no doble-codificadas).

NOTACIÓN MATEMÁTICA: MathML válido y bien formado. Sin LaTeX \
crudo (\\frac, \\sqrt, $...$). Sin Markdown crudo.

INTEGRIDAD: sin texto truncado, placeholders, duplicados, ni \
filtraciones de instrucciones del modelo.

Ignora: src="...", xmlns, xsi:schemaLocation, identifier, URLs, \
hashes SHA. No corrijas gramática ni estilo.
</text_quality_standard>

"""

_STANDARDS = _NOTATION_STANDARD + _QUALITY_STANDARD

# -- Scan-only prompts — Pass 1: detect, no corrections -----------

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
Revisa el contenido buscando problemas de NOTATION (formato \
numérico PAES) y TEXT_QUALITY (calidad textual).
Solo REPORTA los problemas encontrados. NO generes contenido \
corregido.
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

_SCAN_ONLY_BATCH = """\
<role>
Revisor experto de contenido educativo matemático PAES M1 \
(Chile). DETECTAR problemas de notación numérica y calidad \
de texto en un lote de preguntas QTI XML. NO corrijas.
</role>

{standards}\
<questions>
{content}
</questions>

<task>
Revisa CADA pregunta buscando problemas de NOTATION y \
TEXT_QUALITY. Solo REPORTA los problemas por pregunta. \
NO generes XML corregido.
</task>

<output_format>
JSON puro (sin markdown):

Si ninguna pregunta tiene problemas:
{{"items": []}}

Si hay preguntas con problemas:
{{
  "items": [
    {{"item_id": "question-11", "issues": ["Descripción breve"]}}
  ]
}}

- item_id = atributo identifier de la pregunta.
- Solo incluye preguntas con problemas reales.
- NO incluyas corrected_xml.
</output_format>
"""


# -- Fix-only prompts — Pass 2: correct detected issues -----------

_FIX_ONLY_SINGLE = """\
<role>
Revisor experto de contenido educativo matemático PAES M1 \
(Chile). Tu tarea es CORREGIR los problemas detectados \
previamente y devolver una versión corregida.
</role>

{standards}\
<detected_issues>
{issues_description}
</detected_issues>

<content>
{content}
</content>

<task>
Los problemas en detected_issues fueron identificados por un \
escaneo previo. Produce una versión COMPLETA corregida que \
resuelva estos problemas. Correcciones MÍNIMAS: solo corrige \
lo necesario. La versión corregida debe ser el documento \
completo, no un fragmento.
</task>

<output_format>
JSON puro (sin markdown):

Si los problemas no son reales o ya están resueltos:
{{"status": "OK"}}

Si se realizaron correcciones:
{{
  "status": "FIXED",
  "issues": ["Descripción breve del cambio"],
  "corrected_content": "<contenido completo corregido>"
}}

- corrected_content DEBE ser el documento COMPLETO.
</output_format>
"""

_FIX_ONLY_BATCH = """\
<role>
Revisor experto de contenido educativo matemático PAES M1 \
(Chile). CORREGIR los problemas detectados previamente en \
un lote de preguntas QTI XML.
</role>

{standards}\
<detected_issues>
{issues_description}
</detected_issues>

<questions>
{content}
</questions>

<task>
Los problemas en detected_issues fueron identificados por un \
escaneo previo. Para cada pregunta con problemas, produce su \
QTI XML COMPLETO corregido. Solo incluye las preguntas que \
necesitan corrección. Correcciones MÍNIMAS.
</task>

<output_format>
JSON puro (sin markdown):

Si ninguna pregunta tiene problemas reales:
{{"items": []}}

Si hay correcciones:
{{
  "items": [
    {{
      "item_id": "question-11",
      "issues": ["Descripción breve del cambio"],
      "corrected_xml": "<qti-assessment-item>...</qti-assessment-item>"
    }}
  ]
}}

- item_id = atributo identifier de la pregunta.
- corrected_xml = QTI XML COMPLETO de esa pregunta.
</output_format>
"""


# -- Validate prompt — Pass 3: verify corrected version -----------

_VALIDATE_PROMPT = """\
<role>
Verificador QA de contenido PAES M1 (Chile) en formato \
{content_type}.
</role>

<changes_summary>
Cambios reportados:
{issues_description}
</changes_summary>

<original>
{original}
</original>

<corrected>
{corrected}
</corrected>

<task>
Compara original vs corregida. Verifica TODO:
1. Cada cambio aborda un problema real de notación o calidad.
2. Significado matemático idéntico en todas las expresiones.
3. No se perdió ni agregó contenido fuera de las correcciones.
4. Estructura MathML/HTML sigue válida.
5. Sin nuevos errores. Símbolos de moneda ($) preservados.
6. Misma cantidad de alternativas de respuesta.
7. Sin texto narrativo eliminado ni truncado.
Si CUALQUIERA falla, el veredicto es FAIL.
</task>

<output_format>
JSON puro:
{{"verdict": "PASS"}}

Si hay problemas:
{{"verdict": "FAIL", "reasons": ["descripción del problema"]}}
</output_format>
"""


# -- Revalidate prompt — Pass 4: semantic equivalence -------------

_REVALIDATE_PROMPT = """\
<role>
Auditor QA independiente de contenido educativo PAES M1 (Chile).
Tu única tarea es verificar que dos versiones de un contenido \
son equivalentes en significado.
</role>

<before>
{original}
</before>

<after>
{corrected}
</after>

<task>
La versión AFTER fue producida por un pipeline automatizado. \
Verifica TODOS estos puntos:
1. SIGNIFICADO MATEMÁTICO: ¿Mismo significado en ambas versiones?
2. RESPUESTA CORRECTA: ¿La respuesta correcta es la misma?
3. ALTERNATIVAS: ¿Todas las opciones presentes y equivalentes?
4. CONTENIDO COMPLETO: ¿Falta texto o párrafos en AFTER?
5. MATHML VÁLIDO: ¿El MathML en AFTER está bien formado?
6. NUEVOS ERRORES: ¿Se introdujo algún error nuevo?

NO evalúes formato numérico (comas vs puntos) ni separadores \
de miles — esos cambios son intencionales.
NO evalúes gramática ni estilo.
</task>

<output_format>
JSON puro:
{{"pass": true}}

Si hay problemas:
{{"pass": false, "issues": ["descripción del problema"]}}
</output_format>
"""


# -- Retry prompt -------------------------------------------------

_RETRY_PROMPT = """\
<role>
Revisor experto de contenido educativo matemático PAES M1 \
(Chile). Un intento previo de corrección fue RECHAZADO. \
Produce una nueva versión que evite los problemas identificados.
</role>

<previous_rejection>
{rejection_reasons}
</previous_rejection>

<original>
{original}
</original>

<task>
Produce una versión corregida que:
1. Corrija problemas reales de notación PAES y calidad.
2. EVITE los errores señalados en previous_rejection.
3. Sea MÁS CONSERVADORA: solo corrige lo 100% seguro.
4. NO elimines símbolos ($), operadores, ni contenido.
Si el original NO tiene problemas reales, devuelve "OK".
</task>

<output_format>
JSON puro (sin markdown):

Si no hay problemas reales:
{{"status": "OK"}}

Si hay correcciones seguras:
{{
  "status": "FIXED",
  "issues": ["Descripción breve del cambio"],
  "corrected_content": "<contenido completo corregido>"
}}
</output_format>
"""


# -- Preambles ----------------------------------------------------

_QTI_BATCH_PREAMBLE = """\
Lote de preguntas QTI XML del átomo {atom_id}. \
Cada pregunta está delimitada por <qti-assessment-item>.\
"""

_MINI_CLASS_PREAMBLE = """\
Mini-clase HTML educativa del átomo {atom_id}.\
"""

_XML_FILE_PREAMBLE = """\
Pregunta QTI XML individual ({file_label}).\
"""

# -- Builders: scan-only (Pass 1) ---------------------------------


def build_scan_batch_prompt(
    atom_id: str, qti_xmls: list[str],
) -> str:
    """Build a scan-only prompt for a batch of QTI questions."""
    separator = "\n<!-- === NEXT ITEM === -->\n"
    preamble = _QTI_BATCH_PREAMBLE.format(atom_id=atom_id)
    return preamble + "\n\n" + _SCAN_ONLY_BATCH.format(
        standards=_STANDARDS, content=separator.join(qti_xmls),
    )


def build_scan_mini_class_prompt(
    atom_id: str, html: str,
) -> str:
    """Build a scan-only prompt for a single mini-class."""
    preamble = _MINI_CLASS_PREAMBLE.format(atom_id=atom_id)
    return preamble + "\n\n" + _SCAN_ONLY_SINGLE.format(
        standards=_STANDARDS, content=html,
    )


def build_scan_xml_file_prompt(
    file_label: str, xml: str,
) -> str:
    """Build a scan-only prompt for a standalone QTI XML file."""
    preamble = _XML_FILE_PREAMBLE.format(file_label=file_label)
    return preamble + "\n\n" + _SCAN_ONLY_SINGLE.format(
        standards=_STANDARDS, content=xml,
    )

# -- Builders: fix-only (Pass 2) ----------------------------------


def _format_issues(issues: list[str]) -> str:
    if issues:
        return "\n".join(f"- {i}" for i in issues)
    return "(ninguna)"


def build_fix_batch_prompt(
    atom_id: str,
    items_with_issues: list[dict],
    qti_xmls: list[str],
) -> str:
    """Build a fix prompt for a batch of flagged QTI questions.

    ``items_with_issues``: dicts with ``item_id`` and ``issues``.
    """
    separator = "\n<!-- === NEXT ITEM === -->\n"
    lines: list[str] = []
    for item in items_with_issues:
        iid = item.get("item_id", "?")
        for issue in item.get("issues", []):
            lines.append(f"- {iid}: {issue}")
    preamble = _QTI_BATCH_PREAMBLE.format(atom_id=atom_id)
    return preamble + "\n\n" + _FIX_ONLY_BATCH.format(
        standards=_STANDARDS,
        content=separator.join(qti_xmls),
        issues_description="\n".join(lines) or "(ninguna)",
    )


def build_fix_mini_class_prompt(
    atom_id: str, html: str, issues: list[str],
) -> str:
    """Build a fix prompt for a single mini-class."""
    preamble = _MINI_CLASS_PREAMBLE.format(atom_id=atom_id)
    return preamble + "\n\n" + _FIX_ONLY_SINGLE.format(
        standards=_STANDARDS,
        content=html,
        issues_description=_format_issues(issues),
    )


def build_fix_xml_file_prompt(
    file_label: str, xml: str, issues: list[str],
) -> str:
    """Build a fix prompt for a standalone QTI XML file."""
    preamble = _XML_FILE_PREAMBLE.format(file_label=file_label)
    return preamble + "\n\n" + _FIX_ONLY_SINGLE.format(
        standards=_STANDARDS,
        content=xml,
        issues_description=_format_issues(issues),
    )

# -- Builders: validate, revalidate, retry ------------------------


def build_validation_prompt(
    original: str,
    corrected: str,
    issues: list[str],
    content_type: str,
) -> str:
    """Build a validation prompt comparing original vs corrected."""
    return _VALIDATE_PROMPT.format(
        content_type=content_type,
        issues_description=_format_issues(issues),
        original=original,
        corrected=corrected,
    )


def build_revalidation_prompt(
    original: str,
    corrected: str,
) -> str:
    """Build an independent semantic equivalence check prompt."""
    return _REVALIDATE_PROMPT.format(
        original=original,
        corrected=corrected,
    )


def build_retry_prompt(
    original: str,
    rejection_reasons: list[str],
) -> str:
    """Build a retry prompt with feedback from failed validation."""
    reasons_text = "\n".join(
        f"- {r}" for r in rejection_reasons
    ) if rejection_reasons else "(sin detalles)"
    return _RETRY_PROMPT.format(
        original=original,
        rejection_reasons=reasons_text,
    )
