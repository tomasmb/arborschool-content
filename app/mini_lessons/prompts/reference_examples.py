"""HTML reference examples for mini-lesson LLM prompts.

Provides complete, structurally correct HTML examples per template
type (P, C, M) that are injected into generation prompts as
structural anchors. The LLM pattern-matches against these to
produce well-formed, spec-compliant output.

Content is ONLY a structural reference — the LLM receives separate
atom/enrichment/plan context that drives the actual content.

NOTE: these strings are injected via str.format(), so they MUST NOT
contain unescaped curly braces.
"""

from __future__ import annotations

# ------------------------------------------------------------------
# Template P — Procedural atom reference
# ------------------------------------------------------------------

TEMPLATE_P_REFERENCE = """\
<article data-kind="mini-class"
         data-atom-id="A-M1-ALG-01-12"
         data-template="P">
  <header data-block="objective">
    <h1>Mini-clase: Factorización por factor común</h1>
    <p data-role="learning-objective">\
Al terminar esta mini-clase podrás extraer el máximo factor \
común de una expresión algebraica y reescribirla como producto.</p>
    <p data-role="paes-relevance">\
Este procedimiento aparece en al menos 2 preguntas por prueba PAES.</p>
  </header>

  <section data-block="concept">
    <h2>Idea clave</h2>
    <p>Factorizar por factor común es reescribir una suma como un \
<strong>producto</strong>: encuentras el mayor monomio que divide a \
todos los términos y lo sacas fuera de un paréntesis.</p>
    <p>Pasos: (1) halla el MCD de los coeficientes, (2) toma la \
menor potencia de cada variable común, (3) divide cada término \
por ese factor y escribe el resultado entre paréntesis.</p>
  </section>

  <section data-block="worked-example" data-index="1">
    <h2>Ejemplo resuelto 1</h2>
    <p>Factoriza <math xmlns="http://www.w3.org/1998/Math/MathML">\
<mrow><mn>6</mn><msup><mi>x</mi><mn>2</mn></msup>\
<mo>+</mo><mn>9</mn><mi>x</mi></mrow></math>.</p>
    <ol>
      <li><strong>Paso 1:</strong> MCD de 6 y 9 es 3.</li>
      <li><strong>Paso 2:</strong> Menor potencia de \
<math xmlns="http://www.w3.org/1998/Math/MathML">\
<mi>x</mi></math> presente en ambos términos: \
<math xmlns="http://www.w3.org/1998/Math/MathML">\
<msup><mi>x</mi><mn>1</mn></msup></math>.</li>
      <li><strong>Paso 3:</strong> Factor común = \
<math xmlns="http://www.w3.org/1998/Math/MathML">\
<mrow><mn>3</mn><mi>x</mi></mrow></math>.</li>
      <li><strong>Paso 4:</strong> Divide cada término: \
<math xmlns="http://www.w3.org/1998/Math/MathML">\
<mrow><mn>3</mn><mi>x</mi><mo>(</mo><mn>2</mn><mi>x</mi>\
<mo>+</mo><mn>3</mn><mo>)</mo></mrow></math>.</li>
      <li><strong>Verificación:</strong> \
<math xmlns="http://www.w3.org/1998/Math/MathML">\
<mrow><mn>3</mn><mi>x</mi><mo>&middot;</mo><mn>2</mn><mi>x</mi>\
<mo>=</mo><mn>6</mn><msup><mi>x</mi><mn>2</mn></msup></mrow>\
</math> y \
<math xmlns="http://www.w3.org/1998/Math/MathML">\
<mrow><mn>3</mn><mi>x</mi><mo>&middot;</mo><mn>3</mn><mo>=</mo>\
<mn>9</mn><mi>x</mi></mrow></math>. Correcto.</li>
    </ol>
  </section>

  <section data-block="worked-example" data-index="2">
    <h2>Ejemplo resuelto 2</h2>
    <p>Factoriza \
<math xmlns="http://www.w3.org/1998/Math/MathML"><mrow>\
<mn>12</mn><msup><mi>a</mi><mn>3</mn></msup><mi>b</mi>\
<mo>-</mo><mn>18</mn><msup><mi>a</mi><mn>2</mn></msup>\
<msup><mi>b</mi><mn>2</mn></msup>\
<mo>+</mo><mn>6</mn><mi>a</mi><mi>b</mi>\
</mrow></math>.</p>
    <ol>
      <li><strong>Paso 1:</strong> MCD de 12, 18 y 6 es 6. \
Menor potencia de <em>a</em>: \
<math xmlns="http://www.w3.org/1998/Math/MathML">\
<msup><mi>a</mi><mn>1</mn></msup></math>. \
Menor potencia de <em>b</em>: \
<math xmlns="http://www.w3.org/1998/Math/MathML">\
<msup><mi>b</mi><mn>1</mn></msup></math>. \
Factor común: \
<math xmlns="http://www.w3.org/1998/Math/MathML">\
<mrow><mn>6</mn><mi>a</mi><mi>b</mi></mrow></math>.</li>
      <li><strong>Paso 2:</strong> Divide cada término y escribe: \
<math xmlns="http://www.w3.org/1998/Math/MathML"><mrow>\
<mn>6</mn><mi>a</mi><mi>b</mi><mo>(</mo>\
<mn>2</mn><msup><mi>a</mi><mn>2</mn></msup>\
<mo>-</mo><mn>3</mn><mi>a</mi><mi>b</mi>\
<mo>+</mo><mn>1</mn><mo>)</mo></mrow></math>.</li>
    </ol>
  </section>

  <section data-block="quick-check" data-index="1"
           data-format="mcq-abcd">
    <h3>Quick Check 1</h3>
    <p data-role="question-stem">\
¿Cuál es el factor común de \
<math xmlns="http://www.w3.org/1998/Math/MathML"><mrow>\
<mn>8</mn><msup><mi>x</mi><mn>3</mn></msup>\
<mo>+</mo><mn>12</mn><msup><mi>x</mi><mn>2</mn></msup>\
</mrow></math>?</p>
    <ol data-role="options" data-option-format="ABCD">
      <li data-option="A">\
<math xmlns="http://www.w3.org/1998/Math/MathML"><mrow>\
<mn>2</mn><mi>x</mi></mrow></math></li>
      <li data-option="B">\
<math xmlns="http://www.w3.org/1998/Math/MathML"><mrow>\
<mn>4</mn><msup><mi>x</mi><mn>2</mn></msup></mrow></math></li>
      <li data-option="C">\
<math xmlns="http://www.w3.org/1998/Math/MathML"><mrow>\
<mn>4</mn><msup><mi>x</mi><mn>3</mn></msup></mrow></math></li>
      <li data-option="D">\
<math xmlns="http://www.w3.org/1998/Math/MathML"><mrow>\
<mn>8</mn><mi>x</mi></mrow></math></li>
    </ol>
    <div data-role="feedback" data-feedback-type="explanatory">
      <p data-correct-option="B">\
MCD de 8 y 12 es 4; menor potencia de x es x². \
Factor común: 4x².</p>
      <ul data-role="distractor-rationale">
        <li data-option="A">\
2x divide ambos términos, pero no es el máximo factor.</li>
        <li data-option="C">\
x³ no divide a 12x² (dejaría potencia negativa).</li>
        <li data-option="D">\
8 no divide a 12, así que 8x no es factor común.</li>
      </ul>
    </div>
  </section>

  <section data-block="quick-check" data-index="2"
           data-format="mcq-abcd">
    <h3>Quick Check 2</h3>
    <p data-role="question-stem">\
¿Cuál factorización de \
<math xmlns="http://www.w3.org/1998/Math/MathML"><mrow>\
<mn>15</mn><mi>y</mi><mo>-</mo><mn>10</mn>\
</mrow></math> es correcta?</p>
    <ol data-role="options" data-option-format="ABCD">
      <li data-option="A">5(3y - 2)</li>
      <li data-option="B">5(3y + 2)</li>
      <li data-option="C">5y(3 - 2)</li>
      <li data-option="D">3(5y - 10)</li>
    </ol>
    <div data-role="feedback" data-feedback-type="explanatory">
      <p data-correct-option="A">\
MCD de 15 y 10 es 5. Al dividir: 15y/5 = 3y y 10/5 = 2. \
El signo resta se mantiene: 5(3y - 2).</p>
      <ul data-role="distractor-rationale">
        <li data-option="B">\
El signo cambió: debería ser resta, no suma.</li>
        <li data-option="C">\
y no está en el segundo término, así que no puede ir en el \
factor común.</li>
        <li data-option="D">\
3 divide a 15 pero no es el máximo factor de 15 y 10.</li>
      </ul>
    </div>
  </section>

  <section data-block="error-patterns">
    <h2>Errores frecuentes y tip PAES</h2>
    <ul>
      <li><strong>Factor no máximo:</strong> Sacas 2x cuando el \
factor es 4x². Siempre busca el MCD completo.</li>
      <li><strong>Potencia incorrecta:</strong> Tomas la mayor \
potencia en vez de la menor. Regla: la menor potencia es la \
que divide a todos.</li>
      <li><strong>Signos:</strong> Al sacar factor negativo, todos \
los signos dentro del paréntesis cambian.</li>
      <li><strong>Factor incompleto:</strong> Sacas solo el número \
y olvidas la parte literal. Revisa coeficiente y variables.</li>
    </ul>
    <p><strong>Tip PAES:</strong> Verifica tu respuesta multiplicando \
el factor por el paréntesis. Si recuperas la expresión original, \
está correcta.</p>
  </section>

  <section data-block="transition-to-adaptive">
    <h2>A practicar</h2>
    <p>Ahora pasas al set adaptativo donde practicarás factorización \
con dificultad creciente.</p>
  </section>
</article>"""


