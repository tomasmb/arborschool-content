# Análisis de Tiempo de Procesamiento - PAES Invierno 2026

**Fecha**: 2025-12-15  
**Prueba**: PAES Invierno 2026 (65 preguntas)

---

## ⏱️ Tiempo Total

- **Inicio**: 17:30 (primera pregunta procesada)
- **Fin**: 19:42 (última pregunta procesada)
- **Duración total**: ~2 horas 12 minutos
- **Tiempo promedio**: ~2 minutos por pregunta

---

## 📊 Resultados

- **Total preguntas**: 65
- **Procesadas exitosamente**: 59 (90.8%)
- **Fallidas**: 6 (9.2%)
  - Preguntas: 53, 59, 62, 63, 64, 65

---

## 🔍 ¿Por Qué se Demoró Tanto?

### Pasos del Procesamiento (por pregunta):

1. **Extracción de contenido del PDF** (~5-10 seg)
   - PyMuPDF extrae texto, imágenes, tablas
   - Análisis AI para categorizar contenido
   - Llamadas a Gemini para análisis

2. **Transformación a QTI XML** (~10-20 seg)
   - Generación de QTI con Gemini
   - Subida de imágenes a S3
   - Reemplazo de base64 por URLs de S3

3. **Validación externa completa** (~60-90 seg) ⚠️ **MÁS LENTO**
   - Renderiza QTI en sandbox (Chrome headless)
   - Toma screenshots del QTI renderizado
   - Compara visualmente con PDF original usando AI
   - Valida completitud, imágenes, tablas, gráficos

### Tiempo por Componente (estimado):

| Componente | Tiempo | % del Total |
|------------|--------|-------------|
| Extracción PDF | ~5-10 seg | ~10% |
| Transformación QTI | ~10-20 seg | ~20% |
| **Validación externa** | **~60-90 seg** | **~70%** |
| **TOTAL** | **~75-120 seg** | **100%** |

---

## ⚠️ Cuello de Botella: Validación Externa

La validación externa es el paso más lento porque:

1. **Renderizado en sandbox**: Debe iniciar Chrome, renderizar el QTI
2. **Screenshots**: Captura de imágenes del QTI renderizado
3. **Comparación visual con AI**: Llamada a Gemini/OpenAI para comparar visualmente
4. **Timeout de 120 segundos**: Cada validación puede tardar hasta 2 minutos

**Para 65 preguntas**:
- 65 × 90 seg promedio = **~97 minutos** solo en validación
- Esto explica la mayor parte del tiempo total

---

## 🎯 Comparación con Pipeline Anterior

**Pipeline anterior (4 pasos)**:
- ~12-18 seg/pregunta
- **Total para 65 preguntas**: ~13-20 minutos

**Nuevo pipeline**:
- ~2 min/pregunta (con validación completa)
- **Total para 65 preguntas**: ~2 horas 12 minutos

**Diferencia**: El nuevo pipeline es **~6-10x más lento** debido a la validación externa completa.

---

## 💡 ¿Por Qué Mantener la Validación Completa?

Aunque es más lenta, la validación completa es necesaria porque:

1. **PAES tiene contenido visual complejo**:
   - Gráficos en preguntas
   - Tablas en alternativas
   - Imágenes en opciones
   - Notación matemática compleja

2. **Detecta errores que la validación básica no captura**:
   - Imágenes faltantes
   - Tablas mal formateadas
   - Gráficos incompletos
   - Problemas de renderizado

3. **Asegura calidad antes de usar el QTI**

---

## 🔧 Posibles Optimizaciones Futuras

1. **Validación paralela**: Procesar múltiples preguntas en paralelo
2. **Validación opcional**: Hacer validación completa solo en modo "strict"
3. **Cache de validaciones**: Si el QTI no cambió, reutilizar validación anterior
4. **Validación más rápida**: Optimizar el servicio de validación externa

---

## 📝 Notas

- Las 6 preguntas que fallaron (53, 59, 62, 63, 64, 65) probablemente fallaron en:
  - Validación externa (timeout o error)
  - Transformación QTI (error en generación)
  - Extracción de contenido (problema con PDF)

- El `processing_results.json` muestra una ejecución anterior donde todas fallaron por falta de API keys, pero luego hubo una segunda ejecución exitosa que generó los 59 XMLs.

---

**Última actualización**: 2025-12-15
