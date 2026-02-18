"""QTI 3.0 reference examples for LLM prompts.

Provides concrete, structurally correct QTI 3.0 XML examples that are
injected into generation and feedback prompts as structural anchors.
The LLM pattern-matches against these to produce well-formed output,
reducing XSD validation failures.

Source: finalized Q4 from seleccion-regular-2025, reformatted for
readability.  Content is ONLY a structural reference — the LLM
receives separate atom/enrichment/slot context that drives the actual
mathematical content it generates.

NOTE: these strings are injected via str.format(), so they MUST NOT
contain unescaped curly braces.
"""

from __future__ import annotations

# ------------------------------------------------------------------
# Base QTI reference (no feedback) — used by Phase 4 generation
# ------------------------------------------------------------------
# Shows the minimal valid structure: namespace declarations,
# response-declaration, outcome-declaration (SCORE), item-body
# with choice-interaction (4 choices), and response-processing
# template reference.
# ------------------------------------------------------------------

BASE_QTI_REFERENCE = """\
<qti-assessment-item
    xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.imsglobal.org/xsd/imsqtiasi_v3p0
      https://purl.imsglobal.org/spec/qti/v3p0/schema/xsd/\
imsqti_asiv3p0_v1p0.xsd"
    identifier="question-4"
    title="Optimización de compra de alimento para perros"
    adaptive="false"
    time-dependent="false">
  <qti-response-declaration identifier="RESPONSE"
      cardinality="single" base-type="identifier">
    <qti-correct-response>
      <qti-value>ChoiceC</qti-value>
    </qti-correct-response>
  </qti-response-declaration>
  <qti-outcome-declaration identifier="SCORE"
      cardinality="single" base-type="float">
    <qti-default-value>
      <qti-value>0</qti-value>
    </qti-default-value>
  </qti-outcome-declaration>
  <qti-item-body>
    <p>Una persona necesita comprar 60 kg de alimento
      de cierta marca para sus perros.</p>
    <p>En una tienda para mascotas, ese alimento tiene
      los siguientes precios:</p>
    <ul>
      <li>El saco de 20 kg se vende a $33 500.</li>
      <li>El saco de 15 kg se vende a $25 000.</li>
      <li>El saco de 12 kg se vende a $20 000.</li>
      <li>El saco de 5 kg se vende a $10 000.</li>
    </ul>
    <p>Si la persona requiere priorizar en primer lugar
      el menor precio a pagar y luego la menor cantidad
      de sacos, ¿cuál de las siguientes opciones le
      conviene a la persona?</p>
    <qti-choice-interaction max-choices="1"
        response-identifier="RESPONSE">
      <qti-simple-choice identifier="ChoiceA">
        Comprar doce sacos de 5 kg.
      </qti-simple-choice>
      <qti-simple-choice identifier="ChoiceB">
        Comprar cinco sacos de 12 kg.
      </qti-simple-choice>
      <qti-simple-choice identifier="ChoiceC">
        Comprar cuatro sacos de 15 kg.
      </qti-simple-choice>
      <qti-simple-choice identifier="ChoiceD">
        Comprar tres sacos de 20 kg.
      </qti-simple-choice>
    </qti-choice-interaction>
  </qti-item-body>
  <qti-response-processing
    template="https://purl.imsglobal.org/spec/qti/v3p0/\
rptemplates/match_correct.xml"/>
</qti-assessment-item>"""

# ------------------------------------------------------------------
# Feedback QTI reference — used by Phase 7 feedback enhancement
# ------------------------------------------------------------------
# Shows the COMPLETE structure with feedback elements added:
# - FEEDBACK and SOLUTION outcome declarations
# - qti-feedback-inline inside each qti-simple-choice
# - qti-feedback-block with qti-content-body (step-by-step)
# - Full qti-response-processing with per-choice routing
# ------------------------------------------------------------------

