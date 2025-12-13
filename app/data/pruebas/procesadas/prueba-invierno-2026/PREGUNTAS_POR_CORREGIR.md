# Preguntas que requieren corrección manual

## Resumen
- **Total preguntas**: 65
- **Validadas**: 62 ✅
- **Por corregir**: 3 ⚠️

## Preguntas problemáticas

### Q3 - Errores de OCR y opciones con placeholders
**Problemas:**
- Texto corrupto: `3 . (5 4 *+* 3 2 6 ?` (debería ser una expresión matemática)
- Opciones A, B, C, D tienen placeholders `[x]` en lugar de gráficos circulares
- La pregunta trata sobre fracciones representadas en gráficos circulares

**Acción necesaria:**
1. Revisar PDF original para ver la expresión matemática correcta
2. Ver los gráficos circulares en las opciones A, B, C, D
3. Corregir el texto y las opciones manualmente

---

### Q7 - Opciones vacías
**Problemas:**
- Las opciones A, B, C, D están completamente vacías en el parsed.json
- Solo aparecen los labels: `A)`, `B)`, `C)`, `D)` sin contenido

**Contenido actual:**
```
7. Una persona tiene una caja con 12 huevos y realiza lo siguiente:
...
¿Cuántos huevos le quedan a la persona en la caja para ser utilizados en otra preparación?

A)
B)
C)
D)
```

**Acción necesaria:**
1. Revisar PDF original - las opciones pueden estar en otra parte de la página
2. Buscar en páginas adyacentes
3. Completar las opciones manualmente

---

### Q32 - Figura adjunta faltante
**Problemas:**
- Referencia "figura adjunta" pero no tiene la imagen incluida
- El texto menciona `3 > 1` pero no es suficiente para determinar el intervalo correcto
- Necesita ver el gráfico para saber si los extremos son abiertos o cerrados

**Contenido actual:**
```
32. La solución de una inecuación se representa en el intervalo de la figura adjunta.

3 >
1

¿Cuál de los siguientes intervalos representa este gráfico?

A) [1,3] B) ]1,3[
C) [1,3[
D) ]1,3]
```

**Acción necesaria:**
1. Revisar PDF original para encontrar la figura
2. Incluir la imagen en el contenido de la pregunta
3. O agregar descripción textual del gráfico (ej: "intervalo de 1 a 3, ambos cerrados")

---

## Notas
- Estas preguntas no fueron incluidas en el paso de generación QTI
- Pueden agregarse manualmente después o re-segmentarse con ajustes
- Todas las demás preguntas (62) están validadas y listas para continuar
