# Agenda de Cambios Manuales - Versión Final

Este archivo documenta todos los cambios manuales realizados a los átomos en el archivo canónico `app/data/atoms/paes_m1_2026_atoms.json`.

## Propósito

Este archivo registra modificaciones manuales aplicadas después de la generación automática inicial, incluyendo:
- Corrección de errores detectados en validación
- Agregado de átomos faltantes
- Ajuste de prerrequisitos
- Correcciones de coherencia y granularidad

---

## Átomos - Eje 1: Números (M1-NUM)

### Estándar: M1-NUM-01 - Números Enteros y Racionales

**Fecha de cambios**: 2025-12-10

#### Cambio 1: Agregar A-M1-NUM-01-02 (Representación y Orden de Enteros en la Recta Numérica)

**Fecha**: 2025-12-10  
**Tipo**: Agregar átomo faltante  
**Razón**: 
- El estándar M1-NUM-01 incluye explícitamente "Orden de números enteros en la recta numérica" como subcontenido clave
- A-M1-NUM-01-04 (Adición de números enteros) requiere A-M1-NUM-01-02 como prerrequisito, pero el átomo no existía en el archivo canónico
- A-M1-NUM-01-02 y A-M1-NUM-01-03 son complementarios:
  - A-02: Representación y orden básico en recta numérica (concepto_procedimental)
  - A-03: Comparación con justificación usando recta numérica (procedimiento)

**Átomo agregado**:
- **ID**: `A-M1-NUM-01-02`
- **Título**: "Representación y Orden de Enteros en la Recta Numérica"
- **Tipo**: `concepto_procedimental`
- **Habilidad principal**: `representar`
- **Prerrequisitos**: `["A-M1-NUM-01-01"]`
- **Criterios atómicos**:
  - Ubica correctamente números enteros positivos y negativos en la recta numérica
  - Determina qué número es mayor o menor observando su posición en la recta numérica
  - Ordena una secuencia de números enteros de forma ascendente o descendente

**Cambio adicional**:
- **A-M1-NUM-01-03** (Orden y comparación de números enteros):
  - **Antes**: `prerrequisitos: ["A-M1-NUM-01-01"]`
  - **Después**: `prerrequisitos: ["A-M1-NUM-01-01", "A-M1-NUM-01-02"]`
  - **Razón**: A-03 requiere la representación en recta numérica (A-02) antes de poder comparar y justificar

**Fuente**: 
- Validación de circular dependencies identificó que A-M1-NUM-01-04 tenía un prerrequisito inválido (A-M1-NUM-01-02 no existía)
- Análisis del estándar confirmó que el átomo debería existir
- Verificación de coherencia confirmó que no hay duplicación con A-03

---

### Estándar: M1-NUM-03 - Potencias y Raíces Enésimas

**Fecha de cambios**: 2025-12-10

#### Cambio 1: Expandir átomos A-02 a A-06 para incluir exponentes racionales

**Fecha**: 2025-12-10  
**Tipo**: Expansión de cobertura  
**Razón**: 
- El estándar M1-NUM-03 requiere explícitamente "Aplicación de las propiedades de las potencias con base racional y exponente racional (fraccionario)"
- Los átomos A-M1-NUM-03-02 a A-M1-NUM-03-06 limitaban explícitamente a exponentes enteros
- Las propiedades operacionales (multiplicación, división, potencia de potencia) son conceptualmente las mismas para exponentes enteros y racionales
- Los átomos A-07 y A-08 ya cubren la conversión entre notación exponencial y radical, pero no las propiedades operacionales

**Átomos afectados**:
- **A-M1-NUM-03-02** (Multiplicación de potencias de igual base racional)
  - **Descripción**: Actualizada de "exponentes enteros" a "exponentes enteros o racionales"
  - **Criterios**: Agregado criterio para aplicar propiedad con exponentes fraccionarios
  - **Ejemplos**: Agregados ejemplos con exponentes racionales: `(1/2)^(1/2) * (1/2)^(3/2) = (1/2)^2`, `x^(1/3) * x^(2/3) = x`
  - **Notas**: Eliminada limitación "Limitado a exponentes enteros", agregada nota explicando que incluye ambos tipos

