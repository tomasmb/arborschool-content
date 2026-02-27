"""Prompts for auditing Chilean PAES notation and text quality.

Covers both QTI XML questions and mini-class HTML content.
Describes *what correct content looks like* rather than listing
known corruption patterns, to avoid biasing the model.

Three prompts:
- Scan+fix: identify issues and return full corrected content
- Validate: verify the corrected version against the original
- Retry: re-scan with feedback from a failed validation attempt
"""

from __future__ import annotations

# ------------------------------------------------------------------
# Scan + fix prompt (single-item version)
# ------------------------------------------------------------------

_SCAN_FIX_SINGLE = """\
<role>
Revisor experto de contenido educativo matemático para la prueba \
PAES M1 de Chile. Tu tarea es detectar problemas de notación \
numérica y calidad de texto, y devolver una versión corregida.
</role>

<chilean_notation_standard>
Chile usa formato numérico PAES, distinto al anglosajón:

SEPARADOR DECIMAL = coma (,)
  Correcto: 3,14  |  0,5  |  1,75  |  −2,33
  Incorrecto: 3.14  |  0.5  |  1.75  |  −2.33

SEPARADOR DE MILES = espacio (NO punto)
  Correcto: 10 000  |  25 000  |  1 250 000
  Incorrecto: 10.000  |  25.000  |  1.250.000
  Incorrecto: 10,000  |  25,000  |  1,250,000

COMBINADO:
  Correcto: 1 250,5  (mil doscientos cincuenta coma cinco)
  Incorrecto: 1.250,5  |  1,250.5

ENTEROS DE 4 DÍGITOS: pueden ir sin separador.
  Válido: 1000  |  1500  |  2025
  También válido: 1 000  |  1 500

Dentro de MathML, los valores en <mn> siguen la misma convención. \
El espacio de miles DEBE ser un espacio de no separación. Usa \
SIEMPRE la entidad XML &#160; para representarlo:
  Correcto: <mn>3,14</mn>  |  <mn>10&#160;000</mn>
  Incorrecto: <mn>3.14</mn>  |  <mn>10.000</mn>
  Incorrecto: un espacio normal dentro de <mn> (se puede cortar)

En texto plano (fuera de MathML), usa la misma entidad &#160; \
como separador de miles.

NÚMEROS GRANDES en MathML DEBEN estar en UN SOLO <mn>:
  Correcto: <mn>25&#160;000</mn>
  Incorrecto: <mn>25</mn><mspace width="..."/><mn>000</mn>

EXCEPCIONES — NO son errores de notación:
- Enteros sin separador de miles (e.g. "250", "15") son válidos.
- Números dentro de atributos XML, URLs, identificadores, \
sha256 hashes, o versiones de software.
- Coordenadas escritas como (x, y) donde la coma separa \
componentes, no decimales.
- Exponentes y subíndices (e.g. x², a₁) no son números con \
separador.
</chilean_notation_standard>

<text_quality_standard>
El contenido debe cumplir estas normas de calidad textual:

CODIFICACIÓN Y CARACTERES:
- Solo deben aparecer caracteres del español, símbolos \
matemáticos, y puntuación estándar.
- No debe haber secuencias hexadecimales, bytes sueltos, \
caracteres de control, ni caracteres de scripts no latinos \
(excepto letras griegas dentro de MathML).
- Las entidades HTML deben estar correctamente codificadas \
(no doble-codificadas).

NOTACIÓN MATEMÁTICA:
- Toda notación matemática debe usar MathML válido y bien \
formado (tags abiertos y cerrados, estructura correcta).
- No debe haber LaTeX crudo (\\frac, \\sqrt, $...$) en HTML.
- No debe haber Markdown crudo (**texto**, _texto_) en HTML.

INTEGRIDAD DEL CONTENIDO:
- No debe haber texto truncado a mitad de palabra u oración.
- No debe haber placeholders visibles (TODO, INSERT_HERE, etc.).
- No debe haber párrafos o frases duplicadas textualmente.
- No debe haber filtraciones de instrucciones del modelo.

Ignora: atributos src="...", xmlns, xsi:schemaLocation, \
identifier, URLs, hashes SHA. No corrijas gramática ni estilo.
</text_quality_standard>

<content>
{content}
</content>

<task>
Revisa el contenido buscando problemas de NOTATION (formato \
numérico PAES) y TEXT_QUALITY (calidad textual).

Si encuentras problemas, devuelve la versión COMPLETA corregida \
del contenido. Las correcciones deben ser MÍNIMAS: solo corrige \
lo necesario y no toques nada más. No reescribas, reformules \
ni reorganices contenido sano.

IMPORTANTE: la versión corregida debe ser el documento completo, \
no un fragmento. Debe poder reemplazar al original directamente.
</task>

<output_format>
JSON puro (sin markdown):

Si no hay problemas:
{{
  "status": "OK"
}}

Si hay problemas:
{{
  "status": "FIXED",
  "issues": [
    "Descripción breve del problema 1",
    "Descripción breve del problema 2"
  ],
  "corrected_content": "<contenido completo corregido>"
}}

REGLAS:
- corrected_content DEBE ser el documento COMPLETO (no un \
fragmento). Cópialo entero, aplicando solo las correcciones.
- Cada string en issues debe ser una línea breve describiendo \
un cambio realizado.
- Si no hay problemas reales, devuelve status "OK".
</output_format>
"""

