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

<rules>
1. MANTENER todos los elementos originales (stem, choices, images) sin modificar
2. AGREGAR outcome declarations después de qti-response-declaration:
   - <qti-outcome-declaration identifier="FEEDBACK" cardinality="single" base-type="identifier"/>
   - <qti-outcome-declaration identifier="SOLUTION" cardinality="single" base-type="identifier"/>

3. AGREGAR qti-feedback-inline dentro de cada qti-simple-choice:
   - Opción correcta: "¡Correcto! [explicación matemática de POR QUÉ es correcta]"
   - Opciones incorrectas: "Incorrecto. [error conceptual específico que lleva a esta opción]"

4. AGREGAR qti-feedback-block al final de qti-item-body con solución paso a paso:
   ```xml
   <qti-feedback-block identifier="show" outcome-identifier="SOLUTION" show-hide="show">
     <qti-content-body>
       <p><strong>[Título del método]</strong></p>
       <ol><li>Paso 1...</li><li>Paso 2...</li></ol>
     </qti-content-body>
   </qti-feedback-block>
   ```

5. REEMPLAZAR qti-response-processing con versión que incluya FEEDBACK y SOLUTION
</rules>

<evaluation_criteria>
Tu output será evaluado en:
1. PRECISIÓN FACTUAL: ¿El feedback de la opción correcta explica correctamente la matemática?
2. ERRORES CONCEPTUALES: ¿Cada feedback incorrecto identifica el error real que lleva a esa opción?
3. SOLUCIÓN PASO A PASO: ¿Los pasos matemáticos son correctos y llevan a la respuesta correcta?
4. CLARIDAD PEDAGÓGICA: ¿El lenguaje es apropiado para estudiantes de 3°-4° medio?
</evaluation_criteria>

<output_format>
Devuelve SOLO el QTI XML completo. Sin markdown, sin explicaciones.
Debe empezar con <qti-assessment-item y terminar con </qti-assessment-item>
</output_format>

<final_instruction>
Basándote en el QTI XML original arriba, genera el XML completo con retroalimentación.
</final_instruction>
"""


# ---------------------------------------------------------------------------
# FEEDBACK REVIEW PROMPT
# ---------------------------------------------------------------------------
# Lightweight validation focused ONLY on the generated feedback.
# Does NOT validate the original question content.
# Used as a gate after feedback generation in the enrichment pipeline.
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
Revisar ÚNICAMENTE la retroalimentación generada (no el contenido original de la pregunta).
Verificar precisión factual y claridad pedagógica del feedback.
</task>

<checks>
1. PRECISIÓN FACTUAL (feedback_accuracy):
   - ¿El feedback de la opción correcta explica correctamente POR QUÉ es matemáticamente correcta?
   - ¿Los feedbacks de opciones incorrectas identifican errores conceptuales REALES?
   - ¿La solución paso a paso tiene matemáticas correctas y llega a la respuesta correcta?
   - FAIL si hay cualquier error matemático en el feedback

2. CLARIDAD PEDAGÓGICA (feedback_clarity):
   - ¿El lenguaje es claro para estudiantes de 3°-4° medio?
   - ¿Los pasos son suficientemente detallados?
   - ¿El feedback es específico a esta pregunta (no genérico)?
   - FAIL si el feedback es confuso, muy técnico, o genérico
</checks>

<output_format>
JSON con este schema:
- review_result: "pass" o "fail" (fail si cualquier check falla)
- feedback_accuracy: {{status, issues[], reasoning}}
- feedback_clarity: {{status, issues[], reasoning}}
- overall_reasoning: resumen de 1-2 oraciones
</output_format>

<constraints>
- NO evalúes el contenido original de la pregunta
- NO evalúes si la respuesta marcada es correcta (eso es trabajo de validación final)
- SOLO evalúa la calidad del feedback generado
- Sé estricto: cualquier error factual en el feedback = fail
</constraints>

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
   - Caracteres mal codificados
   - Expresiones matemáticas incorrectas (signos, exponentes)
   - Claridad del lenguaje para 3°-4° medio
   - FAIL si hay errores de calidad

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
- Sé ESTRICTO: cualquier error = fail
- Cita contenido exacto cuando reportes issues
- Issues deben ser específicos y accionables
</constraints>

<final_instruction>
Basándote en el QTI XML arriba, valida completamente y responde en JSON.
</final_instruction>
"""