# ------------------------------------------------------------------
# Template C — Conceptual atom reference
# ------------------------------------------------------------------

TEMPLATE_C_REFERENCE = """\
<article data-kind="mini-class"
         data-atom-id="A-M1-ALG-03-01"
         data-template="C">
  <header data-block="objective">
    <h1>Mini-clase: Concepto de función</h1>
    <p data-role="learning-objective">\
Al terminar esta mini-clase podrás distinguir si una relación \
entre variables es o no una función.</p>
    <p data-role="paes-relevance">\
Identificar funciones es base para al menos 5 preguntas PAES \
sobre gráficos e interpretación.</p>
  </header>

  <section data-block="concept">
    <h2>¿Qué es y qué NO es una función?</h2>
    <table>
      <thead>
        <tr><th>Es función</th><th>No es función</th></tr>
      </thead>
      <tbody>
        <tr>
          <td>Cada valor de entrada tiene exactamente una salida</td>
          <td>Una entrada tiene dos o más salidas distintas</td>
        </tr>
        <tr>
          <td>Pasa la prueba de la recta vertical</td>
          <td>Una recta vertical corta la curva en más de un punto</td>
        </tr>
      </tbody>
    </table>
  </section>

  <section data-block="worked-example" data-index="1">
    <h2>Ejemplo resuelto 1 — Interpretación</h2>
    <p>Se da una tabla de valores:</p>
    <table>
      <thead><tr><th>x</th><th>y</th></tr></thead>
      <tbody>
        <tr><td>1</td><td>3</td></tr>
        <tr><td>2</td><td>5</td></tr>
        <tr><td>3</td><td>7</td></tr>
      </tbody>
    </table>
    <p><strong>¿Es función?</strong> Cada x tiene una sola y. \
Sí, es función.</p>
  </section>

  <section data-block="worked-example" data-index="2">
    <h2>Ejemplo resuelto 2 — Decisión</h2>
    <p>Se da un conjunto de pares ordenados: \
(1, 2), (1, 5), (3, 4).</p>
    <p><strong>¿Es función?</strong> La entrada x = 1 tiene dos \
salidas distintas (2 y 5). No es función.</p>
    <p>Criterio rápido: si algún x se repite con distinta y, \
no es función.</p>
  </section>

  <section data-block="quick-check" data-index="1"
           data-format="mcq-abcd">
    <h3>Quick Check</h3>
    <p data-role="question-stem">\
¿Cuál conjunto de pares representa una función?</p>
    <ol data-role="options" data-option-format="ABCD">
      <li data-option="A">(1,3), (2,3), (3,5)</li>
      <li data-option="B">(1,2), (1,4), (2,5)</li>
      <li data-option="C">(2,1), (2,3), (3,1)</li>
      <li data-option="D">(4,1), (4,2), (4,3)</li>
    </ol>
    <div data-role="feedback" data-feedback-type="explanatory">
      <p data-correct-option="A">\
Cada x (1, 2, 3) aparece una sola vez. Que dos x den la misma y \
(como x=1 y x=2 dando y=3) no importa.</p>
      <ul data-role="distractor-rationale">
        <li data-option="B">\
x = 1 aparece con y = 2 e y = 4. No es función.</li>
        <li data-option="C">\
x = 2 aparece con y = 1 e y = 3. No es función.</li>
        <li data-option="D">\
x = 4 aparece tres veces con distintas y. No es función.</li>
      </ul>
    </div>
  </section>

  <section data-block="error-patterns">
    <h2>Errores frecuentes y tip PAES</h2>
    <ul>
      <li><strong>Confundir inyectividad con función:</strong> Que \
dos x den la misma y no la descalifica como función.</li>
      <li><strong>Recta vertical mal aplicada:</strong> La recta \
vertical se aplica al gráfico, no a la tabla directamente.</li>
    </ul>
    <p><strong>Tip PAES:</strong> Busca si algún x se repite con \
distinta y. Si no encuentras ninguno, es función.</p>
  </section>

  <section data-block="transition-to-adaptive">
    <h2>A practicar</h2>
    <p>Ahora pasas al set adaptativo con ejercicios sobre \
identificación de funciones.</p>
  </section>
</article>"""


