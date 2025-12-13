# Recomendaciones sobre Re-correr Paso 2 - Prueba Invierno 2026

**Fecha**: 2025-12-13  
**Contexto**: Análisis sobre si debemos re-correr el paso 2 (segmentación) después de las correcciones manuales

---

## Situación Actual

### Estado de los Archivos

1. **`parsed.json`**
   - ✅ Existe
   - ❌ NO tiene correcciones del `MathCorrector`
   - 📅 Generado: 2025-12-12 18:27:53 (ANTES de implementar MathCorrector)
   - ⚠️ No contiene símbolos √ ni ² (indicadores de corrección automática)

2. **`segmented.json`**
   - ✅ Existe con correcciones manuales aplicadas
   - 📅 Modificado: 2025-12-13 00:12:57
   - ✅ Contiene correcciones manuales para:
     - Q18, Q19, Q20, Q23, Q26, Q36, Q37, Q39, Q40, Q46

3. **`MathCorrector`**
   - ✅ Implementado y funcionando
   - ✅ Integrado en el paso 1 (`pdf_parser.py`)
   - ⚠️ Solo aplicará automáticamente a futuros procesamientos nuevos

---

## Pregunta del Usuario

> "¿Deberíamos correr el paso 2 nuevamente para estas preguntas?"

---

## Respuesta: **NO** (Recomendación Principal)

### Razones para NO re-correr el paso 2:

1. **Se perderían las correcciones manuales**
   - El paso 2 (segmentación) lee `parsed.json` y genera `segmented.json` desde cero
   - Nuestras correcciones manuales están en `segmented.json` y se perderían

2. **El `parsed.json` actual NO tiene correcciones automáticas**
   - Fue generado antes de implementar `MathCorrector`
   - Re-correr paso 2 no mejoraría nada porque el input (`parsed.json`) sigue igual

3. **Para obtener mejoras automáticas se necesitaría:**
   - Re-correr paso 1 (parsear PDF de nuevo con Extend.ai)
   - Esto cuesta créditos de API de Extend.ai
   - Y aún así perderíamos las correcciones manuales al re-correr paso 2

---

## Opciones Disponibles

### ✅ Opción A: **No hacer nada** (RECOMENDADO)

**Ventajas:**
- Mantiene todas las correcciones manuales que ya hicimos
- No cuesta dinero
- El `MathCorrector` ya está listo para futuros PDFs

**Cuándo usar:**
- Cuando las correcciones manuales son suficientes
- Cuando no queremos gastar créditos de Extend.ai

---

### 🔧 Opción B: Aplicar `MathCorrector` al `parsed.json` existente

**Qué hace:**
- Aplica correcciones automáticas al `parsed.json` sin re-parsear el PDF
- Gratis (no usa API de Extend.ai)
- Crea backup antes de modificar

**Comando:**
```python
from app.pdf_to_qti.pipeline.math_corrector import correct_parsed_json

# Crear backup primero
import shutil
shutil.copy('parsed.json', 'parsed.json.backup')

# Aplicar correcciones
correct_parsed_json(
    'app/data/pruebas/procesadas/prueba-invierno-2026/parsed.json',
    output_path='app/data/pruebas/procesadas/prueba-invierno-2026/parsed.json.corrected'
)
```

**Ventajas:**
- Gratis (no usa créditos)
- Permite comparar resultados
- No afecta las correcciones manuales en `segmented.json`

**Cuándo usar:**
- Para experimentar y ver qué mejoraría
- Para tener un `parsed.json` corregido por si acaso

---

### 💰 Opción C: Re-correr paso 1 completo (NO RECOMENDADO)

**Qué hace:**
- Re-parsea el PDF completo con Extend.ai
- Aplica `MathCorrector` automáticamente
- Genera nuevo `parsed.json` corregido

**Costo:**
- Usa créditos de Extend.ai API

**Cuándo usar:**
- Solo si planeamos re-correr paso 2 y perder correcciones manuales
- No recomendado porque perderíamos trabajo manual

---

## Decisiones Pendientes

1. **¿Aplicamos `MathCorrector` al `parsed.json` existente?** (Opción B)
   - Permite tener un `parsed.json` corregido para referencia
   - No afecta el trabajo actual
   - Gratis

2. **¿Re-corremos paso 2 después de corregir `parsed.json`?**
   - ⚠️ Esto perdería las correcciones manuales
   - Solo tiene sentido si queremos probar la diferencia
   - Requiere decidir si mantener correcciones manuales o confiar en automáticas

---

## Recomendación Final

**Para mañana:**