- **A-M1-NUM-03-03** (División de potencias de igual base racional)
  - **Descripción**: Actualizada de "exponentes enteros" a "exponentes enteros o racionales"
  - **Criterios**: Agregado criterio para aplicar propiedad con exponentes fraccionarios
  - **Ejemplos**: Agregados ejemplos con exponentes racionales: `(1/2)^(5/2) / (1/2)^(1/2) = (1/2)^2`, `x^(3/4) / x^(1/4) = x^(1/2)`
  - **Notas**: Eliminada limitación "Limitado a exponentes enteros", agregada nota explicando que incluye ambos tipos

- **A-M1-NUM-03-04** (Potencia de una potencia con base racional)
  - **Descripción**: Actualizada de "exponentes enteros" a "exponentes enteros o racionales"
  - **Criterios**: Actualizado para incluir exponentes fraccionarios en la simplificación
  - **Ejemplos**: Agregados ejemplos con exponentes racionales: `((1/2)^(1/2))^2 = 1/2`, `(x^(1/3))^(3/2) = x^(1/2)`
  - **Notas**: Eliminada limitación "Limitado a exponentes enteros", agregada nota explicando que incluye ambos tipos

- **A-M1-NUM-03-05** (Multiplicación de potencias de igual exponente)
  - **Título**: Actualizado de "igual exponente entero" a "igual exponente"
  - **Descripción**: Actualizada para incluir exponentes racionales
  - **Criterios**: Actualizado para reconocer equivalencia con exponentes racionales
  - **Ejemplos**: Agregados ejemplos con exponentes racionales: `2^(1/2) * 3^(1/2) = 6^(1/2)`, `(1/2)^(2/3) * (4/3)^(2/3) = (2/3)^(2/3)`
  - **Notas**: Eliminada limitación "Limitado a exponentes enteros", agregada nota explicando que incluye ambos tipos

- **A-M1-NUM-03-06** (División de potencias de igual exponente)
  - **Título**: Actualizado de "igual exponente entero" a "igual exponente"
  - **Descripción**: Actualizada para incluir exponentes racionales
  - **Criterios**: Actualizado para reconocer equivalencia con exponentes racionales
  - **Ejemplos**: Agregados ejemplos con exponentes racionales: `8^(1/3) / 2^(1/3) = 4^(1/3)`, `(x^(2/5)) / (y^(2/5)) = (x/y)^(2/5)`
  - **Notas**: Eliminada limitación "Limitado a exponentes enteros", agregada nota explicando que incluye ambos tipos

**Verificación de granularidad**:
- ✅ No hay duplicación: A-07 y A-08 cubren conversión de notación, no propiedades operacionales
- ✅ Intención cognitiva única: Cada átomo mantiene una propiedad específica
- ✅ Carga de memoria razonable: Extender a exponentes racionales no aumenta significativamente la complejidad cognitiva
- ✅ Independencia de evaluación: Se puede evaluar con exponentes enteros o racionales independientemente
- ✅ Límite de generalización apropiado: La propiedad es la misma, solo se extiende el dominio de aplicación

**Fuente**: Validación Gemini - identificó que 5 átomos limitaban explícitamente a exponentes enteros, dejando fuera los exponentes racionales requeridos por el estándar.

---

## Átomos - Eje 2: Álgebra y Funciones (M1-ALG)

### Estándar: M1-ALG-04 - Sistemas de Ecuaciones Lineales 2x2

**Fecha de cambios**: 2025-12-10

#### Cambio 1: Aclarar prerrequisitos alternativos en A-M1-ALG-04-09

**Fecha**: 2025-12-10  
**Tipo**: Aclaración en notas de alcance  
**Razón**: El evaluador identificó que los prerrequisitos A-M1-ALG-04-05, A-M1-ALG-04-06 y A-M1-ALG-04-07 (métodos de resolución: sustitución, igualación, reducción) implican una lógica AND en la estructura de datos, pero pedagógicamente el estudiante solo necesita dominar UNO de estos métodos para resolver problemas contextualizados.

**Átomo afectado**:
- **A-M1-ALG-04-09** (Resolución de Problemas Contextualizados)
  - **Notas de alcance**: Reforzada para aclarar explícitamente que los prerrequisitos de métodos son alternativas pedagógicas y que el estudiante debe dominar al menos uno, no todos.

**Fuente**: Validación Gemini - identificó ambigüedad en la interpretación de prerrequisitos múltiples de métodos alternativos.

---

