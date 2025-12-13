# Ayuda para Revisión Manual con PDF - Plan para Mañana

**Fecha**: 2025-12-13  
**Objetivo**: Facilitar la revisión manual pregunta por pregunta comparando con el PDF original

---

## Situación Actual

- **PDF original**: `app/data/pruebas/raw/prueba-invierno-2026.pdf`
- **Preguntas segmentadas**: `app/data/pruebas/procesadas/prueba-invierno-2026/questions/Q*.md`
- **Total preguntas**: 65

---

## Opciones para Revisión con Ayuda del Asistente

### ✅ Opción 1: Leer PDF Directamente (RECOMENDADO)

**Cómo funciona:**
- El PDF está en el workspace local
- Puedo leerlo directamente si instalamos PyPDF2 o PyMuPDF
- Puedo extraer texto de páginas específicas
- Puedo comparar el contenido con las preguntas segmentadas

**Pros:**
- ✅ Puedo ver el PDF completo
- ✅ Puedo buscar preguntas específicas por número
- ✅ Puedo comparar texto directamente
- ✅ No requiere trabajo adicional del usuario

**Contras:**
- ⚠️ Requiere instalar dependencia: `pip install PyPDF2` o `pip install PyMuPDF`
- ⚠️ El OCR puede no ser perfecto si el PDF es escaneado

**Implementación**:
```bash
# Instalar dependencia
pip install PyPDF2

# Luego puedo leer directamente:
# python -c "from app.pdf_to_qti.tools.pdf_viewer import view_question_in_pdf; view_question_in_pdf('Q46')"
```

---

### ✅ Opción 2: Extraer Páginas como Imágenes

**Cómo funciona:**
- Instalar `pdf2image` y `Pillow`
- Extraer páginas específicas del PDF como imágenes PNG
- Yo puedo leer las imágenes y analizar el contenido
- Más preciso para contenido visual/complejo

**Pros:**
- ✅ Preserva el formato visual completo
- ✅ Puedo ver gráficos, ecuaciones, tablas tal como aparecen
- ✅ Más preciso para notación matemática visual

**Contras:**
- ⚠️ Requiere más dependencias: `pip install pdf2image pillow`
- ⚠️ Puede requerir `poppler` instalado en el sistema
- ⚠️ Las imágenes son más grandes

**Implementación**:
```bash
# Instalar dependencias
pip install pdf2image pillow
# En macOS también: brew install poppler

# Crear script para extraer páginas
# python app/pdf-to-qti/tools/extract_pdf_pages.py Q46
```

---

### ✅ Opción 3: Usuario Comparte Capturas de Pantalla

**Cómo funciona:**
- Usuario toma capturas de pantalla de las preguntas relevantes
- Guarda las imágenes en el workspace
- Yo puedo leer las imágenes directamente

**Pros:**
- ✅ No requiere instalar nada
- ✅ Usuario controla qué compartir
- ✅ Funciona inmediatamente

**Contras:**
- ⚠️ Requiere trabajo manual del usuario
- ⚠️ Solo puedo ver lo que el usuario comparte
- ⚠️ Puede ser más lento si hay muchas preguntas

**Uso**:
1. Usuario toma screenshot de pregunta Q46
2. Guarda como `app/data/pruebas/procesadas/prueba-invierno-2026/revision/Q46.png`
3. Yo leo la imagen y comparo con `questions/Q46.md`

---

### ✅ Opción 4: Script de Comparación Automática

**Cómo funciona:**
- Crear un script que:
  1. Lee el PDF
  2. Extrae texto de cada pregunta
  3. Compara con el contenido segmentado
  4. Resalta diferencias o posibles errores

**Pros:**
- ✅ Automático y sistemático
- ✅ Puede detectar diferencias automáticamente
- ✅ Útil para revisión masiva

**Contras:**
- ⚠️ Requiere desarrollo previo
- ⚠️ Puede tener falsos positivos
- ⚠️ No reemplaza revisión manual completa

