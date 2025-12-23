# Agenda de Cambios Manuales - Prueba Invierno 2026

Este documento registra todos los cambios manuales realizados durante la conversión de la prueba de invierno 2026 a formato QTI.

## Resumen General

- **Prueba**: PAES M1 - Prueba de Invierno Admisión 2026
- **Fecha de procesamiento**: 2025-12-12
- **Total preguntas**: 65
- **Preguntas corregidas manualmente**: 13
- **Preguntas revisadas y sin corrección**: 0

---

## Preguntas con Cambios Manuales

### Q3 - Gráficos Circulares (Fracciones)

**Problema identificado:**
- Texto corrupto por errores de OCR: `3 . (5 4 *+* 3 2 6 ?`
- Opciones A, B, C, D tenían placeholders `[x]` en lugar de gráficos circulares reales
- La opción D aparecía incompleta

**Cambios realizados:**
1. **Operación matemática corregida:**
   - Antes: `3 . (5 4 *+* 3 2 6 ?`
   - Después: `3*((1/6) + (3/2)*(4/6))`

2. **Opciones reescritas con descripciones textuales de gráficos:**
   - A) Gráfico circular con 6 partes y 3 pintadas
   - B) Gráfico circular con 6 partes y todas pintadas
   - C) Dos gráficos circulares de 6 partes cada uno, el primero con todas las partes pintadas, el segundo con 3 partes pintadas
   - D) Cuatro gráficos circulares de 6 partes cada uno, los 3 primeros con todas las partes pintadas, el cuarto con 3 partes pintadas

**Razón del cambio:**
- Las imágenes de los gráficos circulares no fueron capturadas correctamente por Extend.ai
- Se utilizaron descripciones textuales detalladas para preservar la información visual
- Nota: La imagen del ejemplo inicial (5/6 y 1 1/6) sí está presente con URL de Extend.ai

**Archivos modificados:**
- `segmented.json` - Pregunta Q3 en `validated_questions`
- `questions/Q3.md` - Archivo markdown individual

---

### Q7 - Cajas de Huevos

**Problema identificado:**
- Las opciones A, B, C, D estaban completamente vacías en el `parsed.json` original
- Solo aparecían los labels sin contenido: `A)`, `B)`, `C)`, `D)`

**Cambios realizados:**
1. **Opciones completadas:**
   - A) 0
   - B) 2
   - C) 3
   - D) 4

**Razón del cambio:**
- Las imágenes de las cajas de huevos no fueron extraídas del PDF por Extend.ai
- Se completaron con los valores numéricos correspondientes
- Nota: Las opciones originales mostraban imágenes de cajas con diferentes cantidades de huevos

**Archivos modificados:**
- `segmented.json` - Pregunta Q7 en `validated_questions`
- `questions/Q7.md` - Archivo markdown individual

---

### Q32 - Intervalo en Línea Numérica

**Problema identificado:**
- Referencia a "figura adjunta" pero el gráfico de la línea numérica no fue capturado como imagen
- Solo aparecía texto fragmentado: "3 >" y "1" sin contexto visual

**Cambios realizados:**
1. **Agregada representación visual ASCII art del gráfico:**
   ```
       0    1    2    3    4
       |----●========○----|
             [        )
   ```

2. **Agregada explicación detallada:**
   - El círculo relleno (●) en el 1 indica que el extremo izquierdo está cerrado (incluido)
   - El círculo vacío (○) en el 3 indica que el extremo derecho está abierto (no incluido)
   - La línea continua entre ambos puntos representa todos los números del intervalo

**Razón del cambio:**
- La imagen del gráfico es esencial para mantener la dificultad de la pregunta
- Sin la representación visual, los estudiantes no pueden analizar el gráfico
- El ASCII art preserva la información visual necesaria para resolver la pregunta
- Respuesta correcta: C) [1,3[ (cerrado en 1, abierto en 3)

**Archivos modificados:**
- `segmented.json` - Pregunta Q32 en `validated_questions`
- `questions/Q32.md` - Archivo markdown individual

**Nota futura:**
- Idealmente debería extraerse la imagen real del PDF para mejor visualización
- El ASCII art funciona pero una imagen PNG/SVG sería preferible

---

### Q18 - Potencias con Bacterias (Exponentes)

**Problema identificado:**
- Potencias concatenadas incorrectamente por Extend.ai
- Alternativas mostraban números sin exponentes: `20025`, `20024`, `100 · 224`, `100 · 225`

**Cambios realizados:**
1. **Alternativas corregidas:**
   - A) `20025` → `200²⁵`
   - B) `20024` → `200²⁴`
   - C) `100 · 224` → `100 · 2²⁴`
   - D) `100 · 225` → `100 · 2²⁵`

