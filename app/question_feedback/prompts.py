"""PAES-specific prompts for feedback generation and validation (Spanish).

All prompts follow Gemini 3 Pro best practices:
- Direct, precise instructions
- Structured sections (Role, Task, Rules, Output Format, Context)
- Context first, instructions last
- Explicit output format requirements
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# SHARED PROMPT SECTIONS
# ---------------------------------------------------------------------------
# Reusable blocks injected into multiple prompts via string concatenation.
# ---------------------------------------------------------------------------

CHILEAN_NUMBER_FORMAT_SECTION = """
<chilean_number_format>
IMPORTANTE: Este contenido usa formato numérico chileno:
- Punto (.) = separador de MILES (no decimal)
- Coma (,) = separador DECIMAL

Ejemplos de interpretación:
- "160.934" significa 160934 (ciento sesenta mil novecientos treinta y cuatro)
- "100.000" significa 100000 (cien mil)
- "321.868" significa 321868 (trescientos veintiún mil ochocientos sesenta y ocho)
- "3,21868" significa 3.21868 (tres coma veintiuno...)
- "0,80467" significa 0.80467 (cero coma ochenta...)

Al validar cálculos, interpreta los números según este formato ANTES de verificar.
</chilean_number_format>
"""

# ---------------------------------------------------------------------------
# FEEDBACK ENHANCEMENT PROMPT
# ---------------------------------------------------------------------------
# Used by FeedbackEnhancer to generate QTI XML with feedback.
# The prompt explicitly tells the model what it will be evaluated on.
# ---------------------------------------------------------------------------

FEEDBACK_ENHANCEMENT_PROMPT = """
<role>
Experto en educación matemática PAES Chile y formato QTI 3.0.
</role>

<context>
QTI XML ORIGINAL (sin retroalimentación):
```xml
{original_qti_xml}
```

{images_section}
</context>

<reference_example>
Este es un ejemplo completo de QTI con retroalimentación correctamente
integrada. Tu output DEBE seguir esta misma estructura.
{feedback_reference_example}
</reference_example>

<task>
Agregar retroalimentación educativa al QTI XML. Devolver el XML completo con feedback.
</task>

<xml_structure>
1. MANTENER todos los elementos originales (stem, choices, images) sin modificar

2. AGREGAR outcome declarations después de qti-response-declaration:
   <qti-outcome-declaration identifier="FEEDBACK" cardinality="single" base-type="identifier"/>
   <qti-outcome-declaration identifier="SOLUTION" cardinality="single" base-type="identifier"/>

3. AGREGAR qti-feedback-inline dentro de cada qti-simple-choice
   CRÍTICO: qti-feedback-inline solo acepta contenido INLINE (texto, strong, em, span, sub, sup).
   PROHIBIDO usar elementos de bloque dentro de qti-feedback-inline: NO <p>, NO <div>, NO <ol>.
   Ejemplo correcto: <qti-feedback-inline ...>Incorrecto. El cálculo correcto es...</qti-feedback-inline>
   Ejemplo INCORRECTO: <qti-feedback-inline ...><p>Incorrecto.</p></qti-feedback-inline>

4. AGREGAR qti-feedback-block al final de qti-item-body:
   <qti-feedback-block identifier="show" outcome-identifier="SOLUTION" show-hide="show">
     <qti-content-body>
       <p><strong>[Título del método]</strong></p>
       <ol><li>Paso 1...</li></ol>
     </qti-content-body>
   </qti-feedback-block>

5. REEMPLAZAR qti-response-processing:
   - Mapear CADA opción (A, B, C, D) a su feedback específico
   - El fallback (qti-response-else) debe asignar feedback de una opción INCORRECTA
</xml_structure>

<feedback_requirements>
Para cada opción, el feedback debe ser AUTO-CONTENIDO (el estudiante entiende sin hacer
cálculos adicionales):

OPCIÓN CORRECTA:
- Formato: "¡Correcto! [demostración matemática]"
- Incluir el cálculo o razonamiento que PRUEBA que es correcta

