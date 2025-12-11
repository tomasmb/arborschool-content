# Agenda de Cambios Manuales a Resultados de Tests

Este archivo documenta todos los cambios manuales realizados a los átomos generados automáticamente en los tests de generación.

## Estructura

Para cada eje temático, se documentan:
- Cambios realizados (fecha, descripción, razón)
- Átomos afectados
- Validación post-cambio

---

## Átomos - Eje 1: Números (M1-NUM)

### Estándar: M1-NUM-01 - Números Enteros y Racionales

**Archivo base**: `tests/atoms/generacion_automatica/atoms_M1_NUM_01_final_test.json`  
**Archivo con cambios manuales**: `tests/atoms/cambios_manuales/atoms_M1_NUM_01_cambios_manuales.json`

**Fecha de generación inicial**: 2025-12-09 (v23)  
**Fecha de cambios manuales**: 2025-12-09

**Cambios realizados**:

#### Cambio 1: Agregar prerrequisito A-01 a átomos de operatoria en Z

**Fecha**: 2025-12-09  
**Tipo**: Agregar prerrequisitos  
**Razón**: Los átomos de operatoria en enteros (suma, resta) requieren el concepto base de números enteros como prerrequisito explícito, no solo el valor absoluto.

**Átomos afectados**:
- **A-M1-NUM-01-04** (Suma de Enteros de Igual Signo)
  - Antes: `["A-M1-NUM-01-03"]`
  - Después: `["A-M1-NUM-01-01", "A-M1-NUM-01-03"]`
  
- **A-M1-NUM-01-05** (Suma de Enteros de Distinto Signo)
  - Antes: `["A-M1-NUM-01-03", "A-M1-NUM-01-04"]`
  - Después: `["A-M1-NUM-01-01", "A-M1-NUM-01-03", "A-M1-NUM-01-04"]`
  
- **A-M1-NUM-01-06** (Resta de Números Enteros)
  - Antes: `["A-M1-NUM-01-04", "A-M1-NUM-01-05"]`
  - Después: `["A-M1-NUM-01-01", "A-M1-NUM-01-04", "A-M1-NUM-01-05"]`

**Fuente**: Validación OpenAI - identificó que faltaba el concepto base de enteros como prerrequisito explícito.

---

#### Cambio 2: Ampliar prerrequisitos de A-29 (Evaluación de Argumentos)

**Fecha**: 2025-12-09  
**Tipo**: Ampliar prerrequisitos  
**Razón**: El átomo tiene alcance general ("evaluación de argumentos y procedimientos en Z y Q en general") pero tenía solo 4 prerrequisitos limitados. Se amplió para cubrir todas las operaciones y comparaciones necesarias para evaluar argumentos en general.

**Átomo afectado**:
- **A-M1-NUM-01-29** (Evaluación de Argumentos y Procedimientos en Z y Q)
  - Antes: `["A-M1-NUM-01-02", "A-M1-NUM-01-07", "A-M1-NUM-01-15", "A-M1-NUM-01-19"]` (4 átomos)
  - Después: `["A-M1-NUM-01-02", "A-M1-NUM-01-04", "A-M1-NUM-01-05", "A-M1-NUM-01-06", "A-M1-NUM-01-07", "A-M1-NUM-01-08", "A-M1-NUM-01-14", "A-M1-NUM-01-15", "A-M1-NUM-01-16", "A-M1-NUM-01-17", "A-M1-NUM-01-18", "A-M1-NUM-01-19", "A-M1-NUM-01-20", "A-M1-NUM-01-21", "A-M1-NUM-01-22"]` (15 átomos)

**Fuente**: Validación OpenAI - identificó que los prerrequisitos eran insuficientes para el alcance declarado del átomo.

---

**Resumen de cambios**:
- Total de átomos modificados: 16 (A-04, A-05, A-06, A-17, A-18, A-19, A-20, A-21, A-22, A-23, A-24, A-25, A-26, A-28, A-29 dos veces)
- Tipo de cambios: Solo prerrequisitos (agregar/ampliar)
- Validación post-cambio: Pendiente (ver sección "Cambio 4")

---

#### Validación Post-Cambio

**Fecha**: 2025-12-09  
**Evaluador**: Gemini (usando prompt de validación actualizado)

