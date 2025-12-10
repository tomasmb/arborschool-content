# Issues Pendientes - Segunda Validación

**Fecha**: 2025-12-10  
**Total issues pendientes**: 4 (todos "warning")

## Issues por Estándar

### M1-ALG-06 (2 issues)

#### Issue 1: A-M1-ALG-06-01 - Granularidad
**Categoría**: Granularidad (warning)  
**Problema**: Agrupa estrategias cognitivas distintas: 'Factor común' (para ecuaciones incompletas ax²+bx=0) y 'Factorización de trinomios' (para completas) suelen requerir procesos de reconocimiento de patrones distintos.

**Acción requerida**: Evaluar si deben separarse en dos átomos distintos según las reglas de granularidad (independencia de evaluación, estrategias cognitivas diferentes).

---

#### Issue 2: A-M1-ALG-06-09 - Granularidad
**Categoría**: Granularidad (warning)  
**Problema**: Alta carga cognitiva: Analizar simultáneamente los efectos de 'a', 'b' y 'c' es denso. El análisis de 'b' (desplazamiento horizontal/simetría) es significativamente más complejo que 'c' (vertical) y 'a' (forma).

**Acción requerida**: Evaluar si el análisis de parámetros debe dividirse en átomos más pequeños (ej: análisis de 'a', análisis de 'b', análisis de 'c') o si la carga cognitiva es aceptable para un átomo integrador.

---

### M1-GEO-01 (2 issues)

#### Issue 3: A-M1-GEO-01-05 - Granularidad
**Categoría**: Granularidad (warning)  
**Problema**: Mezcla dos estrategias cognitivas distintas: el algoritmo general de suma de lados (iterativo) y el uso de fórmulas simplificadas basadas en propiedades (multiplicativo, ej: 4L). Aunque el resultado es el mismo, la abstracción es diferente.

**Acción requerida**: Evaluar si deben separarse según las reglas de granularidad (independencia de evaluación, estrategias cognitivas diferentes).

---

#### Issue 4: A-M1-GEO-01-08 - Completitud
**Categoría**: Completitud (warning)  
**Problema**: La descripción lista 'cuadrados, rectángulos y romboides' pero omite 'rombos'. Aunque el rombo es un paralelogramo y la fórmula b*h aplica, la omisión explícita puede generar confusión dado que existe un átomo separado (A-09) para rombos con diagonales.

**Acción requerida**: Agregar 'rombos' a la descripción y criterios atómicos de A-08 para mayor claridad, o justificar por qué se omite explícitamente.

---

## Notas

- Todos los issues de **prerrequisitos** fueron corregidos aplicando transitividad.
- Los issues de **M1-GEO-03** (A-07, A-08, A-10, A-11) fueron identificados como **falsos positivos** (limitaciones intencionales de procedimientos, mientras que los conceptos son generales).
- Los issues de **M1-NUM-01** y **M1-NUM-03** relacionados con prerrequisitos fueron corregidos.