FEEDBACK_QTI_REFERENCE = """\
<qti-assessment-item
    xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.imsglobal.org/xsd/imsqtiasi_v3p0
      https://purl.imsglobal.org/spec/qti/v3p0/schema/xsd/\
imsqti_asiv3p0_v1p0.xsd"
    identifier="question-4"
    title="Optimización de compra de alimento para perros"
    adaptive="false"
    time-dependent="false">
  <qti-response-declaration identifier="RESPONSE"
      cardinality="single" base-type="identifier">
    <qti-correct-response>
      <qti-value>ChoiceC</qti-value>
    </qti-correct-response>
  </qti-response-declaration>
  <qti-outcome-declaration identifier="FEEDBACK"
      cardinality="single" base-type="identifier"/>
  <qti-outcome-declaration identifier="SOLUTION"
      cardinality="single" base-type="identifier"/>
  <qti-outcome-declaration identifier="SCORE"
      cardinality="single" base-type="float">
    <qti-default-value>
      <qti-value>0</qti-value>
    </qti-default-value>
  </qti-outcome-declaration>
  <qti-item-body>
    <p>Una persona necesita comprar 60 kg de alimento
      de cierta marca para sus perros.</p>
    <p>En una tienda para mascotas, ese alimento tiene
      los siguientes precios:</p>
    <ul>
      <li>El saco de 20 kg se vende a $33 500.</li>
      <li>El saco de 15 kg se vende a $25 000.</li>
      <li>El saco de 12 kg se vende a $20 000.</li>
      <li>El saco de 5 kg se vende a $10 000.</li>
    </ul>
    <p>Si la persona requiere priorizar en primer lugar
      el menor precio a pagar y luego la menor cantidad
      de sacos, ¿cuál de las siguientes opciones le
      conviene a la persona?</p>
    <qti-choice-interaction max-choices="1"
        response-identifier="RESPONSE">
      <qti-simple-choice identifier="ChoiceA">
        Comprar doce sacos de 5 kg.
        <qti-feedback-inline identifier="FB_ChoiceA"
            outcome-identifier="FEEDBACK">
          Incorrecto. Doce sacos de 5 kg entregan los
          60 kg requeridos, pero el costo total es mayor.
          El costo total de doce sacos es:
          <math xmlns="http://www.w3.org/1998/Math/MathML">
            <mn>12</mn><mo>&#xD7;</mo>
            <mn>10.000</mn><mo>=</mo><mn>120.000</mn>
          </math>.
          En cambio, cuatro sacos de 15 kg cuestan:
          <math xmlns="http://www.w3.org/1998/Math/MathML">
            <mn>4</mn><mo>&#xD7;</mo>
            <mn>25.000</mn><mo>=</mo><mn>100.000</mn>
          </math>,
          que es menor que $120.000.
        </qti-feedback-inline>
      </qti-simple-choice>
      <qti-simple-choice identifier="ChoiceB">
        Comprar cinco sacos de 12 kg.
        <qti-feedback-inline identifier="FB_ChoiceB"
            outcome-identifier="FEEDBACK">
          Incorrecto. El costo total de cinco sacos es:
          <math xmlns="http://www.w3.org/1998/Math/MathML">
            <mn>5</mn><mo>&#xD7;</mo>
            <mn>20.000</mn><mo>=</mo><mn>100.000</mn>
          </math>.
          Aunque este valor es igual al costo de cuatro
          sacos de 15 kg, la persona debe priorizar la
          menor cantidad de sacos. Cinco sacos son más
          que cuatro.
        </qti-feedback-inline>
      </qti-simple-choice>
      <qti-simple-choice identifier="ChoiceC">
        Comprar cuatro sacos de 15 kg.
        <qti-feedback-inline identifier="FB_ChoiceC"
            outcome-identifier="FEEDBACK">
          ¡Correcto! Cuatro sacos de 15 kg entregan
          exactamente los 60 kg requeridos. Costo total:
          <math xmlns="http://www.w3.org/1998/Math/MathML">
            <mn>4</mn><mo>&#xD7;</mo>
            <mn>25.000</mn><mo>=</mo><mn>100.000</mn>
          </math>.
          Comparando: doce sacos de 5 kg cuestan $120.000
          y tres sacos de 20 kg cuestan $100.500, por lo
          que $100.000 es el menor precio. Además, esta
          opción tiene menos sacos que cinco sacos de
          12 kg.
        </qti-feedback-inline>
      </qti-simple-choice>
      <qti-simple-choice identifier="ChoiceD">
        Comprar tres sacos de 20 kg.
        <qti-feedback-inline identifier="FB_ChoiceD"
            outcome-identifier="FEEDBACK">
          Incorrecto. El costo total de tres sacos es:
          <math xmlns="http://www.w3.org/1998/Math/MathML">
            <mn>3</mn><mo>&#xD7;</mo>
            <mn>33.500</mn><mo>=</mo><mn>100.500</mn>
          </math>.
          En cambio, cuatro sacos de 15 kg cuestan:
          <math xmlns="http://www.w3.org/1998/Math/MathML">
            <mn>4</mn><mo>&#xD7;</mo>
            <mn>25.000</mn><mo>=</mo><mn>100.000</mn>
          </math>,
          que es menor que $100.500.
        </qti-feedback-inline>
      </qti-simple-choice>
    </qti-choice-interaction>
    <qti-feedback-block identifier="show"
        outcome-identifier="SOLUTION" show-hide="show">
      <qti-content-body>
        <p><strong>Resolución paso a paso</strong></p>
        <ol>
          <li>
            <p><strong>Paso 1: Verificar que cada opción
              entregue 60 kg</strong></p>
            <p>Opción A:
              <math xmlns="http://www.w3.org/1998/Math/MathML">
                <mn>12</mn><mo>&#xD7;</mo><mn>5</mn>
                <mo>=</mo><mn>60</mn>
              </math>
            </p>
            <p>Opción B:
              <math xmlns="http://www.w3.org/1998/Math/MathML">
                <mn>5</mn><mo>&#xD7;</mo><mn>12</mn>
                <mo>=</mo><mn>60</mn>
              </math>
            </p>
            <p>Opción C:
              <math xmlns="http://www.w3.org/1998/Math/MathML">
                <mn>4</mn><mo>&#xD7;</mo><mn>15</mn>
                <mo>=</mo><mn>60</mn>
              </math>
            </p>
            <p>Opción D:
              <math xmlns="http://www.w3.org/1998/Math/MathML">
                <mn>3</mn><mo>&#xD7;</mo><mn>20</mn>
                <mo>=</mo><mn>60</mn>
              </math>
            </p>
            <p>Todas entregan los 60 kg requeridos.</p>
          </li>
          <li>
            <p><strong>Paso 2: Calcular el costo total
              de cada opción</strong></p>
            <p><em>Opción A:</em>
              <math xmlns="http://www.w3.org/1998/Math/MathML">
                <mn>12</mn><mo>&#xD7;</mo><mn>10.000</mn>
                <mo>=</mo><mn>120.000</mn>
              </math>
            </p>
            <p><em>Opción B:</em>
              <math xmlns="http://www.w3.org/1998/Math/MathML">
                <mn>5</mn><mo>&#xD7;</mo><mn>20.000</mn>
                <mo>=</mo><mn>100.000</mn>
              </math>
            </p>
            <p><em>Opción C:</em>
              <math xmlns="http://www.w3.org/1998/Math/MathML">
                <mn>4</mn><mo>&#xD7;</mo><mn>25.000</mn>
                <mo>=</mo><mn>100.000</mn>
              </math>
            </p>
            <p><em>Opción D:</em>
              <math xmlns="http://www.w3.org/1998/Math/MathML">
                <mn>3</mn><mo>&#xD7;</mo><mn>33.500</mn>
                <mo>=</mo><mn>100.500</mn>
              </math>
            </p>
          </li>
          <li>
            <p><strong>Paso 3: Comparar costos</strong></p>
            <p>El menor precio es $100.000, que
              corresponde a las opciones B y C.</p>
          </li>
          <li>
            <p><strong>Paso 4: Aplicar la segunda
              condición (menor cantidad de sacos)</strong></p>
            <p>Opción B: cinco sacos. Opción C: cuatro
              sacos. Cuatro es menor que cinco.</p>
          </li>
          <li>
            <p><strong>Conclusión</strong></p>
            <p>La opción correcta es comprar cuatro
              sacos de 15 kg (alternativa C).</p>
          </li>
        </ol>
      </qti-content-body>
    </qti-feedback-block>
  </qti-item-body>
  <qti-response-processing>
    <qti-response-condition>
      <qti-response-if>
        <qti-match>
          <qti-variable identifier="RESPONSE"/>
          <qti-base-value base-type="identifier">
            ChoiceC
          </qti-base-value>
        </qti-match>
        <qti-set-outcome-value identifier="SCORE">
          <qti-base-value base-type="float">1</qti-base-value>
        </qti-set-outcome-value>
        <qti-set-outcome-value identifier="FEEDBACK">
          <qti-base-value base-type="identifier">
            FB_ChoiceC
          </qti-base-value>
        </qti-set-outcome-value>
        <qti-set-outcome-value identifier="SOLUTION">
          <qti-base-value base-type="identifier">
            show
          </qti-base-value>
        </qti-set-outcome-value>
      </qti-response-if>
      <qti-response-else-if>
        <qti-match>
          <qti-variable identifier="RESPONSE"/>
          <qti-base-value base-type="identifier">
            ChoiceA
          </qti-base-value>
        </qti-match>
        <qti-set-outcome-value identifier="FEEDBACK">
          <qti-base-value base-type="identifier">
            FB_ChoiceA
          </qti-base-value>
        </qti-set-outcome-value>
        <qti-set-outcome-value identifier="SOLUTION">
          <qti-base-value base-type="identifier">
            show
          </qti-base-value>
        </qti-set-outcome-value>
      </qti-response-else-if>
      <qti-response-else-if>
        <qti-match>
          <qti-variable identifier="RESPONSE"/>
          <qti-base-value base-type="identifier">
            ChoiceB
          </qti-base-value>
        </qti-match>
        <qti-set-outcome-value identifier="FEEDBACK">
          <qti-base-value base-type="identifier">
            FB_ChoiceB
          </qti-base-value>
        </qti-set-outcome-value>
        <qti-set-outcome-value identifier="SOLUTION">
          <qti-base-value base-type="identifier">
            show
          </qti-base-value>
        </qti-set-outcome-value>
      </qti-response-else-if>
      <qti-response-else-if>
        <qti-match>
          <qti-variable identifier="RESPONSE"/>
          <qti-base-value base-type="identifier">
            ChoiceD
          </qti-base-value>
        </qti-match>
        <qti-set-outcome-value identifier="FEEDBACK">
          <qti-base-value base-type="identifier">
            FB_ChoiceD
          </qti-base-value>
        </qti-set-outcome-value>
        <qti-set-outcome-value identifier="SOLUTION">
          <qti-base-value base-type="identifier">
            show
          </qti-base-value>
        </qti-set-outcome-value>
      </qti-response-else-if>
      <qti-response-else>
        <qti-set-outcome-value identifier="FEEDBACK">
          <qti-base-value base-type="identifier">
            FB_ChoiceA
          </qti-base-value>
        </qti-set-outcome-value>
        <qti-set-outcome-value identifier="SOLUTION">
          <qti-base-value base-type="identifier">
            show
          </qti-base-value>
        </qti-set-outcome-value>
      </qti-response-else>
    </qti-response-condition>
  </qti-response-processing>
</qti-assessment-item>"""

