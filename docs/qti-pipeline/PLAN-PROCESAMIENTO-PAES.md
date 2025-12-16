# Plan para Procesar PAES Invierno 2026 con Nuevo Código

**Fecha**: 2025-12-15  
**Objetivo**: Procesar PAES invierno con nuevo código y comparar con pipeline anterior

---

## ✅ Lo Que Está Listo

1. **Gemini Preview 3 como default** ✅
2. **Fallback a OpenAI** ✅
3. **S3 integrado para imágenes** ✅
4. **Modo PAES optimizado** ✅
   - Salta detección de tipo (siempre "choice")
   - Prompts optimizados para matemáticas
   - Validación completa mantenida

---

## 📋 Pasos para Procesar

### Opción A: Usar pdf-splitter primero (Recomendado)

**Paso 1: Dividir PDF en preguntas individuales**

```bash
cd pdf-splitter
python3 main.py ../app/data/pruebas/raw/prueba-invierno-2026.pdf ./output/paes-invierno
```

Esto creará PDFs individuales en `output/paes-invierno/questions/`

**Paso 2: Procesar cada pregunta**

```bash
cd ../pdf-to-qti
python3 process_paes_invierno.py \
    --questions-dir ../pdf-splitter/output/paes-invierno/questions \
    --output-dir ./output/paes-invierno-2026-new \
    --paes-mode
```

### Opción B: Procesar pregunta por pregunta manualmente

Si prefieres probar con una pregunta primero:

```bash
cd pdf-to-qti

# Primero dividir el PDF (solo una vez)
cd ../pdf-splitter
python3 main.py ../app/data/pruebas/raw/prueba-invierno-2026.pdf ./output/paes-invierno

# Luego procesar una pregunta de prueba
cd ../pdf-to-qti
python3 main.py \
    ../pdf-splitter/output/paes-invierno/questions/question_001.pdf \
    ./output/test \
    --paes-mode
```

---

## 🔍 Comparación de Resultados

Después de procesar, comparar:

1. **Tasa de éxito**: ¿Cuántas preguntas se procesaron correctamente?
2. **Calidad**: ¿Las imágenes, tablas, gráficos se extrajeron bien?
3. **Notación matemática**: ¿Se preservó correctamente?
4. **Tiempo**: ¿Cuánto tardó vs. pipeline anterior?
5. **Errores**: ¿Qué errores aparecieron?

---

## 📊 Resultados del Pipeline Anterior

- **Total preguntas**: 65
- **Exitosas**: 64/65 (Q46 falló)
- **Correcciones manuales**: 13 preguntas
- **Tiempo**: ~12-18 seg/pregunta

---

## 🎯 Objetivo de la Comparación

Determinar:
- ¿El nuevo código tiene menos errores?
- ¿Mejor manejo de imágenes/tablas/gráficos?
- ¿Mejor notación matemática?
- ¿Más rápido o más lento?
- ¿Vale la pena migrar completamente?

---

## ⚠️ Notas Importantes

1. **Primero dividir PDF**: El nuevo código necesita PDFs individuales
2. **Modo PAES**: Usar `--paes-mode` para optimizaciones
3. **Validación completa**: Se mantiene para asegurar calidad
4. **S3**: Las imágenes se subirán automáticamente a S3

---

**Última actualización**: 2025-12-15