OPCIONES INCORRECTAS:
- Formato: "Incorrecto. [demostración matemática]"
- Incluir el cálculo que PRUEBA que esta opción NO satisface el problema
- NO especular sobre qué error cometió el estudiante
- Preservar la semántica exacta del enunciado (no agregar ni quitar calificadores)
- Para negar afirmaciones universales: incluir un CONTRAEJEMPLO CONCRETO con valores específicos

SOLUCIÓN PASO A PASO:
- Resolver el problema completo con pasos claros
- Llegar explícitamente a la respuesta correcta
- Lenguaje claro para estudiantes de 3°-4° medio
- Explicitar supuestos cuando se usan en desigualdades (ej: "como n > 0...")
</feedback_requirements>

<formatting_rules>
1. Notación matemática: usar SOLO MathML, nunca LaTeX (\\(...\\) está prohibido)

2. Formato de números chileno:
   - Separador de miles: punto (.)
   - Separador decimal: coma (,)
   - MathML: `<mn>160.934</mn>`, `<mn>3,21868</mn>`
   - Texto: `32.186.800.000 kilómetros`
</formatting_rules>

<verification_process>
ANTES de generar el feedback, DEBES:

1. IDENTIFICAR la respuesta marcada como correcta en el XML original
2. RESOLVER el problema paso a paso para entender el razonamiento
3. VERIFICAR que tu solución llega a esa respuesta

Para CADA cálculo o ejemplo numérico que incluyas en el feedback (respuesta correcta,
opciones incorrectas, contraejemplos y solución paso a paso):
- Muestra cada operación intermedia y verifica el resultado
- Confirma que los valores usados cumplen todas las restricciones del enunciado
- Si hay conversión de unidades, verifica que se cancelen correctamente
- Cuenta los ceros cuidadosamente en números grandes
</verification_process>

<output_format>
Devuelve SOLO el QTI XML completo. Sin markdown, sin explicaciones.
Debe empezar con <qti-assessment-item y terminar con </qti-assessment-item>
</output_format>
"""


# ---------------------------------------------------------------------------
# FEEDBACK CORRECTION PROMPT
# ---------------------------------------------------------------------------
# Used when feedback review fails - asks model to fix specific issues.
# ---------------------------------------------------------------------------

FEEDBACK_CORRECTION_PROMPT = """
<role>
Experto en educación matemática PAES Chile y formato QTI 3.0.
</role>

<context>
QTI XML CON FEEDBACK QUE TIENE ERRORES:
```xml
{qti_xml_with_errors}
```

{images_section}
</context>

<errors_to_fix>
{review_issues}
</errors_to_fix>

<task>
Corregir los errores identificados en el feedback. Devolver el XML completo corregido.
</task>
""" + CHILEAN_NUMBER_FORMAT_SECTION + """
<correction_instructions>
1. Lee cuidadosamente cada error identificado

2. RESUELVE EL PROBLEMA COMPLETO desde cero, paso a paso, para obtener
   los valores correctos ANTES de modificar cualquier feedback

3. Para errores de PRECISIÓN MATEMÁTICA:
   - Reescribe COMPLETAMENTE la solución paso a paso y los feedbacks afectados
   - NO intentes parchar expresiones individuales — re-deriva todo desde el principio
   - Verifica cada igualdad y cada paso aritmético antes de incluirlo

4. Para errores de CLARIDAD o FORMATO:
   - Corrige solo las partes afectadas, manteniendo el resto intacto

5. Verifica que cada número, cálculo y ejemplo en el feedback corregido
   cumpla todas las restricciones del enunciado y sea aritméticamente correcto
</correction_instructions>

<formatting_rules>
1. Notación matemática: usar SOLO MathML, nunca LaTeX
2. Formato de números chileno: punto para miles, coma para decimal
</formatting_rules>

