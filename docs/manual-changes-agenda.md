# Agenda de Cambios Manuales

Este archivo documenta todos los cambios manuales realizados a los átomos generados automáticamente.

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

<!-- Sección para futuros ejes -->

---

## Notas Generales

- Todos los cambios manuales deben documentarse aquí
- Antes de hacer cambios, verificar que no rompan dependencias
- Después de cambios, ejecutar validación con `python -m app.atoms.validate_atoms`

