"""HTML reference examples for mini-lesson LLM prompts.

Structural anchors per template type (P, C, M). The LLM
pattern-matches these to produce spec-compliant output.

NOTE: injected via str.format() — no unescaped curly braces.
"""

from __future__ import annotations

# -- Template P — Procedural atom reference --------------------------

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
Este procedimiento aparece en al menos 2 preguntas por prueba \
PAES.</p>
  </header>
  <section data-block="concept">
    <h2>Idea clave</h2>
    <h3>Regla principal</h3>
    <p>Factorizar por factor común es reescribir una suma como \
un <strong>producto</strong>: encuentras el mayor monomio que \
divide a todos los términos y lo sacas fuera de un paréntesis.</p>
    <h3>Los 3 pasos</h3>
    <p>(1) Halla el MCD de los coeficientes, (2) toma la menor \
potencia de cada variable común, (3) divide cada término.</p>
    <h3>Trampa PAES</h3>
    <p>❌ Sacar 2x cuando el factor es 4x² (factor no máximo).\
</p>
    <p>✔ Siempre busca el MCD completo de coeficientes Y \
variables.</p>
  </section>
  <section data-block="worked-example" data-index="1">
    <h2>Ejemplo resuelto 1</h2>
    <p>Factoriza <math xmlns="http://www.w3.org/1998/Math/MathML"\
><mrow><mn>6</mn><msup><mi>x</mi><mn>2</mn></msup><mo>+</mo>\
<mn>9</mn><mi>x</mi></mrow></math>.</p>
    <ol data-role="steps">
      <li><details>
        <summary><strong>Paso 1:</strong> MCD de coeficientes\
</summary>
        <p>MCD de 6 y 9 es 3.</p>
      </details></li>
      <li><details>
        <summary><strong>Paso 2:</strong> Menor potencia de x\
</summary>
        <p>x aparece como x² y x¹. La menor es x¹.</p>
      </details></li>
      <li><details>
        <summary><strong>Paso 3:</strong> Factor y divide\
</summary>
        <p>Factor = 3x. 6x²/3x = 2x, 9x/3x = 3. \
Resultado: 3x(2x + 3).</p>
      </details></li>
      <li><details>
        <summary><strong>Verificación:</strong> Multiplica\
</summary>
        <p>3x·2x = 6x², 3x·3 = 9x. Recupera 6x² + 9x. ✓</p>
      </details></li>
    </ol>
    <p data-role="micro-reinforcement">Si obtuviste 3x(2x + 3), \
vas bien — el punto clave fue tomar la menor potencia de x.</p>
  </section>
  <section data-block="worked-example" data-index="2">
    <h2>Ejemplo resuelto 2</h2>
    <p>Factoriza 12a³b − 18a²b² + 6ab.</p>
    <ol data-role="steps">
      <li><details>
        <summary><strong>Paso 1:</strong> MCD y variables\
</summary>
        <p>MCD(12,18,6) = 6. Menor: a¹, b¹. Factor: 6ab.</p>
      </details></li>
      <li><details>
        <summary><strong>Paso 2:</strong> Divide</summary>
        <p data-role="prediction-cue">¿Cuánto da 12a³b ÷ 6ab? \
Piénsalo antes de abrir el siguiente paso.</p>
      </details></li>
      <li><details>
        <summary><strong>Paso 3:</strong> Resultado</summary>
        <p>2a² − 3ab + 1. Resultado: 6ab(2a² − 3ab + 1).</p>
      </details></li>
    </ol>
    <p data-role="micro-reinforcement">Si obtuviste \
6ab(2a² − 3ab + 1), vas bien.</p>
  </section>
  <section data-block="quick-check" data-index="1"
           data-format="mcq-abcd">
    <h3>Quick Check 1</h3>
    <p data-role="question-stem">¿Factor común de \
8x³ + 12x²?</p>
    <ol data-role="options" data-option-format="ABCD">
      <li data-option="A">2x</li>
      <li data-option="B">4x²</li>
      <li data-option="C">4x³</li>
      <li data-option="D">8x</li>
    </ol>
    <div data-role="feedback" data-feedback-type="explanatory">
      <details>
        <summary>Ver explicación</summary>
        <p data-correct-option="B">\
MCD(8,12)=4; menor potencia=x². Factor: 4x². \
Regla: Si buscas factor común, toma el MCD de coeficientes \
y la menor potencia de cada variable.</p>
        <ul data-role="distractor-rationale">
          <li data-option="A">2x divide ambos pero no es el \