**Resultados**:
- **Total átomos**: 29
- **Átomos pasando todos los checks**: 28/29 (96.6%)
- **Átomos con problemas**: 1
- **Calidad general**: excellent
- **Cobertura**: complete
- **Granularidad**: appropriate

**Problema identificado**:
- **A-M1-NUM-01-29** (Evaluación de Argumentos):
  - **Tipo**: Prerrequisitos incompletos
  - **Detalle**: Faltan los átomos de operaciones con decimales (A-23 a A-26) en los prerrequisitos, a pesar de que el átomo evalúa argumentos en "números racionales" que incluyen decimales.
  - **Recomendación**: Agregar A-M1-NUM-01-23, A-M1-NUM-01-24, A-M1-NUM-01-25 y A-M1-NUM-01-26 a la lista de prerrequisitos.

**Nota**: Este problema fue identificado después de aplicar los cambios iniciales.

---

#### Cambio 3: Agregar operaciones con decimales a prerrequisitos de A-29

**Fecha**: 2025-12-09  
**Tipo**: Agregar prerrequisitos  
**Razón**: El átomo evalúa argumentos en "números racionales" que incluyen tanto fracciones como decimales, por lo que debe incluir las operaciones con decimales en sus prerrequisitos.

**Átomo afectado**:
- **A-M1-NUM-01-29** (Evaluación de Argumentos y Procedimientos en Z y Q)
  - Antes: 15 prerrequisitos (sin operaciones con decimales)
  - Después: 19 prerrequisitos (incluyendo A-23, A-24, A-25, A-26)

**Fuente**: Validación Gemini post-cambio inicial - identificó que faltaban operaciones con decimales.

**Comparación con versión automática**:
- Los cambios de prerrequisitos mejoraron la evaluación de A-04, A-05, A-06 (ahora pasan todos los checks)
- A-29 mejoró completamente: de "good" con warning a "excellent" con pass en prerrequisitos

---

#### Validación Post-Cambio Final

**Fecha**: 2025-12-09  
**Evaluador**: Gemini (usando prompt de validación actualizado)

**Resultados**:
- **Total átomos**: 29
- **Átomos pasando todos los checks**: 19/29 (65.5%)
- **Átomos con problemas**: 10
- **Calidad general**: good
- **Cobertura**: complete
- **Granularidad**: appropriate

**A-29**: ✅ **RESUELTO COMPLETAMENTE**
- Score: good → **excellent**
- Prerrequisitos: warning → **pass**
- Sin problemas identificados

**Cambios aplicados - Prerrequisitos de operaciones con enteros**:

El evaluador identificó que varios átomos de fracciones y decimales necesitan prerrequisitos directos de operaciones con enteros porque operan con numeradores/denominadores o partes enteras que pueden ser negativos. Estos NO son transitivos porque la cadena A-17 → A-10 → A-09 → A-01 solo proporciona el concepto de enteros, no las operaciones.

**Átomos modificados**:
- **A-17** (Suma de Fracciones de Igual Denominador): Agregados A-04, A-05 (suma/sustracción de enteros para numeradores negativos)
- **A-18** (Resta de Fracciones de Igual Denominador): Agregado A-06 (sustracción de enteros)
- **A-19** (Suma de Fracciones de Distinto Denominador): Agregados A-04, A-05 (operaciones con enteros para numeradores)
- **A-20** (Resta de Fracciones de Distinto Denominador): Agregado A-06 (sustracción de enteros)
- **A-21** (Multiplicación de Fracciones): Agregado A-07 (multiplicación de enteros para regla de signos)
- **A-22** (División de Fracciones): Agregado A-08 (división de enteros para regla de signos)
- **A-23** (Suma de Números Decimales): Agregado A-05 (suma de enteros si hay decimales de distinto signo)
- **A-24** (Resta de Números Decimales): Agregado A-06 (sustracción de enteros si hay decimales negativos)
- **A-25** (Multiplicación de Números Decimales): Agregado A-07 (multiplicación de enteros para regla de signos)
- **A-26** (División de Números Decimales): Agregado A-08 (división de enteros para regla de signos)
- **A-28** (Resolución de Problemas Contextuales con Racionales): Agregados A-04, A-05, A-06, A-07, A-08 (enlace explícito a operaciones en Z)

