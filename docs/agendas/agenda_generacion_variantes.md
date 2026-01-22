# Agenda: Pipeline de Generación de Variantes de Preguntas

> Documento de seguimiento del desarrollo del pipeline para generar variantes de preguntas que evalúan el mismo concepto con diferentes números/contexto.

---

## Objetivo

Crear un sistema que genere variantes confiables de preguntas PAES para:
- No "quemar" las preguntas oficiales
- Poder hacer múltiples diagnósticos al mismo usuario
- Aumentar el banco de preguntas sin perder calidad pedagógica

---

## ✅ Completado

### 1. Diseño e Implementación Base (2025-01-22)
- [x] Revisada documentación de Tomás (`docs/ai-question-generation/ASSESSMENT_VARIANT_GENERATION.md`)
- [x] Creado módulo `app/question_variants/` con:
  - `models.py` - Dataclasses: SourceQuestion, VariantQuestion, ValidationResult
  - `variant_generator.py` - Generación con prompts restrictivos via Gemini
  - `variant_validator.py` - Validación matemática y de concepto
  - `pipeline.py` - Orquestador del flujo
  - `run_variant_generation.py` - CLI para ejecutar

### 2. Pruebas Iniciales
| Pregunta | Tipo | Generadas | Aprobadas | Notas |
|----------|------|-----------|-----------|-------|
| Q1 | Aritmética enteros | 2 | 2 | Aprobadas manualmente (falso negativo del validador) |
| Q4 | Fracciones | 2 | 0 | Problema con extracción MathML `<mfrac>` |
| Q5 | Tabla + comparación | 2 | 2 | Aprobadas manualmente |

### 3. Correcciones al Validador
- [x] Corregido `_element_to_text()` para incluir `<qti-prompt>`
- [x] Corregido `_mathml_to_text()` para procesar `<mfrac>` como `(num/den)`
- [x] Agregado `_process_mathml_element()` recursivo para MathML complejo

---

## 🔄 En Progreso / Por Probar

### Validación Mejorada de MathML
- [ ] Probar Q4 (fracciones) con el validador corregido
- [ ] Verificar que `(11/6)` se muestra correctamente en el prompt de validación

### Generador
- [ ] El generador también necesita mejor extracción de MathML para el prompt de generación
- [ ] Considerar pasar el XML raw al LLM en lugar de texto extraído

---

## 📋 Por Hacer

### Mejoras al Pipeline
- [ ] Agregar soporte para imágenes (reuso de imágenes originales)
- [ ] Implementar retry automático para variantes rechazadas
- [ ] Agregar flag `--dry-run` para ver qué se generaría sin llamar a la API
- [ ] Mejorar logging y reportes

### Pruebas Pendientes
- [ ] Probar con preguntas que tienen `<mfrac>` (fracciones)
- [ ] Probar con preguntas que tienen `<msup>` (potencias)
- [ ] Probar con preguntas que tienen `<msqrt>` (raíces)
- [ ] Probar con preguntas con imágenes/gráficos
- [ ] Probar batch de 10+ preguntas para evaluar tasa de aprobación

### Integración
- [ ] Definir cómo se usarán las variantes en el sistema de diagnóstico
- [ ] Documentar estructura de output para frontend
- [ ] Agregar variantes a la base de datos

---

## Uso Actual

```bash
# Generar variantes para preguntas específicas
python -m app.question_variants.run_variant_generation \
  --source-test "Prueba-invierno-2025" \
  --questions "Q1,Q5" \
  --variants-per-question 2

# Output en: app/data/pruebas/alternativas/
```

---

## Estructura de Output

```
app/data/pruebas/alternativas/
└── Prueba-invierno-2025/
    └── Q1/
        ├── approved/
        │   ├── Q1_v1/
        │   │   ├── question.xml
        │   │   ├── metadata_tags.json
        │   │   └── variant_info.json
        │   └── Q1_v2/
        ├── rejected/
        └── generation_report.json
```

---

## Notas Técnicas

- **API**: Gemini 3 Pro (con fallback a OpenAI si hay rate limits)
- **Costo estimado**: ~7500 tokens por pregunta (3 variantes)
- **Tasa de aprobación actual**: ~50% (necesita mejorar extracción MathML)
