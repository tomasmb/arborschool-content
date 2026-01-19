# Propuesta Reunión - 17 Enero 2026

## 1. Alineación de Átomos: Conectar Frontend a la Verdad

**Problema Actual:**
El Frontend (`KnowledgeGraph`) vive en el pasado: lee un archivo estático viejo (`paes_math_kg.json`) y desconectado, mientras que tu Base de Datos ya tiene los datos nuevos y oficiales cargados desde `content`.

**Diagnóstico Técnico:**
*   ✅ **Backend**: BDD `arbor_local` ya está poblada con 229 átomos oficiales. Script de sincronización funciona perfecto.
*   ⚠️ **Frontend**: No existe una API para pedirle los átomos a la BDD, por eso sigue usando el archivo viejo.

**Solución Propuesta:**
1.  **Crear API simple (`/api/atoms`)**: Un puente para que el Frontend pida datos reales.
2.  **Conectar Grafo**: Cambiar 1 línea en `KnowledgeGraph.tsx` para usar esa API.
3.  **Eliminar Legacy**: Borrar `math.json` y `paes_math_kg.json` para siempre.

---

## 2. UI Móvil: Estilo Duolingo

**Estado Actual:**
*   ✅ **Infraestructura Lista**: Usamos tecnologías modernas (Tailwind CSS) que facilitan el diseño móvil.
*   ✅ **Landing Page**: Ya es responsiva y se adapta bien.

**Propuesta:**
Tu socio tiene razón: la base está. No hay que reehacer, solo **ajustar**.
1.  **Foco**: Pulir vista de "Pregunta" en el diagnóstico (botones grandes, texto legible).
2.  **Dashboard**: Simplificar la vista de grafo para pantallas chicas.

---

## 3. Feedback Post-Diagnóstico: Lo tenemos TODO

**Hallazgo Clave**: Revisé los datos de las preguntas y tenemos una mina de oro:
*   ✅ **Feedback por Distractor**: Sabemos exactamente *por qué* marcó la alternativa A (error específico) vs la C.
*   ✅ **Guía General**: Tenemos la explicación paso a paso de cómo se resolvía.

**Propuesta de Flujo:**

1.  **Pantalla de Resultados**: Al finalizar, junto al puntaje, un botón grande **"Ver Feedback por Pregunta"**.
2.  **Modo Revisión**: Lleva a una vista pregunta por pregunta donde ve su respuesta vs la correcta.
3.  **Feedback Dinámico** (automático del JSON):

| Caso | Qué mostramos (Automático) | Data source (Ya existe) |
|------|---------------------------|-------------------------|
| **Respondió Mal** | 1. **Tu Error**: "Marcaste A porque probablemente sumaste mal los signos..." <br> 2. **Solución**: "La correcta era B porque..." | `per_option_feedback[seleccionada]` <br> `per_option_feedback[correcta]` |
| **"No lo sé"** | 1. **Paso a Paso**: Mostramos directamente la guía general de resolución. | `general_guidance` |
| **Respondió Bien** | 1. **Refuerzo Positivo**: "¡Exacto! Era B porque..." | `per_option_feedback[correcta]` |

**Acción Inmediata**:
*   Diseñar el componente "FeedbackCard" que consuma estos campos del JSON. Es pura UI, la data ya está.

---

## 4. Evolución de la Prueba: De MST a CAT-KG (Brain)

**Lo que tenemos hoy (MST):**
*   **Qué es**: Test Multietapa (bloques fijos).
*   **Datos**: 16 Preguntas $\approx$ **Cobertura de ~190 Átomos** (vía transitividad y alcance M1).
*   **Por qué sirve HOY (MVP)**: Nos permite **clasificar YA** a los alumnos (Básico/Medio/Avanzado) y dar un puntaje inicial confiable. Es una lógica simple y robusta que nos deja lanzar **esta semana** sin riesgo de que el algoritmo "se vuelva loco" (como podría pasar con un CAT mal calibrado).
*   **Limitación**: Cobertura amplia pero poco profunda. Si marcas mal Ecuación Cuadrática, no sé si fallaste en factorizar (básico) o en la fórmula (medio). Es ciego a la causa raíz.

**La Mejora: CAT-KG (Adaptive Top-Down)**
Modelo que navega el grafo y se adapta (Rango: **12-18 preguntas**).

**Cómo funciona ("Top-Down"):**
1.  **Disparo**: El sistema lanza una pregunta de un átomo "Tope" (difícil).
2.  **Si Responde Bien**: ✅ Asume dominado ese átomo **Y TODOS sus prerrequisitos**. (Con 1 pregunta validamos ~10 átomos).
3.  **Si Responde Mal**: ❌ Baja un nivel en el grafo. Pregunta por el prerrequisito inmediato para buscar dónde se rompió la cadena.

**Por qué es mejor:**
*   **Cobertura Massiva**: Con las mismas 16 preguntas, valida **~100+ átomos** con certeza alta.
*   **Diagnóstico Real**: Identifica exactamente el "ladrillo suelto" en la base del estudiante.

**Plan de Implementación (Roadmap):**
1.  **Fase 1**: Script "The Brain". Motor lógico desconectado del UI.
2.  **Fase 2**: API `/api/next-question`. Endpoint que recibe el historial y devuelve el siguiente átomo a evaluar.
3.  **Fase 3**: Integración Frontend. Reemplazar la lógica de etapas fijas por llamadas a esta API.
---

---

## 5. Escalabilidad: Generación de Preguntas con IA

**Estrategia**: Aprovechar el pipeline que ya creamos para taggear (Gemini) y usarlo para **generar**.

**Aplicaciones Clave:**
1.  **Variantes (Anti-Burning)**: Generar "clones" del mismo átomo/dificultad. Vital para no "quemar" preguntas si el alumno repite el test.
2.  **Hard Mode**: Generar automáticamente versiones más difíciles del mismo ejercicio.
3.  **Banco para CAT**: El CAT necesita muchas preguntas. Con IA llenamos el banco masivamente usando la estructura de átomos que ya definimos.

**Valor**: Construimos el activo más valioso de un Preu (Banco de Preguntas) a costo marginal cero y velocidad x100.

---

## 6. Resumen de Acuerdo (Para cerrar la reunión)

*   [ ] Front: Switch a API de BDD.
*   [ ] UI: Ajuste móvil simple.
*   [ ] Features: Botón Feedback, Roadmap CAT y **Motor de IA**.
