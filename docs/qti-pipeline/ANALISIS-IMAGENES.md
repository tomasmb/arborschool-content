# Análisis: Cómo Manejan Imágenes los Dos Pipelines

**Fecha**: 2025-12-14  
**Objetivo**: Entender diferencias en manejo de imágenes para planificar integración con S3

---

## Pipeline Actual (`app/qti-pipeline-4steps/`)

### Flujo de Imágenes

```
PDF → [Extend.ai] → parsed.json
                    ↓
              URLs de imágenes en imageUrl
                    ↓
              [Segmenter] → Markdown con ![alt](url)
                    ↓
              [Generator] → QTI XML con URLs de Extend.ai
```

### Características

- **Fuente**: Extend.ai devuelve URLs de imágenes en `imageUrl` dentro de los bloques
- **Almacenamiento**: URLs externas (Extend.ai)
- **Referencia en QTI**: URLs directas de Extend.ai
- **Problema**: 
  - URLs pueden expirar
  - URLs pueden no ser públicas
  - Dependencia externa

### Ejemplo en código

```python
# En pipeline/pdf_parser.py
# Extend.ai devuelve:
{
  "blocks": [
    {
      "imageUrl": "https://extend.ai/.../image.png",
      "text": "..."
    }
  ]
}

# Se inyecta en markdown como:
![alt](https://extend.ai/.../image.png)

# Se usa directamente en QTI XML:
<img src="https://extend.ai/.../image.png" />
```

---

## Nuevo Código (`pdf-to-qti/`)

### Flujo de Imágenes

```
PDF → [PyMuPDF] → Extracción directa de imágenes
       ↓
  [Image Processing Module] → Procesamiento especializado
       ↓
  Base64 encoding → data URIs
       ↓
  [QTI Transformer] → QTI XML con data URIs
```

### Características

- **Fuente**: Extracción directa del PDF usando PyMuPDF (`fitz`)
- **Almacenamiento**: Base64 embebido en el XML
- **Referencia en QTI**: Data URIs (`data:image/png;base64,...`)
- **Módulos especializados**:
  - `image_processing/image_detection.py` - Detección con AI
  - `image_processing/choice_diagrams.py` - Diagramas de alternativas
  - `image_processing/multipart_images.py` - Preguntas multiparte
  - `image_processing/bbox_utils.py` - Cálculo de bounding boxes

### Ejemplo en código

```python
# En modules/pdf_processor.py
# Extrae imágenes del PDF:
page = doc.load_page(page_num)
image_list = page.get_images()

# Convierte a base64:
image_base64 = base64.b64encode(image_bytes).decode('utf-8')

# En modules/qti_transformer.py
# Incluye en QTI como data URI:
image_data = f"data:image/png;base64,{image_base64}"
# Se usa en QTI XML:
<img src="data:image/png;base64,..." />
```

### Ventajas

- ✅ No depende de servicios externos
- ✅ Imágenes siempre disponibles
- ✅ Procesamiento especializado para diferentes tipos

### Desventajas

- ❌ XML muy grande (imágenes embebidas)
- ❌ No usa S3 (no hay URLs públicas)
- ❌ Puede ser lento para PDFs con muchas imágenes

---

## Comparación

| Aspecto | Pipeline Actual | Nuevo Código |
|---------|----------------|--------------|
| **Fuente** | Extend.ai (URLs) | PDF directo (PyMuPDF) |
| **Formato** | URLs externas | Base64 embebido |
| **Tamaño XML** | Pequeño | Muy grande |
| **Dependencias** | Extend.ai | Ninguna |
| **Procesamiento** | Básico | Especializado |
| **S3** | ❌ No usa | ❌ No usa |
| **Problema principal** | URLs pueden expirar | XML muy grande |

---

## Integración con S3 (Tarea Pendiente)

### Para Pipeline Actual

**Necesita**:
1. Descargar imágenes desde URLs de Extend.ai
2. Subir a S3 bucket `paes-question-images`
3. Reemplazar URLs en QTI XML con URLs de S3

**Cuándo hacerlo**:
- Durante el paso GENERATE (antes de crear QTI XML)
- O después de generar QTI, reemplazando URLs

### Para Nuevo Código

**Necesita**:
1. Extraer imágenes del PDF (ya lo hace)
2. Subir a S3 bucket `paes-question-images` (nuevo)
3. Reemplazar data URIs con URLs de S3 en QTI XML

**Cuándo hacerlo**:
- Durante `qti_transformer.py` (antes de generar XML final)
- O después de generar QTI, reemplazando data URIs

---

## Recomendación

### Opción 1: Modificar Nuevo Código (Recomendado)

**Ventajas**:
- Ya extrae imágenes correctamente del PDF
- Tiene módulo especializado de procesamiento
- No depende de Extend.ai

**Cambios necesarios**:
1. Agregar función `upload_image_to_s3()` en `modules/utils/`
2. Modificar `qti_transformer.py` para:
   - Subir imágenes a S3 antes de generar XML
   - Usar URLs de S3 en lugar de data URIs
3. Configurar credenciales S3 desde `.env`

### Opción 2: Modificar Pipeline Actual

**Ventajas**:
- Ya tiene estructura modular
- Más fácil de modificar

**Cambios necesarios**:
1. Agregar función para descargar imágenes de Extend.ai
2. Agregar función para subir a S3
3. Modificar `generator.py` para usar URLs de S3

---

## Próximos Pasos

1. ✅ **Análisis completado** - Entendemos cómo ambos manejan imágenes
2. ⏳ **Decidir enfoque** - ¿Modificar nuevo código o pipeline actual?
3. ⏳ **Implementar S3** - Crear función de upload y modificar generación QTI
4. ⏳ **Probar** - Verificar que imágenes se suben y URLs funcionan

---

**Última actualización**: 2025-12-14
