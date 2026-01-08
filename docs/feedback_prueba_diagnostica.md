# Feedback: Prueba Diagnóstica PAES M1

**Fecha:** 2026-01-06  
**Tipo:** Observaciones y preguntas para explorar

---

## Observación 1: Átomo-level vs Score-level

El research trata bien el factor "suerte" (guessing) para predecir el puntaje global, pero me quedé pensando en qué pasa a nivel de átomos individuales.

Si un estudiante responde correctamente una pregunta, ¿lo marcamos como que "sabe" ese átomo? ¿Qué pasa si simplemente adivinó? Con 4 alternativas hay 25% de chance de acertar sin saber.

Quizás no es un problema grave, pero vale la pena pensarlo dado que queremos usar los átomos para armar planes de estudio personalizados.

---

## Idea: Botón "No lo sé"

Una forma de reducir el ruido del azar podría ser darle al estudiante la opción de decir "No lo sé" en lugar de forzarlo a elegir una alternativa.

Algunas preguntas que surgieron:
- ¿Cambiaría mucho la experiencia del estudiante?
- ¿Los estudiantes lo usarían o seguirían adivinando igual?
- ¿Cómo afectaría la predicción del puntaje PAES si algunos responden "no sé"?

Podría ser interesante explorar qué hacen otros tests diagnósticos con esto.

---

## Reflexión: ¿Binario o probabilístico?

Para armar el plan de estudio necesitamos decidir qué átomos enseñar. Esto me llevó a preguntarme:

**¿Necesitamos realmente probabilidades por átomo?**

Si el objetivo es "qué enseñar", quizás basta con ser conservadores: si hay duda sobre si sabe un átomo, asumir que no lo sabe y enseñarlo. El costo de enseñar algo que ya sabe es bajo comparado con no enseñar algo que necesita.

Pero también podría haber valor en tener más matices... no sé. Depende de cómo se use después.

---

## Dato potencialmente útil

Si se implementa algo como "No lo sé", podría ser interesante distinguir:
- Respondió incorrectamente → quizás tiene una misconception
- Dijo "no lo sé" → simplemente no sabe

Esto podría informar *cómo* enseñar, no solo *qué* enseñar. Pero es solo una idea.

---

## Resumen

Básicamente son dos temas para pensar:

1. **El gap átomo vs score:** el manejo del azar está bien pensado para el puntaje, pero ¿aplica igual para el diagnóstico por átomo?

2. **Alternativa "No lo sé":** podría ser una forma simple de obtener datos más limpios sin modelos complejos.

Nada urgente, solo cosas que me quedaron dando vueltas.
