# Guía: Integración de Respuestas Correctas

Este documento explica cómo integrar las respuestas correctas de un PDF al proceso de generación QTI.

## 📋 Proceso Completo

### Paso 1: Subir PDF con Respuestas Correctas

Coloca el PDF con las respuestas correctas en la carpeta de la prueba:
```
app/data/pruebas/raw/{test-name}/respuestas-{nombre-prueba}.pdf
```

Por ejemplo:
```
app/data/pruebas/raw/prueba-invierno-2026/respuestas-prueba-invierno-2026.pdf
```

O si el archivo tiene otro nombre (como un clavijero):
```
app/data/pruebas/raw/prueba-invierno-2026/2026-25-07-18-clavijero-paes-invierno-m1.pdf
```

**Estructura de carpetas:**
```
app/data/pruebas/raw/
  └── prueba-invierno-2026/
      ├── prueba-invierno-2026.pdf        # PDF de la prueba
      └── respuestas-prueba-invierno-2026.pdf  # PDF con respuestas (o cualquier nombre)
```

### Paso 2: Extraer Respuestas del PDF

Ejecuta el script de extracción:

```bash
cd app/pruebas/pdf-to-qti

python scripts/extract_answer_key.py \
    --pdf-path ../../data/pruebas/raw/prueba-invierno-2026/respuestas-prueba-invierno-2026.pdf \
    --output ../../data/pruebas/procesadas/prueba-invierno-2026/respuestas_correctas.json \
    --test-name prueba-invierno-2026 \
    --focus-page 3
```

Si las respuestas están en una página específica (por ejemplo, página 3), usa `--focus-page 3` para que el script se enfoque solo en esa página.

Este script:
- Extrae el texto del PDF
- Usa AI para identificar las respuestas correctas
- Genera un JSON con el mapeo pregunta → respuesta
- Guarda el resultado en la ubicación especificada

### Paso 3: Procesar Preguntas con Respuestas

Cuando proceses las preguntas, el pipeline detectará automáticamente el archivo `respuestas_correctas.json` y usará las respuestas correctas al generar el QTI.

```bash
# El pipeline buscará automáticamente el archivo de respuestas
python process_paes_invierno.py --paes-mode
```

## 📁 Estructura del JSON de Respuestas

El archivo `respuestas_correctas.json` tiene esta estructura:

```json
{
  "test_name": "prueba-invierno-2026",
  "source_pdf": "app/data/pruebas/raw/prueba-invierno-2026/respuestas-prueba-invierno-2026.pdf",
  "total_questions": 65,
  "answers": {
    "1": "ChoiceA",
    "2": "ChoiceB",
    "3": "ChoiceD",
    "4": "ChoiceC",
    ...
    "65": "ChoiceA"
  },
  "metadata": {
    "extraction_method": "AI (Gemini/OpenAI)",
    "question_numbers": ["1", "2", "3", ..., "65"]
  }
}
```

**Formato de respuestas:**
- Las claves son números de pregunta como strings: `"1"`, `"2"`, etc.
- Los valores son identificadores QTI: `"ChoiceA"`, `"ChoiceB"`, `"ChoiceC"`, `"ChoiceD"`

## 🔍 Cómo Funciona

1. **Extracción**: El script `extract_answer_key.py` usa AI para identificar respuestas correctas en el PDF
2. **Detección automática**: El pipeline busca `respuestas_correctas.json` en el directorio de la prueba
3. **Integración**: Las respuestas se pasan al prompt del LLM que genera el QTI
4. **Inclusión en XML**: El LLM incluye la respuesta correcta en `<qti-correct-response>`

## 📍 Ubicación del Archivo de Respuestas

El pipeline busca el archivo en estas ubicaciones (en orden):

1. `app/data/pruebas/procesadas/{test_name}/respuestas_correctas.json`
2. El directorio padre del output si está en una estructura específica

Asegúrate de que el archivo esté en la primera ubicación para garantizar que se encuentre.

## ✅ Verificación

Después de procesar, verifica que las respuestas correctas están en los XMLs:

```bash
# Verificar que una pregunta tiene la respuesta correcta
grep -A 2 "qti-correct-response" app/data/pruebas/procesadas/prueba-invierno-2026/qti/Q3.xml
```

Deberías ver algo como:
```xml
<qti-correct-response>
  <qti-value>ChoiceD</qti-value>
</qti-correct-response>
```

## ⚠️ Notas Importantes

- Si no se encuentra el archivo de respuestas, el LLM intentará inferir la respuesta correcta del contenido (comportamiento anterior)
- Las respuestas deben estar en formato `ChoiceA`, `ChoiceB`, etc. (el script convierte automáticamente de A, B, C, D)
- Si una pregunta no tiene respuesta en el JSON, se usará la inferencia del LLM
- El archivo de respuestas es opcional - el pipeline funciona sin él, pero es más preciso con él
