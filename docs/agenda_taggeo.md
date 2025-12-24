# Agenda de Taggeo - Arbor School Content

Este documento registra el progreso, las decisiones de diseño y la arquitectura del nuevo sistema de etiquetado (tagging) de preguntas utilizando Inteligencia Artificial (Gemini) y un Grafo de Conocimiento (Knowledge Graph).

## Objetivos
Implementar un sistema automatizado que enriquezca las preguntas (XML QTI) con metadatos educativos profundos:
1.  **Mapeo a Átomos**: Identificar qué habilidades cognitivas específicas evalúa cada pregunta.
2.  **Evaluación de Dificultad**: Estimar la demanda cognitiva (Baja/Media/Alta).
3.  **Feedback Instruccional**: Generar explicaciones pedagógicas para cada opción de respuesta (correcta y distractores).
4.  **Limpieza por Transitividad**: Utilizar el Grafo de Conocimientos para filtrar habilidades que son prerrequisitos implícitos, manteniendo solo la habilidad de mayor nivel.

## Arquitectura Implementada (`app/tagging/`)

### 1. `kg_utils.py` (Gestor del Knowledge Graph)
*   **Función**: Carga y gestiona los ~230 átomos desde `app/data/atoms/paes_m1_2026_atoms.json`.
*   **Característica Clave (Transitividad)**: Implementa `filter_redundant_atoms(ids)`.
    *   Recorre recursivamente los `prerrequisitos` de cada átomo seleccionado.
    *   Si un átomo seleccionado es prerrequisito de otro seleccionado, se elimina el prerrequisito.
    *   *Resultado*: Etiquetas más limpias y precisas, enfocadas en la habilidad "techo".

### 2. `tagger.py` (Motor de Etiquetado)
*   **Motor**: Usa `GeminiService` (Gemini 1.5 Pro/Flash).
*   **Capas de Extracción Robustas**:
    *   **MathML Recursivo**: Maneja fracciones, potencias, raíces y sistemas de ecuaciones (`mtable`) convirtiéndolos a notación legible (ej: `[ 2x+y=6 ; 4x+3y=12 ]`).
    *   **Tablas HTML**: Preserva la estructura de filas y columnas de tablas estándar, crucial para estadística y datasets.
    *   **Espaciado de Bloques**: Inserta saltos de línea inteligentes entre `<p>`, `<div>` y `<li>` para evitar la fusión de palabras y mantener la estructura de "Pasos" en resoluciones.
    *   **Contexto Visual**: Extrae el texto `alt` de las imágenes para dar contexto a la IA sobre gráficos o diagramas que sirven de opciones.
    *   **Respuesta Correcta**: Identifica el `qti-correct-response` directamente del XML para guiar el análisis pedagógico.
*   **Proceso Unificado**:
    1.  **Extracción**: Parsea el XML QTI usando las capas arriba descritas.
    2.  **Selección de Átomos**: Prompt con contexto completo de todos los átomos.
    3.  **Filtrado de Transitividad**: Remoción de habilidades redundantes vía `kg_utils`.
    4.  **Análisis Multimodal**: Generación de Dificultad y Feedback (en español) usando texto enriquecido e imágenes.
    5.  **Output**: Genera archivo sidecar `metadata_tags.json`.

### 4. `tagger.py` (QA Validator Integration)
*   **Fase de Validación**: Se agrega un paso final post-generación.
*   **Rol**: "Juez IA" (QA Specialist).
*   **Input**: Recibe la pregunta original y los metadatos generados (tags, dificultad, feedback).
*   **Checklist**: Verifica consistencia, relevancia de átomos y exactitud matemática del feedback.
*   **Output**: Un estado `PASS` o `FAIL`, lista de `issues` y un score de calidad. Si falla, genera una alerta pero guarda el resultado (feedback loop manual).