## Átomos - Eje 3: Geometría (M1-GEO)

### Estándar: M1-GEO-01 - Geometría Plana: Teorema de Pitágoras, Perímetros y Áreas

**Fecha de cambios**: 2025-12-10

#### Cambio 1: Agregar prerrequisito de Teorema de Pitágoras a A-M1-GEO-01-13

**Fecha**: 2025-12-10  
**Tipo**: Agregar prerrequisito  
**Razón**: El átomo A-M1-GEO-01-13 (Resolución de problemas integrados de perímetro y área) es integrador y resuelve problemas que combinan perímetro y área. Muchos de estos problemas requieren el cálculo de un lado faltante utilizando el Teorema de Pitágoras (cubierto por A-M1-GEO-01-04) como paso intermedio. Este prerrequisito asegura que el estudiante tenga las herramientas necesarias para abordar estos problemas complejos.

**Átomo afectado**:
- **A-M1-GEO-01-13** (Resolución de problemas integrados de perímetro y área)
  - **Antes**: `prerrequisitos: ["A-M1-GEO-01-05", "A-M1-GEO-01-06", "A-M1-GEO-01-07", "A-M1-GEO-01-08", "A-M1-GEO-01-09", "A-M1-GEO-01-10", "A-M1-GEO-01-11", "A-M1-GEO-01-12"]`
  - **Después**: Agregado `A-M1-GEO-01-04` (Modelado de situaciones con Teorema de Pitágoras) a la lista de prerrequisitos.

**Fuente**: Validación Gemini - identificó que faltaban prerrequisitos relacionados con el Teorema de Pitágoras para problemas integrados.

---

## Átomos - Eje 4: Probabilidad y Estadística (M1-PROB)

### Estándar: M1-PROB-01 - Representación de Datos y Medidas de Tendencia Central

**Fecha de cambios**: 2025-12-10

#### Cambio 1: Eliminar prerrequisito restrictivo de A-M1-PROB-01-09

**Fecha**: 2025-12-10  
**Tipo**: Eliminar prerrequisito  
**Razón**: El prerrequisito original A-M1-PROB-01-02 (Cálculo de frecuencia absoluta) era demasiado restrictivo. Los gráficos de línea se utilizan comúnmente para representar variables continuas o series de tiempo que no necesariamente provienen de un conteo de frecuencias absolutas. Eliminar este prerrequisito permite una aplicación más general del átomo.

**Átomo afectado**:
- **A-M1-PROB-01-09** (Construcción de gráficos de línea)
  - **Antes**: `prerrequisitos: ["A-M1-PROB-01-02", "A-M1-PROB-01-07"]`
  - **Después**: `prerrequisitos: ["A-M1-PROB-01-07"]` (eliminado A-M1-PROB-01-02).

**Fuente**: Validación Gemini - identificó que el prerrequisito era innecesariamente restrictivo y limitaba el uso del gráfico de línea a datos de frecuencia, cuando también se usa para variables continuas o series de tiempo.

---

## Átomos - Eje 2: Álgebra y Funciones (M1-ALG)

### Estándar: M1-ALG-01 - Expresiones Algebraicas

**Fecha de cambios**: 2025-12-10

#### Cambio 1: Expandir A-M1-ALG-01-01 para cubrir traducción bidireccional

**Fecha**: 2025-12-10  
**Tipo**: Expansión de cobertura / Fidelidad al estándar  
**Razón**: 
- El estándar M1-ALG-01 exige explícitamente en la habilidad "representar": "Traduce del lenguaje natural al lenguaje matemático y viceversa"
- El estándar incluye un ejemplo conceptual que requiere interpretación de expresiones algebraicas: "Interpretar una expresión como 2x + 3y como el costo total de comprar 'x' unidades de un producto a $2 cada uno y 'y' unidades de otro a $3 cada uno"
- El átomo original solo cubría la dirección Natural→Algebraico, dejando incompleta la cobertura del estándar
- El evaluador identificó que faltaba la dirección Algebraico→Natural