máximo. Revisa si hay un divisor mayor.</li>
          <li data-option="C">x³ no divide a 12x². Revisa que \
la potencia sea ≤ en todos los términos.</li>
          <li data-option="D">8 no divide a 12. Revisa que \
divida a TODOS los coeficientes.</li>
        </ul>
      </details>
    </div>
  </section>
  <section data-block="quick-check" data-index="2"
           data-format="mcq-abcd">
    <h3>Quick Check 2</h3>
    <p data-role="question-stem">¿Factorización correcta de \
15y − 10?</p>
    <ol data-role="options" data-option-format="ABCD">
      <li data-option="A">5(3y - 2)</li>
      <li data-option="B">5(3y + 2)</li>
      <li data-option="C">5y(3 - 2)</li>
      <li data-option="D">3(5y - 10)</li>
    </ol>
    <div data-role="feedback" data-feedback-type="explanatory">
      <details>
        <summary>Ver explicación</summary>
        <p data-correct-option="A">\
MCD(15,10)=5. Divide: 3y y 2. Signo resta se mantiene. \
Regla: Si factorizas, verifica multiplicando — debes recuperar \
la expresión original.</p>
        <ul data-role="distractor-rationale">
          <li data-option="B">Signo cambió a suma. Revisa \
signos al dividir.</li>
          <li data-option="C">y no está en ambos términos. \
Revisa variables comunes.</li>
          <li data-option="D">3 no es MCD(15,10). Revisa que \
uses el máximo.</li>
        </ul>
      </details>
    </div>
  </section>
  <section data-block="error-patterns">
    <h2>Errores frecuentes</h2>
    <ul>
      <li><strong>Factor no máximo:</strong> Sacas 2x cuando \
es 4x². Busca el MCD completo.</li>
      <li><strong>Potencia incorrecta:</strong> Tomas la mayor \
en vez de la menor.</li>
      <li><strong>Signos:</strong> Al sacar factor negativo, \
todos los signos del paréntesis cambian.</li>
    </ul>
    <p><strong>Checklist PAES</strong></p>
    <ul data-role="paes-checklist">
      <li>✅ ¿El MCD divide a TODOS los coeficientes?</li>
      <li>✅ ¿Tomé la menor potencia de cada variable?</li>
      <li>✅ ¿Al multiplicar recupero la expresión original?</li>
    </ul>
  </section>
  <section data-block="transition-to-adaptive">
    <h2>A practicar</h2>
    <p>Ahora pasas al set adaptativo donde practicarás \
factorización con dificultad creciente.</p>
  </section>
