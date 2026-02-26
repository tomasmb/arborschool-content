"""HTML reference examples for mini-lesson LLM prompts.

Structural anchors per template (P, C, M). The LLM
pattern-matches these to produce spec-compliant output.
Injected via str.format() — no unescaped curly braces.

Each template has 3 sections: objective, concept, worked-example
(with Checklist PAES folded into the WE closing).
"""

from __future__ import annotations

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
    <h2>Ejemplo resuelto</h2>
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
    <ul data-role="paes-checklist">
      <li>✅ ¿El MCD divide a TODOS los coeficientes?</li>
      <li>✅ ¿Tomé la menor potencia de cada variable?</li>
      <li>✅ ¿Al multiplicar recupero la expresión original?</li>
    </ul>
  </section>
</article>"""

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
    <h3>Trampa PAES</h3>
    <p>❌ Creer que si dos x dan la misma y, no es función.</p>
    <p>✔ Lo prohibido es que UNA entrada dé DOS salidas.</p>
  </section>
  <section data-block="worked-example" data-index="1">
    <h2>Ejemplo resuelto</h2>
    <table>
      <thead><tr><th>x</th><th>y</th></tr></thead>
      <tbody>
        <tr><td>1</td><td>3</td></tr>
        <tr><td>2</td><td>5</td></tr>
        <tr><td>1</td><td>7</td></tr>
      </tbody>
    </table>
    <p>¿Es función esta tabla?</p>
    <ol data-role="steps">
      <li><details>
        <summary><strong>Paso 1:</strong> Busca x repetidos\
</summary>
        <p>x = 1 aparece dos veces (con y=3 e y=7).</p>
      </details></li>
      <li><details>
        <summary><strong>Paso 2:</strong> Concluye</summary>
        <p>x=1 tiene dos salidas distintas. No es función.</p>
      </details></li>
      <li><details>
        <summary><strong>Verificación:</strong> Recta vertical\
</summary>
        <p>En un gráfico, una recta vertical en x=1 toca dos \
puntos. Confirma: no es función. ✓</p>
      </details></li>
    </ol>
    <p data-role="micro-reinforcement">Si identificaste que \
x=1 tiene dos salidas, vas bien — eso descalifica la relación \
como función.</p>
    <ul data-role="paes-checklist">
      <li>✅ ¿Algún x se repite con distinta y?</li>
      <li>✅ ¿Apliqué recta vertical al gráfico?</li>
      <li>✅ ¿No confundí "misma salida" con "no función"?</li>
    </ul>
  </section>
</article>"""

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
    <h2>Ejemplo resuelto</h2>
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
    <ul data-role="paes-checklist">
      <li>✅ ¿Resté en el mismo orden arriba y abajo?</li>
      <li>✅ ¿Identifiqué m (pendiente) y b (intercepto)?</li>
      <li>✅ ¿Al sustituir puntos obtengo igualdad?</li>
    </ul>
  </section>
</article>"""


# -- Template selection helpers --------------------------------------

_TEMPLATE_REFS: dict[str, str] = {
    "P": TEMPLATE_P_REFERENCE,
    "C": TEMPLATE_C_REFERENCE,
    "M": TEMPLATE_M_REFERENCE,
}


def get_reference_for_template(template_type: str) -> str:
    """Return full HTML reference example for a template type."""
    return _TEMPLATE_REFS.get(template_type, "")


def extract_section_reference(
    template_type: str, block_name: str, index: int | None = None,
) -> str:
    """Extract a single section from a template reference."""
    return _extract_block(
        get_reference_for_template(template_type),
        block_name, index,
    )


def _extract_block(
    html: str, block_name: str, index: int | None = None,
) -> str:
    """Extract a section/header block from full HTML by data-block."""
    tag = "header" if block_name == "objective" else "section"
    needle = (
        f'<{tag} data-block="{block_name}" data-index="{index}"'
        if index is not None
        else f'<{tag} data-block="{block_name}"'
    )
    start = html.find(needle)
    if start == -1:
        return ""
    end_tag = f"</{tag}>"
    end = html.find(end_tag, start)
    return html[start:end + len(end_tag)] if end != -1 else ""