1. ✅ **Mantener el estado actual** - Las correcciones manuales están bien
2. 🔍 **Opcionalmente aplicar Opción B** - Para tener `parsed.json` corregido como referencia
3. ❌ **NO re-correr paso 2** - A menos que queramos experimentar (y aceptar perder correcciones manuales)

**Para futuros PDFs:**
- El `MathCorrector` ya está integrado y funcionará automáticamente
- Se aplicará en el paso 1, mejorando el `parsed.json` desde el inicio
- Esto debería reducir la necesidad de correcciones manuales

---

## Nueva Pregunta del Usuario

> "¿Los datos obtenidos en el paso 2 no se podrían ajustar manualmente para reflejar lo arreglado en el paso 1 de forma manual?"

**Respuesta: SÍ, es posible y ahora tenemos una herramienta para hacerlo.**

### ✅ Solución Implementada

Se creó un script que aplica las mismas correcciones de `MathCorrector` directamente a `segmented.json`:

**Archivo**: `app/pdf-to-qti/pipeline/apply_math_corrections_to_segmented.py`

**Cómo funciona:**
1. Lee `segmented.json`
2. Aplica las mismas reglas de corrección que `MathCorrector`
3. Busca y reemplaza patrones matemáticos incorrectos en el contenido de cada pregunta
4. Guarda el resultado corregido (con backup automático)

**Ventajas:**
- ✅ No requiere re-correr el paso 2 (no usa Gemini API)
- ✅ Mantiene consistencia entre `parsed.json` y `segmented.json`
- ✅ Gratis (no usa APIs pagas)
- ✅ Crea backup automático antes de modificar

**Uso:**
```bash
# Desde el directorio del proyecto
python -m app.pdf_to_qti.pipeline.apply_math_corrections_to_segmented \
    app/data/pruebas/procesadas/prueba-invierno-2026/segmented.json
```

---

## Pregunta sobre Mejoras en Paso 1

> "¿Pudiste o podrás mañana mejorar el prompt del primer paso para evitar los errores que identificamos manualmente?"

**Respuesta: Extend.ai NO permite prompts personalizados, pero podemos mejorar el post-procesamiento.**

### Limitaciones de Extend.ai

**❌ Extend.ai NO ofrece:**
- Campo para instrucciones o prompts personalizados
- Configuración específica para notación matemática
- Post-procesamiento de símbolos matemáticos en la API

**✅ Opciones disponibles:**
- Target format (markdown/spatial)
- Chunking strategy
- Block options (figures, tables, text)
- Advanced options (page rotation)

### Solución Actual

Ya tenemos `MathCorrector` que corrige automáticamente:
- ✅ `V`/`v` → `√` (raíz cuadrada)
- ✅ Potencias concatenadas (`2002` → `200²`)
- ✅ Eliminación de marcadores `[x]` ambiguos

### Posibles Mejoras para Mañana

1. **Extender MathCorrector** con más patrones:
   - Fracciones sin símbolo: `15 4` → `15/4`
   - Unidades fragmentadas: `km 110 - h` → `110 km/h`

2. **Usar AI para post-procesamiento inteligente**:
   - Procesar chunks con Gemini para corrección matemática
   - Más preciso pero más costoso

3. **Contactar Extend.ai**:
   - Reportar errores comunes
   - Solicitar mejoras para notación matemática

**Documentación completa**: Ver `app/pdf-to-qti/docs/LIMITACIONES-EXTEND-AI-Y-SOLUCIONES.md`

---

## Preguntas para Mañana

1. ¿Queremos aplicar `MathCorrector` al `parsed.json` existente?
2. ¿Queremos aplicar correcciones automáticas a `segmented.json` usando el nuevo script?
3. ¿Queremos extender `MathCorrector` con más patrones (fracciones, unidades)?
4. ¿Evaluamos usar AI para post-procesamiento inteligente de notación matemática?
5. ¿Hay alguna pregunta específica que queramos re-generar desde cero?
6. ¿Queremos comparar los resultados antes/después de aplicar correcciones?

---

## Plan para Revisión Manual con PDF (Mañana)

> "Mañana revisaré 1 a 1 las preguntas con el PDF, piensa si hay alguna forma de que veas el PDF para ayudarme con ese proceso manual"

### ✅ Solución Preparada

**Script creado**: `app/pdf-to-qti/tools/pdf_question_extractor.py`

**Funcionalidades**:
- Extraer pregunta específica del PDF
- Comparar con contenido segmentado
- Identificar diferencias automáticamente

**Para usar mañana**:

1. **Instalar dependencia**:
   ```bash
   pip install PyPDF2
   ```