**Razón del cambio:**
- Extend.ai no interpretó correctamente la notación de exponentes en el PDF
- La pregunta trata sobre bacterias que duplican cada hora, requiriendo potencias de 2
- Respuesta correcta: C) `100 · 2²⁴` (100 bacterias iniciales, duplicando 24 veces)

**Archivos modificados:**
- `segmented.json` - Pregunta Q18 en `validated_questions`
- `questions/Q18.md` - Archivo markdown individual

---

### Q19 - Raíz Cuadrada y Potencias

**Problema identificado:**
- Notación matemática mal interpretada
- `V` y `v` no fueron reconocidos como símbolos de raíz cuadrada
- Potencias concatenadas incorrectamente

**Cambios realizados:**
1. **Enunciado corregido:**
   - `2 · 215? [x]` → `2 · (2√5)?`

2. **Alternativas corregidas:**
   - A) `2010 [x]` → `2√10`
   - B) `4V5 [x]` → `4√5`
   - D) `4v10 [x]` → `4√10`
   - Los marcadores `[x]` fueron eliminados (no indicaban respuesta correcta, solo notación matemática)

**Razón del cambio:**
- Extend.ai interpretó `V` y `v` como texto en lugar de símbolos de raíz cuadrada
- Los números concatenados fueron mal parseados (ej: `215` no se reconoció como expresión matemática)

**Archivos modificados:**
- `segmented.json` - Pregunta Q19 en `validated_questions`
- `questions/Q19.md` - Archivo markdown individual

---

### Q20 - Expresión Algebraica Incompleta

**Problema identificado:**
- Enunciado mostraba solo `2.9` en lugar de la expresión matemática completa
- La notación estaba truncada o mal parseada

**Cambios realizados:**
1. **Enunciado corregido:**
   - `2.9` → `((2³ · 3⁴) / (2 · 9))`

**Razón del cambio:**
- Extend.ai perdió parte de la expresión matemática durante el parsing
- La expresión completa requiere potencias y división

**Archivos modificados:**
- `segmented.json` - Pregunta Q20 en `validated_questions`
- `questions/Q20.md` - Archivo markdown individual

---

### Q23 - Potencias de Base 2 y 5

**Problema identificado:**
- Expresiones matemáticas con potencias completamente mal parseadas
- Multiplicación interpretada como resta: `(4 - 125)3` en lugar de `(4 · 125)³`
- Notación de exponentes perdida

**Cambios realizados:**
1. **Enunciado corregido:**
   - `(4 - 125)3` → `(4 · 125)³`

2. **Pasos corregidos:**
   - Paso 1: `(22 . 53)3` → `((2²) · (5³))³`
   - Paso 2: `(22)3 . (53)3` → `((2²)³) · ((5³)³)`
   - Paso 3: `2(2+3) . 5(3+3)` → `2^(2+3) · 5^(3+3)`
   - Paso 4: `25 . 56` → `2⁵ · 5⁶`

3. **Ortografía:**
   - `obteniendose` → `obteniéndose`

**Razón del cambio:**
- Extend.ai no reconoció correctamente la notación de potencias
- Los puntos fueron interpretados como multiplicación en algunos casos, pero perdieron el contexto de potencias
- La expresión requiere descomponer 4 como 2² y 125 como 5³

**Archivos modificados:**
- `segmented.json` - Pregunta Q23 en `validated_questions`
- `questions/Q23.md` - Archivo markdown individual

---

### Q26 - Alternativas Desorganizadas

**Problema identificado:**
- Las alternativas estaban completamente desorganizadas y sin estructura clara
- Números y expresiones mezclados sin formato coherente

