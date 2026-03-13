# Research: Model Selection for Hard Variant Generation

Fecha: 2026-03-11

## Objetivo

Definir una estrategia de modelos para generar variantes no mecanizables
(10 por pregunta) con validacion robusta de constructo, solucion e imagen.

## Hallazgos clave

1. OpenAI models page lista `GPT-5.4` como el modelo insignia actual para tareas complejas.
2. OpenAI documenta soporte de vision y structured outputs en guias oficiales,
   lo que calza con validaciones tipo checklist/schema.
3. Google mantiene familia Gemini (incluyendo 2.5/3.x segun disponibilidad)
   y documenta flujo dedicado para generacion de imagen.
4. Google publica deprecations/sunsets de modelos, por lo que conviene pin
   de modelo y control de drift.

## Recomendacion de arquitectura (corta)

- Generacion de blueprints + QTI inicial: Gemini (continuidad con repo actual).
- Validacion semantica estricta (constructo, dificultad, no mecanizable):
  OpenAI `gpt-5.4` con salida JSON estructurada.
- Imagen:
  - Generar con Gemini image model.
  - Validar imagen+prompt con OpenAI vision independiente.

## Por que no fijar un solo proveedor ahora

La calidad real en este caso depende de la interaccion entre:

- dificultad matematica por tipo de item,
- fidelidad de imagen en items visuales,
- tasa de falsos positivos del validador.

Por eso se recomienda benchmark en muestra controlada antes de corrida total.

## Benchmark minimo recomendado

- Muestra: 20 preguntas mixtas (con/sin imagen, 4 pruebas).
- Corridas: 3 stacks (`Gemini->Gemini`, `Gemini->OpenAI`, `OpenAI->OpenAI`).
- Metricas:
  - precision de aprobacion (QA humano),
  - tasa de rechazo correcto,
  - costo por variante aprobada,
  - latencia por pregunta.

## Fuentes oficiales revisadas

- https://platform.openai.com/docs/models
- https://platform.openai.com/docs/guides/latest-model
- https://platform.openai.com/docs/guides/images-vision
- https://platform.openai.com/docs/guides/images/image-generation
- https://platform.openai.com/docs/guides/structured-outputs
- https://ai.google.dev/models/gemini
- https://ai.google.dev/gemini-api/docs/image-generation
- https://ai.google.dev/gemini-api/docs/deprecations

