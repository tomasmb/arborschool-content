"""PAES-specific prompts for feedback generation and validation (Spanish).

All prompts follow Gemini 3 Pro best practices:
- Direct, precise instructions
- Structured sections (Role, Task, Rules, Output Format, Context)
- Context first, instructions last
- Explicit output format requirements
"""

from __future__ import annotations

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

<task>
Agregar retroalimentación educativa al QTI XML. Devolver el XML completo con feedback.
</task>

<xml_structure>
1. MANTENER todos los elementos originales (stem, choices, images) sin modificar

2. AGREGAR outcome declarations después de qti-response-declaration:
   <qti-outcome-declaration identifier="FEEDBACK" cardinality="single" base-type="identifier"/>
   <qti-outcome-declaration identifier="SOLUTION" cardinality="single" base-type="identifier"/>

3. AGREGAR qti-feedback-inline dentro de cada qti-simple-choice

4. AGREGAR qti-feedback-block al final de qti-item-body:
   <qti-feedback-block identifier="show" outcome-identifier="SOLUTION" show-hide="show">
     <qti-content-body>
       <p><strong>[Título del método]</strong></p>
       <ol><li>Paso 1...</li></ol>
     </qti-content-body>
   </qti-feedback-block>

5. REEMPLAZAR qti-response-processing: cada opción debe mapear a su feedback específico.
   IMPORTANTE: El fallback final (qti-response-else) debe asignar el feedback de una opción
   INCORRECTA, nunca el de la correcta. Esto evita mostrar "¡Correcto!" cuando el estudiante
   no selecciona nada o hay un error.
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

SOLUCIÓN PASO A PASO:
- Resolver el problema completo con pasos claros
- Llegar explícitamente a la respuesta correcta
- Lenguaje claro para estudiantes de 3°-4° medio
</feedback_requirements>

<formatting_rules>
1. Notación matemática: usar SOLO MathML, nunca LaTeX (\(...\) está prohibido)

2. Formato de números chileno:
   - Separador de miles: punto (.)
   - Separador decimal: coma (,)
   - MathML: `<mn>160.934</mn>`, `<mn>3,21868</mn>`
   - Texto: `32.186.800.000 kilómetros`
</formatting_rules>

<output_format>
Devuelve SOLO el QTI XML completo. Sin markdown, sin explicaciones.
Debe empezar con <qti-assessment-item y terminar con </qti-assessment-item>
</output_format>

<final_instruction>
Antes de generar, resuelve el problema tú mismo para verificar la respuesta correcta.
Basándote en el QTI XML original arriba, genera el XML completo con retroalimentación.
</final_instruction>
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
   - ¿El fallback en qti-response-processing asigna feedback de opción INCORRECTA (no correcta)?
   - FAIL si hay LaTeX, formato incorrecto, o fallback muestra feedback de opción correcta
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

<task>
Validar completamente esta pregunta. Encontrar CUALQUIER error o problema.
</task>

<checks>
1. RESPUESTA CORRECTA (correct_answer_check):
   - Resuelve el problema paso a paso
   - Verifica que <qti-correct-response> tenga la respuesta matemáticamente correcta
   - FAIL si la respuesta marcada no es correcta

2. RETROALIMENTACIÓN (feedback_check):
   - ¿Feedback de opción correcta explica POR QUÉ es correcta?
   - ¿Feedbacks incorrectos identifican errores conceptuales reales?
   - ¿Solución paso a paso llega a la respuesta correcta?
   - FAIL si hay errores en el feedback

3. CALIDAD DE CONTENIDO (content_quality_check):
   - Errores tipográficos
   - Caracteres mal codificados (excepto entidades HTML válidas como &#x00A1;)
   - Expresiones matemáticas incorrectas (signos, exponentes)
   - Formato numérico chileno: punto para miles, coma para decimal
   - Claridad del lenguaje para 3°-4° medio
   - FAIL si hay errores de calidad reales

4. IMÁGENES (image_check):
   - Referencias corresponden a imágenes reales
   - Imágenes son relevantes y correctas
   - Alt-text adecuado
   - NOT_APPLICABLE si no hay imágenes

5. VALIDEZ MATEMÁTICA PAES (math_validity_check):
   - Contenido dentro del temario PAES M1
   - Valores numéricos razonables
   - Unidades correctas si aplica
   - FAIL si está fuera de temario o tiene errores de magnitud
</checks>

<output_format>
JSON con este schema:
- validation_result: "pass" o "fail"
- correct_answer_check: {{status, expected_answer, marked_answer, verification_steps, issues[]}}
- feedback_check: {{status, issues[], reasoning}}
- content_quality_check: {{status, typos_found[], character_issues[], clarity_issues[]}}
- image_check: {{status, issues[], reasoning}}
- math_validity_check: {{status, issues[], reasoning}}
- overall_reasoning: resumen de 1-2 oraciones
</output_format>

<constraints>
- Sé riguroso pero no excesivamente estricto
- NO marcar como error:
  - "¡Correcto!" en feedback de opción correcta (es apropiado)
  - qti-response-else asignando feedback de opción incorrecta (válido en QTI 3.0)
  - Entidades HTML válidas (&#x00A1;, &#x00BF;, etc.)
- SÍ marcar como error:
  - Errores matemáticos reales
  - Respuesta correcta marcada incorrectamente
  - Feedback que no corresponde a la alternativa
- Cita contenido exacto cuando reportes issues
- Issues deben ser específicos y accionables
</constraints>

<final_instruction>
Basándote en el QTI XML arriba, valida completamente y responde en JSON.
</final_instruction>
"""
