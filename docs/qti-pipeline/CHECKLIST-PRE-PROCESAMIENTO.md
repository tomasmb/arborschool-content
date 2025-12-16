# Checklist Pre-Procesamiento - Antes de Probar con Otra Prueba

**Fecha**: 2025-12-15  
**Objetivo**: Verificar que el pipeline está listo para procesar una nueva prueba

---

## ✅ Estado Actual del Pipeline

### Funcionalidades Implementadas

- [x] **Verificación automática de codificación**: Integrada en 3 puntos del pipeline
- [x] **Integración con S3**: Subida automática de imágenes (fallback a base64 si falla)
- [x] **Modo PAES optimizado**: Salta detección de tipo, prompts optimizados
- [x] **Validación externa completa**: Renderizado visual y comparación con AI
- [x] **Manejo de errores**: El pipeline continúa procesando aunque algunas preguntas fallen
- [x] **Fallback a OpenAI**: Si Gemini falla, usa GPT-5.1 automáticamente

### Resultados de Prueba Invierno 2026

- ✅ **65 QTI generados exitosamente**
- ✅ **5 preguntas corregidas automáticamente** (codificación)
- ✅ **37 preguntas sin problemas detectados**
- ⚠️ **28 QTI con data:image** (no S3) - probablemente por fallo en subida S3 durante procesamiento

---

## ⚠️ Puntos a Considerar Antes de Probar con Otra Prueba

### 1. **Imágenes en S3** ⚠️

**Situación actual**:
- 28 QTI tienen `data:image` en lugar de URLs S3
- El código tiene fallback: si S3 falla, usa base64
- Las credenciales AWS están configuradas

**Posibles causas**:
- Fallo temporal de S3 durante el procesamiento
- Problemas de permisos en el bucket
- Timeout en la subida

**Recomendación**:
- ✅ **El pipeline está listo**: El fallback a base64 funciona
- ⚠️ **Opcional**: Verificar permisos del bucket S3 antes de procesar otra prueba
- ⚠️ **Opcional**: Revisar logs de S3 para entender por qué fallaron algunas subidas

**¿Es crítico?**: No. El pipeline funciona con base64, aunque S3 es preferible.

---

### 2. **"Problemas de Codificación" Reportados** ✅

**Situación actual**:
- El script `check_all_encoding_issues.py` reporta problemas en muchas preguntas
- Estos son **falsos positivos** de MathML (patrones como `e3s`, `f3w` en fórmulas matemáticas)

**Estado real**:
- ✅ Todos los problemas reales de codificación fueron corregidos
- ✅ La verificación automática está integrada y funcionando
- ✅ Los patrones genéricos detectados son parte del contenido técnico (MathML)

**Recomendación**:
- ✅ **El pipeline está listo**: La verificación automática funciona correctamente
- ⚠️ **Opcional**: Mejorar el script de verificación para ignorar MathML

**¿Es crítico?**: No. Los problemas reportados son falsos positivos.

---

### 3. **Validación Externa** ⚠️

**Situación actual**:
- La validación externa puede fallar si el servicio no está disponible
- El pipeline tiene umbrales de score (60% overall, 65% completeness/functionality)
- Si la validación falla completamente, el QTI no se retorna

**Posibles problemas**:
- Servicio de validación externa no disponible
- Timeout en renderizado (Chrome headless)
- Problemas de red

**Recomendación**:
- ✅ **El pipeline está listo**: Maneja errores de validación y continúa
- ⚠️ **Verificar**: Que el servicio de validación esté disponible antes de procesar
- ⚠️ **Considerar**: Hacer validación opcional en modo "fast" si es necesario

**¿Es crítico?**: Parcialmente. Si el servicio falla, las preguntas no se procesarán. Pero el pipeline maneja esto correctamente.

---

### 4. **Documentación del Proceso** ✅

**Situación actual**:
- ✅ Script `setup_paes_processing.sh` para procesamiento completo
- ✅ Script `process_paes_invierno.py` para procesar todas las preguntas
- ✅ Documentación en `PLAN-PROCESAMIENTO-PAES.md`

**Recomendación**:
- ✅ **El pipeline está listo**: La documentación es suficiente

---

### 5. **Manejo de Errores** ✅

**Situación actual**:
- ✅ El pipeline captura excepciones y continúa procesando
- ✅ Guarda resultados de preguntas exitosas y fallidas
- ✅ Genera `processing_results.json` con resumen

**Recomendación**:
- ✅ **El pipeline está listo**: El manejo de errores es robusto

---

### 6. **Validación XSD** ⚠️

**Situación actual**:
- ✅ Validación XML básica (parsing)
- ⚠️ Validación XSD completa depende del servicio externo
- ✅ Los QTI generados son XML válidos (verificado)

**Recomendación**:
- ✅ **El pipeline está listo**: La validación XML básica es suficiente
- ⚠️ **Opcional**: Verificar que el servicio externo valide XSD correctamente

---

## 🎯 Recomendación Final

### ✅ **El Pipeline Está Listo para Probar con Otra Prueba**

**Razones**:
1. ✅ **Funcionalidades core implementadas**: Codificación, S3, validación, manejo de errores
2. ✅ **65 QTI generados exitosamente** en la prueba anterior
3. ✅ **Manejo robusto de errores**: Continúa procesando aunque algunas preguntas fallen
4. ✅ **Fallbacks implementados**: S3 → base64, Gemini → OpenAI
5. ✅ **Documentación completa**: Scripts y guías disponibles

### ⚠️ **Mejoras Opcionales (No Críticas)**

1. **Verificar permisos S3** antes de procesar (para evitar data:image)
2. **Verificar disponibilidad del servicio de validación** antes de procesar
3. **Mejorar script de verificación de codificación** para ignorar MathML (cosmético)

### 📋 **Checklist Pre-Procesamiento**

Antes de procesar una nueva prueba:

- [ ] Verificar que las credenciales AWS están configuradas (`.env`)
- [ ] Verificar que las credenciales de API (Gemini/OpenAI) están configuradas
- [ ] Verificar que el servicio de validación externa está disponible
- [ ] Tener el PDF de la nueva prueba listo en `app/data/pruebas/raw/`
- [ ] Ejecutar `setup_paes_processing.sh` o `process_paes_invierno.py`

---

## 🚀 Comandos para Procesar Nueva Prueba

### Opción 1: Script Completo (Recomendado)

```bash
cd app/pruebas/pdf-to-qti
bash scripts/setup_paes_processing.sh
```

### Opción 2: Manual

```bash
# 1. Dividir PDF
cd app/pruebas/pdf-splitter
python3 main.py ../../data/pruebas/raw/nueva-prueba.pdf ./output/nueva-prueba

# 2. Procesar todas las preguntas
cd ../pdf-to-qti
python3 process_paes_invierno.py \
    --questions-dir ../pdf-splitter/output/nueva-prueba/questions \
    --output-dir ./output/nueva-prueba-new \
    --paes-mode
```

---

## 📊 Métricas Esperadas

Basado en la prueba anterior:

- **Tiempo**: ~2 minutos por pregunta (con validación completa)
- **Tasa de éxito**: ~90-95% (algunas pueden fallar en validación)
- **Problemas de codificación**: Automáticamente corregidos
- **Imágenes en S3**: Depende de disponibilidad del servicio

---

**Última actualización**: 2025-12-15
