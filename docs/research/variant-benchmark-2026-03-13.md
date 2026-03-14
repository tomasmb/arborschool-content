# Research: Controlled Variant Benchmark (2026-03-13)

## Objetivo

Confirmar con evidencia local la recomendación provisional:

- planning + generación con Gemini;
- gate semántico/estructural independiente con OpenAI `gpt-5.4`;
- no congelar stack final para preguntas con imagen hasta implementar gate visual real.

## Corpus observado

Baseline persistido en `app/data/pruebas/old_variants/prueba-invierno-2025`:

- 81 variantes observadas.
- 23 aprobadas.
- 58 rechazadas.
- 0 fallas de feedback pipeline persistidas en `validation_result.json`.

Distribución de gates persistidos:

- constructo: 33 pass / 48 fail
- dificultad: 27 pass / 54 fail
- answer_correct: 55 pass / 26 fail
- non_mechanizable: 53 pass / 28 fail
- imagen: 51 `not_applicable`, 29 `not_implemented`, 1 `unknown`

Lectura principal: incluso antes del benchmark cruzado, el cuello de botella ya estaba en
constructo y dificultad, no en cálculo de respuesta.

## Benchmark controlado

Se tomó una muestra balanceada del corpus existente:

- preguntas: `Q1,Q11,Q12,Q13,Q14`
- 2 variantes por pregunta
- total: 10 variantes

Se revalidó exactamente el mismo corpus con `app/question_variants/revalidate_benchmark.py`
usando OpenAI `gpt-5.4` como validador semántico.

### Resultado OpenAI `gpt-5.4`

- variantes vistas: 10
- aprobadas por OpenAI: 1
- rechazadas por OpenAI: 9
- aprobadas originalmente en el corpus: 9
- rechazadas originalmente en el corpus: 1
- acuerdo con la etiqueta original: 2/10
- desacuerdo con la etiqueta original: 8/10

Distribución de gates en la muestra:

- constructo: 5 pass / 5 fail
- dificultad: 3 pass / 7 fail
- answer_correct: 10 pass / 0 fail
- non_mechanizable: 8 pass / 2 fail
- imagen: 8 `not_applicable`, 2 `not_implemented`

### Interpretación

OpenAI `gpt-5.4` fue mucho más estricto que la validación persistida del corpus y rechazó
principalmente por:

- drift de constructo;
- aumento o cambio no permitido de dificultad;
- calidad estructural del ítem (por ejemplo, distractores poco plausibles).

No rechazó por corrección matemática en la muestra balanceada: `answer_correct` pasó en 10/10.

Eso es consistente con la hipótesis de trabajo: el problema principal no es "resolver bien la
cuenta", sino mantener el mismo constructo con dificultad controlada y sin mecanización.

## Evidencia end-to-end adicional

Se ejecutó una corrida aislada `Gemini->Gemini` en:

- `app/data/.question_variants_runs/benchmark-2026-03-13/gemini-gemini/`

Resumen:

- 15 variantes generadas
- 5 aprobadas
- 10 rechazadas
- tasa de aprobación: 33,3%

Distribución de gates persistidos:

- constructo: 9 pass / 6 fail
- dificultad: 8 pass / 7 fail
- answer_correct: 8 pass / 7 fail
- non_mechanizable: 15 pass / 0 fail
- imagen: 10 `not_applicable`, 5 `not_implemented`

Desglose por pregunta:

- `Q1`: 2/3 aprobadas
- `Q11`: 0/3 aprobadas
- `Q12`: 2/3 aprobadas
- `Q13`: 1/3 aprobadas
- `Q14`: 0/3 aprobadas

Además de los rechazos semánticos, la corrida mostró fallas estructurales concretas:

- SVG embebido inválido para el schema QTI.
- contaminación de opciones con texto de feedback.
- variantes con referencia a gráficos que no quedaron realmente incluidos o descargables.

Estas fallas refuerzan la necesidad de gates más duros y de mantener la generación masiva
separada de la evidencia de benchmark.

## Recomendación

### Decisión de stack

- Mantener Gemini para planning + generación, de forma provisional.
- Mover el gate semántico principal a OpenAI `gpt-5.4`.
- Tratar el veredicto OpenAI como bloqueante para constructo/dificultad/no mecanizable.

### Condiciones para corrida completa

No recomendar todavía una full run de 4 pruebas con imágenes como stack "cerrado" hasta cumplir:

1. Implementar gate visual real para variantes con imagen.
2. Corregir generación QTI cuando aparezcan `svg` no permitidos u opciones contaminadas con feedback.
3. Repetir benchmark controlado con muestra más grande y QA humano ciego.

## Conclusión

La evidencia local disponible favorece claramente un esquema:

- Gemini genera.
- OpenAI `gpt-5.4` gatea.

Pero esa recomendación es sólida sólo para el gate semántico textual. Para preguntas con imagen,
el stack sigue siendo provisional hasta cerrar Gate F.
