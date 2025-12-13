# Limitaciones de Extend.ai y Soluciones Implementadas

**Fecha**: 2025-12-13  
**Contexto**: Análisis de errores de parsing matemático y opciones de configuración de Extend.ai

---

## Limitaciones de Extend.ai API

### Opciones de Configuración Disponibles

Según la documentación oficial de Extend.ai, las opciones de configuración son limitadas:

1. **Target Format** (`target`): `markdown` o `spatial`
2. **Chunking Strategy** (`chunkingStrategy`): Tipo de chunking y tamaños
3. **Block Options** (`blockOptions`):
   - Figures: enabled, image clipping
   - Tables: enabled, target format (markdown/html)
   - Text: signature detection
4. **Advanced Options** (`advancedOptions`): Page rotation detection

**❌ NO hay opción para:**
- Instrucciones personalizadas o prompts
- Configuración específica para notación matemática
- Post-procesamiento de símbolos matemáticos en la API
- Reglas de conversión de símbolos (V → √)

### Errores Comunes de Parsing Matemático

Los siguientes errores son causados por limitaciones del OCR/parsing de Extend.ai:

#### 1. Notación de Raíz Cuadrada (MUY COMÚN)

**Error**: `V` y `v` no son reconocidos como símbolo de raíz cuadrada `√`

**Ejemplos**:
- `V2002` en lugar de `√(200²)`
- `4V5` en lugar de `4√5`
- `4v10` en lugar de `4√10`

**Causa**: El OCR interpreta el símbolo `√` como la letra `V` o `v` mayúscula/minúscula.

**Frecuencia**: Muy común (Q19, Q46, y probablemente más)

---

#### 2. Potencias Concatenadas (MUY COMÚN)

**Error**: Números donde el último dígito es un exponente se parsean como números normales.

**Ejemplos**:
- `2002` en lugar de `200²`
- `1502` en lugar de `150²`
- `20025` en lugar de `200²⁵`
- `224` en lugar de `2²⁴`

**Causa**: El OCR no distingue entre un exponente superíndice y un dígito normal concatenado.

**Frecuencia**: Muy común (Q18, Q23, Q46)

---

#### 3. Fracciones Sin Símbolo (POCO COMÚN)

**Error**: Fracciones parseadas como dos números separados.

**Ejemplos**:
- `15 4` en lugar de `15/4`

**Causa**: El símbolo de división `/` se pierde durante el OCR o no se reconoce.

**Frecuencia**: Poco común (Q37)

---

#### 4. Unidades Fragmentadas (POCO COMÚN)

**Error**: Unidades de medida parseadas incorrectamente.

**Ejemplos**:
- `km 110 - h` en lugar de `110 km/h`
- `70 km h` en lugar de `70 km/h`

**Causa**: El parsing no mantiene la estructura correcta de unidades compuestas.

**Frecuencia**: Poco común (Q40)

---

#### 5. Marcadores Ambiguos [x] (COMÚN)

**Error**: Marcadores `[x]` agregados o mal interpretados.

**Ejemplos**:
- `V2002 - 1502 [x]` donde `[x]` indica raíz cuadrada (no respuesta correcta)
- `[x]` después de cada alternativa sin significado

**Causa**: El OCR añade marcadores ambiguos o los interpreta incorrectamente.

**Frecuencia**: Común (Q19, Q37, Q39, Q40, Q46)

---

#### 6. Expresiones Matemáticas Incompletas (POCO COMÚN)

**Error**: Expresiones truncadas o mal parseadas.

**Ejemplos**:
- `2.9` en lugar de `((2³ · 3⁴) / (2 · 9))`
- `(4 - 125)3` en lugar de `(4 · 125)³`

**Causa**: Pérdida de contexto o fragmentación durante el parsing.

**Frecuencia**: Poco común (Q20, Q23)

---

#### 7. Sistemas de Ecuaciones Sin Separación (POCO COMÚN)

**Error**: Ecuaciones pegadas sin separación clara.

**Ejemplos**:
- `x + y =18 8500x + 7500y = 146 000` en lugar de:
  ```
  x + y = 18
  8500x + 7500y = 146 000
  ```