# ------------------------------------------------------------------
# Base QTI reference WITH IMAGE — used by Phase 4 generation
# when the slot has image_required=True.
# ------------------------------------------------------------------
# Same structural rules as BASE_QTI_REFERENCE but includes an
# <img> placeholder inside <qti-item-body>. The src is
# "IMAGE_PLACEHOLDER" which gets replaced with an S3 URL after
# image generation.
#
# The detailed image description is returned in a separate JSON
# field ("image_description"), NOT embedded in the XML, so that
# XSD validation passes on the raw XML.
# ------------------------------------------------------------------

BASE_QTI_WITH_IMAGE_REFERENCE = """\
<qti-assessment-item
    xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.imsglobal.org/xsd/imsqtiasi_v3p0
      https://purl.imsglobal.org/spec/qti/v3p0/schema/xsd/\
imsqti_asiv3p0_v1p0.xsd"
    identifier="atom-123_Q5"
    title="Interpretar grafico de funcion cuadratica"
    adaptive="false"
    time-dependent="false">
  <qti-response-declaration identifier="RESPONSE"
      cardinality="single" base-type="identifier">
    <qti-correct-response>
      <qti-value>ChoiceB</qti-value>
    </qti-correct-response>
  </qti-response-declaration>
  <qti-outcome-declaration identifier="SCORE"
      cardinality="single" base-type="float">
    <qti-default-value>
      <qti-value>0</qti-value>
    </qti-default-value>
  </qti-outcome-declaration>
  <qti-item-body>
    <p>La siguiente figura muestra el grafico de una
      funcion
      <math xmlns="http://www.w3.org/1998/Math/MathML">
        <mi>f</mi>
      </math>.</p>
    <p>
      <img src="IMAGE_PLACEHOLDER"
        alt="Grafico de funcion cuadratica con vertice \
en (1, -4) y raices en x=-1 y x=3"
        style="max-width:100%;height:auto;" />
    </p>
    <p>A partir del grafico, ¿cual es el valor minimo
      de
      <math xmlns="http://www.w3.org/1998/Math/MathML">
        <mrow><mi>f</mi><mo>(</mo><mi>x</mi><mo>)</mo></mrow>
      </math>?</p>
    <qti-choice-interaction max-choices="1"
        response-identifier="RESPONSE">
      <qti-simple-choice identifier="ChoiceA">
        <math xmlns="http://www.w3.org/1998/Math/MathML">
          <mn>-1</mn>
        </math>
      </qti-simple-choice>
      <qti-simple-choice identifier="ChoiceB">
        <math xmlns="http://www.w3.org/1998/Math/MathML">
          <mn>-4</mn>
        </math>
      </qti-simple-choice>
      <qti-simple-choice identifier="ChoiceC">
        <math xmlns="http://www.w3.org/1998/Math/MathML">
          <mn>1</mn>
        </math>
      </qti-simple-choice>
      <qti-simple-choice identifier="ChoiceD">
        <math xmlns="http://www.w3.org/1998/Math/MathML">
          <mn>3</mn>
        </math>
      </qti-simple-choice>
    </qti-choice-interaction>
  </qti-item-body>
  <qti-response-processing
    template="https://purl.imsglobal.org/spec/qti/v3p0/\
rptemplates/match_correct.xml"/>
</qti-assessment-item>"""
