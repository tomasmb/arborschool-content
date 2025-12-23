# Corrección Automática de Notación Matemática

## Descripción

El módulo `MathCorrector` corrige automáticamente errores comunes de notación matemática que ocurren durante el parsing de PDFs con Extend.ai.

## Problema

Extend.ai (PASO 1 del pipeline) a veces interpreta incorrectamente la notación matemática:
- `V5` en lugar de `√5` (raíz cuadrada)
- `4V5` en lugar de `4√5`
- `4v10` en lugar de `4√10`
- Y otros patrones similares

## Solución

El `MathCorrector` se ejecuta automáticamente después del parsing (PASO 1) y antes de la segmentación (PASO 2).

### Correcciones Automáticas

El corrector aplica las siguientes reglas:

1. **V seguida de 4+ dígitos (último dígito = exponente)**: `V2002` → `√(200²)`, `V1502` → `√(150²)`
   - Interpreta que el último dígito es el exponente
   - Los primeros 3 dígitos son la base
   
2. **Número seguido de V y número**: `4V5` → `4√5`, `2V5` → `2√5`

3. **Número seguido de v minúscula y número**: `4v10` → `4√10`

4. **V seguida de números simples**: `V5` → `√5`, `V10` → `√10`

5. **Números con último dígito como exponente**: `2002` → `200²`, `1502` → `150²`
   - Solo en contexto matemático (expresiones con operadores)
   - El último dígito `2` se interpreta como exponente `²`

6. **Eliminación de marcadores [x]**: Remueve `[x]` después de expresiones matemáticas con raíz cuadrada

### Limitaciones

El corrector es **conservador** y solo corrige patrones claros. No puede manejar:

- **Expresiones complejas que requieren contexto**: 
  - `V2002 - 1502` no se convierte automáticamente en `√(200² - 150²)`
  - Esto requiere interpretación matemática más avanzada
  
- **Potencias concatenadas**:
  - `215` no se convierte en `2¹⁵` (requiere contexto)
  - `2010` no se convierte en `2¹⁰` (requiere contexto)

Para estos casos, se requiere **corrección manual** o **corrección asistida por AI** en el futuro.

## Integración en el Pipeline

El corrector se ejecuta automáticamente después del parsing:

```
PASO 1: PARSE (Extend.ai)
  ↓
  [MathCorrector] ← Corrección automática
  ↓
PASO 2: SEGMENT
```

## Ejemplos de Correcciones

| Original | Corregido | Estado |
|----------|-----------|--------|
| `4V5` | `4√5` | ✅ Automático |
| `4v10` | `4√10` | ✅ Automático |
| `V5` | `√5` | ✅ Automático |
| `V2002` | `√(200²)` | ✅ Automático |
| `V1502` | `√(150²)` | ✅ Automático |
| `V2002 - 1502` | `√(200²) - 150²` | ✅ Automático |
| `2002 - 1502` | `200² - 150²` | ✅ Automático |
| `215` | `215` | ⚠️ Requiere corrección manual (podría ser `2¹⁵`) |
| `2010` | `2010` | ⚠️ Requiere corrección manual (podría ser `2¹⁰`) |

## Uso Manual

Si necesitas corregir un `parsed.json` existente:

```python
from pipeline.math_corrector import correct_parsed_json

# Corregir y guardar (sobrescribe el archivo)
correct_parsed_json('path/to/parsed.json')

# O guardar en otro archivo
correct_parsed_json('path/to/parsed.json', 'path/to/parsed_corrected.json')
```

## Extensión Futura

Para agregar más patrones de corrección:

1. Edita `pipeline/math_corrector.py`
2. Agrega nuevos patrones regex en `_build_correction_patterns()`
3. O implementa lógica más avanzada en `_correct_power_notation()` para usar AI