</article>"""

# -- Template C — Conceptual atom reference --------------------------

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
Identificar funciones es base para al menos 5 preguntas PAES.</p>
  </header>
  <section data-block="concept">
    <h2>¿Qué es una función?</h2>
    <h3>Definición clave</h3>
    <p>Una función asigna a cada entrada <strong>exactamente \
una</strong> salida.</p>
    <h3>Prueba de la recta vertical</h3>
    <p>En un gráfico, si alguna recta vertical corta la curva \
en más de un punto, no es función.</p>
    <h3>Trampa PAES</h3>
    <p>❌ Creer que si dos x dan la misma y, no es función.</p>
    <p>✔ Lo prohibido es que UNA entrada dé DOS salidas.</p>
  </section>
  <section data-block="worked-example" data-index="1">
    <h2>Ejemplo resuelto 1 — Interpretación</h2>
    <table>
      <thead><tr><th>x</th><th>y</th></tr></thead>
      <tbody>
        <tr><td>1</td><td>3</td></tr>
        <tr><td>2</td><td>5</td></tr>
        <tr><td>3</td><td>7</td></tr>
      </tbody>
    </table>
    <ol data-role="steps">
      <li><details>
        <summary><strong>Paso 1:</strong> Revisa x repetidos\
</summary>
        <p>x = 1, 2, 3: todos distintos.</p>
      </details></li>
      <li><details>
        <summary><strong>Paso 2:</strong> Concluye</summary>
        <p>Cada x tiene exactamente una y. Sí es función.</p>
      </details></li>
      <li><details>
        <summary><strong>Verificación:</strong> Recta vertical\
</summary>
        <p>Ninguna recta vertical toca más de un punto. ✓</p>
      </details></li>
    </ol>
    <p data-role="micro-reinforcement">Si concluiste que sí es \
función, vas bien — ningún x se repite con distinta y.</p>
  </section>
  <section data-block="worked-example" data-index="2">
    <h2>Ejemplo resuelto 2 — Decisión</h2>
    <p>Pares: (1, 2), (1, 5), (3, 4).</p>
    <ol data-role="steps">
      <li><details>
        <summary><strong>Paso 1:</strong> Entradas repetidas\
</summary>
        <p data-role="prediction-cue">¿Hay algún x que aparezca \
más de una vez? Piénsalo antes de abrir.</p>
      </details></li>
      <li><details>
        <summary><strong>Paso 2:</strong> Concluye</summary>
        <p>x=1 tiene y=2 e y=5. Dos salidas. No es función.</p>
      </details></li>
    </ol>
    <p data-role="micro-reinforcement">Si identificaste que \
x=1 tiene dos salidas, vas bien.</p>
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
      <details>
        <summary>Ver explicación</summary>
        <p data-correct-option="A">\
Cada x aparece una sola vez. Que dos x den la misma y está \
permitido. Regla: Si cada entrada tiene exactamente una salida, \
entonces es función.</p>
        <ul data-role="distractor-rationale">
          <li data-option="B">x=1 tiene dos salidas. Revisa \
entradas duplicadas.</li>
          <li data-option="C">x=2 tiene dos salidas. Revisa \
si algún x se repite.</li>
          <li data-option="D">x=4 aparece tres veces. Revisa \
entradas con múltiples salidas.</li>
        </ul>
      </details>
    </div>
  </section>
  <section data-block="error-patterns">
    <h2>Errores frecuentes</h2>
    <ul>
      <li><strong>Confundir inyectividad:</strong> Que dos x \
den la misma y no la descalifica.</li>
      <li><strong>Recta vertical mal aplicada:</strong> Se \
aplica al gráfico, no a la tabla.</li>
    </ul>
    <p><strong>Checklist PAES</strong></p>
    <ul data-role="paes-checklist">
      <li>✅ ¿Algún x se repite con distinta y?</li>
      <li>✅ ¿Apliqué recta vertical al gráfico?</li>
      <li>✅ ¿No confundí "misma salida" con "no función"?</li>
    </ul>
  </section>
  <section data-block="transition-to-adaptive">
    <h2>A practicar</h2>
    <p>Ahora pasas al set adaptativo con ejercicios sobre \
identificación de funciones.</p>
  </section>
</article>"""

# -- Template M — Mixed atom reference -------------------------------

