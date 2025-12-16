# Estado del Proyecto QTI - 2025-12-14

**Última actualización**: 2025-12-14  
**Estado**: En standby temporal - Organización de información nueva

---

## 📋 Resumen Ejecutivo

Este documento organiza:
1. **Estado actual** del trabajo realizado ayer (2025-12-13)
2. **Información nueva** recibida del socio
3. **Tareas pendientes** y plan de acción
4. **Comparación de enfoques** para decidir el mejor proceso

---

## 📊 Estado Actual del Trabajo (Ayer - 2025-12-13)

### Pipeline Actual: 4 Pasos con MD Intermedio

**Ubicación**: `app/qti-pipeline-4steps/`

**Pasos del Pipeline**:
1. **PARSE**: PDF → Parsed JSON (Extend.ai)
2. **SEGMENT**: Parsed JSON → Individual Questions (Markdown)
3. **GENERATE**: Questions → QTI XML
4. **VALIDATE**: QTI XML → Validated QTI

**Problemas Identificados**:
- ❌ Errores de reconocimiento de notación matemática (V → √, potencias concatenadas)
- ❌ Errores con imágenes (no se extraen correctamente del PDF)
- ❌ Muchos errores requieren corrección manual

**Soluciones Implementadas**:
- ✅ `MathCorrector` - Corrección automática de notación matemática
- ✅ Correcciones manuales documentadas (13 preguntas)
- ✅ Herramientas para aplicar correcciones y regenerar QTI
- ✅ Extractor de PDF para revisión manual

**Archivos Clave**:
- `app/qti-pipeline-4steps/pipeline/pdf_parser.py` - Paso 1 (con MathCorrector integrado)
- `app/qti-pipeline-4steps/pipeline/segmenter.py` - Paso 2
- `app/qti-pipeline-4steps/pipeline/generator.py` - Paso 3
- `app/qti-pipeline-4steps/pipeline/math_corrector.py` - Corrección automática
- `app/qti-pipeline-4steps/pipeline/apply_math_corrections_to_segmented.py` - Aplicar correcciones
- `app/qti-pipeline-4steps/pipeline/regenerate_qti_for_questions.py` - Regenerar QTI selectivo

**Documentación**:
- [Correcciones Manuales](./CORRECCIONES-MANUALES.md) - Todas las correcciones realizadas
- [Recomendaciones](./RECOMENDACIONES.md) - Recomendaciones y decisiones
- [Comparación de Pipelines](./COMPARACION-PIPELINES.md) - Comparación de enfoques
- `app/pdf-to-qti/docs/LIMITACIONES-EXTEND-AI-Y-SOLUCIONES.md` - Limitaciones Extend.ai (técnico)

**Estado de Prueba Actual**:
- Prueba procesada: `prueba-invierno-2026`
- 65 preguntas totales
- 13 preguntas corregidas manualmente
- 64/65 preguntas con QTI generado (Q46 falló)

---

## 🆕 Información Nueva del Socio

### 1. Credenciales y Recursos

**Amazon S3**:
- **Bucket**: `paes-question-images`
- **Propósito**: Subir imágenes necesarias para QTI
- **URL pública**: Disponible para usar en QTI XML
- **Acción requerida**: Conectarse al servidor y subir imágenes ahí

**OpenAI API**:
- **Versión**: OpenAI 5.1
- **Propósito**: Backup cuando se acaben créditos de Gemini
- **Acción requerida**: Configurar como alternativa en el pipeline

### 2. Código Nuevo en Main

**Ubicación**: Código subido a `main` (branch principal)

**Componentes**:
- **PDF Splitter**: Nueva versión
- **PDF a QTI**: Nueva versión

**Características**:
- ✅ **Sin pasar por MD**: Evita errores de reconocimiento matemático e imágenes
- ✅ **Overfitting para PAES M1**: Optimizado para formato específico
- ✅ **Mismo formato**: Todas las pruebas son de alternativas (múltiple choice)
- ⚠️ **Versión desactualizada**: Necesita actualización

**Actualizaciones Necesarias**:
- Cambiar a **Gemini Preview 3** o **OpenAI 5.1** (versiones más actualizadas)
- Adaptar el PDF splitter para que sea similar al que pasaba por MD pero sin MD

### 3. Objetivos del Socio

1. **Cambiar PDF splitter**: Similar al que pasaba por MD pero sin MD
2. **Overfitting para PAES M1**: Optimizar para formato de alternativas
3. **Actualizar modelos**: Gemini Preview 3 o OpenAI 5.1
4. **Subir imágenes a S3**: Usar bucket `paes-question-images`

---

## 📝 Tareas Pendientes

### Prioridad Alta

1. **🔍 Investigar dónde se guardan las imágenes actualmente**
   - ✅ **Pipeline actual**: Extend.ai devuelve URLs de imágenes en `imageUrl` dentro de los bloques
   - ✅ Las imágenes se inyectan en el markdown como `![alt](url)`
   - ✅ Se referencian directamente en el QTI XML usando las URLs de Extend.ai
   - ⚠️ **Problema**: URLs de Extend.ai pueden expirar o no ser públicas
   - ✅ **Solución requerida**: Subir imágenes a S3 bucket `paes-question-images` y usar URLs públicas