<output_format>
Devuelve SOLO el QTI XML completo corregido. Sin markdown, sin explicaciones.
Debe empezar con <qti-assessment-item y terminar con </qti-assessment-item>
</output_format>
"""


# ---------------------------------------------------------------------------
# FEEDBACK REVIEW PROMPT
# ---------------------------------------------------------------------------
# Validates generated feedback by solving the problem and verifying accuracy.
# Used as a gate after feedback generation in the enrichment pipeline.
# Catches mathematical errors and incomplete explanations before final validation.
# ---------------------------------------------------------------------------

FEEDBACK_REVIEW_PROMPT = """
<role>
Revisor de retroalimentación educativa para preguntas PAES Matemática M1.
</role>

<context>
QTI XML CON RETROALIMENTACIÓN GENERADA:
```xml
{qti_xml_with_feedback}
```
</context>

<task>
Resolver el problema y validar que cada feedback sea matemáticamente correcto y auto-contenido.
</task>
""" + CHILEAN_NUMBER_FORMAT_SECTION + """
<checks>
1. PRECISIÓN FACTUAL (feedback_accuracy):
   - Resuelve el problema paso a paso para verificar la respuesta correcta
   - Feedback de opción correcta: ¿incluye demostración matemática de POR QUÉ es correcta?
   - Feedbacks incorrectos: ¿incluyen el cálculo que PRUEBA que no satisfacen el problema?
   - Solución paso a paso: ¿tiene matemáticas correctas y llega a la respuesta correcta?
   - FAIL si hay error matemático, justificación incorrecta, o falta la demostración

2. CLARIDAD PEDAGÓGICA (feedback_clarity):
   - ¿El lenguaje es claro para estudiantes de 3°-4° medio?
   - ¿Cada feedback es auto-contenido? (estudiante entiende sin cálculos adicionales)
   - ¿El feedback es específico a esta pregunta (no genérico)?
   - FAIL si el feedback es confuso, asume conocimiento previo, o es genérico

3. FORMATO (formatting_check):
   - ¿Usa MathML para notación matemática (no LaTeX)?
   - ¿Usa formato chileno? (punto para miles, coma para decimal)
   - Fallback (qti-response-else): PASS si asigna feedback de cualquier opción INCORRECTA.
     FAIL solo si asigna feedback de la opción CORRECTA (la marcada en qti-correct-response)
</checks>

<output_format>
JSON con este schema:
- review_result: "pass" o "fail" (fail si cualquier check falla)
- feedback_accuracy: {{status, issues[], reasoning}}
- feedback_clarity: {{status, issues[], reasoning}}
- formatting_check: {{status, issues[], reasoning}}
- overall_reasoning: resumen de 1-2 oraciones
</output_format>

<final_instruction>
Basándote en el QTI XML arriba, revisa la retroalimentación y responde en JSON.
</final_instruction>
"""


# ---------------------------------------------------------------------------
# FINAL VALIDATION PROMPT
# ---------------------------------------------------------------------------
# Comprehensive validation of the complete QTI XML including:
# - Original question correctness
# - Feedback quality
# - Content quality (typos, encoding)
# - Image validation
# - PAES curriculum alignment
# Used as a SEPARATE validation step (not during enrichment).
# ---------------------------------------------------------------------------

FINAL_VALIDATION_PROMPT = """
<role>
Validador experto de preguntas PAES Matemática M1 de Chile.
</role>

<context>
QTI XML COMPLETO (pregunta + retroalimentación):
```xml
{qti_xml_with_feedback}
```

{images_section}
</context>
""" + CHILEAN_NUMBER_FORMAT_SECTION + """
<task>
Verificar que esta pregunta es matemáticamente correcta y su retroalimentación
es precisa. Solo reportar errores concretos y demostrables.
</task>

<checks>
Evalúa cada check de forma INDEPENDIENTE. Un error en un check NO debe
contaminar otros checks.

1. RESPUESTA CORRECTA (correct_answer_check):
   - Resuelve el problema paso a paso usando formato numérico chileno
   - Identifica cuál Choice es correcta según tu resolución
   - Verifica que coincide con el valor en <qti-correct-response>
   - FAIL SOLO si tu resolución llega a una respuesta DIFERENTE a la marcada
   - PASS si la respuesta marcada es matemáticamente correcta

