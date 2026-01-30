# Pipeline de Generación de Variantes - Especificaciones Técnicas

**Ubicación del Código**: `app/question_variants/`
**Estado Actual**: En desarrollo activo (Fase 1-2 completada)

## Objetivo del Sistema
Crear variantes robustas, matemáticamente equivalentes y contextualmente similares de preguntas PAES (Prueba de Acceso a la Educación Superior) para pruebas diagnósticas, usando LLMs (Gemini 3 Pro).

---

## 🏗️ Arquitectura

### Componentes Principales
1.  **Orquestador (`pipeline.py`)**: Coordina la obtención de preguntas fuente, llamada a LLM, validación y guardado.
2.  **Generador (`variant_generator.py`)**: Construye prompts con restricciones estrictas (mismo concepto, diferente contexto/números).
3.  **Validador (`variant_validator.py`)**: Verifica validez matemática y estructural.
    *   Comprueba que la respuesta correcta sea única y matemáticamente válida.
    *   Verifica estructura XML válida (QTI).
4.  **Modelos (`models.py`)**: Dataclasses para `SourceQuestion`, `VariantQuestion`.

### Flujo de Trabajo
1.  **Lectura**: Lee `question.xml` y metadata de la pregunta fuente.
2.  **Generación**: Prompt a Gemini para crear 3 variantes.
3.  **Validación**:
    *   Sintaxis XML.
    *   Consistencia matemática (opcionalmente con ejecuciones de código o verificación lógica).
4.  **Guardado**: Almacena en `app/data/pruebas/alternativas/` con estructura específica.

---

## 💻 Uso Operativo (CLI)

El pipeline se ejecuta principalmente vía línea de comandos:

```bash
# Generar N variantes para preguntas específicas de una prueba
python -m app.question_variants.run_variant_generation \
  --source-test "Prueba-invierno-2025" \
  --questions "Q1,Q5,Q50" \
  --variants-per-question 2
```

### Argumentos Comunes
*   `--source-test`: Nombre de la carpeta de prueba en `data/pruebas/`.
*   `--questions`: Lista separada por comas de IDs de preguntas (e.g. `Q1,Q2`).
*   `--variants-per-question`: Número de variantes a intentar generar por pregunta.

---

## 📂 Estructura de Salida

Las variantes generadas se organizan en `app/data/pruebas/alternativas/`:

```
app/data/pruebas/alternativas/
└── [NombrePrueba]/
    └── [PreguntaID]/
        ├── approved/               # Variantes validadas y listas
        │   ├── [PreguntaID]_v1/
        │   │   ├── question.xml
        │   │   ├── metadata_tags.json
        │   │   └── variant_info.json
        │   └── [PreguntaID]_v2/
        ├── rejected/               # Fallaron validación (para debug)
        └── generation_report.json  # Resumen de ejecución
```

---

## ⚠️ Consideraciones y Limitaciones Conocidas

1.  **MathML Complejo**: La extracción y generación de estructuras MathML muy complejas (e.g. tablas anidadas, sistemas de ecuaciones grandes) aún presenta desafíos de fidelidad.
2.  **Imágenes**:
    *   Imágenes decorativas se preservan o instruyen al LLM para ignorar.
    *   Imágenes esenciales (geométricas) requieren generación/modificación SVGs (parcialmente soportado).
3.  **Costo**: ~7.5k tokens por pregunta (aprox).

## Referencias
*   Agenda de Desarrollo: `docs/agendas/agenda_generacion_variantes.md`