**Cambios realizados:**
1. **Alternativas reorganizadas:**
   - A) `2 000 100 000 / 2 600 000`
   - B) `(2 700 000 / 2 600 000) · 2 000 000 000`
   - C) `(2 000 000 000 / 2 600 000) + 100 000`
   - D) `2 600 000 · 2 000 000 000 + 100 000`

**Razón del cambio:**
- El parsing de Extend.ai no mantuvo la estructura de las alternativas
- Las expresiones matemáticas estaban fragmentadas y requerían reconstrucción completa

**Archivos modificados:**
- `segmented.json` - Pregunta Q26 en `validated_questions`
- `questions/Q26.md` - Archivo markdown individual

---

### Q36 - Sistema de Ecuaciones

**Problema identificado:**
- Sistema de ecuaciones sin separación clara entre las dos ecuaciones
- Error en expresión matemática del Paso 3 (resta en lugar de multiplicación)

**Cambios realizados:**
1. **Paso 1 - Sistema de ecuaciones separado:**
   - Antes: `x + y =18 8500x + 7500y = 146 000 + 25 000`
   - Después:
     ```
     x + y = 18
     8500x + 7500y = 146 000 + 25 000.
     ```

2. **Paso 3 - Expresión corregida:**
   - Antes: `8500x - 7500x = 146 000 + 25 000 - 7500 - 18.`
   - Después: `8500x - 7500x = 146 000 + 25 000 - 7500 · 18.`

**Razón del cambio:**
- Extend.ai no separó correctamente las ecuaciones del sistema
- En el Paso 3, faltaba la multiplicación correcta: debería ser `7500 · 18` (sustituyendo y = 18 - x), no `7500 - 18`

**Archivos modificados:**
- `segmented.json` - Pregunta Q36 en `validated_questions`
- `questions/Q36.md` - Archivo markdown individual

---

### Q37 - Fracción y Marcadores

**Problema identificado:**
- Fracción escrita como dos números separados: `15 4` en lugar de `15/4`
- Marcadores `[x]` innecesarios en el enunciado

**Cambios realizados:**
1. **Alternativa A corregida:**
   - `15 4` → `15/4`

2. **Marcadores eliminados:**
   - Eliminados `[x]` en el enunciado (no indicaban respuesta correcta)

**Razón del cambio:**
- Extend.ai no reconoció el símbolo de división `/` en la alternativa
- Los marcadores `[x]` fueron mal interpretados (no indican respuesta correcta en este contexto)

**Archivos modificados:**
- `segmented.json` - Pregunta Q37 en `validated_questions`
- `questions/Q37.md` - Archivo markdown individual

---

### Q39 - Marcadores Innecesarios

**Problema identificado:**
- Marcadores `[x]` después de cada alternativa
- Alternativas mal formateadas (algunas juntas sin separación)

**Cambios realizados:**
1. **Eliminación de marcadores:**
   - Eliminados todos los `[x]` en las alternativas A, B, C, D

2. **Formato mejorado:**
   - Separación correcta entre alternativas

**Razón del cambio:**
- Los marcadores `[x]` no tienen significado en este contexto (no indican respuesta correcta)
- Fueron agregados por error durante el parsing de Extend.ai

**Archivos modificados:**
- `segmented.json` - Pregunta Q39 en `validated_questions`
- `questions/Q39.md` - Archivo markdown individual

---

### Q40 - Unidades de Velocidad

**Problema identificado:**
- Unidades de velocidad mal parseadas en la tabla
- Pregunta final con notación incorrecta
- Marcadores `[x]` innecesarios
- Texto suelto "km" entre la tabla y la pregunta

**Cambios realizados:**
1. **Tabla corregida:**
   - `km 110 - h` → `110 km/h`
   - `70 km h` → `70 km/h`

2. **Pregunta final corregida:**
   - `30 *?* h` → `30 km/h?`

3. **Limpieza:**
   - Eliminado `[x]` del enunciado
   - Eliminado texto suelto "km"

**Razón del cambio:**
- Extend.ai no reconoció correctamente las unidades de velocidad `km/h`
- El formato fue fragmentado durante el parsing
- Los marcadores y texto suelto fueron errores de extracción

**Archivos modificados:**
- `segmented.json` - Pregunta Q40 en `validated_questions`
- `questions/Q40.md` - Archivo markdown individual

---

### Q46 - Raíces Cuadradas y Potencias