**Causa**: El parsing no identifica correctamente los saltos de línea entre ecuaciones.

**Frecuencia**: Poco común (Q36)

---

## Solución Implementada: MathCorrector

Dado que Extend.ai **NO permite** configuraciones personalizadas para notación matemática, implementamos un módulo de post-procesamiento:

### `MathCorrector` - Corrección Post-Parsing

**Ubicación**: `app/pdf-to-qti/pipeline/math_corrector.py`

**Cuándo se ejecuta**: Automáticamente después del paso 1 (parsing) y antes del paso 2 (segmentación)

**Correcciones automáticas**:
- ✅ `V` y `v` → `√` (raíz cuadrada)
- ✅ `V2002` → `√(200²)` (raíz con potencia)
- ✅ `4V5` → `4√5` (número × raíz)
- ✅ `2002 - 1502` → `200² - 150²` (potencias en expresiones)
- ✅ Eliminación de marcadores `[x]` ambiguos

**Limitaciones**:
- ⚠️ No puede corregir expresiones complejas que requieren contexto
- ⚠️ No puede corregir fracciones sin símbolo (`15 4` → `15/4`)
- ⚠️ No puede corregir unidades fragmentadas
- ⚠️ No puede corregir expresiones truncadas

**Para más detalles**: Ver `app/pdf-to-qti/CORRECCION_MATEMATICA.md`

---

## Posibles Mejoras Futuras

### 1. Extender MathCorrector

Podríamos agregar más patrones al `MathCorrector` para manejar:
- Fracciones sin símbolo: `15 4` → `15/4` (en contexto matemático)
- Unidades: `km 110 - h` → `110 km/h` (con validación de patrones)
- Expresiones más complejas usando regex avanzado

**Trade-off**: Mayor complejidad y riesgo de falsos positivos.

---

### 2. Usar AI para Post-Procesamiento Inteligente

Podríamos usar Gemini/GPT para corregir notación matemática:
- Procesar cada chunk con un prompt especializado
- Pedirle al modelo que identifique y corrija errores matemáticos
- Más preciso pero más costoso

**Ejemplo de prompt**:
```
Eres un experto en notación matemática. Corrige los siguientes errores comunes en esta expresión:

- V o v → √ (símbolo de raíz cuadrada)
- Números como "2002" donde el último dígito es exponente → "200²"
- Fracciones sin símbolo "15 4" → "15/4"

Expresión original: {content}
Expresión corregida:
```

**Trade-off**: Más costoso pero más preciso.

---

### 3. Contactar Extend.ai

Podríamos contactar a Extend.ai para:
- Solicitar soporte mejorado para notación matemática
- Reportar los errores comunes que encontramos
- Pedir opciones de configuración adicionales

**Trade-off**: Incierto, depende de la respuesta de Extend.ai.

---

### 4. Pre-procesamiento del PDF

Podríamos pre-procesar el PDF antes de enviarlo a Extend.ai:
- Usar OCR especializado (MathPix, Tesseract con modelo matemático)
- Convertir a imágenes de alta resolución
- Aplicar filtros para mejorar legibilidad

**Trade-off**: Más complejo, puede no mejorar significativamente.

---

## Recomendación Actual

**Estrategia actual (recomendada)**:
1. ✅ Usar `MathCorrector` para correcciones automáticas comunes
2. ✅ Corrección manual para casos complejos o ambiguos
3. ✅ Documentar los errores comunes para referencia futura

**Para mañana**:
- Evaluar si podemos extender `MathCorrector` con más patrones
- Considerar si usar AI para post-procesamiento vale la pena (costo vs. beneficio)
- Mantener documentación actualizada de errores encontrados

---

## Referencias

- Extend.ai API Documentation: https://docs.extend.ai/product/parsing/parse
- `app/pdf-to-qti/CORRECCION_MATEMATICA.md` - Documentación del MathCorrector
- `docs/agenda-cambios-manuales-prueba-invierno-2026.md` - Correcciones manuales realizadas
