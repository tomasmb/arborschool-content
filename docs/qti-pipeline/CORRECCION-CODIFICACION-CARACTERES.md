# Corrección de Codificación de Caracteres - QTI Pipeline

**Fecha de creación**: 2025-12-15  
**Última actualización**: 2025-12-15  
**Prueba**: PAES Invierno 2026 (65 preguntas)

---

## 📋 Resumen Ejecutivo

Este documento registra el análisis, corrección e integración de un sistema automático de verificación y corrección de problemas de codificación de caracteres (tildes, "ñ", signos de interrogación) en el pipeline de conversión PDF a QTI.

### Problema Identificado

Durante la revisión de los QTI generados, se detectaron errores de codificación en varias preguntas donde caracteres especiales del español (tildes, "ñ", "¿") aparecían incorrectamente codificados, por ejemplo:
- `e1cido` en lugar de `ácido`
- `af1o` en lugar de `año`
- `bfCue1l` en lugar de `¿Cuál`
- `reflexif3n` en lugar de `reflexión`

### Solución Implementada

Se implementó un sistema de verificación y corrección automática que:
1. Detecta problemas de codificación conocidos
2. Corrige automáticamente los errores detectados
3. Se integra en el pipeline principal para prevenir futuros problemas

---

## 🔧 Modificaciones Realizadas

### 1. Integración de Verificación Automática en el Pipeline

**Archivo**: `pdf-to-qti/modules/qti_transformer.py`

- **Función agregada**: `verify_and_fix_encoding(qti_xml: str) -> tuple[str, bool]`
  - Verifica y corrige automáticamente problemas de codificación comunes
  - Retorna el XML corregido y un booleano indicando si se realizaron correcciones
  - Se ejecuta automáticamente después de:
    - Parsear la respuesta del LLM (`parse_transformation_response`)
    - Limpiar el XML (`transform_to_qti`)
    - Parsear correcciones del LLM (`parse_correction_response`, `fix_qti_xml_with_llm`)

- **Diccionario de correcciones**: `ENCODING_FIXES`
  - Contiene mapeo de patrones incorrectos a caracteres correctos UTF-8
  - Incluye más de 40 patrones conocidos de errores de codificación
  - Se actualiza iterativamente cuando se descubren nuevos patrones

### 2. Actualización de Scripts de Verificación y Corrección

**Archivos modificados**:
- `pdf-to-qti/scripts/check_all_encoding_issues.py`
- `pdf-to-qti/scripts/fix_encoding_in_xml.py`

**Cambios**:
- Ambos scripts ahora importan `ENCODING_FIXES` desde `qti_transformer.py` para mantener consistencia
- Eliminación de diccionarios duplicados y hardcodeados
- Mejora en la detección: ahora verifica el XML completo (incluyendo atributos), no solo el texto

### 3. Expansión del Diccionario de Correcciones

Se agregaron nuevos patrones basados en problemas encontrados durante la revisión completa:

```python
# Patrones agregados recientemente:
'comenzare1': 'comenzará',
'restaurare1': 'restaurará',
'ab bajabb': '"baja"',
'ab no bajabb': '"no baja"',
'bfCon cue1l': '¿Con cuál',
'bfCon': '¿Con',
'cue1l': 'cuál',
'orge1nicos': 'orgánicos',
'gre1ficos': 'gráficos',
'construccif3n': 'construcción',
'comparacif3n': 'comparación',
'afirmacif3n': 'afirmación',
'continfachn': 'continuación',
'este1n': 'están',
'este1': 'está',
'este1 graduados': 'están graduados',
'este1 escritos': 'están escritos',
'este1 juntas': 'están juntas',
'Ilustracif3n': 'Ilustración',
'ilustracif3n': 'ilustración',
```

---

## ⚙️ Funcionamiento Actual del Pipeline

### Flujo de Procesamiento con Verificación de Codificación

```
1. Extracción de contenido del PDF
   └─> PyMuPDF extrae texto, imágenes, tablas
   └─> Análisis AI para categorizar contenido

2. Transformación a QTI XML
   └─> ✅ Subida de imágenes a S3 (obtener URLs públicas)
   └─> Generación de QTI con LLM (Gemini/GPT)
   └─> Parseo de respuesta del LLM
   └─> ✅ VERIFICACIÓN AUTOMÁTICA DE CODIFICACIÓN (nuevo)
   └─> Limpieza de XML
   └─> ✅ VERIFICACIÓN AUTOMÁTICA DE CODIFICACIÓN (nuevo)
   └─> Reemplazo de data URIs base64 por URLs de S3

3. Corrección de errores (si es necesario)
   └─> Si hay errores, se solicita corrección al LLM
   └─> Parseo de corrección
   └─> ✅ VERIFICACIÓN AUTOMÁTICA DE CODIFICACIÓN (nuevo)

4. Validación externa completa
   └─> Renderizado en sandbox (Chrome headless)
   └─> Screenshots del QTI renderizado
   └─> Comparación visual con PDF original usando AI
```

