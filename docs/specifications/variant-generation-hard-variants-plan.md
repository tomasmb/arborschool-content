# Generacion de Variantes No Mecanizables (v1)

Este documento define una estrategia para generar variantes de preguntas PAES que:

- evalúen el mismo constructo que la pregunta fuente;
- sean mas dificiles;
- no sean mecanizables por receta/memoria;
- escalen a N variantes por pregunta para 4 pruebas (N configurable; inicio en 10).

Fecha de referencia del documento: 2026-03-11.

---

## 1. Objetivo y alcance

### 1.1 Objetivo principal

Pasar desde variantes "isomorficas por cambio superficial" a variantes de mayor profundidad cognitiva:

- mismo constructo evaluado;
- distinto patron de resolucion superficial;
- mayor exigencia de transferencia;
- sin salirse del temario ni del atom asociado.

### 1.2 Alcance inicial (fase 0-1)

- Insumo: preguntas finalizadas en `app/data/pruebas/finalizadas/`.
- Cobertura objetivo: 4 pruebas.
- Volumen objetivo inicial: 10 variantes por pregunta (parametro inicial, no limite de diseno).
- Modo de ejecucion: pipeline por fases con gates de validacion estrictos.

### 1.3 No-objetivos (por ahora)

- No optimizar costo final antes de cerrar calidad.
- No abrir cobertura a preguntas fuera de las 4 pruebas priorizadas.
- No entrenar/fine-tuning en esta fase; solo prompting + evaluacion.

---

## 2. Definicion operativa de "no mecanizable"

Una variante se considera no mecanizable si cumple simultaneamente:

1. Mantiene el mismo constructo y habilidad principal.
2. Cambia al menos 2 dimensiones estructurales (no solo numeros):
   - representacion (tabla/grafico/texto/diagrama),
   - tipo de distractor dominante,
   - restriccion o dato irrelevante,
   - forma de pregunta (directa vs inferencial),
   - orden de pasos o subobjetivo intermedio.
3. Requiere justificar (explicita o implicitamente) por que el metodo aplica.
4. Bloquea atajos por patron (ejemplo: plug-and-chug directo).

Regla de oro: "mismo que evalua, distinto como se llega".

---

## 3. Artefacto objetivo por pregunta fuente

Por cada pregunta `Qx`:

- `variant_plan.json`:
  - constructo fuente,
  - atom principal/secundarios,
  - limites de dificultad,
  - N blueprints de variante.
- `image_plan.json`:
  - decision de uso de imagen por variante,
  - tipo de imagen,
  - prompt largo de generacion.
- `variants_generated/`:
  - N candidatos QTI.
- `validation_report.json`:
  - resultado por gate (constructo, dificultad, solucion, distractores, anti-memoria, imagen).
- `approved/`:
  - variantes aprobadas.

---

## 4. Arquitectura propuesta (v2 pipeline)

## 4.1 Fases

1. Perfilado de pregunta fuente
2. Planificacion de N variantes (blueprints)
3. Enriquecimiento visual y generacion de imagen (cuando aplique)
4. Generacion QTI de variantes
5. Validacion multi-gate
6. Seleccion final y export
7. Futuro: proceso independiente de feedback sobre variantes ya aprobadas

## 4.2 Gates obligatorios

- Gate A: mismo constructo/atom.
- Gate B: dificultad >= fuente (dentro de banda permitida).
- Gate C: solucion correcta y unica.
- Gate D: distractores plausibles y diagnosticos.
- Gate E: anti-memoria/no mecanizable.
- Gate F: calidad visual (si hay imagen).

Solo pasan a `approved/` las variantes que superan todos los gates.

---

## 5. Estrategia de modelos (investigacion actual)

No fijar modelo definitivo sin benchmark interno. Usar arquitectura "best model per task".

## 5.1 Candidatos por tarea

- Planeacion/razonamiento pedagogico:
  - `gemini-3-pro-preview` (alto contexto multimodal).
  - `gpt-5.4` para control estricto y validacion estructurada.
- Generacion de imagen:
  - `gemini-3-pro-image-preview` (max fidelidad en prompts complejos).
  - `gemini-2.5-flash-image` (mejor costo/latencia para volumen).
- Validacion de imagen + texto:
  - `gpt-5.4` (vision + structured outputs) como verificador independiente.

## 5.2 Recomendacion inicial de stack (para empezar esta semana)

1. Blueprint + generacion QTI: Gemini (continuidad con pipeline actual).
2. Validacion de constructo/dificultad/anti-memoria: OpenAI (`gpt-5.4`) con schema JSON estricto.
3. Imagen:
   - generar con Gemini image model,
   - validar con OpenAI vision usando prompt + imagen + checklist.

Esto mantiene tu idea actual (Gemini genera, OpenAI valida) pero con gates mas formales.

