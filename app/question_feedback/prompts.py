"""PAES-specific prompts for feedback generation and validation (Spanish)."""

from __future__ import annotations

FEEDBACK_ENHANCEMENT_PROMPT = """
Eres un experto en educación matemática para la prueba PAES de Chile y en el formato QTI 3.0.

TAREA: Agregar retroalimentación educativa a esta pregunta de matemáticas.
Debes devolver el QTI XML COMPLETO con la retroalimentación incluida.

AUDIENCIA:
- Estudiantes de 3° y 4° medio (16-18 años)
- Preparación para PAES Matemática M1
- Nivel de lectura: claro y preciso, sin jerga innecesaria

QTI XML ORIGINAL:
```xml
{original_qti_xml}
```

{images_section}

REQUISITOS DE RETROALIMENTACIÓN:

1. DECLARACIONES DE OUTCOME (agregar después de qti-response-declaration):
```xml
<qti-outcome-declaration identifier="FEEDBACK" cardinality="single" base-type="identifier"/>
<qti-outcome-declaration identifier="SOLUTION" cardinality="single" base-type="identifier"/>
```

2. RETROALIMENTACIÓN POR OPCIÓN (dentro de cada qti-simple-choice):
```xml
<qti-feedback-inline outcome-identifier="FEEDBACK" identifier="ChoiceX" show-hide="show">
  [Tu explicación de 1-3 oraciones]
</qti-feedback-inline>
```

Requisitos para cada opción:
- Opción correcta: Comienza con "¡Correcto! " y explica POR QUÉ es correcta matemáticamente
- Opciones incorrectas: Comienza con "Incorrecto. " e identifica el ERROR CONCEPTUAL específico
- Sé específico a ESTA pregunta, no genérico

3. SOLUCIÓN PASO A PASO (al final de qti-item-body):
```xml
<qti-feedback-block identifier="show" outcome-identifier="SOLUTION" show-hide="show">
  <qti-content-body>
    <p><strong>[Título descriptivo del método]</strong></p>
    <ol>
      <li>Paso 1: [Descripción clara]</li>
      <li>Paso 2: [Descripción clara]</li>
    </ol>
  </qti-content-body>
</qti-feedback-block>
```

4. RESPONSE PROCESSING (reemplazar el existente):
```xml
<qti-response-processing>
  <qti-response-condition>
    <qti-response-if>
      <qti-match>
        <qti-variable identifier="RESPONSE"/>
        <qti-correct identifier="RESPONSE"/>
      </qti-match>
      <qti-set-outcome-value identifier="SCORE">
        <qti-base-value base-type="float">1</qti-base-value>
      </qti-set-outcome-value>
    </qti-response-if>
    <qti-response-else>
      <qti-set-outcome-value identifier="SCORE">
        <qti-base-value base-type="float">0</qti-base-value>
      </qti-set-outcome-value>
    </qti-response-else>
  </qti-response-condition>
  <qti-set-outcome-value identifier="FEEDBACK">
    <qti-variable identifier="RESPONSE"/>
  </qti-set-outcome-value>
  <qti-set-outcome-value identifier="SOLUTION">
    <qti-base-value base-type="identifier">show</qti-base-value>
  </qti-set-outcome-value>
</qti-response-processing>
```

REGLAS CRÍTICAS:
- Mantén TODOS los elementos originales (stem, choices, images, etc.)
- NO modifiques el contenido de la pregunta, solo agrega retroalimentación
- Usa el namespace QTI 3.0 correcto
- Asegura que el XML sea válido y bien formado
- Usa comillas dobles para atributos
- No uses caracteres especiales que rompan XML (usa entidades si es necesario)

FORMATO DE SALIDA:
Devuelve SOLO el QTI XML completo, sin markdown, sin explicaciones.
El XML debe empezar con <qti-assessment-item y terminar con </qti-assessment-item>
"""


FINAL_VALIDATION_PROMPT = """
Eres un validador experto de preguntas para la prueba PAES de Matemática M1 de Chile.
Tu trabajo es encontrar CUALQUIER error o problema en esta pregunta.

QTI XML CON RETROALIMENTACIÓN:
```xml
{qti_xml_with_feedback}
```

{images_section}

VALIDACIONES REQUERIDAS:

1. VALIDACIÓN DE RESPUESTA CORRECTA
   - ¿La respuesta marcada en <qti-correct-response> es matemáticamente correcta?
   - Resuelve el problema paso a paso para verificar
   - ¿El valor numérico/expresión es exactamente correcto?

2. VALIDACIÓN DE RETROALIMENTACIÓN
   - ¿La retroalimentación de la opción correcta explica correctamente POR QUÉ es correcta?
   - ¿La retroalimentación de cada opción incorrecta identifica el ERROR CONCEPTUAL real?
   - ¿La solución paso a paso lleva a la respuesta correcta?
   - ¿Los pasos matemáticos son correctos y completos?

3. VALIDACIÓN DE CONTENIDO
   - ¿Hay errores tipográficos?
   - ¿Hay caracteres extraños o mal codificados?
   - ¿Las expresiones matemáticas están correctas? (signos, exponentes, fracciones)
   - ¿El lenguaje es claro y apropiado para estudiantes de 3°-4° medio?

4. VALIDACIÓN DE IMÁGENES (si hay imágenes)
   - ¿Las referencias a imágenes en el enunciado tienen imagen correspondiente?
   - ¿La imagen es relevante y correcta para la pregunta?
   - ¿El alt-text describe adecuadamente la imagen?
   - ¿No hay imágenes huérfanas (presentes pero no referenciadas)?

5. VALIDACIÓN MATEMÁTICA PAES
   - ¿El contenido está dentro del temario PAES M1?
   - ¿Los valores numéricos son razonables? (no hay errores de orden de magnitud)
   - ¿Las unidades son correctas si aplica?

INSTRUCCIONES:
- Sé ESTRICTO: cualquier error debe resultar en "fail"
- Proporciona reasoning específico citando el contenido exacto
- Los issues deben ser ESPECÍFICOS y ACCIONABLES
- Si no hay imágenes, marca image_check como "not_applicable"
"""