**Razón**: Estos átomos operan directamente con enteros (numeradores, denominadores, partes enteras de decimales) y necesitan las operaciones con enteros como prerrequisito directo, no solo el concepto transitivo.

**Nota sobre transitividad**:
Se agregó una regla explícita al prompt de validación (`app/atoms/validation.py`) que instruye al evaluador a NO marcar como problema si falta un prerrequisito transitivo, solo si falta un prerrequisito directo. En este caso, las operaciones con enteros son prerrequisitos directos porque se usan explícitamente en los algoritmos de fracciones/decimales.

**Fuente**: Validación Gemini con regla de transitividad - identificó que faltaban prerrequisitos directos de operaciones con enteros en átomos que operan con numeradores/denominadores o partes enteras de decimales.

---

#### Cambio 4: Agregar prerrequisitos de operaciones con enteros a A-09 para transitividad

**Fecha**: 2025-12-09  
**Tipo**: Agregar prerrequisitos a punto común de la cadena  
**Razón**: Si casi todos los átomos de fracciones y decimales necesitan operaciones con enteros, entonces tiene sentido agregar esas operaciones a un punto común en la cadena de dependencias para que se propague transitivamente. A-09 (Concepto de Racionales) es el punto común porque:
- Todos los átomos de fracciones dependen de A-09 (a través de A-10)
- Todos los átomos de decimales dependen directamente de A-09
- Todos los 10 átomos que necesitan operaciones con enteros (A-17 a A-26) dependen transitivamente de A-09

**Átomo afectado**: 
- **A-09** (Concepto de Números Racionales): Agregados A-04, A-05, A-06, A-07, A-08 (todas las operaciones con enteros)

**Beneficio**: 
- Respeto de la transitividad: Los átomos que necesitan operaciones con enteros (A-17 a A-26) ahora tienen acceso transitivo a través de A-09
- No es necesario agregar prerrequisitos individuales a cada átomo
- Solución más elegante y pedagógicamente coherente: antes de trabajar con racionales, necesitas saber operar con enteros

**Validación post-cambio**:
- **Total átomos**: 29
- **Átomos pasando todos los checks**: 29/29 (100%)
- **Átomos con problemas**: 0
- **Calidad general**: excellent (mejoró de "good")
- **Cobertura**: complete
- **Granularidad**: appropriate

**Resultado**: ✅ **ÉXITO COMPLETO** - Todos los problemas de prerrequisitos resueltos mediante transitividad.

---

## Átomos - Eje 2: Álgebra y Funciones (M1-ALG)

<!-- Sección para futuros ejes -->

---

## Átomos - Eje 3: Geometría (M1-GEO)

<!-- Sección para futuros ejes -->

---

## Átomos - Eje 4: Probabilidad y Estadística (M1-PROB)

---

## Átomos - Eje 2: Álgebra y Funciones (M1-ALG)

### Estándar: M1-ALG-01 - Expresiones Algebraicas

**Archivo base**: `tests/atoms/generacion_automatica/atoms_M1_ALG_01_test.json`  
**Archivo con cambios manuales**: `tests/atoms/cambios_manuales/atoms_M1_ALG_01_cambios_manuales.json`

**Fecha de generación inicial**: 2025-12-09  
**Fecha de cambios manuales**: 2025-12-09

**Cambios realizados**:

#### Cambio 1: Expandir A-05 para cubrir suma/resta de polinomios completa

**Fecha**: 2025-12-09  
**Tipo**: Expansión de cobertura  
**Razón**: El estándar menciona explícitamente "Suma y resta de monomios y polinomios" como subcontenido clave, pero el átomo A-05 solo cubría "Reducción de términos semejantes", que es parte del proceso pero no la operación completa. La operación completa requiere manejo de paréntesis, aplicación de signos (distributiva del signo), y luego reducción de términos semejantes.

**Átomo afectado**:
- **A-M1-ALG-01-05** (Suma y resta de polinomios)
  - **Título**: Cambiado de "Reducción de términos semejantes" a "Suma y resta de polinomios"
  - **Descripción**: Expandida para incluir eliminación de paréntesis, aplicación de signos, y reducción de términos semejantes
  - **Criterios**: Agregados criterios sobre eliminación de paréntesis y aplicación de signos
  - **Ejemplos**: Actualizados para mostrar operaciones completas con paréntesis
  - **Notas**: Actualizadas para reflejar que cubre la operación completa