# ------------------------------------------------------------------
# Scan + fix prompt (batch version for atom questions)
# ------------------------------------------------------------------

_SCAN_FIX_BATCH = """\
<role>
Revisor experto de contenido educativo matemático para la prueba \
PAES M1 de Chile. Tu tarea es detectar problemas de notación \
numérica y calidad de texto en un lote de preguntas QTI XML, \
y devolver versiones corregidas.
</role>

<chilean_notation_standard>
Chile usa formato numérico PAES, distinto al anglosajón:

SEPARADOR DECIMAL = coma (,)
  Correcto: 3,14  |  0,5  |  1,75  |  −2,33
  Incorrecto: 3.14  |  0.5  |  1.75  |  −2.33

SEPARADOR DE MILES = espacio (NO punto)
  Correcto: 10 000  |  25 000  |  1 250 000
  Incorrecto: 10.000  |  25.000  |  1.250.000
  Incorrecto: 10,000  |  25,000  |  1,250,000

COMBINADO:
  Correcto: 1 250,5  (mil doscientos cincuenta coma cinco)
  Incorrecto: 1.250,5  |  1,250.5

ENTEROS DE 4 DÍGITOS: pueden ir sin separador.
  Válido: 1000  |  1500  |  2025

Dentro de MathML, los valores en <mn> siguen la misma convención. \
El espacio de miles DEBE ser un espacio de no separación. Usa \
SIEMPRE la entidad XML &#160; para representarlo:
  Correcto: <mn>3,14</mn>  |  <mn>10&#160;000</mn>
  Incorrecto: <mn>3.14</mn>  |  <mn>10.000</mn>

En texto plano, usa también &#160; como separador de miles.

NÚMEROS GRANDES en MathML DEBEN estar en UN SOLO <mn>:
  Correcto: <mn>25&#160;000</mn>
  Incorrecto: <mn>25</mn><mspace width="..."/><mn>000</mn>

EXCEPCIONES — NO son errores:
- Enteros cortos sin separador ("250", "15") son válidos.
- Números en atributos XML, URLs, identificadores, hashes.
- Coordenadas (x, y) donde coma separa componentes.
</chilean_notation_standard>

<text_quality_standard>
CODIFICACIÓN: solo caracteres español, símbolos matemáticos, \
puntuación estándar. Sin hex, bytes sueltos, caracteres de \
control, scripts no latinos (excepto griegas en MathML).

NOTACIÓN MATEMÁTICA: MathML válido. Sin LaTeX crudo. Sin Markdown.

INTEGRIDAD: sin texto truncado, placeholders, duplicados, ni \
filtraciones de instrucciones.

Ignora: src, xmlns, xsi:schemaLocation, identifier, URLs, SHA. \
No corrijas gramática ni estilo.
</text_quality_standard>

<questions>
{content}
</questions>

<task>
Revisa CADA pregunta buscando problemas de NOTATION y TEXT_QUALITY.

Para cada pregunta con problemas, devuelve su QTI XML COMPLETO \
corregido. Solo incluye en el resultado las preguntas que \
necesitan corrección. Las correcciones deben ser MÍNIMAS.
</task>

<output_format>
JSON puro (sin markdown):

Si ninguna pregunta tiene problemas:
{{
  "items": []
}}

Si hay preguntas con problemas:
{{
  "items": [
    {{
      "item_id": "question-11",
      "issues": [
        "Descripción breve del cambio 1",
        "Descripción breve del cambio 2"
      ],
      "corrected_xml": "<qti-assessment-item ...>...</qti-assessment-item>"
    }}
  ]
}}

REGLAS:
- item_id = atributo identifier de la pregunta.
- corrected_xml = el QTI XML COMPLETO de esa pregunta (desde \
<qti-assessment-item> hasta </qti-assessment-item>).
- Solo incluye preguntas que tienen problemas reales.
- issues = lista breve de cambios realizados.
</output_format>
"""

