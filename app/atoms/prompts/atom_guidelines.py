"""Atom granularity guidelines for learning atom generation.

These guidelines define what makes a good learning atom and when to split
atoms into smaller units.
"""

from __future__ import annotations

ATOM_GRANULARITY_GUIDELINES = """
## Criterios de Granularidad Atómica

Un átomo debe cumplir TODOS estos criterios. Si falla en CUALQUIERA, debe dividirse:

1. **Una sola intención cognitiva**: Cada átomo debe tener exactamente una
   intención cognitiva clara y específica. Si el título o descripción menciona
   "y" o "y/o" conectando dos conceptos distintos, probablemente deba dividirse.

2. **Carga de memoria de trabajo razonable**: No debe requerir más de ~4
   piezas novedosas de información a manipular simultáneamente. Si los
   criterios_atomicos requieren dominar múltiples algoritmos, procedimientos
   o conceptos independientes, DEBE dividirse. Cada algoritmo o procedimiento
   distinto cuenta como una pieza novedosa.

3. **Independencia de prerrequisitos**: Si la parte A debe aprenderse antes
   que la parte B (secuencia pedagógica natural), deben ser átomos separados
   con un prerrequisito explícito. Pregúntate: ¿puede un estudiante aprender
   B sin haber dominado A primero?

4. **Independencia de evaluación** (CRÍTICO): Si un profesor puede evaluar
   dos partes por separado con diferentes preguntas o rúbricas, DEBEN ser
   átomos separados. Este es el criterio más importante. Pregúntate:
   - ¿Puedo crear una pregunta de evaluación solo para la parte A?
   - ¿Puedo crear una pregunta de evaluación solo para la parte B?
   - ¿Las rúbricas de evaluación son diferentes?
   - ¿Requieren estrategias cognitivas diferentes? (ej: una parte es conceptual
     y otra procedimental, o una usa método A y otra método B)
   Si la respuesta es SÍ a cualquiera, son átomos separados.

5. **Límite de generalización**: Si dos habilidades se generalizan
   diferentemente en distintos contextos (una funciona en un dominio pero la
   otra no), no deben estar en el mismo átomo.

6. **Átomos integradores**: Si un átomo pretende "integrar" o "combinar"
   múltiples conceptos, procedimientos o habilidades que ya fueron cubiertos
   en otros átomos, debe ser extremadamente cuidadoso. Un átomo integrador
   solo es válido si:
   - Tiene una intención cognitiva única (ej: "aplicar jerarquía de operaciones")
   - No sobrecarga la memoria de trabajo (≤4 piezas novedosas)
   - Puede evaluarse con una rúbrica específica
   - NO simplemente "mezcla" múltiples procedimientos sin una intención unificada
   - **PRERREQUISITOS EXHAUSTIVOS**: Si requiere aplicar múltiples operaciones,
     conceptos o procedimientos, DEBE incluir TODOS los prerrequisitos necesarios.
     No omitas prerrequisitos porque parecen "obvios" o porque el átomo es
     "integrador". Si requiere A, B y C, lista explícitamente los átomos que
     cubren A, B y C.

   Si un átomo requiere más de 3-4 prerrequisitos complejos, probablemente
   esté intentando integrar demasiado y deba dividirse.

## Preguntas clave antes de combinar conceptos en un átomo

Antes de crear un átomo que combine dos conceptos (ej: "X e Y"), pregúntate:

1. ¿Puedo evaluar X sin evaluar Y? → Si SÍ, son átomos separados.
2. ¿Puedo evaluar Y sin evaluar X? → Si SÍ, son átomos separados.
3. ¿X debe aprenderse antes que Y? → Si SÍ, son átomos separados con prerrequisito.
4. ¿Los estudiantes recuerdan X e Y como una unidad o por separado? → Si por
   separado, son átomos separados.
5. ¿X e Y requieren diferentes rúbricas de evaluación? → Si SÍ, son átomos separados.

Si CUALQUIERA de estas respuestas es SÍ, crea átomos separados.

## Casos especiales: Conceptos relacionados pero evaluables por separado

Dos conceptos que están relacionados (inversos, complementarios, o que comparten
reglas/procedimientos comunes) DEBEN ser átomos separados si pueden evaluarse
independientemente, incluso si:
- Comparten reglas, principios o procedimientos comunes
- Son conceptualmente relacionadas o complementarias
- Se enseñan típicamente en secuencia cercana
- Parecen "parte del mismo tema"

Razón fundamental: Si pueden evaluarse por separado con diferentes preguntas o
rúbricas, son átomos separados. El hecho de compartir elementos comunes NO
justifica combinarlos en un solo átomo.

Principio general: La evaluación independiente es el criterio decisivo, no la
relación conceptual o la proximidad pedagógica.

## Ejemplos de buenos átomos (granularidad apropiada)

- Átomos con una sola intención cognitiva clara
- Átomos que pueden evaluarse con una pregunta o rúbrica específica
- Átomos que requieren ≤4 piezas novedosas de información
- Variaciones de un mismo concepto que requieren evaluación diferente
  (ej: "X con condición A" vs "X con condición B" si se evalúan por separado)

## Ejemplos de átomos demasiado grandes (deben dividirse)

- "Entender todo sobre [tema amplio]"
  → Dividir en conceptos más específicos que puedan evaluarse independientemente

- "[Concepto amplio] y [otro concepto amplio]"
  → Si cada parte puede evaluarse por separado, dividir

- "[Concepto A] y [Concepto B]" (si se pueden evaluar por separado)
  → Dividir en: "[Concepto A]" y "[Concepto B]" como átomos separados

- "Concepto y aplicación de [X]"
  → Dividir en: "Concepto de [X]" y "Aplicación de [X]"

- Átomos que requieren múltiples algoritmos o procedimientos distintos
  → Cada algoritmo/procedimiento distinto generalmente debe ser un átomo separado

- Átomos "integradores" que mezclan muchos conceptos previos sin una intención
  cognitiva unificada clara → Dividir en átomos más específicos

- Cualquier átomo cuyo título tenga "y" o "y/o" conectando dos conceptos,
  procedimientos o habilidades que puedan evaluarse independientemente.
"""