# ------------------------------------------------------------------
# Template M — Mixed atom reference
# ------------------------------------------------------------------

TEMPLATE_M_REFERENCE = """\
<article data-kind="mini-class"
         data-atom-id="A-M1-ALG-04-01"
         data-template="M">
  <header data-block="objective">
    <h1>Mini-clase: Ecuación de la recta desde dos puntos</h1>
    <p data-role="learning-objective">\
Al terminar esta mini-clase podrás obtener la ecuación de una \
recta dados dos puntos y explicar qué representan pendiente \
e intercepto.</p>
    <p data-role="paes-relevance">\
Ecuaciones de rectas aparecen en problemas de modelación y \
gráficos en la PAES.</p>
  </header>

  <section data-block="concept">
    <h2>Idea clave</h2>
    <p>La pendiente <em>m</em> mide cuánto cambia <em>y</em> por \
cada unidad de <em>x</em>. Con dos puntos puedes calcular \
<em>m</em> y luego usar la forma punto-pendiente para llegar a \
<em>y = mx + b</em>.</p>
  </section>

  <section data-block="worked-example" data-index="1">
    <h2>Ejemplo resuelto 1 — Procedimiento</h2>
    <p>Encuentra la ecuación de la recta que pasa por (1, 3) \
y (3, 7).</p>
    <ol>
      <li><strong>Paso 1:</strong> Calcula la pendiente: \
m = (7 - 3)/(3 - 1) = 4/2 = 2.</li>
      <li><strong>Paso 2:</strong> Usa punto-pendiente con (1, 3): \
y - 3 = 2(x - 1).</li>
      <li><strong>Paso 3:</strong> Simplifica: y = 2x + 1.</li>
    </ol>
  </section>

  <section data-block="worked-example" data-index="2">
    <h2>Ejemplo resuelto 2 — Conceptual</h2>
    <p>Una tienda cobra $500 fijos + $200 por km de reparto. \
Puntos: (0, 500) y (3, 1100).</p>
    <ol>
      <li><strong>Paso 1:</strong> m = (1100 - 500)/(3 - 0) = 200. \
Interpretación: cada km extra cuesta $200.</li>
      <li><strong>Paso 2:</strong> b = 500 (cargo fijo). \
Ecuación: y = 200x + 500.</li>
    </ol>
    <p>La pendiente tiene significado concreto: costo por km.</p>
  </section>

  <section data-block="quick-check" data-index="1"
           data-format="mcq-abcd">
    <h3>Quick Check 1</h3>
    <p data-role="question-stem">\
¿Cuál es la pendiente de la recta que pasa por (-1, 4) \
y (2, -2)?</p>
    <ol data-role="options" data-option-format="ABCD">
      <li data-option="A">-2</li>
      <li data-option="B">2</li>
      <li data-option="C">-1/2</li>
      <li data-option="D">6</li>
    </ol>
    <div data-role="feedback" data-feedback-type="explanatory">
      <p data-correct-option="A">\
m = (-2 - 4)/(2 - (-1)) = -6/3 = -2.</p>
      <ul data-role="distractor-rationale">
        <li data-option="B">\
Olvidaste el signo negativo del numerador.</li>
        <li data-option="C">\
Invertiste numerador y denominador.</li>
        <li data-option="D">\
Sumaste en vez de dividir: -6 no es la pendiente, \
es solo el numerador.</li>
      </ul>
    </div>
  </section>

  <section data-block="quick-check" data-index="2"
           data-format="mcq-abcd">
    <h3>Quick Check 2</h3>
    <p data-role="question-stem">\
Si y = 3x - 5, ¿cuál es el intercepto con el eje y?</p>
    <ol data-role="options" data-option-format="ABCD">
      <li data-option="A">3</li>
      <li data-option="B">-5</li>
      <li data-option="C">5</li>
      <li data-option="D">-3</li>
    </ol>
    <div data-role="feedback" data-feedback-type="explanatory">
      <p data-correct-option="B">\
El intercepto es el valor de y cuando x = 0: y = 3(0) - 5 = -5.</p>
      <ul data-role="distractor-rationale">
        <li data-option="A">\
3 es la pendiente, no el intercepto.</li>
        <li data-option="C">\
Cambiaste el signo de -5.</li>
        <li data-option="D">\
Confundiste pendiente con intercepto y cambiaste signo.</li>
      </ul>
    </div>
  </section>

  <section data-block="error-patterns">
    <h2>Errores frecuentes y tip PAES</h2>
    <ul>
      <li><strong>Puntos invertidos:</strong> Al calcular m, \
asegúrate de restar en el mismo orden: numerador y denominador.</li>
      <li><strong>Confundir m y b:</strong> m es la pendiente \
(multiplicada por x); b es donde la recta cruza el eje y.</li>
      <li><strong>Signos en resta:</strong> Cuidado con doble \
negativo: 2 - (-1) = 3, no 1.</li>
    </ul>
    <p><strong>Tip PAES:</strong> Verifica tu ecuación sustituyendo \
ambos puntos originales. Si dan igualdad, tu recta es correcta.</p>
  </section>

  <section data-block="transition-to-adaptive">
    <h2>A practicar</h2>
    <p>Ahora pasas al set adaptativo con problemas de ecuaciones \
de recta.</p>
  </section>
</article>"""