**Fuente**: Validación OpenAI - identificó que faltaba cobertura explícita de suma/resta de polinomios como operación completa.

---

#### Cambio 2: Agregar prerrequisitos de productos notables y factorización a A-21

**Fecha**: 2025-12-09  
**Tipo**: Agregar prerrequisitos  
**Razón**: A-21 (Problemas contextualizados) es un átomo integrador que requiere aplicar productos notables (para problemas de áreas) y factorización (para simplificación) en problemas típicos del estándar. Aunque A-08 (multiplicación) puede depender de productos notables, los problemas contextualizados requieren estos conocimientos directamente.

**Átomo afectado**:
- **A-M1-ALG-01-21** (Resolución de problemas contextualizados)
  - **Antes**: `["A-M1-ALG-01-02", "A-M1-ALG-01-04", "A-M1-ALG-01-08"]`
  - **Después**: Agregados A-11 a A-19 (productos notables: A-11, A-12, A-13, A-14; factorización: A-16, A-17, A-18, A-19)

**Fuente**: Validación Gemini - identificó que faltaban prerrequisitos directos de factorización y productos notables para problemas contextualizados típicos del estándar.

---

#### Cambio 3: Dividir A-16 en dos átomos (Factor común monomio y polinomio)

**Fecha**: 2025-12-09  
**Tipo**: División de átomo por granularidad  
**Razón**: El estándar lista dos subcontenidos_clave separados:
- "Factorización por factor común monomio"
- "Factorización por factor común compuesto (polinomio)"

El modelo original combinó ambos en un solo átomo (A-16), pero deben ser átomos separados porque:
- Requieren estrategias cognitivas diferentes (identificar monomio común vs. reconocer polinomio completo como factor común)
- Pueden evaluarse independientemente
- El estándar los lista como elementos separados

**Átomos afectados**:
- **A-M1-ALG-01-16** (originalmente "Factorización por factor común")
  - **Nuevo**: "Factorización por factor común monomio"
  - Prerrequisitos: `["A-M1-ALG-01-09"]`
  
- **A-M1-ALG-01-17** (nuevo átomo)
  - **Título**: "Factorización por factor común compuesto (polinomio)"
  - Prerrequisitos: `["A-M1-ALG-01-16"]` (monomio antes de polinomio)

**Renumeración resultante**:
- A-17 → A-18: Factorización de diferencia de cuadrados
- A-18 → A-19: Factorización de trinomio cuadrado perfecto
- A-19 → A-20: Factorización de trinomios de la forma x^2+bx+c
- A-20 → A-21: Simplificación de expresiones algebraicas racionales simples
- A-21 → A-22: Resolución de problemas contextualizados con expresiones algebraicas

**Prerrequisitos actualizados**:
- A-21 (Simplificación): Agregado A-20 a la lista de prerrequisitos
- A-22 (Problemas contextualizados): Agregado A-20 a la lista de prerrequisitos

**Fuente**: Validación Gemini y OpenAI - identificaron que A-16 combinaba dos subcontenidos_clave separados que requieren estrategias cognitivas diferentes y pueden evaluarse independientemente.

---

## Átomos - Eje 3: Geometría (M1-GEO)

### Estándar: M1-GEO-01 - Geometría Plana: Teorema de Pitágoras, Perímetros y Áreas

**Archivo base**: `tests/atoms/generacion_automatica/atoms_M1_GEO_01_test.json`  
**Archivo con cambios manuales**: `tests/atoms/cambios_manuales/atoms_M1_GEO_01_cambios_manuales.json`

**Fecha de generación inicial**: 2025-12-09  
**Fecha de cambios manuales**: 2025-12-09

**Cambios realizados**:

#### Cambio 1: Agregar prerrequisito A-04 a A-13 (Problemas integrados)

**Fecha**: 2025-12-09  
**Tipo**: Agregar prerrequisitos  
**Razón**: El átomo A-13 (Resolución de problemas integrados de perímetro y área) requiere el uso del Teorema de Pitágoras como paso intermedio para calcular dimensiones faltantes antes de calcular área o perímetro. Muchos problemas integrados requieren calcular primero un lado faltante usando Pitágoras.

