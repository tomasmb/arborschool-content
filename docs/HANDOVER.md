# 🌴 Informe de Entrega (Handover) - Enero 2026

**Estado del Repositorio**: 🟢 Estable | Linting Clean | Tests Passing
**Última actualización**: 30 de Enero, 2026

Este documento resume el estado actual del proyecto `arborschool-content`, los logros recientes y las tareas pendientes para quien tome el relevo.

---

## 🗺️ Mapa del Tesoro (Estructura Clave)

| Directorio | Propósito |
|------------|-----------|
| `app/question_variants/` | **Pipeline de Variantes**: Generación de clones de preguntas con IA. |
| `app/pruebas/pdf-to-qti/` | **Pipeline PDF→QTI**: Conversión de PDFs PAES a formato QTI. |
| `app/data/pruebas/alternativas/` | **Output Variantes**: Aquí se guardan las variantes generadas. |
| `docs/specifications/` | **Verdades del Proyecto**: Estándares, modelos de datos, guías. |
| `docs/archive/` | **Histórico**: Agendas y scripts antiguos que ya cumplieron función. |
| `TECHNICAL_DEBT.md` | **Deuda Técnica**: Archivos que necesitan refactorización futura. |

---

## ✅ Logros Recientes (Ready to Use)

1.  **Sistema de Generación de Variantes (Pipeline de Alternativas)**:
    *   **Pipeline Operativo**: Se creo un sistema completo en `app/question_variants/` que genera, valida y guarda variantes de preguntas PAES.
    *   **Cobertura Diagnóstica**: Se generaron **mínimo 2 variantes** para todas las preguntas de la prueba diagnóstica.
        *   *Excepción*: **Q50 (Invierno 2025)** tiene 1 variante debido a la dificultad de crear un contexto alternativo equivalente sin cambiar la naturaleza de la pregunta.
    *   **Soporte Avanzado**: El pipeline maneja preguntas con imágenes complejas, gráficos y distintos tipos de lógica matemática.

2.  **Limpieza y Estándares**:
    *   Repo libre de errores de linting (Ruff).
    *   Documentación técnica centralizada en `docs/specifications/`.
    *   Limpieza de archivos obsoletos.

---

## 🚧 Próximos Pasos (To-Do List)

### 1. Validación de Feedback (Prioridad Alta)
*   [ ] **Correlación Feedback-Alternativa**: Se detectó que algunas preguntas diagnósticas tienen el feedback asignado a la alternativa incorrecta (dicen "incorrecto" cuando es la correcta).
*   *Acción*: Integrar una validación en el pipeline que asegure que el feedback generado corresponda lógicamente a la alternativa marcada como correcta.

### 2. Generalización del Pipeline
*   [ ] **Clasificación de Preguntas**: Para evitar revisión manual intensiva, seleccionar 1-2 preguntas representativas de cada "tipo":
    *   Con Imagen Clave (la imagen contiene la info).
    *   Con Imagen de Apoyo (contextual).
    *   Lógica Pura / Texto.
    *   Gráficos/Tablas.
*   *Meta*: Validar que el pipeline funcione robustamente para cada categoría y así confiar en la generación masiva.

### 3. Deuda Técnica y Refactorización
*   [ ] **Refactorización Gradual**: Existen archivos grandes (e.g., `main.py`) que deben modularizarse. Ver detalles en **[TECHNICAL_DEBT.md](TECHNICAL_DEBT.md)**.
*   *Nota*: No refactorizar todo de una vez; hacerlo progresivamente al trabajar en esos archivos.

### 4. Discusión Estratégica: MST vs CAT (Pendiente)
*   [ ] **Evaluar rendimiento MST (16 ítems)**: Analizar si la prueba actual logra la precisión esperada con sus 16 preguntas fijas por ruta.
*   [ ] **Decisión de Migración**: Discutir con el socio si es necesario migrar a un modelo **CAT (Computerized Adaptive Testing)** para optimizar la longitud del test y la precisión.
    *   *Contexto*: Ver comparativa detallada y roadmap en **[Diseño e Implementación Prueba Diagnóstica](specifications/diagnostic-test-implementation.md)** (Sección 3 y 5).

---

## 🛠️ Guía Rápida de Comandos

### Generar Variantes
```bash
# Específico para una pregunta
python -m app.question_variants.run_variant_generation \
  --source-test "Prueba-invierno-2025" \
  --questions "Q50" \
  --variants-per-question 1
```

### Verificar Calidad de Código
```bash
# Correr linter (Ruff)
ruff check app/

# Verificar estadísticas
ruff check app/ --statistics
```

### Gestión de Deuda Técnica
*   Si necesitas modificar un archivo listado en `TECHNICAL_DEBT.md`, intenta dividirlo en módulos más pequeños.
*   **NO** intentes refactorizar todo de una vez antes de probar funcionalidad.

---

¡Buenas vacaciones! 🏖️
