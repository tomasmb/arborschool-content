# Optimizaciones para PAES M1

**Fecha**: 2025-12-15  
**Objetivo**: Optimizar el código para el formato específico de PAES M1

---

## 📋 Características de PAES M1

- ✅ **Solo preguntas de alternativas** (choice)
- ✅ **4 alternativas por pregunta** (A, B, C, D)
- ✅ **65 preguntas totales**
- ✅ **Todas de matemáticas**
- ✅ **Formato consistente**

---

## ⚡ Optimizaciones Implementadas

### 1. Modo PAES (`--paes-mode`)

**Flag**: `--paes-mode` en CLI o `paes_mode=True` en código

**Beneficios**:
- ⚡ **Más rápido**: Salta detección de tipo de pregunta
- ⚡ **Más rápido**: Salta validación externa (solo XML básico)
- ⚡ **Más eficiente**: Prompts optimizados para matemáticas
- ⚡ **Menos costos**: Menos llamadas a API

### 2. Detección de Tipo de Pregunta

**Antes** (sin PAES mode):
```
PDF → AI Analysis → Detect Type → Choice/Text-entry/etc
```
- ❌ Llamada a API innecesaria
- ❌ Tiempo: ~2-3 segundos

**Después** (con PAES mode):
```
PDF → Skip Detection → Always "choice"
```
- ✅ Sin llamada a API
- ✅ Tiempo: ~0 segundos
- ✅ Ahorro: ~2-3 seg por pregunta = ~2-3 min para 65 preguntas

### 3. Validación Externa

**NOTA**: La validación externa NO se salta en modo PAES porque:
- ✅ Algunas preguntas tienen gráficos
- ✅ Algunas tienen tablas
- ✅ Algunas tienen imágenes en las alternativas
- ✅ Necesitamos asegurar que todo se extrajo correctamente

**Validación completa siempre**:
```
QTI XML → External Validation Service → Screenshot → AI Comparison
```
- ✅ Validación visual completa
- ✅ Detecta problemas con imágenes, tablas, gráficos
- ✅ Tiempo: ~10-15 segundos (necesario para calidad)

### 4. Prompts Optimizados para Matemáticas

**Optimizaciones**:
- ✅ Instrucciones específicas para notación matemática
- ✅ Enfoque en preservar símbolos (√, ², ³, fracciones)
- ✅ Mejor manejo de MathML
- ✅ Énfasis en 4 alternativas

---

## 🚀 Cómo Usar

### Desde CLI

```bash
# Modo normal (para otros formatos)
python main.py input.pdf ./output

# Modo PAES (optimizado)
python main.py input.pdf ./output --paes-mode
```

### Desde Código

```python
from main import process_single_question_pdf

result = process_single_question_pdf(
    input_pdf_path="question.pdf",
    output_dir="./output",
    paes_mode=True  # Activa optimizaciones PAES
)
```

---

## 📊 Ahorro de Tiempo Estimado

Para 65 preguntas de PAES:

| Paso | Sin PAES Mode | Con PAES Mode | Ahorro |
|------|---------------|---------------|--------|
| Detección tipo | ~2-3 seg/preg | 0 seg | ~2-3 min |
| Validación externa | ~10-15 seg/preg | ~10-15 seg/preg | 0 (mantenida) |
| **Total** | **~12-18 seg/preg** | **~10-15 seg/preg** | **~2-3 min** |

**Nota**: La validación externa se mantiene para asegurar calidad con imágenes, tablas y gráficos.

**Ahorro total**: ~12-18 minutos para 65 preguntas

---

## 💰 Ahorro de Costos

**Llamadas a API eliminadas**:
- Detección de tipo: 65 llamadas menos
- Validación externa: 0 (mantenida para calidad)
- **Total**: ~65 llamadas menos

**Estimación de ahorro** (con Gemini):
- ~65 llamadas × ~$0.001 = **~$0.065 por prueba completa**

**Nota**: Se mantiene la validación externa para asegurar calidad con contenido visual complejo.

---

## ✅ Optimizaciones Específicas

### 1. Tipo de Pregunta Fijo

```python
# Siempre retorna "choice" sin llamar a API
detection_result = {
    "question_type": "choice",
    "can_represent": True,
    "confidence": 1.0
}
```

### 2. Prompts para Matemáticas

```python
# Agrega instrucciones específicas para matemáticas
prompt += """
IMPORTANT FOR MATHEMATICS QUESTIONS:
- Preserve all mathematical notation exactly
- Use MathML for all expressions
- Ensure 4 alternatives (A, B, C, D)
"""
```

### 3. Validación Completa (Mantenida)

```python
# Validación completa siempre (incluye imágenes, tablas, gráficos)
validation_result = validate_with_external_service(
    qti_xml,
    original_pdf_image,
    api_key,
    external_validation_url
)
```

**Razón**: PAES puede tener imágenes, tablas, gráficos e imágenes en alternativas que necesitan validación visual.

---

## 🔧 Archivos Modificados

1. **`modules/paes_optimizer.py`** - **NUEVO**
   - Funciones de optimización
   - Configuración PAES
   - Helpers para matemáticas

2. **`main.py`**
   - Agregado parámetro `paes_mode`
   - Lógica condicional para saltar pasos
   - Flag `--paes-mode` en CLI

3. **`modules/qti_transformer.py`**
   - Soporte para `paes_mode`
   - Optimización de prompts

---

## ⚠️ Cuándo Usar PAES Mode

**Usar `--paes-mode` cuando**:
- ✅ Todas las preguntas son de alternativas (choice)
- ✅ Formato consistente (4 alternativas)
- ✅ Mismo tema (matemáticas en este caso)
- ✅ Quieres ahorrar tiempo en detección de tipo

**NO usar `--paes-mode` cuando**:
- ❌ Hay diferentes tipos de preguntas
- ❌ Quieres detectar automáticamente el tipo

**Nota**: La validación visual completa siempre se ejecuta, incluso en modo PAES, para asegurar calidad con imágenes, tablas y gráficos.

---

## 🧪 Pruebas Recomendadas

1. **Probar con una pregunta**:
   ```bash
   python main.py question1.pdf ./output --paes-mode
   ```

2. **Verificar que funciona**:
   - ✅ Tipo siempre es "choice"
   - ✅ XML válido generado
   - ✅ 4 alternativas presentes
   - ✅ Notación matemática preservada

3. **Comparar tiempos**:
   - Con `--paes-mode`: ~10-15 segundos (validación completa mantenida)
   - Sin `--paes-mode`: ~12-18 segundos

---

## 📝 Notas

- Las optimizaciones son **seguras**: solo saltan detección de tipo (que sabemos que siempre es "choice")
- **Validación completa siempre**: Se mantiene para asegurar calidad con imágenes, tablas, gráficos
- El código sigue funcionando sin `--paes-mode` para otros formatos
- Las optimizaciones son **reversibles**: puedes desactivarlas fácilmente

---

**Última actualización**: 2025-12-15