**Átomo afectado**:
- **A-M1-ALG-01-01** (Traducción bidireccional entre lenguaje natural y algebraico)
  - **Título**: Actualizado de "Traducción de lenguaje natural a algebraico" a "Traducción bidireccional entre lenguaje natural y algebraico"
  - **Descripción**: Expandida para incluir ambas direcciones de traducción y la equivalencia entre representaciones
  - **Criterios atómicos**:
    - Mantenidos: Traducción Natural→Algebraico (3 criterios originales)
    - Agregados: 
      - "Interpreta expresiones algebraicas dadas, traduciéndolas a lenguaje natural o describiendo su significado contextual"
      - "Identifica el significado de variables, constantes y operaciones en expresiones algebraicas dadas"
  - **Ejemplos conceptuales**: Agregados ejemplos de interpretación Algebraico→Natural:
    - "Interpretar la expresión 2x + 3y como 'el doble de un número más el triple de otro número' o como 'el costo total de comprar x unidades a $2 cada una y y unidades a $3 cada una'"
    - "Describir qué representa la expresión x² - 5 en lenguaje natural: 'el cuadrado de un número disminuido en cinco'"
  - **Notas de alcance**: Actualizadas para aclarar que cubre ambas direcciones de traducción

**Verificación de granularidad**:
- ✅ No hay duplicación: Ningún otro átomo cubre la interpretación de expresiones algebraicas en lenguaje natural
- ✅ Misma intención cognitiva: Ambas direcciones son parte de la misma habilidad "representar"
- ✅ Carga de memoria razonable: Agregar la dirección inversa no aumenta significativamente la complejidad cognitiva
- ✅ Independencia de evaluación: Pueden evaluarse juntas sin violar la independencia (de hecho, es común evaluar ambas direcciones en la misma pregunta)
- ✅ El evaluador ya dio "pass" en granularity y recomendó "Ampliar criterios" (no crear átomo separado)

**Fuente**: Validación Gemini - identificó que el átomo solo cubría Natural→Algebraico, pero el estándar exige explícitamente "viceversa" (Algebraico→Natural) y los ejemplos conceptuales incluyen interpretación de expresiones.

---

### Estándar: M1-ALG-06 - Función Cuadrática

**Fecha de cambios**: 2025-12-10

#### Cambio 1: Expandir A-M1-ALG-06-09 para incluir análisis completo del parámetro 'b'

**Fecha**: 2025-12-10  
**Tipo**: Expansión de cobertura / Fidelidad al estándar  
**Razón**: 
- El estándar M1-ALG-06 menciona explícitamente en `incluye`: "Análisis de la función cuadrática a través de tablas de valores y gráficos, comprendiendo cómo la variación de sus parámetros (a, b, c) afecta la forma y posición de la parábola"
- El estándar lista explícitamente los tres parámetros "(a, b, c)"
- El átomo original solo cubría 'a' y 'c' de forma completa, limitando el análisis de 'b' a "su efecto en la posición del vértice si es necesario"
- El parámetro 'b' tiene efectos relevantes: afecta la posición horizontal del vértice (x_v = -b/(2a)) y la simetría de la parábola
- Aunque el efecto de 'b' es menos directo visualmente que 'a' y 'c', el estándar lo requiere explícitamente

**Átomo afectado**:
- **A-M1-ALG-06-09** (Análisis de la variación de parámetros en la función cuadrática)
  - **Descripción**: Actualizada para incluir los tres parámetros: "cómo los cambios en los parámetros 'a', 'b' y 'c' de la función f(x) = ax² + bx + c afectan la forma y posición de la gráfica de la parábola"
  - **Criterios atómicos**:
    - Mantenidos: Análisis de 'a' (apertura) y 'c' (traslación vertical)
    - Agregado: "Describe cómo el signo de 'a' determina la concavidad (abre hacia arriba o hacia abajo)"
    - Agregado: "Describe cómo el parámetro 'b' afecta la posición horizontal del vértice y la simetría de la parábola"
  - **Ejemplos conceptuales**: Agregados ejemplos sobre el efecto de 'b':
    - "Comparar las gráficas de y = x² + 2x y y = x² - 2x para observar cómo 'b' afecta la posición del vértice"
    - "Explicar que en y = x² + 4x, el vértice está en x = -2, mientras que en y = x² - 4x, el vértice está en x = 2"
  - **Notas de alcance**: Actualizadas para reflejar que se cubren los tres parámetros, aclarando que el efecto de 'b' se analiza principalmente a través de su impacto en la coordenada x del vértice

**Fuente**: Validación Gemini - identificó que el átomo limitaba el análisis de 'b' y se centraba en 'a' y 'c', dejando incompleta la cobertura del requisito explícito del estándar que menciona "(a, b, c)".