## 5.3 Regla de decision final (benchmark)

Comparar 3 configuraciones:

1. Gemini->Gemini (gen + val)
2. Gemini->OpenAI (gen + val cruzada)
3. OpenAI->OpenAI (gen + val)

Elegir segun:

- precision de aprobacion (QA humano),
- tasa de rechazo correcto,
- costo por variante aprobada,
- latencia por pregunta.

---

## 6. Pipeline de imagen (detallado)

Cuando una variante requiera imagen:

1. Generar `image_prompt_long` (descripcion detallada y verificable):
   - objetos y relaciones espaciales exactas,
   - magnitudes y etiquetas,
   - estilo visual pedagogico (sin ruido decorativo),
   - restricciones de legibilidad (tamano minimo de texto, contraste).
2. Generar imagen con Gemini image model.
3. Validar con OpenAI vision usando:
   - imagen resultante,
   - `image_prompt_long`,
   - checklist de exactitud pedagogica.
4. Si falla, regenerar max N intentos; luego fallback a variante sin imagen solo si la imagen no era esencial.

Regla critica: si la imagen es esencial para resolver, no hay fallback text-only.

---

## 7. Prompting y contratos JSON

Todos los pasos LLM deben usar salida estructurada con schema:

- `variant_blueprint.schema.json`
- `variant_qti_output.schema.json`
- `semantic_validation.schema.json`
- `image_validation.schema.json`

Con esto evitamos respuestas ambiguas y hacemos validacion automatizable.

---

## 8. Rubrica de validacion "mismo constructo, mas dificil"

Scoring por variante (0-2 por criterio):

1. Constructo equivalente.
2. Habilidad principal equivalente.
3. Dificultad relativa (>= fuente sin desbordar temario).
4. No mecanizable (cambio estructural real).
5. Distractores diagnosticos.
6. Exactitud de solucion.
7. Calidad visual (si aplica).

Umbral de aprobacion sugerido: >= 11/14 y sin fallas criticas.

Fallas criticas:

- constructo distinto,
- respuesta incorrecta,
- imagen esencial incorrecta.

---

## 9. Plan de experimento para arrancar

## 9.1 Muestra inicial

- 20 preguntas (mezcla de las 4 pruebas, con y sin imagen).
- N variantes objetivo por pregunta (en el piloto inicial, N=10).
- 200 variantes candidatas totales.

## 9.2 Protocolo

1. Ejecutar las 3 configuraciones de modelo.
2. Tomar muestra ciega para QA humano.
3. Medir:
   - `% aprobadas QA`,
   - `% rechazo correcto`,
   - costo por variante aprobada,
   - tiempo promedio por pregunta.
4. Congelar stack ganador para corrida completa.

---

## 10. Cambios concretos propuestos en el repo (siguiente iteracion)

1. Crear `docs/specifications/variant-generation-hard-variants-execution.md` con runbook operativo.
2. Extender `app/question_variants/models.py`:
   - `VariantBlueprint`,
   - `ImagePlan`,
   - `ValidationScorecard`.
3. Agregar fase de planning antes de `variant_generator.py`.
4. Agregar validador anti-memoria en `variant_validator.py`.
5. Agregar modulo de validacion visual cruzada.
6. Parametrizar `--variants-per-question 10` por defecto para la corrida nueva.
7. TODO futuro: agregar pipeline separado de feedback/enrichment solo sobre
   `hard_variants/approved/`, fuera del camino critico de generacion.

---

## 11. Riesgos y mitigaciones

- Riesgo: variantes "mas dificiles" se salen del constructo.
  - Mitigacion: gate de constructo previo a aprobacion.
- Riesgo: costo alto por rejecion masiva.
  - Mitigacion: planning fuerte + schema + retries acotados.
- Riesgo: imagen bonita pero pedagogicamente incorrecta.
  - Mitigacion: validacion cruzada imagen+prompt con checklist.
- Riesgo: drift de modelos preview.
  - Mitigacion: pin de version/model code + benchmark recurrente.

---

## 12. Fuentes externas revisadas

- OpenAI models overview:
  - https://platform.openai.com/docs/models
- OpenAI latest model guide:
  - https://platform.openai.com/docs/guides/latest-model
- OpenAI images/vision:
  - https://platform.openai.com/docs/guides/images-vision
- OpenAI image generation:
  - https://platform.openai.com/docs/guides/images/image-generation
- OpenAI structured outputs:
  - https://platform.openai.com/docs/guides/structured-outputs
- Gemini models:
  - https://ai.google.dev/models/gemini
- Gemini image generation:
  - https://ai.google.dev/gemini-api/docs/image-generation
- Gemini deprecations:
  - https://ai.google.dev/gemini-api/docs/deprecations
