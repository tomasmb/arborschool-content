# 🔒 Estándares de Código — arborschool-content

> Este documento es la **fuente de verdad** para la calidad del código.  
> Antes de cada commit, TODO debe cumplirse.

---

## 1. Principios Fundamentales

### SOLID

| Principio | Aplicación |
|-----------|------------|
| **S**ingle Responsibility | Un módulo/función hace **una cosa bien** |
| **O**pen/Closed | Agregar features sin modificar código existente |
| **L**iskov Substitution | Implementaciones intercambiables |
| **I**nterface Segregation | Interfaces pequeñas y enfocadas |
| **D**ependency Inversion | Depender de abstracciones, no concreciones |

→ Ver detalles: [python-best-practices.md](./python-best-practices.md#4-solid-and-dry-in-this-project)

### DRY (Don't Repeat Yourself)

- Si copias 3+ líneas de lógica estructural → **extrae un helper**
- Si dos módulos comparten lógica → `app/common/`
- Helpers comunes: I/O de archivos, JSON load/save, utilidades de temarios

---

## 2. Límites de Tamaño

| Elemento | Límite Máximo | Ideal |
|----------|---------------|-------|
| **Archivos** | 500 líneas | 300-400 líneas |
| **Funciones** | 40 líneas | 25-30 líneas |
| **Líneas de código** | 150 caracteres | ~100 caracteres |

> Si algo excede el límite **→ refactoriza antes de commit**

---

## 3. Prompts (LLM)

Los prompts deben seguir la guía de [gemini-3-pro-prompt-engineering-best-practices.md](./gemini-3-pro-prompt-engineering-best-practices.md).

**Los 3 mandamientos:**
1. **Sin redundancia** — No repetir la misma instrucción de formas diferentes
2. **Sin contradicciones** — Revisar que reglas nuevas no conflictúen con existentes
3. **Bien segmentado** — Usar estructura clara (`<role>`, `<task>`, `<rules>`, etc.)

**Checklist anti-overfitting:**
- [ ] ¿El fix es un principio general o un parche específico?
- [ ] ¿Probaste con inputs diversos, no solo el caso que falla?
- [ ] ¿Simplificaste reglas existentes antes de agregar nuevas?
- [ ] ¿Hay referencias a IDs o valores específicos? (red flag 🚩)

---

## 4. Linting

**Herramienta:** Ruff (configurado en `pyproject.toml`)

**Reglas activas:** `E`, `F`, `W`, `I` (errores, pyflakes, warnings, imports)

**Antes de commit:**
```bash
ruff check app/
```

> **Cero errores tolerados.** Si hay un caso válido para ignorar, usa `# noqa: <CODE>` con comentario explicando por qué.

---

## 5. Documentación

### Niveles de documentación

| Nivel | Cuándo usar | Ejemplo |
|-------|-------------|---------|
| **Comentarios en código** | Lógica no obvia, "por qué" no "qué" | `# skip empty lines to avoid division by zero` |
| **Docstrings** | Funciones públicas, APIs | Parámetros, retorno, excepciones |
| **README en carpeta** | Módulos con múltiples archivos relacionados | `app/temarios/README.md` |
| **MD en docs/** | Decisiones arquitectónicas, reasoning complejo | `specifications/`, `research/` |

### ❌ Anti-patrones de documentación

- **Sobre-documentación**: Un MD para cada función
- **Sub-documentación**: Código complejo sin explicar el "por qué"
- **Documentación obsoleta**: Peor que no documentar
- **MDs temporales**: Una vez implementado, eliminar o mover a `research/`

### ✅ Cuándo crear un MD

- Reasoning detrás de **sistemas complejos** (ej: generación de variantes)
- **Decisiones de diseño** que no son obvias
- **Especificaciones** que son verdades del repo
- **Agendas** de trabajo en progreso (temporales, se archivan al terminar)

---

## 6. Type Hints

**Obligatorio** en funciones nuevas (públicas e internas).

```python
from __future__ import annotations

def process_question(question_id: str, options: dict[str, Any]) -> QuestionResult:
    """Procesa una pregunta y retorna el resultado."""
    ...
```

---

## 7. Code Smells (Alarmas)

| Smell | Síntoma | Solución |
|-------|---------|----------|
| **Long Method** | Función >40 líneas | Dividir en helpers |
| **Large Class/Module** | Archivo >500 líneas | Separar responsabilidades |
| **Duplicate Code** | Copy-paste de lógica | Extraer función común |
| **Feature Envy** | Función usa más datos de otro módulo | Mover función |
| **Magic Numbers** | `if x > 42:` | Usar constantes con nombre |
| **Dead Code** | Código comentado o nunca usado | Eliminar |
| **Long Parameter List** | Función con 5+ params | Usar dataclass/dict |

---

## 8. Checklist Pre-Commit

```markdown
## Antes de hacer commit, verificar:

### Código
- [ ] Ruff pasa sin errores: `ruff check app/`
- [ ] Archivos modificados < 500 líneas
- [ ] Funciones nuevas < 40 líneas  
- [ ] Funciones nuevas tienen type hints
- [ ] Sin duplicación obvia (DRY)

### Prompts (si aplica)
- [ ] Sin redundancia en instrucciones
- [ ] Sin contradicciones con reglas existentes
- [ ] Estructura clara y segmentada

### Documentación
- [ ] Código no obvio tiene comentarios explicando "por qué"
- [ ] Funciones públicas tienen docstring
- [ ] No hay documentación obsoleta
```

---

## 9. Referencias

- [Python Best Practices](./python-best-practices.md)
- [Prompt Engineering Best Practices](./gemini-3-pro-prompt-engineering-best-practices.md)
- [Estructura del Repo](./repo-structure-and-modules.md)

---

*Última actualización: 2025-01-30*
