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

1.  **Limpieza de Código y Estándares**:
    *   Repo libre de errores de linting (Ruff).
    *   Archivos obsoletos y agendas viejas archivados en `archive/`.
    *   Configuración de `pyproject.toml` modernizada.

2.  **Generación de Variantes (Diagnostic Test)**:
    *   Pipeline operativo en `app/question_variants/`.
    *   **Q50 (Invierno 2025)**: Finalizada con 1 variante robusta ("Radios como manecillas") y SVG corregido.
    *   Soporte para preguntas con imágenes y gráficos complejos (boxplots, transformaciones isométricas).
    *   Validación automática de respuestas correctas.

3.  **Documentación**:
    *   `docs/README.md` actualizado como índice central.
    *   `docs/TECHNICAL_DEBT.md` creado para tracking de refactorización.

---

## 🚧 Próximos Pasos (To-Do List)

Basado en las agendas activas en `docs/agendas/`:

### 1. Pipeline de Variantes (`docs/agendas/agenda_generacion_variantes.md`)
*   [ ] **Mejorar Prompts MathML**: Refinar la copia de estructuras complejas (sistemas de ecuaciones).
*   [ ] **Retry Automático**: Implementar reintentos si la API de Gemini falla o el validador rechaza.
*   [ ] **Integración**: Definir flujo final hacia base de datos/frontend.

### 2. Prueba Diagnóstica (`docs/agendas/agenda_prueba_diagnostica.md`)
*   [ ] **Finalizar Q50**: Confirmar visualización en frontend (SVG integrado).
*   [ ] **Revisión Final**: Validar que todas las preguntas del diagnóstico tengan sus variantes generadas y aprobadas.

### 3. Mantenimiento
*   [ ] **Refactorización Gradual**: Consultar `docs/TECHNICAL_DEBT.md` antes de tocar archivos grandes como `main.py`.

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