2. RETROALIMENTACIÓN (feedback_check):
   - ¿El feedback de la opción correcta demuestra por qué es correcta?
   - ¿Los feedbacks de opciones incorrectas demuestran por qué son incorrectas?
   - ¿La solución paso a paso llega a la respuesta correcta?
   - FAIL SOLO si hay un error matemático concreto o una conclusión incorrecta
   - PASS si el feedback es matemáticamente correcto, aunque pudiera redactarse mejor

3. CALIDAD DE CONTENIDO (content_quality_check):
   - Errores tipográficos reales (no diferencias de estilo)
   - Caracteres mal codificados (excepto entidades HTML válidas: &#x00A1; etc.)
   - Expresiones matemáticas con errores de signos o exponentes
   - FAIL SOLO si hay errores objetivos de contenido
   - PASS si el contenido es legible y correcto

4. IMÁGENES (image_check):
   - NOT_APPLICABLE si no hay imágenes adjuntas
   - Verifica que imágenes son consistentes con descripciones textuales
   - FAIL SOLO si hay una contradicción FACTUAL clara entre imagen y texto
     (ej: texto dice "punto en (3,2)" pero imagen muestra punto en (5,1))
   - PASS si las imágenes son legibles y no contradicen el contenido textual
   - NO fallar por diferencias sutiles de interpretación visual

5. VALIDEZ MATEMÁTICA PAES (math_validity_check):
   - ¿El contenido está dentro del temario PAES M1?
   - ¿Los valores numéricos son razonables?
   - FAIL SOLO si el tema está claramente fuera del currículo o hay error de magnitud
   - PASS si el contenido es apropiado para PAES M1
</checks>

<consistency_rule>
REGLA CRÍTICA — tu veredicto DEBE ser consistente con tu análisis:
- Si resolviste el problema y llegaste a la misma respuesta marcada
  → correct_answer_check.status = "pass"
- Si no encontraste errores matemáticos concretos en el feedback
  → feedback_check.status = "pass"
- Si TODOS los checks tienen status "pass" (o "not_applicable")
  → validation_result DEBE ser "pass"
- Si reportas status "fail", DEBES citar el error específico en issues[]
- Un campo issues[] vacío con status "fail" es una CONTRADICCIÓN prohibida
</consistency_rule>

<constraints>
NO marcar como error:
- "¡Correcto!" en feedback de opción correcta
- qti-response-else asignando feedback de opción incorrecta (válido en QTI 3.0)
- Entidades HTML válidas (&#x00A1;, &#x00BF;, etc.)
- Expresiones matemáticamente equivalentes (ej: "entero positivo" = "≥1")
- Cálculos correctos en formato chileno (punto=miles, coma=decimal)
- Diferencias de estilo o redacción que no afectan la corrección matemática
- Descripciones de imágenes que son razonables aunque no pixel-perfect

SÍ marcar como error:
- Resultado numérico incorrecto en un cálculo
- Respuesta marcada que no es la matemáticamente correcta
- Feedback que llega a una conclusión opuesta a lo que demuestra
- Contradicción factual clara entre texto e imagen
</constraints>

<output_format>
Responde en JSON. Evalúa TODOS los checks ANTES de asignar validation_result.
- correct_answer_check: {{status, marked_answer, verification_steps, issues[]}}
- feedback_check: {{status, issues[], reasoning}}
- content_quality_check: {{status, typos_found[], character_issues[], clarity_issues[]}}
- image_check: {{status, issues[], reasoning}}
- math_validity_check: {{status, issues[], reasoning}}
- overall_reasoning: resumen de 1-2 oraciones
- validation_result: "pass" o "fail" (DEBE coincidir con los checks anteriores)
</output_format>

<final_instruction>
Basándote en el QTI XML y las imágenes (si las hay), valida la pregunta.
Recuerda: solo falla por errores concretos y demostrables, no por preferencias
de estilo ni interpretaciones subjetivas de imágenes.
</final_instruction>
"""