### 3. `batch_runner.py` (Orquestador)
*   Busca recursivamente todos los archivos `question.xml` en `app/data/pruebas/finalizadas`.
*   Soporta la nueva estructura de carpetas (`.../Q1/question.xml`).
*   Ejecuta el tagging de forma secuencial (o paralela si se optimiza) y maneja errores.

## Progreso Actual (24 Dic 2024)

### Hitos Completados
- [x] **Infraestructura Base**: Creación de módulos y lectura de átomos.
- [x] **Integración con Gemini**: Configuración de `GeminiService` para prompts de contexto largo.
- [x] **Soporte Multi-Átomo**: Capacidad de detectar múltiples habilidades.
- [x] **Dificultad Cognitiva**: Rúbrica genérica implementada y verificada.
- [x] **Feedback Instruccional**: Generación exitosa de feedback por opción.
- [x] **Filtro de Transitividad**: Implementado exitosamente. Reduce redundancia eliminando átomos prerrequisitos.
- [x] **Validador QA (Juez IA)**: Implementado. Verifica calidad, idioma y exactitud matemática.
- [x] **Soporte Multimodal (Imágenes)**: Habilitado para leer gráficos directamente.
- [x] **Extracción de Precisión (Fix Matemático)**: Implementación de MathML recursivo, tablas HTML y espaciado de bloques para evitar alucinaciones en fracciones, potencias y sistemas de pasos.
- [x] **Identificación de Respuesta Correcta**: Extracción automática del ID correcto desde el XML para anclar el análisis.

### Próximos Pasos (En Curso)
1.  **Ejecución Masiva (220 preguntas)**: Proceso iniciado (`batch_runner.py`). Ejecutándose en segundo plano (estimado ~15 hrs).
2.  **Reporte de Cobertura**: Una vez terminada la ejecución, generar reporte de átomos cubiertos.
3.  **Ejecución Masiva**: Correr `batch_runner.py` sobre el dataset completo (~220 preguntas).
4.  **Reporte de Cobertura**: Analizar qué átomos quedaron sin preguntas.

## Análisis de Código de Referencia (`exemplars`)
*   Se detectó que faltaba el código fuente de `FeedbackGenerator` (módulos perdidos `app.feedback`).
*   **Solución**: Se reimplementó la lógica de generación de feedback desde cero dentro de `tagger.py`, adaptándola a las necesidades actuales.
*   Falta implementar un "Juez/Validador" automatizado (presente en referencia como `validate_feedback.py`), que podría usarse como segunda capa de aseguramiento de calidad.


## Reglas Operativas y Principios (Actualizado 24 Dic)
1.  **Preservación de Artefactos API**: NUNCA eliminar archivos generados por la API (`.json`, `.xml`) sin autorización explícita del usuario.
    *   *Razón*: Optimización de costos y cuotas. Es preferible intentar reparaciones locales ("surgical fixes") antes que descartar contenido valioso ya pagado.
    *   *Excepción*: Solo si el archivo está corrupto a nivel de sistema de archivos o totalmente vacío (0 bytes).
2.  **Validación Previa**: Antes de cualquier modificación masiva, realizar un "dry-run" o script de diagnóstico para confirmar el alcance.

## Registro de Procesamiento - Primera Tanda (Versión 1)

> [!NOTE]
> Esta sección es un registro histórico de las preguntas que se procesaron exitosamente con la primera versión del código de taggeo. Este registro es estático y no debe modificarse en futuras ejecuciones para preservar la trazabilidad.

Las siguientes preguntas obtuvieron un estado `PASS` en la validación inicial:

### Prueba-invierno-2025 (36 preguntas)
Q1, Q2, Q5, Q6, Q7, Q11, Q12, Q13, Q14, Q15, Q17, Q18, Q21, Q22, Q24, Q27, Q28, Q29, Q30, Q32, Q33, Q35, Q38, Q40, Q43, Q46, Q49, Q52, Q54, Q56, Q58, Q59, Q60, Q61, Q62, Q63

### prueba-invierno-2026 (1 pregunta)
Q1

---
*Documento generado automáticamente por Antigravity Agent.*