TEMPLATE_M_REFERENCE = """\
<article data-kind="mini-class"
         data-atom-id="A-M1-ALG-04-01"
         data-template="M">
  <header data-block="objective">
    <h1>Mini-clase: Ecuación de la recta desde dos puntos</h1>
    <p data-role="learning-objective">\
Al terminar esta mini-clase podrás obtener la ecuación de una \
recta dados dos puntos y explicar pendiente e intercepto.</p>
    <p data-role="paes-relevance">\
Ecuaciones de rectas aparecen en modelación y gráficos PAES.</p>
  </header>
  <section data-block="concept">
    <h2>Idea clave</h2>
    <h3>Pendiente</h3>
    <p>m mide cuánto cambia y por cada unidad de x: \
m = (y₂−y₁)/(x₂−x₁).</p>
    <h3>Forma punto-pendiente</h3>
    <p>Con un punto y m: y−y₁ = m(x−x₁). Simplifica a \
y = mx + b.</p>
    <h3>Trampa PAES</h3>
    <p>❌ Restar en distinto orden: (y₁−y₂)/(x₂−x₁).</p>
    <p>✔ Mismo orden en numerador y denominador.</p>
  </section>
  <section data-block="worked-example" data-index="1">
    <h2>Ejemplo resuelto 1 — Procedimiento</h2>
    <p>Ecuación de la recta por (1, 3) y (3, 7).</p>
    <ol data-role="steps">
      <li><details>
        <summary><strong>Paso 1:</strong> Pendiente</summary>
        <p>m = (7−3)/(3−1) = 4/2 = 2.</p>
      </details></li>
      <li><details>
        <summary><strong>Paso 2:</strong> Punto-pendiente\
</summary>
        <p>y−3 = 2(x−1). Distribuye: y−3 = 2x−2.</p>
      </details></li>
      <li><details>
        <summary><strong>Paso 3:</strong> Simplifica</summary>
        <p>y = 2x−2+3 = 2x+1.</p>
      </details></li>
      <li><details>
        <summary><strong>Verificación:</strong> Sustituye\
</summary>
        <p>(1): y=2(1)+1=3 ✓. (3): y=2(3)+1=7 ✓.</p>
      </details></li>
    </ol>
    <p data-role="micro-reinforcement">Si obtuviste y=2x+1, \
vas bien — el punto clave fue el mismo orden al restar.</p>
  </section>
  <section data-block="worked-example" data-index="2">
    <h2>Ejemplo resuelto 2 — Conceptual</h2>
    <p>Tienda: $500 fijos + $200/km. Puntos: (0,500), \
(3,1100).</p>
    <ol data-role="steps">
      <li><details>
        <summary><strong>Paso 1:</strong> Pendiente</summary>
        <p data-role="prediction-cue">¿Cuánto da \
(1100−500)/(3−0)? Piénsalo antes de abrir.</p>
      </details></li>
      <li><details>
        <summary><strong>Paso 2:</strong> Interpreta</summary>
        <p>m=600/3=200 (costo/km). b=500 (cargo fijo). \
Ecuación: y=200x+500.</p>
      </details></li>
    </ol>
    <p data-role="micro-reinforcement">Si obtuviste \
y=200x+500, vas bien.</p>
  </section>
  <section data-block="quick-check" data-index="1"
           data-format="mcq-abcd">
    <h3>Quick Check 1</h3>
    <p data-role="question-stem">\
¿Pendiente de la recta por (-1,4) y (2,-2)?</p>
    <ol data-role="options" data-option-format="ABCD">
      <li data-option="A">-2</li>
      <li data-option="B">2</li>
      <li data-option="C">-1/2</li>
      <li data-option="D">6</li>
    </ol>
    <div data-role="feedback" data-feedback-type="explanatory">
      <details>
        <summary>Ver explicación</summary>
        <p data-correct-option="A">\
m=(-2−4)/(2−(-1))=-6/3=-2. Regla: Si restas coordenadas, \
mantén el mismo orden arriba y abajo.</p>
        <ul data-role="distractor-rationale">
          <li data-option="B">Olvidaste el signo. Revisa: \
-2−4=-6.</li>
          <li data-option="C">Invertiste Δy/Δx. m=Δy/Δx, \
no Δx/Δy.</li>
          <li data-option="D">-6 es el numerador, no m. \
Divide por Δx.</li>
        </ul>
      </details>
    </div>
  </section>
  <section data-block="quick-check" data-index="2"
           data-format="mcq-abcd">
    <h3>Quick Check 2</h3>
    <p data-role="question-stem">\
Si y=3x−5, ¿intercepto con eje y?</p>
    <ol data-role="options" data-option-format="ABCD">
      <li data-option="A">3</li>
      <li data-option="B">-5</li>
      <li data-option="C">5</li>
      <li data-option="D">-3</li>
    </ol>
    <div data-role="feedback" data-feedback-type="explanatory">
      <details>
        <summary>Ver explicación</summary>
        <p data-correct-option="B">\
Intercepto: y cuando x=0: y=3(0)−5=-5. Regla: Si necesitas \
el intercepto, sustituye x=0.</p>
        <ul data-role="distractor-rationale">
          <li data-option="A">3 es la pendiente, no b. Revisa \
el término sin x.</li>
          <li data-option="C">Cambiaste signo de -5. Revisa el \
término independiente.</li>
          <li data-option="D">Confundiste m y b. m multiplica \
x; b es el término libre.</li>
        </ul>
      </details>
    </div>
  </section>
  <section data-block="error-patterns">
    <h2>Errores frecuentes</h2>
    <ul>
      <li><strong>Orden de resta:</strong> Mismo orden en \
numerador y denominador.</li>
      <li><strong>Confundir m y b:</strong> m es pendiente; \
b es donde cruza eje y.</li>
      <li><strong>Doble negativo:</strong> 2−(−1)=3, no 1.</li>
    </ul>
    <p><strong>Checklist PAES</strong></p>
    <ul data-role="paes-checklist">
      <li>✅ ¿Resté en el mismo orden arriba y abajo?</li>
      <li>✅ ¿Identifiqué m (pendiente) y b (intercepto)?</li>
      <li>✅ ¿Al sustituir puntos obtengo igualdad?</li>
    </ul>
  </section>
  <section data-block="transition-to-adaptive">
    <h2>A practicar</h2>
    <p>Ahora pasas al set adaptativo con problemas de ecuaciones \
de recta.</p>
  </section>
</article>"""


# -- Template selection helpers --------------------------------------


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
    """Extract a single section from a template reference."""
    full = get_reference_for_template(template_type)
    return _extract_block(full, block_name, index)


def _extract_block(
    html: str,
    block_name: str,
    index: int | None = None,
) -> str:
    """Extract a section/header block from full HTML by data-block."""
    tag = "header" if block_name == "objective" else "section"

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
