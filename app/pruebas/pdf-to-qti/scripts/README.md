# Scripts Auxiliares

Esta carpeta contiene scripts auxiliares y temporales para tareas específicas del pipeline.

## Scripts Disponibles

### `process_missing_questions.py`
Script para procesar preguntas específicas que fallaron en una ejecución inicial.

**Uso:**
```bash
python3 scripts/process_missing_questions.py
```

**Descripción:** Procesa las preguntas 53 y 59 que inicialmente fallaron. Ya completado.

---

### `create_question_pdfs_from_segmented.py`
Script para crear PDFs individuales de preguntas a partir de resultados de segmentación.

**Uso:**
```bash
python3 scripts/create_question_pdfs_from_segmented.py
```

**Descripción:** Convierte el output del pdf-splitter en PDFs individuales por pregunta.

---

### `setup_paes_processing.sh`
Script de configuración para procesar pruebas PAES.

**Uso:**
```bash
bash scripts/setup_paes_processing.sh
```

**Descripción:** Configura el entorno y estructura de directorios para procesar pruebas PAES.

---

### `validate_qti_output.py`
Script para validar la calidad de los QTI generados.

**Uso:**
```bash
python3 scripts/validate_qti_output.py
python3 scripts/validate_qti_output.py --json output/validation_report.json
```

**Descripción:** Valida estructura QTI, elementos requeridos, MathML, imágenes, tablas, y genera un reporte detallado.

---

### `render_qti_to_html.py`
Script para renderizar QTI XML a HTML visual atractivo.

**Uso:**
```bash
# Renderizar pregunta 7
python3 scripts/render_qti_to_html.py --question 7

# Renderizar pregunta específica con output personalizado
python3 scripts/render_qti_to_html.py --question 46 --output-html preview.html
```

**Descripción:** Convierte QTI XML a HTML visual con:
- Estilos CSS modernos
- Renderizado de MathML con MathJax
- Visualización de imágenes
- Tablas formateadas
- Alternativas interactivas
- Indicador de respuesta correcta

El HTML generado se puede abrir directamente en el navegador para verificar visualmente que el contenido del PDF se plasmó correctamente.

---

### `render_all_questions_to_html.py`
Script para renderizar todas las preguntas QTI a un único HTML navegable.

**Uso:**
```bash
# Generar HTML completo con todas las preguntas (por defecto 65)
python3 scripts/render_all_questions_to_html.py

# Especificar número de preguntas
python3 scripts/render_all_questions_to_html.py --num-questions 65

# Especificar directorio de salida y archivo HTML
python3 scripts/render_all_questions_to_html.py --output-dir ./output/paes-invierno-2026-new --output-html ./preview_completo.html
```

**Descripción:** Genera un único archivo HTML con:
- Índice navegable de todas las preguntas
- Todas las preguntas en secuencia
- Navegación entre preguntas (anterior/siguiente)
- Botón para volver al índice
- Mismos estilos y funcionalidades que `render_qti_to_html.py`

Ideal para revisar toda la prueba de una vez en un solo archivo.

---

## Notas

- Estos scripts son auxiliares y pueden ser temporales
- Si un script ya no se usa, considerar moverlo a `legacy/` o eliminarlo
- Los scripts principales del pipeline están en el directorio raíz de `pdf-to-qti/`
