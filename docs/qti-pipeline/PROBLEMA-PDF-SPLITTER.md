# Problema con PDF Splitter para PAES Invierno

**Fecha**: 2025-12-15  
**Problema**: El pdf-splitter no está segmentando correctamente el PDF de PAES invierno

---

## 🔍 Problema Identificado

El pdf-splitter usando OpenAI o4-mini solo detecta **5 preguntas** de las **65** que debería encontrar.

### Análisis

1. **Primeras páginas**: Las páginas 1-2 contienen instrucciones (no preguntas)
2. **Preguntas empiezan en página 3**: Confirmado que Q1 empieza en página 3
3. **Modelo confundido**: El modelo está agrupando múltiples preguntas o no detectando todas

### Intentos de Solución

1. ✅ Mejorado el prompt para indicar que las primeras 2-3 páginas son instrucciones
2. ✅ Agregado instrucciones explícitas sobre que cada pregunta numerada es separada
3. ❌ Aún solo detecta 5 preguntas

---

## 📊 Estado Actual

- **PDFs generados**: 4 (Q1-Q4 pasaron validación básica)
- **Preguntas detectadas**: 5 (deberían ser 65)
- **Problema**: El modelo no está segmentando correctamente

---

## 💡 Opciones de Solución

### Opción 1: Usar PDFs Generados Parcialmente (Rápido)
- Probar el nuevo código con los 4 PDFs que ya se generaron
- Validar que el nuevo código funciona
- Luego decidir estrategia para las 65 preguntas

### Opción 2: Mejorar PDF Splitter
- Usar un modelo más potente (GPT-4o en lugar de o4-mini)
- Ajustar más el prompt
- Procesar en chunks más pequeños

### Opción 3: Usar Segmented.json Existente
- El pipeline anterior ya tiene las 65 preguntas identificadas
- Crear script que busque las preguntas en el PDF usando el contenido del segmented.json
- Extraer PDFs individuales basándose en texto coincidente

### Opción 4: Procesar Directamente sin Splitter
- Modificar el nuevo código para procesar el PDF completo
- Extraer preguntas directamente en el nuevo pipeline

---

## 🎯 Recomendación

**Corto plazo**: Usar los 4 PDFs generados para probar el nuevo código y validar que funciona.

**Largo plazo**: Evaluar si es mejor:
- Mejorar el pdf-splitter (Opción 2)
- Usar el segmented.json existente (Opción 3)
- Procesar directamente sin splitter (Opción 4)

---

**Última actualización**: 2025-12-15