2. **Probar con una pregunta**:
   ```bash
   python app/pdf-to-qti/tools/pdf_question_extractor.py \
       app/data/pruebas/raw/prueba-invierno-2026.pdf \
       46 \
       --compare app/data/pruebas/procesadas/prueba-invierno-2026/questions/Q46.md
   ```

3. **Workflow durante revisión**:
   - Usuario: "revisa Q46 con el PDF"
   - Yo: [Extraigo Q46 del PDF, comparo con Q46.md, reporto diferencias]
   - Usuario: "correcto, aplica corrección X"
   - Yo: [Aplico correcciones en Q46.md y segmented.json]

**Documentación completa**: Ver `app/data/pruebas/procesadas/prueba-invierno-2026/AYUDA-REVISION-PDF.md`

---

## Archivos Relacionados

- `app/pdf-to-qti/pipeline/pdf_parser.py` - Paso 1 (integra MathCorrector)
- `app/pdf-to-qti/pipeline/math_corrector.py` - Módulo de corrección automática
- `app/pdf-to-qti/pipeline/segmenter.py` - Paso 2 (segmentación)
- `app/data/pruebas/procesadas/prueba-invierno-2026/parsed.json` - Input del paso 2
- `app/data/pruebas/procesadas/prueba-invierno-2026/segmented.json` - Output del paso 2 (con correcciones manuales)
- `docs/agenda-cambios-manuales-prueba-invierno-2026.md` - Documentación de correcciones manuales

---

## Notas Técnicas

- El `MathCorrector` corrige:
  - `V` y `v` → `√` (raíz cuadrada)
  - `XXX2` → `XXX²` (en contexto matemático)
  - `[x]` marcadores ambiguos
  - Expresiones como `4V5` → `4√5`

- El paso 2 (segmentación) usa Gemini API y:
  - Lee `parsed.json` completo
  - Genera `segmented.json` desde cero
  - No preserva modificaciones manuales previas

---

## Pregunta sobre Paso 3 (Generación QTI)

> "¿Después tendríamos que correr el paso 3 nuevamente para las preguntas cambiadas manualmente?"

**Respuesta: SÍ, es necesario regenerar el QTI para las preguntas modificadas.**

### Situación Actual

- **9/10 preguntas corregidas** ya tienen QTI generado (pero fueron generadas ANTES de las correcciones)
- **Q46** no tiene QTI (probablemente falló en generación previa)

### Opciones para Regenerar QTI

#### ✅ Opción A: Regenerar Solo Preguntas Específicas (RECOMENDADO)

**Herramienta creada**: `regenerate_qti_for_questions.py`

**Uso:**
```bash
python -m app.pdf_to_qti.pipeline.regenerate_qti_for_questions \
    --questions Q18 Q19 Q20 Q23 Q26 Q36 Q37 Q39 Q40 Q46 \
    --input app/data/pruebas/procesadas/prueba-invierno-2026/segmented.json \
    --output app/data/pruebas/procesadas/prueba-invierno-2026
```

**Ventajas:**
- ✅ Solo regenera las preguntas necesarias (más rápido, menos costo)
- ✅ Lee el contenido corregido de `segmented.json`
- ✅ Guarda solo los archivos QTI correspondientes

**Costo:**
- Usa Gemini API solo para las preguntas especificadas
- ~10 preguntas = ~10 llamadas a API (mucho menos que regenerar todas las 65)

#### ⚠️ Opción B: Regenerar Todas las Preguntas

**Uso:**
```bash
python app/pdf-to-qti/run.py \
    app/data/pruebas/procesadas/prueba-invierno-2026/segmented.json \
    --step generate \
    --output app/data/pruebas/procesadas/prueba-invierno-2026
```

**Desventajas:**
- Regenera las 65 preguntas (más costoso en API)
- Las preguntas no modificadas se regeneran innecesariamente

---

### Flujo Completo Recomendado

```
1. Aplicar MathCorrector a parsed.json
   └─> parsed.json corregido

2. Aplicar correcciones a segmented.json
   └─> segmented.json corregido (manual o con script)

3. Regenerar QTI solo para preguntas modificadas
   └─> Q18.xml, Q19.xml, Q20.xml, ... Q46.xml (actualizados)
```

---

### Notas Importantes

- El generador QTI lee el contenido desde `segmented.json`
- Si `segmented.json` tiene contenido corregido, el QTI reflejará esas correcciones
- La validación semántica comparará el QTI generado con el contenido de `segmented.json`
- Si las correcciones son correctas, el QTI debería pasar validación más fácilmente