**Problema identificado:**
- Raíces cuadradas mal interpretadas (V como texto)
- Potencias concatenadas (2002 en lugar de 200²)
- Marcadores `[x]` mal interpretados como indicadores de respuesta correcta (cuando en realidad indicaban raíz cuadrada)

**Cambios realizados:**
1. **Alternativas corregidas:**
   - A) `V2002 - 1502 [x]` → `√(200² - 150²)`
   - B) `2002 - 1502` → `200² - 150²`
   - C) `2002 + 1502 [x]` → `√(200² + 150²)`
   - D) `2002 + 1502` → `200² + 150²`

**Razón del cambio:**
- `V` en el PDF representa raíz cuadrada (símbolo √), no fue reconocido por Extend.ai
- Los últimos dígitos en números de 4 dígitos son exponentes (ej: `2002` = `200²`)
- Los marcadores `[x]` en este contexto indicaban raíz cuadrada, no respuesta correcta

**Archivos modificados:**
- `segmented.json` - Pregunta Q46 en `validated_questions`
- `questions/Q46.md` - Archivo markdown individual

---

## Estado Final

- ✅ **65 preguntas validadas** (100% de cobertura)
- ✅ **0 preguntas sin validar**
- ✅ **13 preguntas corregidas manualmente**
- ✅ **Todas las preguntas listas para generación QTI**

---

## Notas Adicionales

### Imágenes Preservadas
- **Q3**: La imagen del ejemplo inicial (gráficos circulares de 5/6 y 1 1/6) está preservada con URL de Extend.ai
- Las opciones de Q3 y Q7 no tienen imágenes (fueron reemplazadas por descripciones textuales)

### Próximos Pasos Recomendados
1. Revisar QTI generado para verificar que las representaciones visuales se rendericen correctamente
2. Considerar extraer imágenes reales del PDF para Q32 si es necesario mejorar la calidad visual
3. Validar que las preguntas corregidas mantienen la dificultad original

---

## Patrones de Errores Identificados

### Errores Comunes de Extend.ai

1. **Notación de raíz cuadrada:**
   - `V` o `v` no son reconocidos como símbolos de raíz cuadrada (√)
   - Requiere corrección manual post-parsing

2. **Potencias concatenadas:**
   - Números como `2002`, `1502` donde el último dígito es exponente
   - Ejemplo: `2002` → `200²`, `1502` → `150²`

3. **Exponentes perdidos:**
   - Expresiones como `224` deberían ser `2²⁴`
   - O `225` debería ser `2²⁵`

4. **Marcadores `[x]` ambiguos:**
   - A veces indican raíz cuadrada (en contexto matemático)
   - A veces son errores de parsing que deben eliminarse
   - Nunca indican respuesta correcta en las preguntas revisadas

5. **Unidades fragmentadas:**
   - `km/h` aparece como `km 110 - h` o `70 km h`
   - Requiere reconstrucción manual

6. **Fracciones sin símbolo:**
   - `15 4` en lugar de `15/4`
   - Requiere reconocimiento del contexto matemático

7. **Expresiones matemáticas incompletas:**
   - `2.9` en lugar de `((2³ · 3⁴) / (2 · 9))`
   - Requiere verificación con PDF original

8. **Sistemas de ecuaciones sin separación:**
   - Ecuaciones pegadas sin separación clara
   - Requiere identificación de límites entre ecuaciones

### Módulo de Corrección Automática

Se implementó `pipeline/math_corrector.py` que corrige automáticamente algunos de estos errores:
- Convierte `V` y `v` a `√` en contexto matemático
- Corrige números seguidos de `V` (ej: `4V5` → `4√5`)
- Convierte pares de números con exponente en expresiones matemáticas (ej: `2002 - 1502` → `200² - 150²`)

**Limitaciones:**
- Solo corrige patrones claros y conservadores
- No puede manejar expresiones complejas que requieren contexto
- Aún requiere revisión manual para casos ambiguos

---

## Fechas de Cambios

- **2025-12-12**: Correcciones iniciales de Q3, Q7, Q32
- **2025-12-12**: Análisis automatizado y correcciones de notación matemática (Q18, Q19, Q20, Q23, Q26, Q36, Q37, Q39, Q40, Q46)