2. **📥 Revisar código nuevo en main** ✅ COMPLETADO
   - ✅ Encontrados: `pdf-splitter/` y `pdf-to-qti/` en root del proyecto
   - ✅ Commit identificado: `e46815e`
   - ⏳ **Pendiente**: Entender cómo funciona el nuevo enfoque en detalle
   - ⏳ **Pendiente**: Comparar arquitectura con pipeline actual

3. **🔧 Modificar código nuevo**
   - Agregar opción de trabajo (nueva alternativa)
   - Actualizar a Gemini Preview 3 o OpenAI 5.1
   - Adaptar PDF splitter (similar a MD pero sin MD)
   - Implementar overfitting para PAES M1

4. **☁️ Integración con Amazon S3**
   - Configurar credenciales de S3
   - Crear función para subir imágenes al bucket `paes-question-images`
   - Obtener URLs públicas para usar en QTI XML
   - Modificar pipeline para usar S3 en lugar de URLs de Extend.ai

### Prioridad Media

5. **⚖️ Comparar enfoques**
   - Pipeline actual (4 pasos con MD) vs. Nuevo código (sin MD)
   - Métricas: eficiencia, errores, tiempo de procesamiento
   - Decidir cuál es mejor

6. **🧪 Perfeccionar con una prueba**
   - Elegir una prueba de prueba
   - Aplicar el mejor enfoque
   - Iterar hasta que funcione perfectamente

7. **📈 Aplicar a más pruebas**
   - Una vez perfeccionado, aplicar a todas las pruebas
   - Automatizar el proceso

---

## 🔄 Plan de Acción

### Fase 1: Investigación y Análisis (Standby)

**Objetivo**: Entender ambos enfoques completamente

**Tareas**:
1. ✅ Documentar estado actual (este documento)
2. ⏳ Investigar dónde se guardan imágenes actualmente
3. ⏳ Revisar código nuevo en main
4. ⏳ Comparar arquitecturas de ambos enfoques

**Resultado esperado**: Documento comparativo de ambos enfoques

---

### Fase 2: Desarrollo (Después del standby)

**Objetivo**: Mejorar el enfoque elegido

**Tareas**:
1. Modificar código nuevo según requerimientos del socio
2. Integrar S3 para almacenamiento de imágenes
3. Actualizar modelos (Gemini Preview 3 / OpenAI 5.1)
4. Implementar overfitting para PAES M1

**Resultado esperado**: Pipeline funcional mejorado

---

### Fase 3: Pruebas y Comparación

**Objetivo**: Decidir el mejor enfoque

**Tareas**:
1. Probar pipeline actual mejorado
2. Probar nuevo código modificado
3. Comparar resultados (eficiencia, errores, calidad)
4. Decidir cuál usar

**Resultado esperado**: Decisión documentada sobre el mejor enfoque

---

### Fase 4: Perfeccionamiento

**Objetivo**: Perfeccionar el enfoque elegido con una prueba

**Tareas**:
1. Elegir prueba de prueba
2. Aplicar el mejor enfoque
3. Iterar hasta perfección
4. Documentar proceso

**Resultado esperado**: Pipeline perfeccionado y documentado

---

### Fase 5: Escalamiento

**Objetivo**: Aplicar a todas las pruebas

**Tareas**:
1. Automatizar proceso perfeccionado
2. Aplicar a todas las pruebas PAES M1
3. Validar resultados

**Resultado esperado**: Todas las pruebas procesadas correctamente

---

## 🔍 Preguntas por Resolver

### Sobre Imágenes

1. **¿Dónde se guardan las imágenes actualmente?**
   - ¿Extend.ai devuelve URLs?
   - ¿Se descargan localmente?
   - ¿Cómo se referencian en el QTI XML actual?

2. **¿Cómo integrar S3?**
   - ¿Subir todas las imágenes de Extend.ai?
   - ¿Subir imágenes del PDF directamente?
   - ¿Cuándo subir (durante parsing, durante generación QTI)?

### Sobre Código Nuevo

3. **¿Dónde está el código nuevo?**
   - ¿En qué branch/commit?
   - ¿Qué archivos específicos?
   - ¿Cómo se ejecuta?

4. **¿Cómo funciona el nuevo enfoque?**
   - ¿Qué pasos tiene?
   - ¿Cómo evita los errores de MD?
   - ¿Qué ventajas tiene?

### Sobre Modelos

5. **¿Gemini Preview 3 o OpenAI 5.1?**
   - ¿Cuál es mejor para este caso?
   - ¿Cuál es más económico?
   - ¿Cuál tiene mejor soporte para matemáticas?

6. **¿Cómo actualizar el código?**
   - ¿Qué cambios requiere?
   - ¿Hay breaking changes?