# ------------------------------------------------------------------
# Validation prompt (compares original vs corrected)
# ------------------------------------------------------------------

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
Compara la versión original con la corregida. Verifica TODO:
1. Cada cambio aborda un problema real de notación o calidad.
2. No se alteró el significado matemático de ninguna expresión.
3. No se perdió ni agregó contenido fuera de las correcciones.
4. La estructura MathML/HTML sigue siendo válida.
5. No se introdujeron nuevos errores.
6. TODOS los símbolos de moneda ($) están preservados exactamente.
7. No se eliminaron operadores ni símbolos matemáticos.
8. La cantidad de alternativas de respuesta es la misma.
9. No se eliminó ni truncó texto narrativo o enunciados.
Si CUALQUIERA de estos puntos falla, el veredicto es FAIL.
</task>

<output_format>
JSON puro:
{{"verdict": "PASS"}}

Si hay problemas:
{{"verdict": "FAIL", "reasons": ["descripción del problema"]}}
</output_format>
"""

# ------------------------------------------------------------------
# Content-type preambles
# ------------------------------------------------------------------

_RETRY_PROMPT = """\
<role>
Revisor experto de contenido educativo matemático para la prueba \
PAES M1 de Chile. Un intento previo de corrección fue RECHAZADO. \
Debes producir una nueva versión corregida que evite los problemas \
identificados.
</role>

<previous_rejection>
La corrección anterior fue rechazada por estas razones:
{rejection_reasons}
</previous_rejection>

<original>
{original}
</original>

<task>
Produce una nueva versión corregida del contenido original que:
1. Corrija los problemas reales de notación PAES y calidad.
2. EVITE los errores señalados en previous_rejection.
3. Sea MÁS CONSERVADORA: solo corrige lo que estés 100% seguro.
4. NO elimines símbolos de moneda ($), operadores, ni contenido.
5. Preserva la estructura XML/HTML exacta excepto lo corregido.

Si después de considerar el rechazo crees que el original NO \
tiene problemas reales, devuelve status "OK".
</task>

<output_format>
JSON puro (sin markdown):

Si no hay problemas reales:
{{
  "status": "OK"
}}

Si hay problemas que puedes corregir de forma segura:
{{
  "status": "FIXED",
  "issues": ["Descripción breve del cambio"],
  "corrected_content": "<contenido completo corregido>"
}}
</output_format>
"""

# ------------------------------------------------------------------
# Content-type preambles
# ------------------------------------------------------------------

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


# ------------------------------------------------------------------
# Builder functions
# ------------------------------------------------------------------


def build_qti_batch_prompt(
    atom_id: str, qti_xmls: list[str],
) -> str:
    """Build a scan+fix prompt for a batch of QTI questions."""
    separator = "\n<!-- === NEXT ITEM === -->\n"
    combined = separator.join(qti_xmls)
    preamble = _QTI_BATCH_PREAMBLE.format(atom_id=atom_id)
    return (
        preamble + "\n\n"
        + _SCAN_FIX_BATCH.format(content=combined)
    )


def build_single_content_prompt(
    preamble: str, content: str,
) -> str:
    """Build a scan+fix prompt for a single content item."""
    return preamble + "\n\n" + _SCAN_FIX_SINGLE.format(
        content=content,
    )


def build_mini_class_prompt(atom_id: str, html: str) -> str:
    """Build a scan+fix prompt for a single mini-class."""
    preamble = _MINI_CLASS_PREAMBLE.format(atom_id=atom_id)
    return build_single_content_prompt(preamble, html)


def build_xml_file_prompt(file_label: str, xml: str) -> str:
    """Build a scan+fix prompt for a standalone QTI XML file."""
    preamble = _XML_FILE_PREAMBLE.format(file_label=file_label)
    return build_single_content_prompt(preamble, xml)


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


def build_validation_prompt(
    original: str,
    corrected: str,
    issues: list[str],
    content_type: str,
) -> str:
    """Build a validation prompt comparing original vs corrected.

    ``content_type`` is "QTI XML" or "HTML".
    """
    desc = "\n".join(f"- {i}" for i in issues) if issues else "(ninguna)"
    return _VALIDATE_PROMPT.format(
        content_type=content_type,
        issues_description=desc,
        original=original,
        corrected=corrected,
    )