---

## Recomendación: Híbrido

**Para mañana, sugiero usar Opción 1 + Opción 3:**

1. **Instalar PyPDF2** (simple y rápido):
   ```bash
   pip install PyPDF2
   ```

2. **Crear script helper** para leer preguntas del PDF:
   ```python
   # app/pdf-to-qti/tools/pdf_viewer.py
   def get_question_from_pdf(question_id: str, pdf_path: str) -> str:
       # Extrae y retorna el texto de la pregunta desde el PDF
   ```

3. **Workflow durante revisión**:
   - Usuario pregunta: "¿Cómo está la Q46 en el PDF?"
   - Yo leo el PDF directamente y extraigo la pregunta Q46
   - Comparo con `questions/Q46.md`
   - Señalo diferencias y errores potenciales
   - Usuario confirma y hacemos correcciones

4. **Para casos complejos** (gráficos, ecuaciones visuales):
   - Usuario puede compartir screenshot específico
   - Yo analizo la imagen
   - Aplicamos correcciones

---

## Script Helper Propuesto

Crear `app/pdf-to-qti/tools/pdf_question_extractor.py`:

```python
"""Extract specific questions from PDF for manual review."""

def extract_question_text(pdf_path: str, question_number: int) -> str:
    """Extract text content for a specific question from PDF."""
    # Lee PDF, busca pregunta por número, retorna texto

def extract_question_page(pdf_path: str, question_number: int) -> int:
    """Find which page contains a specific question."""
    # Retorna número de página

def compare_with_segmented(pdf_path: str, question_id: str, segmented_md_path: str) -> dict:
    """Compare PDF content with segmented question."""
    # Compara y retorna diferencias
```

---

## Comandos Útiles para Mañana

### Si instalamos PyPDF2:
```bash
# Ver pregunta Q46 en el PDF
python -c "
from app.pdf_to_qti.tools.pdf_question_extractor import extract_question_text
text = extract_question_text('app/data/pruebas/raw/prueba-invierno-2026.pdf', 46)
print(text)
"
```

### Si usamos imágenes:
```bash
# Extraer página específica
python app/pdf-to-qti/tools/extract_pdf_pages.py --question Q46 --output ./revision/
```

### Revisión interactiva:
```
Usuario: "revisa Q46 con el PDF"
Yo: [Leo PDF, extraigo Q46, comparo con Q46.md, reporto diferencias]
Usuario: "correcto, aplica correcciones X, Y, Z"
Yo: [Aplico correcciones]
```

---

## Tareas para Mañana

1. ✅ Decidir qué opción usar (recomiendo Opción 1: PyPDF2)
2. ✅ Instalar dependencia: `pip install PyPDF2`
3. ✅ Crear script helper `pdf_question_extractor.py`
4. ✅ Probar con 1-2 preguntas para verificar que funciona
5. ✅ Iniciar revisión sistemática pregunta por pregunta

---

## Notas Adicionales

- Si el PDF está protegido o escaneado, puede ser necesario usar OCR
- Para ecuaciones complejas, las imágenes pueden ser más útiles que texto
- Podemos combinar métodos según la complejidad de cada pregunta
- El objetivo es facilitar la revisión, no automatizarla completamente

---

## Plan de Acción Inmediato (Para Mañana)

**Paso 1**: Instalar dependencia
```bash
cd /Users/francosolari/Arbor/arborschool-content
pip install PyPDF2
```

**Paso 2**: Crear script helper
- Crear `app/pdf-to-qti/tools/pdf_question_extractor.py`
- Función para extraer pregunta específica del PDF
- Función para comparar con contenido segmentado

**Paso 3**: Probar con una pregunta
- Probar con Q46 (ya sabemos que tiene errores)
- Verificar que puedo leer y comparar correctamente

**Paso 4**: Iniciar revisión sistemática
- Pregunta por pregunta
- Usuario pregunta, yo extraigo y comparo
- Aplicamos correcciones según sea necesario