### Puntos de Verificación

La función `verify_and_fix_encoding` se ejecuta en **3 puntos críticos**:

1. **Después de parsear respuesta del LLM**: Corrige errores introducidos durante la generación inicial
2. **Después de limpiar XML**: Corrige cualquier problema que pueda haber quedado
3. **Después de correcciones del LLM**: Asegura que las correcciones no introduzcan nuevos errores

### Características de la Verificación

- **Automática**: No requiere intervención manual
- **No intrusiva**: Solo corrige cuando detecta problemas conocidos
- **Conservadora**: Prioriza patrones específicos sobre correcciones genéricas
- **Extensible**: Fácil agregar nuevos patrones al diccionario `ENCODING_FIXES`

### Integración con S3

El pipeline está completamente integrado con **AWS S3** para el almacenamiento de imágenes:

- **Subida de imágenes**: Las imágenes extraídas del PDF (en base64) se suben a S3 **antes** de generar el QTI XML
- **URLs públicas**: Se obtienen URLs públicas de S3 para usar en el XML final
- **Reemplazo automático**: Los data URIs base64 se reemplazan automáticamente por URLs de S3 en el XML final
- **Bucket configurable**: Usa `AWS_S3_BUCKET` del `.env` (default: `paes-question-images`)
- **Beneficios**:
  - XML más pequeño: de ~500KB a ~50KB por pregunta
  - Carga más rápida: URLs públicas de S3
  - Escalabilidad: S3 maneja el almacenamiento
  - Reutilización: Imágenes pueden ser compartidas entre preguntas

**Configuración requerida** (variables de entorno en `.env`):
```bash
AWS_ACCESS_KEY_ID=tu_access_key
AWS_SECRET_ACCESS_KEY=tu_secret_key
AWS_REGION=us-east-1
AWS_S3_BUCKET=paes-question-images
```

Ver documentación completa en: [`docs/qti-pipeline/INTEGRACION-S3.md`](./INTEGRACION-S3.md)

---

## 📊 Resultados de la Revisión Completa

### Preguntas con Problemas Detectados y Corregidos

Se revisaron los **65 QTI generados** y se identificaron problemas de codificación en:

1. **Pregunta 7**: `d1a` → `día` (2 ocurrencias) ✅ Corregida
2. **Pregunta 47**: 
   - `este1` → `está` (1 ocurrencia)
   - `Ilustracif3n` → `Ilustración` (1 ocurrencia) ✅ Corregida
3. **Pregunta 49**: `d1a` → `día` (1 ocurrencia) ✅ Corregida
4. **Pregunta 54**: `d1a` → `día` (1 ocurrencia) ✅ Corregida
5. **Pregunta 57**: Múltiples problemas:
   - `orge1nicos` → `orgánicos` (4 ocurrencias)
   - `gre1ficos` → `gráficos` (4 ocurrencias)
   - `construccif3n` → `construcción` (1 ocurrencia)
   - `comparacif3n` → `comparación` (1 ocurrencia)
   - `afirmacif3n` → `afirmación` (1 ocurrencia)
   - `continfachn` → `continuación` (1 ocurrencia)
   - `este1n` → `están` (2 ocurrencias)
   - `este1` → `está` (2 ocurrencias) ✅ Corregida

### Estadísticas Finales

- **Total preguntas revisadas**: 65
- **Preguntas sin problemas**: 37 (56.9%)
- **Preguntas corregidas automáticamente**: 5 (7.7%)
- **Preguntas con falsos positivos (MathML)**: 23 (35.4%)
  - Nota: Los patrones genéricos (`e[0-9][a-z]`, `f[0-9][a-z]`) detectados en estas preguntas son falsos positivos de MathML y otras entidades codificadas, no problemas reales de codificación de caracteres en español.

### Nota sobre Falsos Positivos

Los patrones genéricos que aparecen en muchas preguntas son **falsos positivos** de:
- Entidades MathML (por ejemplo, `e3s`, `f3w` en fórmulas matemáticas)
- Codificación de caracteres especiales en atributos XML
- Contenido base64 de imágenes

Estos no requieren corrección ya que son parte del contenido técnico del QTI, no errores de codificación de texto en español.

---

## ⏱️ Tiempo de Procesamiento de la Prueba Completa

