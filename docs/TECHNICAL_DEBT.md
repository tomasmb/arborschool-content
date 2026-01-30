# Deuda Técnica - arborschool-content

> Último actualizado: 2025-01-30

## Archivos > 500 líneas (Pendientes de Refactorización)

Estos archivos exceden el límite de 500 líneas establecido en CODE_STANDARDS.md.
Se recomienda refactorizarlos cuando se modifiquen, no como tarea separada.

| Archivo | Líneas | Prioridad | Notas |
|---------|--------|-----------|-------|
| `app/pruebas/pdf-to-qti/main.py` | 1,092 | 🔴 Alta | Orquestador principal, dividir en submódulos |
| `app/pruebas/pdf-to-qti/modules/qti_transformer.py` | 1,036 | 🔴 Alta | Transformador QTI, extraer helpers |
| `app/pruebas/pdf-to-qti/modules/pdf_processor.py` | 981 | 🔴 Alta | Procesador PDF, dividir por responsabilidad |
| `app/atoms/prompts.py` | 882 | 🟡 Media | Solo prompts, pero función muy larga |
| `app/pruebas/pdf-to-qti/modules/image_processing/image_detection.py` | 826 | 🔴 Alta | Detección de imágenes, extraer algoritmos |
| `app/pruebas/pdf-to-qti/scripts/render_qti_to_html.py` | 806 | 🟢 Baja | Script de renderizado |
| `app/pruebas/pdf-to-qti/modules/validation/question_validator.py` | 787 | 🔴 Alta | Validador, dividir por tipo de validación |
| `app/pruebas/pdf-to-qti/modules/prompt_builder.py` | 685 | 🟡 Media | Prompts, extraer templates |
| `app/tagging/tagger.py` | 678 | 🔴 Alta | Motor de tagging, extraer extractors |
| `app/pruebas/pdf-to-qti/modules/ai_processing/ai_content_analyzer.py` | 584 | 🟡 Media | Analizador AI |
| `app/pruebas/pdf-to-qti/modules/image_processing/choice_diagrams.py` | 542 | 🟡 Media | Procesamiento de diagramas |
| `app/pruebas/pdf-splitter/modules/chunk_segmenter.py` | 534 | 🟡 Media | Segmentador de chunks |
| `app/pruebas/pdf-splitter/modules/pdf_utils.py` | 532 | 🟡 Media | Utilidades PDF |
| `app/pruebas/pdf-to-qti/scripts/migrate_s3_images_by_test.py` | 504 | 🟢 Baja | Script de migración |
| `app/pruebas/pdf-to-qti/modules/qti_configs.py` | 502 | 🟢 Baja | Configuraciones QTI |

## Estrategia de Refactorización

### Cuándo Refactorizar
- **Al modificar el archivo**: Si vas a hacer cambios significativos, aprovecha para dividir
- **Al agregar features**: Si necesitas agregar funcionalidad, extrae primero
- **NO como tarea separada**: Alto riesgo de introducir bugs sin necesidad

### Cómo Refactorizar
1. **Identificar responsabilidades**: ¿Qué hace cada sección del archivo?
2. **Extraer módulos**: Crear archivos nuevos para cada responsabilidad
3. **Mantener imports**: El archivo original puede re-exportar para compatibilidad
4. **Testear exhaustivamente**: Verificar que todo sigue funcionando

### Prioridades Sugeridas
1. `main.py` → Dividir en `orchestrator.py`, `cli.py`, `config.py`
2. `qti_transformer.py` → Extraer `xml_helpers.py`, `encoding_fixer.py`
3. `tagger.py` → Extraer `extractors.py`, `validators.py`

---

## Scripts Archivados

Los siguientes scripts fueron movidos a `app/pruebas/archive/fix_scripts/`:

- `fix_images_without_api.py`
- `fix_specific_questions.py`
- `fix_and_organize_invierno_2025.py`
- `fix_invierno_2025_questions.py`
- `fix_q14_q56.py`
- `fix_base64_in_xmls.py`
- `fix_encoding_in_xml.py`
- `fix_final_image_issues.py`
- `fix_final_issues_v2.py`
- `fix_issues_final_v3.py`
- `fix_remaining_image_issues.py`

**Razón**: Scripts de corrección one-time que ya cumplieron su propósito.

---

## Documentación Archivada

Las siguientes agendas fueron movidas a `docs/archive/agendas/`:

- `agenda-pdf-splitter-qti-pipeline.md` - Pipeline completado
- `agenda-cambios-manuales-version-final.md` - Cambios finalizados
- `agenda-cambios-manuales-tests.md` - Tests finalizados
- `agenda-cambios-manuales-prueba-invierno-2026.md` - Prueba procesada
- `agenda_taggeo.md` - Tagging completado (100% PASS)
- `pipeline-improvements-2025-01.md` - Mejoras implementadas

**Razón**: Documentación de trabajo completado, preservada para referencia histórica.