---

#### Cambio 2: Expandir A-M1-ALG-06-11 para incluir evaluación general de funciones cuadráticas

**Fecha**: 2025-12-10  
**Tipo**: Expansión de cobertura / Calidad de contenido  
**Razón**: 
- El título del átomo menciona "evaluación", pero los criterios solo cubrían "resolución" (encontrar x dado y)
- La evaluación general de funciones cuadráticas (calcular f(x) dado x) no estaba explícitamente cubierta en ningún átomo dedicado
- Solo estaba cubierta como parte de procedimientos específicos (cálculo del vértice: f(x_v), intersección Y: f(0))
- El estándar menciona "tablas de valores" que requiere evaluación general
- El evaluador identificó inconsistencia entre título y contenido: "El título menciona 'evaluación', pero la descripción y criterios se centran exclusivamente en 'resolución'"

**Átomo afectado**:
- **A-M1-ALG-06-11** (Resolución de problemas de contexto mediante raíces o evaluación)
  - **Descripción**: Expandida para incluir ambos tipos de operaciones:
    - Resolución: encontrar cuándo la función es cero o alcanza un valor específico (encontrar x dado y)
    - Evaluación: calcular el valor de la función para un valor dado de la variable independiente (calcular y dado x)
  - **Criterios atómicos**:
    - Agregado: "Identifica si el problema requiere resolución (encontrar x dado y) o evaluación (calcular y dado x)"
    - Mantenidos: Criterios de resolución (plantear ecuación, resolver)
    - Agregado: "Para problemas de evaluación: sustituye el valor dado de x en la función cuadrática y calcula el valor resultante de f(x) realizando las operaciones aritméticas correctamente"
    - Actualizado: Criterio de validación para incluir ambos tipos de problemas
  - **Ejemplos conceptuales**: 
    - Mantenidos: Ejemplos de resolución (tiempo de caída, población)
    - Agregados: Ejemplos de evaluación (altura a los 3 segundos, costo para 50 unidades)
  - **Notas de alcance**: Actualizadas para aclarar que cubre ambos tipos de problemas y que la evaluación general está cubierta aquí, no solo como parte de procedimientos específicos

**Fuente**: Validación Gemini - identificó inconsistencia entre título y contenido. El evaluador señaló: "El título menciona 'evaluación', pero la descripción y criterios se centran exclusivamente en 'resolución' (encontrar x dado y). La evaluación simple (encontrar y dado x) es una operación cognitiva distinta (aritmética vs algebraica)."

---

## Átomos - Eje 1: Números (M1-NUM)

### Estándar: M1-NUM-01 - Números Enteros y Racionales

**Fecha de cambios**: 2025-12-10

#### Cambio 1: Separar A-M1-NUM-01-13 en dos átomos (decimal finito vs periódico)

**Fecha**: 2025-12-10  
**Tipo**: Granularidad (división de átomo)  
**Razón**: 
- El átomo original A-M1-NUM-01-13 combinaba dos algoritmos distintos:
  - Conversión de decimal finito: usa potencias de 10 en el denominador (algoritmo directo)
  - Conversión de decimal periódico: usa método algebraico o regla de nueves (algoritmo más complejo)
- Son procedimientos cognitivamente distintos que requieren estrategias diferentes
- El evaluador identificó que violaba la regla de granularidad (`single_cognitive_intention: false`)
- Pueden enseñarse y evaluarse independientemente
- El estándar no los agrupa explícitamente como un solo procedimiento

**Átomos afectados**:
- **A-M1-NUM-01-13** (originalmente "Conversión de decimal a fracción")
  - **Nuevo**: "Conversión de decimal finito a fracción"
  - **Descripción**: Actualizada para enfocarse solo en decimales finitos
  - **Criterios**: 
    - Mantenido: Conversión usando potencias de 10
    - Agregado: "Identifica el número de cifras decimales para determinar la potencia de 10 correspondiente"
    - Eliminado: Criterio sobre decimales periódicos
  - **Ejemplos**: Actualizados para incluir solo decimales finitos
  - **Notas**: Actualizadas para aclarar que es solo para decimales finitos y que el algoritmo es basado en potencias de 10
  