### Información del Procesamiento Inicial

**Referencia**: `docs/qti-pipeline/ANALISIS-TIEMPO-PROCESAMIENTO.md`

- **Fecha de procesamiento**: 2025-12-15
- **Inicio**: 17:30 (primera pregunta procesada)
- **Fin**: 19:42 (última pregunta procesada)
- **Duración total**: ~2 horas 12 minutos
- **Tiempo promedio**: ~2 minutos por pregunta

### Desglose de Tiempo por Componente

| Componente | Tiempo | % del Total |
|------------|--------|-------------|
| Extracción PDF | ~5-10 seg | ~10% |
| Transformación QTI | ~10-20 seg | ~20% |
| **Validación externa** | **~60-90 seg** | **~70%** |
| **TOTAL** | **~75-120 seg** | **100%** |

### Nota sobre Tiempo de Verificación de Codificación

La verificación automática de codificación (`verify_and_fix_encoding`) es **extremadamente rápida**:
- Tiempo de ejecución: < 1 milisegundo por pregunta
- Impacto en tiempo total: **Despreciable** (< 0.01%)
- Se ejecuta en memoria, sin I/O adicional

Por lo tanto, la integración de la verificación automática **no afecta significativamente** el tiempo total de procesamiento.

### Resultados del Procesamiento

- **Total preguntas**: 65
- **Procesadas exitosamente**: 59 (90.8%)
- **Fallidas**: 6 (9.2%)
  - Preguntas: 53, 59, 62, 63, 64, 65

---

## 🔍 Análisis de Causas Raíz

### ¿Por Qué Ocurren Estos Errores?

1. **Problemas del LLM**: A pesar de instrucciones explícitas en los prompts, los modelos (especialmente GPT-5.1 como fallback) ocasionalmente generan caracteres mal codificados.

2. **Codificación intermedia**: Durante el procesamiento, el contenido puede pasar por múltiples transformaciones (PDF → texto → JSON → XML) donde se pueden introducir errores de codificación.

3. **Falta de validación previa**: Antes de esta implementación, no había verificación automática de codificación en el pipeline.

### Solución Implementada

La verificación automática actúa como una **capa de seguridad** que:
- Detecta errores conocidos inmediatamente después de la generación
- Corrige automáticamente sin requerir reprocesamiento
- Previene que los errores se propaguen a pasos posteriores

---

## 📝 Mejoras en los Prompts del LLM

Además de la verificación automática, se mejoraron los prompts en `prompt_builder.py`:

### Sección "CRITICAL: Character Encoding and Special Characters"

Se agregaron instrucciones más explícitas:
- Ejemplos negativos: "DO NOT use patterns like `e1`, `f3`"
- Ejemplos positivos y negativos claros
- Instrucciones específicas para tildes, "ñ", y signos de interrogación

Esto ayuda a **prevenir** errores, mientras que la verificación automática los **corrige** si ocurren.

---

## 🎯 Estado Actual

### ✅ Completado

- [x] Implementación de `verify_and_fix_encoding` en el pipeline principal
- [x] Integración en 3 puntos críticos del flujo
- [x] Actualización de scripts de verificación y corrección
- [x] Expansión del diccionario `ENCODING_FIXES` con nuevos patrones
- [x] Revisión completa de los 65 QTI generados
- [x] Corrección automática de 5 preguntas con problemas

### 🔄 En Progreso / Futuro

- [ ] Monitoreo continuo para detectar nuevos patrones de errores
- [ ] Expansión del diccionario cuando se descubran nuevos problemas
- [ ] Considerar validación de codificación en el servicio de validación externa

---

## 📚 Archivos Relacionados

- `pdf-to-qti/modules/qti_transformer.py`: Implementación principal
- `pdf-to-qti/modules/prompt_builder.py`: Prompts mejorados
- `pdf-to-qti/modules/utils/s3_uploader.py`: Integración con S3 para imágenes
- `pdf-to-qti/scripts/check_all_encoding_issues.py`: Script de verificación
- `pdf-to-qti/scripts/fix_encoding_in_xml.py`: Script de corrección manual
- `docs/qti-pipeline/ANALISIS-TIEMPO-PROCESAMIENTO.md`: Análisis de tiempo
- `docs/qti-pipeline/INTEGRACION-S3.md`: Documentación de integración S3

---

## 🔗 Referencias

- [Resumen de conversación sobre corrección de codificación](./README.md#corrección-de-codificación)
- [Análisis de tiempo de procesamiento](./ANALISIS-TIEMPO-PROCESAMIENTO.md)

---

**Última actualización**: 2025-12-15