**Átomo afectado**:
- **A-M1-GEO-01-13** (Resolución de problemas integrados de perímetro y área)
  - **Antes**: `["A-M1-GEO-01-05", "A-M1-GEO-01-06", "A-M1-GEO-01-07", "A-M1-GEO-01-08", "A-M1-GEO-01-09", "A-M1-GEO-01-10", "A-M1-GEO-01-11", "A-M1-GEO-01-12"]`
  - **Después**: Agregado `A-M1-GEO-01-04` (Modelado de situaciones con Teorema de Pitágoras)

**Fuente**: Validación Gemini - identificó que faltaba el prerrequisito de modelado con Pitágoras para problemas donde no se dan todas las dimensiones explícitamente.

---

## Átomos - Eje 4: Probabilidad y Estadística (M1-PROB)

### Estándar: M1-PROB-01 - Representación de Datos y Medidas de Tendencia Central

**Archivo base**: `tests/atoms/generacion_automatica/atoms_M1_PROB_01_test.json`  
**Archivo con cambios manuales**: `tests/atoms/cambios_manuales/atoms_M1_PROB_01_cambios_manuales.json`

**Fecha de generación inicial**: 2025-12-09  
**Fecha de cambios manuales**: 2025-12-09

**Cambios realizados**:

#### Cambio 1: Quitar prerrequisito restrictivo de A-09 (Construcción de gráficos de línea)

**Fecha**: 2025-12-09  
**Tipo**: Ajustar prerrequisitos  
**Razón**: El prerrequisito A-M1-PROB-01-02 (Cálculo de frecuencia absoluta) restringe innecesariamente el gráfico de línea a datos de frecuencia, cuando este gráfico suele usarse también para variables continuas o series de tiempo dadas directamente (sin conteo previo). Los gráficos de línea no siempre requieren cálculo previo de frecuencias.

**Átomo afectado**:
- **A-M1-PROB-01-09** (Construcción de gráficos de línea)
  - **Antes**: `["A-M1-PROB-01-02", "A-M1-PROB-01-07"]`
  - **Después**: `["A-M1-PROB-01-07"]` (solo características del gráfico de línea)

**Fuente**: Validación Gemini - identificó que el prerrequisito era demasiado restrictivo para el uso general de gráficos de línea.

---

#### Cambio 2: Expandir A-12 para incluir comprensión del proceso de construcción

**Fecha**: 2025-12-09  
**Tipo**: Expansión de cobertura  
**Razón**: El estándar menciona "construcción de gráficos circulares" en los subcontenidos_clave, pero el átomo A-12 solo cubría el cálculo matemático de ángulos. Sin embargo, dado que la PAES M1 es una prueba de selección múltiple, no se requiere construcción física manual con compás y transportador. El átomo debe cubrir el cálculo de ángulos (evaluable en selección múltiple) y la comprensión del proceso de construcción, pero no el trazado físico.

**Átomo afectado**:
- **A-M1-PROB-01-12** (originalmente "Cálculo de ángulos para gráficos circulares")
  - **Título nuevo**: "Cálculo de ángulos para construcción de gráficos circulares"
  - **Descripción**: Expandida para incluir cálculo de ángulos Y comprensión del proceso de construcción
  - **Criterios agregados**:
    - Identifica los pasos del proceso de construcción de un gráfico circular (cálculo de ángulos, trazado de sectores, etiquetado)
    - Relaciona correctamente los ángulos calculados con las proporciones representadas en el gráfico circular
  - **Ejemplos conceptuales**: Actualizados para enfocarse en cálculo y comprensión del proceso
  - **Notas de alcance**: Actualizadas para reflejar que se enfoca en cálculo y comprensión, no en construcción física manual

**Fuente**: Validación Gemini - identificó que faltaba la construcción procedimental de gráficos circulares. Ajustado para contexto de selección múltiple (no requiere construcción física manual).

---

## Notas Generales

- Todos los cambios manuales deben documentarse aquí
- Antes de hacer cambios, verificar que no rompan dependencias
- Después de cambios, ejecutar validación con `python -m app.atoms.validate_atoms`