- **A-M1-NUM-01-14** (nuevo átomo)
  - **Título**: "Conversión de decimal periódico a fracción"
  - **Descripción**: Enfocada en el algoritmo estándar (método algebraico o regla de nueves)
  - **Criterios**:
    - "Identifica el período (cifras que se repiten) en un decimal periódico"
    - "Aplica el algoritmo estándar para convertir decimales periódicos a fracción (multiplicar por potencia de 10, restar, resolver)"
    - "Simplifica la fracción resultante hasta su mínima expresión"
  - **Prerrequisitos**: `["A-M1-NUM-01-11", "A-M1-NUM-01-12", "A-M1-NUM-01-13"]` (requiere el concepto de fracción y la conversión de decimal finito como base)
  - **Notas**: Aclarado que es solo para decimales periódicos y que el algoritmo es distinto al de decimales finitos (método algebraico vs potencias de 10)

**Renumeración de átomos posteriores**:
- A-14 (original: Orden y comparación de fracciones) → A-15
- A-15 (original: Orden y comparación de decimales) → A-16
- A-16 (original: Adición y sustracción de fracciones homogéneas) → A-17
- A-17 (original: Adición y sustracción de fracciones heterogéneas) → A-18
- A-18 (original: Multiplicación de fracciones) → A-19
- A-19 (original: División de fracciones) → A-20
- A-20 (original: Adición y sustracción de números decimales) → A-21
- A-21 (original: Multiplicación de números decimales) → A-22
- A-22 (original: División de números decimales) → A-23
- A-23 (original: Modelado de situaciones) → A-24
- A-24 (original: Resolución de problemas) → A-25

**Prerrequisitos actualizados**:
- A-18 (Adición y sustracción de fracciones heterogéneas): Actualizado de A-16 a A-17
- A-20 (División de fracciones): Actualizado de A-18 a A-19
- A-21 (Adición y sustracción de números decimales): Actualizado de A-15 a A-16
- A-23 (División de números decimales): Actualizado de A-21 a A-22
- A-25 (Resolución de problemas): Actualizado para incluir A-13, A-14, A-15, A-16 (nuevos números)

**Verificación de granularidad**:
- ✅ Intención cognitiva única: Cada átomo ahora tiene una única estrategia cognitiva
- ✅ Independencia de evaluación: Pueden evaluarse independientemente
- ✅ Algoritmos distintos: Decimal finito (potencias de 10) vs periódico (método algebraico)
- ✅ Carga de memoria razonable: Separar no aumenta la complejidad, la reduce al enfocarse en un algoritmo a la vez

**Fuente**: Validación Gemini - identificó que el átomo combinaba dos algoritmos distintos (decimal finito vs periódico) que violaban la regla de granularidad (`single_cognitive_intention: false`).

---

#### Cambio 2: Expandir A-M1-PROB-01-12 para cubrir comprensión del proceso de construcción de gráficos circulares

**Fecha**: 2025-12-10  
**Tipo**: Expansión de cobertura / Ajuste a contexto de evaluación  
**Razón**: 
- El estándar M1-PROB-01 requiere la "construcción" de gráficos circulares como subcontenido clave
- El evaluador identificó que el átomo solo cubría el cálculo matemático, pero no cubría la comprensión del proceso de construcción
- En el contexto de una prueba de selección múltiple (PAES), no se requiere construcción física con herramientas geométricas (compás, transportador)
- Sin embargo, el estudiante necesita entender CÓMO se forma el gráfico circular para poder interpretarlo correctamente
- La comprensión del proceso (cálculo de ángulos → trazado de sectores → etiquetado) es fundamental para la interpretación

**Átomo afectado**:
- **A-M1-PROB-01-12** (Cálculo de ángulos para construcción de gráficos circulares)
  - **Título**: Actualizado de "Cálculo de ángulos para gráficos circulares" a "Cálculo de ángulos para construcción de gráficos circulares"
  - **Descripción**: Expandida para enfatizar la comprensión del proceso de construcción y su relación con la interpretación
  - **Criterios atómicos**:
    - Mantenidos: Cálculo de ángulos y verificación de suma 360°
    - Agregados: 
      - "Identifica los pasos del proceso de construcción de un gráfico circular (cálculo de ángulos, trazado de sectores, etiquetado)"
      - "Relaciona correctamente los ángulos calculados con las proporciones representadas en el gráfico circular"
      - "Interpreta un gráfico circular identificando las proporciones a partir de los ángulos de los sectores"
  - **Ejemplos conceptuales**: Agregados ejemplos sobre interpretación de gráficos circulares dados (identificar proporciones a partir de ángulos)
  - **Notas de alcance**: Actualizadas para aclarar que se enfoca en cálculo y comprensión del proceso para facilitar la interpretación, no requiere construcción física manual en contexto de selección múltiple