---

## 📚 Referencias y Documentos

### Documentos de Ayer

- [Correcciones Manuales](./CORRECCIONES-MANUALES.md) - Correcciones manuales
- [Recomendaciones](./RECOMENDACIONES.md) - Recomendaciones
- `app/pdf-to-qti/docs/LIMITACIONES-EXTEND-AI-Y-SOLUCIONES.md` - Limitaciones Extend.ai (documentación técnica)
- `app/pdf-to-qti/CORRECCION_MATEMATICA.md` - MathCorrector

### Código Actual

- `app/qti-pipeline-4steps/` - Pipeline completo actual (4 pasos con MD)
- `app/data/pruebas/procesadas/prueba-invierno-2026/` - Prueba procesada

### Código Nuevo (encontrado en main)

**Ubicación**: Root del proyecto (no en `app/`)

**Carpetas**:
- `pdf-splitter/` - Splitter de PDFs (Lambda function)
- `pdf-to-qti/` - Conversión directa PDF a QTI (sin MD, Lambda function)

**Commit**: `e46815e` - "added examples of pdf to qti direct conversion"

**Características del nuevo código**:
- ✅ **Conversión directa PDF → QTI** (sin pasar por MD intermedio)
- ✅ **Procesamiento de imágenes especializado** (módulo completo `image_processing/`)
- ✅ **Validación visual y de XML** (módulo `validation/`)
- ✅ **Configurado para AWS Lambda** (serverless, ya desplegado)
- ✅ **Endpoints en producción**:
  - `convertPdfToQti`: https://6yuvwmyy6mjtu5ojqbkindumpq0zaxwv.lambda-url.us-east-1.on.aws/
  - `questionDetail`: https://dwz3c4pziukfhwfqkkauvzh4bu0uicgu.lambda-url.us-east-1.on.aws/
- ⚠️ **Usa versiones desactualizadas** de modelos (necesita actualización a Gemini Preview 3 o OpenAI 5.1)

**Estructura del código nuevo**:
```
pdf-splitter/
├── main.py                    # Lógica principal de splitting
├── lambda_handler.py          # Handler para Lambda
├── modules/
│   ├── pdf_processor.py      # Procesamiento de PDF
│   ├── chunk_segmenter.py    # Segmentación de chunks
│   ├── block_matcher.py      # Matching de bloques
│   └── ...

pdf-to-qti/
├── main.py                    # Lógica principal (512 líneas)
├── lambda_handler.py          # Handler para Lambda
├── modules/
│   ├── pdf_processor.py      # Procesamiento PDF (898 líneas)
│   ├── question_detector.py  # Detección de preguntas
│   ├── qti_transformer.py    # Transformación a QTI
│   ├── prompt_builder.py     # Construcción de prompts (647 líneas)
│   ├── ai_processing/        # Análisis con AI
│   ├── image_processing/     # Procesamiento de imágenes
│   ├── content_processing/   # Procesamiento de contenido
│   └── validation/           # Validación
└── ...
```

**Total**: ~13,718 líneas de código nuevo

---

## 🎯 Próximos Pasos Inmediatos

Cuando retomemos el trabajo:

1. **✅ Código nuevo encontrado** - Ya identificado en `pdf-splitter/` y `pdf-to-qti/`

2. **Revisar código nuevo en detalle**
   ```bash
   git checkout main
   git pull
   # Revisar pdf-splitter/main.py y pdf-to-qti/main.py
   # Entender el flujo completo
   ```

3. **Investigar imágenes actuales** ✅ PARCIALMENTE COMPLETADO
   - ✅ Extend.ai devuelve URLs en `imageUrl`
   - ⏳ Verificar cómo el nuevo código maneja imágenes
   - ⏳ Comparar ambos enfoques

4. **Configurar credenciales**
   - Guardar credenciales S3 de forma segura (`.env` o similar)
   - Configurar OpenAI 5.1 API key
   - Probar conexión a S3 bucket `paes-question-images`

5. **Crear documento comparativo**
   - Comparar pipeline actual (`app/qti-pipeline-4steps/`) vs. nuevo código (`pdf-to-qti/`)
   - Listar pros/contras de cada uno
   - Decidir cuál mejorar primero

6. **Modificar código nuevo según requerimientos**
   - Actualizar a Gemini Preview 3 o OpenAI 5.1
   - Adaptar PDF splitter (similar a MD pero sin MD)
   - Implementar overfitting para PAES M1 (formato de alternativas)
   - Integrar S3 para imágenes

---

## 📝 Notas Adicionales

- **Standby temporal**: El proyecto está en pausa pero bien documentado
- **Información completa**: Todo está organizado para retomar fácilmente
- **Dos enfoques**: Necesitamos comparar y decidir cuál es mejor
- **Objetivo final**: Pipeline perfecto para procesar todas las pruebas PAES M1

---

**Última actualización**: 2025-12-14  
**Próxima revisión**: Cuando se retome el trabajo