# ------------------------------------------------------------------
# Template selection helper
# ------------------------------------------------------------------


def get_reference_for_template(template_type: str) -> str:
    """Return the full HTML reference example for a template type."""
    refs = {
        "P": TEMPLATE_P_REFERENCE,
        "C": TEMPLATE_C_REFERENCE,
        "M": TEMPLATE_M_REFERENCE,
    }
    return refs.get(template_type, "")


def extract_section_reference(
    template_type: str,
    block_name: str,
    index: int | None = None,
) -> str:
    """Extract a single section from a template reference.

    Used to give section-specific generation prompts only the
    relevant portion of the reference, not the entire document.

    Args:
        template_type: P, C, or M.
        block_name: data-block value (e.g. "worked-example").
        index: data-index value for repeated blocks (1 or 2).

    Returns:
        Extracted HTML section string, or empty string if not found.
    """
    full = get_reference_for_template(template_type)
    return _extract_block(full, block_name, index)


def _extract_block(
    html: str,
    block_name: str,
    index: int | None = None,
) -> str:
    """Extract a section/header block from full HTML by data-block.

    Uses simple string scanning (not regex on HTML structure).
    """
    if block_name == "objective":
        tag = "header"
    else:
        tag = "section"

    if index is not None:
        needle = (
            f'<{tag} data-block="{block_name}" '
            f'data-index="{index}"'
        )
    else:
        needle = f'<{tag} data-block="{block_name}"'

    start = html.find(needle)
    if start == -1:
        return ""

    end_tag = f"</{tag}>"
    end = html.find(end_tag, start)
    if end == -1:
        return ""

    return html[start:end + len(end_tag)]