**Fuente**: Validación Gemini - identificó que el átomo no cubría la "construcción" completa. Solución acordada: no construir físicamente, pero sí entender cómo se forma para poder interpretarlo correctamente.

---

### Estándar: M1-GEO-03 - Transformaciones Isométricas

**Fecha de cambios**: 2025-12-10

#### Cambio 1: Agregar A-M1-GEO-03-02 (Localización e identificación de puntos en el plano cartesiano) y renumerar átomos

**Fecha**: 2025-12-10  
**Tipo**: Agregar átomo faltante y renumerar  
**Razón**: 
- El estándar M1-GEO-03 incluye explícitamente "Localización de puntos en el plano cartesiano" como subcontenido clave
- El estándar también menciona "Identificación y representación de puntos y vectores en el plano cartesiano" en su sección "incluye"
- El átomo A-M1-GEO-03-03 (Vectores de traslación) y otros átomos posteriores asumen conocimiento de localización de puntos, pero no había un átomo dedicado que cubriera explícitamente este contenido
- El evaluador identificó que A-M1-GEO-03-02 (original, Vectores) asumía implícitamente el manejo de puntos sin un átomo dedicado

**Átomo agregado**:
- **ID**: `A-M1-GEO-03-02` (nuevo)
- **Título**: "Localización e identificación de puntos en el plano cartesiano"
- **Tipo**: `concepto_procedimental`
- **Habilidad principal**: `representar`
- **Prerrequisitos**: `[]` (conocimiento básico del plano cartesiano)
- **Criterios atómicos**:
  - Identifica las coordenadas de un punto dado gráficamente en el plano cartesiano
  - Localiza un punto en el plano cartesiano dadas sus coordenadas (x, y)
  - Reconoce la notación (x, y) para representar puntos y la relación entre coordenadas y posición en el plano
  - Distingue entre coordenadas positivas y negativas y su ubicación en los cuadrantes correspondientes

**Renumeración de átomos**:
Todos los átomos desde el original A-02 en adelante fueron renumerados:
- A-02 (original: Vectores) → A-03
- A-03 (original: Traslación de punto) → A-04
- A-04 (original: Traslación de figuras) → A-05
- A-05 (original: Concepto de reflexión) → A-06
- A-06 (original: Reflexión de punto) → A-07
- A-07 (original: Reflexión de figuras) → A-08
- A-08 (original: Concepto de rotación) → A-09
- A-09 (original: Rotación de punto) → A-10
- A-10 (original: Rotación de figuras) → A-11
- A-11 (original: Identificación) → A-12
- A-12 (original: Problemas contextualizados) → A-13

**Prerrequisitos actualizados**:
- A-03 (Vectores): Agregado A-02 (Puntos) como prerrequisito
- A-04 (Traslación de punto): Prerrequisito actualizado de A-02 a A-03 (Vectores)
- A-05 (Traslación de figuras): Prerrequisito actualizado de A-03 a A-04 (Traslación de punto)
- A-07 (Reflexión de punto): Agregado A-02 (Puntos) como prerrequisito
- A-08 (Reflexión de figuras): Prerrequisitos actualizados de A-06, A-05 a A-07, A-06
- A-10 (Rotación de punto): Agregado A-02 (Puntos) como prerrequisito
- A-11 (Rotación de figuras): Prerrequisitos actualizados de A-09, A-08 a A-10, A-09
- A-12 (Identificación): Prerrequisitos actualizados de A-04, A-07, A-10 a A-05, A-08, A-11
- A-13 (Problemas contextualizados): Prerrequisitos actualizados de A-03, A-06, A-09, A-11 a A-04, A-07, A-10, A-12

**Fuente**: Validación Gemini - identificó que A-M1-GEO-03-02 (original) cubría vectores pero asumía implícitamente el manejo de puntos sin un átomo dedicado a "Identificación de puntos", siendo que el estándar menciona explícitamente "Localización de puntos en el plano cartesiano" como subcontenido clave.

---

