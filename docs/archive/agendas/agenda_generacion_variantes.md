# Agenda: Pipeline de Generación de Variantes de Preguntas

> Documento de seguimiento del desarrollo del pipeline para generar variantes de preguntas que evalúan el mismo concepto con diferentes números/contexto.

---

## Objetivo

Crear un sistema que genere variantes confiables de preguntas PAES para:
- No "quemar" las preguntas oficiales
- Poder hacer múltiples diagnósticos al mismo usuario
- Aumentar el banco de preguntas sin perder calidad pedagógica

---

## ✅ Completado

### 1. Diseño e Implementación Base (2025-01-22)
- [x] Revisada documentación de Tomás (`docs/ai-question-generation/ASSESSMENT_VARIANT_GENERATION.md`)
- [x] Creado módulo `app/question_variants/` con:
  - `models.py` - Dataclasses: SourceQuestion, VariantQuestion, ValidationResult
  - `variant_generator.py` - Generación con prompts restrictivos via Gemini
  - `variant_validator.py` - Validación matemática y de concepto
  - `pipeline.py` - Orquestador del flujo
  - `run_variant_generation.py` - CLI para ejecutar

### 2. Pruebas Iniciales
| Pregunta | Tipo | Generadas | Aprobadas | Notas |
|----------|------|-----------|-----------|-------|
| Q1 | Aritmética enteros | 2 | 2 | Aprobadas manualmente (falso negativo del validador) |
| Q4 | Fracciones | 2 | 2 | ✅ Aprobadas tras fix de MathML/XML element truthiness |
| Q5 | Tabla + comparación | 2 | 2 | Aprobadas manualmente |

### 3. Correcciones al Validador
- [x] Corregido `_element_to_text()` para incluir `<qti-prompt>`
- [x] Corregido `_mathml_to_text()` para procesar `<mfrac>` como `(num/den)`
- [x] Agregado `_process_mathml_element()` recursivo para MathML complejo
- [x] Corregido bug de truthiness de XML Elements en `_find_correct_answer()` y `_extract_question_text()`
      - Elementos XML sin hijos evalúan como `False` en Python - ahora usa `is not None` explícito

---

### 4. Generación Variantes Diagnóstico (Fase 1a: Sin Imagen) - ✅ COMPLETADO
- [x] Configurar guardado en doble ubicación (original + carpeta diagnóstico)
- [x] Ejecutar lote R1, A2, B2, C2 (preguntas sin imagen)
- **Resultados**: 29/32 variantes aprobadas (91%)
  - Q35 (3 intentos fallidos): Fallo en copia de MathML complejo
  - Q3_v1: Aprobada manualmente (falso negativo)
  - 27 Variantes generadas y validadas automáticamente

---

### 5. Fase 1b: Imágenes Decorativas - ✅ COMPLETADO
- [x] Etiquetar metadatos `image_type: decorative`
- [x] Modificar generador para incluir instrucción de preservación de imagen
- [x] Ejecutar lote Q46, Q60, Q6, Q63
- **Resultados**: 7/8 variantes aprobadas (87.5%)
  - Q46 (inv-25): 2/2 ✅
  - Q60 (sr-26): 2/2 ✅
  - Q6 (inv-25): 2/2 ✅ (v2 aprobada manualmente - falso negativo)
  - Q63 (sr-25): ✅ Resuelto con imágenes generadas por IA (3 variantes)

---

### 6. Fase 2: Preguntas con Gráficos e Imágenes Complejas - ✅ COMPLETADO
- [x] Q33 (gráfico circular): 2/2 ✅ - Cambio de quién aporta dato conocido
- [x] Q58 (tabla de goles): 2/2 ✅ - Cambio de datos de tabla
- [x] Q63 (transformaciones): 3/3 ✅ - Imágenes generadas con IA
  - v1: Taza - pregunta por traslación
  - v2: Taza - pregunta por reflexión  
  - v3: Velero - pregunta por reflexión (imágenes originales)
- [x] Q65 (box plots): 2/2 ✅ - Datos modificados para diferentes respuestas correctas
  - v1: Datos con Q3=4 → ChoiceA correcta
  - v2: Datos con Med=2.5 → ChoiceD correcta

### 7. Fase 3: Variantes Faltantes y Visuales (Q23, Q55, Q56, Q50) - ✅ COMPLETADO
- [x] **Q23 (sr-26)**: 2/2 ✅ 
  - Variantes de gráfico circular (Pie chart)
  - v1: Gráfico con sectores modificados (25% vs 20%)
  - v2: Gráfico con sectores modificados (15% vs 10%)
- [x] **Q55 (sr-25)**: 2/2 ✅
  - Pregunta de pendiente de línea
  - v1: Pendiente positiva, diferente intersección
  - v2: Pendiente negativa
- [x] **Q56 (inv-25)**: 2/2 ✅
  - Variantes generadas y validadas
- [x] **Q50 (inv-25)**: 1/1 ✅
  - **Nota**: Solo 1 variante generada ya que, por la naturaleza de la pregunta, es difícil generar una variante que no cambie demasiado el propósito original.
  - v1: "Radios como manecillas" - Contexto visual distinto pero matemáticamente equivalente (2πr).
- [x] **Q10, Q45**: Variantes faltantes copiadas exitosamente a carpeta de diagnóstico.

---

## 📚 Documentación Técnica

Para detalles de uso, CLI, arquitectura y estructura de archivos, ver:
👉 [**Especificaciones del Pipeline de Variantes**](../specifications/variant-generation-pipeline.md)

---

## 🔄 Pendientes (Casos Muy Complejos)
- [ ] Mejorar prompt para copiar estructuras MathML complejas (sistemas de ecuaciones, tablas)
- [x] Corrección de extracción de MathML básico (fracciones) ✅

---

## 📋 Por Hacer

### Mejoras al Pipeline
- [ ] Implementar retry automático para variantes rechazadas
- [ ] Agregar flag `--dry-run` para ver qué se generaría sin llamar a la API
- [ ] Mejorar logging y reportes

### Pruebas Pendientes
- [ ] Probar con preguntas que tienen `<mfrac>` (fracciones)
- [ ] Probar con preguntas que tienen `<msup>` (potencias)
- [ ] Probar con preguntas que tienen `<msqrt>` (raíces)
- [ ] Probar con preguntas con imágenes/gráficos
- [ ] Probar batch de 10+ preguntas para evaluar tasa de aprobación

### Integración
- [ ] Definir cómo se usarán las variantes en el sistema de diagnóstico
- [ ] Documentar estructura de output para frontend (ver especificación)
- [ ] Agregar variantes a la base de datos

---

## Notas Técnicas

- **API**: Gemini 3 Pro (con fallback a OpenAI si hay rate limits)
- **Costo estimado**: ~7500 tokens por pregunta (3 variantes)
- **Tasa de aprobación actual**: ~50% (necesita mejorar extracción MathML)
