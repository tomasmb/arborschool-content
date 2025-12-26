# Análisis de Cobertura de Átomos y Dificultades

**Fecha de análisis:** 2025-12-26 17:41
**Última actualización:** Agregado A-M1-NUM-03-18 a Q23 inv-2026

## Resumen Ejecutivo

| Métrica | Valor |
|---------|-------|
| Total de átomos definidos | **229** |
| Átomos con pregunta directa | **130** |
| Átomos cubiertos por transitividad | **59** |
| Átomos SIN cobertura real | **31** |
| Preguntas con metadata | 202 |

## Estadísticas de Cobertura por Dificultad

> [!WARNING]
> No hay preguntas con dificultad **High** para ningún átomo.

| Dificultad | Átomos con ≥1 pregunta | % del total (229) |
|------------|------------------------|------------------------------|
| **Low** | 71 | 31.0% |
| **Medium** | 100 | 43.7% |
| **High** | 0 | 0.0% |

## Cobertura por Eje Temático

- **Algebra Y Funciones**: 39 directos + 20 transitivos = 59/80 (74%), 21 sin cobertura real
- **Geometria**: 26 directos + 17 transitivos = 43/43 (100%), 0 sin cobertura real
- **Numeros**: 38 directos + 15 transitivos = 53/55 (96%), 2 sin cobertura real
- **Probabilidad Y Estadistica**: 27 directos + 15 transitivos = 42/51 (82%), 9 sin cobertura real

---

## 🟡 Átomos Cubiertos por Transitividad (67 átomos)

> [!NOTE]
> Estos átomos son prerrequisitos de otros que sí tienen preguntas directas.

### Algebra Y Funciones (20 transitivos)

| Átomo no cubierto | Título | Cubierto vía |
|-------------------|--------|--------------|
| `A-M1-ALG-01-03` | Reducción de términos semejantes | `A-M1-ALG-01-05` |
| `A-M1-ALG-01-06` | División de polinomio por monomio | `A-M1-ALG-01-17` |
| `A-M1-ALG-01-07` | Reconocimiento de productos notables: Cu | `A-M1-ALG-01-08` |
| `A-M1-ALG-01-09` | Reconocimiento de productos notables: Su | `A-M1-ALG-01-18` |
| `A-M1-ALG-01-13` | Factorización de diferencia de cuadrados | `A-M1-ALG-01-17` |
| `A-M1-ALG-01-14` | Factorización de trinomio cuadrado perfe | `A-M1-ALG-01-17` |
| `A-M1-ALG-02-01` | Concepto de Proporcionalidad Directa | `A-M1-ALG-02-02` |
| `A-M1-ALG-03-01` | Identificación de ecuaciones lineales | `A-M1-ALG-03-06` |
| `A-M1-ALG-03-04` | Resolución de ecuaciones lineales comple | `A-M1-ALG-03-15` |
| `A-M1-ALG-03-07` | Concepto de inecuación lineal y conjunto | `A-M1-ALG-03-15` |
| `A-M1-ALG-03-09` | Representación gráfica de inecuaciones e | `A-M1-ALG-03-10` |
| `A-M1-ALG-03-12` | Resolución de inecuaciones con inversión | `A-M1-ALG-03-15` |
| `A-M1-ALG-03-13` | Resolución de inecuaciones lineales comp | `A-M1-ALG-03-15` |
| `A-M1-ALG-04-01` | Concepto de Sistema 2x2 y Verificación d | `A-M1-ALG-04-02` |
| `A-M1-ALG-05-08` | Concepto de Coeficiente de Posición (n) | `A-M1-ALG-05-11` |
| `A-M1-ALG-06-01` | Resolución de ecuaciones cuadráticas inc | `A-M1-ALG-06-02` |
| `A-M1-ALG-06-03` | Resolución de ecuaciones cuadráticas med | `A-M1-ALG-06-13` |
| `A-M1-ALG-06-04` | Concepto de función cuadrática y concavi | `A-M1-ALG-06-11` |
| `A-M1-ALG-06-06` | Cálculo del vértice de la función cuadrá | `A-M1-ALG-06-11` |
| `A-M1-ALG-06-07` | Cálculo de los ceros (raíces) de la func | `A-M1-ALG-06-13` |

### Geometria (17 transitivos)

| Átomo no cubierto | Título | Cubierto vía |
|-------------------|--------|--------------|
| `A-M1-GEO-01-01` | Identificación de elementos del triángul | `A-M1-GEO-01-13` |
| `A-M1-GEO-01-02` | Cálculo de la hipotenusa mediante Teorem | `A-M1-GEO-01-13` |
| `A-M1-GEO-01-06` | Cálculo de la circunferencia (Perímetro  | `A-M1-GEO-01-13` |
| `A-M1-GEO-01-07` | Cálculo del área de triángulos | `A-M1-GEO-01-13` |
| `A-M1-GEO-01-09` | Cálculo del área de rombos (diagonales) | `A-M1-GEO-01-13` |
| `A-M1-GEO-02-03` | Cálculo de área de superficie de cubos | `A-M1-GEO-02-15` |
| `A-M1-GEO-02-04` | Cálculo de área de superficie de paralel | `A-M1-GEO-02-15` |
| `A-M1-GEO-02-07` | Cálculo de volumen de cubos | `A-M1-GEO-02-15` |
| `A-M1-GEO-02-08` | Cálculo de volumen de paralelepípedos | `A-M1-GEO-02-15` |
| `A-M1-GEO-02-09` | Cálculo de volumen de prismas rectos gen | `A-M1-GEO-02-16` |
| `A-M1-GEO-02-10` | Redes de construcción y elementos del ci | `A-M1-GEO-02-16` |
| `A-M1-GEO-02-11` | Cálculo de área de superficie de cilindr | `A-M1-GEO-02-16` |
| `A-M1-GEO-02-12` | Concepto de volumen en cilindros | `A-M1-GEO-02-16` |
| `A-M1-GEO-02-14` | Selección de modelo: Área vs Volumen en  | `A-M1-GEO-02-16` |
| `A-M1-GEO-03-01` | Concepto de transformación isométrica | `A-M1-GEO-03-05` |
| `A-M1-GEO-03-08` | Reflexión de figuras respecto a ejes coo | `A-M1-GEO-03-13` |
| `A-M1-GEO-03-11` | Rotación de figuras respecto al origen | `A-M1-GEO-03-13` |

### Numeros (9 transitivos)

| Átomo no cubierto | Título | Cubierto vía |
|-------------------|--------|--------------|
| `A-M1-NUM-01-01` | Concepto y representación de números ent | `A-M1-NUM-01-23` |
| `A-M1-NUM-01-02` | Representación y Orden de Enteros en la  | `A-M1-NUM-01-25` |
| `A-M1-NUM-01-12` | Conversión de fracción a decimal | `A-M1-NUM-01-25` |
| `A-M1-NUM-01-13` | Conversión de decimal finito a fracción | `A-M1-NUM-01-25` |
| `A-M1-NUM-01-17` | Adición y sustracción de fracciones homo | `A-M1-NUM-01-25` |
| `A-M1-NUM-02-01` | Concepto de porcentaje como razón | `A-M1-NUM-02-04` |
| `A-M1-NUM-02-05` | Conversión de fracción a porcentaje | `A-M1-NUM-02-11` |
| `A-M1-NUM-03-02` | Potencias de base racional y exponente e | `A-M1-NUM-03-17` |
| `A-M1-NUM-03-03` | Multiplicación de potencias de igual bas | `A-M1-NUM-03-17` |

### Probabilidad Y Estadistica (13 transitivos)

| Átomo no cubierto | Título | Cubierto vía |
|-------------------|--------|--------------|
| `A-M1-PROB-01-04` | Características del gráfico de barras | `A-M1-PROB-01-05` |
| `A-M1-PROB-01-07` | Características del gráfico de línea | `A-M1-PROB-01-09` |
| `A-M1-PROB-01-10` | Características del gráfico circular | `A-M1-PROB-01-11` |
| `A-M1-PROB-01-14` | Concepto de promedio (media aritmética) | `A-M1-PROB-01-17` |
| `A-M1-PROB-02-01` | Concepto de media aritmética | `A-M1-PROB-02-11` |
| `A-M1-PROB-02-05` | Cálculo de la mediana (cantidad par de d | `A-M1-PROB-02-11` |
| `A-M1-PROB-02-06` | Concepto de moda | `A-M1-PROB-02-11` |
| `A-M1-PROB-02-08` | Concepto de rango | `A-M1-PROB-02-11` |
| `A-M1-PROB-03-01` | Concepto de Cuartiles | `A-M1-PROB-03-07` |
| `A-M1-PROB-04-03` | Representación simbólica de eventos comp | `A-M1-PROB-04-05` |
| `A-M1-PROB-04-04` | Distinción de eventos mutuamente excluye | `A-M1-PROB-04-05` |
| `A-M1-PROB-04-07` | Distinción de eventos independientes y d | `A-M1-PROB-04-12` |
| `A-M1-PROB-04-09` | Concepto de probabilidad condicional | `A-M1-PROB-04-10` |

---

## 🔴 Átomos SIN Cobertura Real (31 átomos)

> [!CAUTION]
> Estos átomos no tienen preguntas directas ni son prerrequisitos de átomos cubiertos.

### Algebra Y Funciones (11 sin cobertura)

- `A-M1-ALG-01-11`: **Desarrollo de cubo de binomio**
- `A-M1-ALG-02-07`: **Concepto de Proporcionalidad Inversa**
- `A-M1-ALG-02-08`: **Constante de Proporcionalidad Inversa**
- `A-M1-ALG-02-09`: **Representación Tabular de Proporcionalidad Inversa**
- `A-M1-ALG-02-10`: **Representación Gráfica de Proporcionalidad Inversa**
- `A-M1-ALG-02-11`: **Modelado Algebraico de Proporcionalidad Inversa**
- `A-M1-ALG-02-12`: **Resolución de Problemas de Proporción Inversa**
- `A-M1-ALG-02-13`: **Distinción entre Proporcionalidad Directa e Inversa**
- `A-M1-ALG-04-03`: **Clasificación de Sistemas por Cantidad de Soluciones**
- `A-M1-ALG-05-03`: **Distinción entre Función Lineal y Afín**
- `A-M1-ALG-05-09`: **Graficación mediante Tabla de Valores**

### Numeros (9 sin cobertura)

- `A-M1-NUM-01-14`: **Conversión de decimal periódico a fracción**
- `A-M1-NUM-03-07`: **División de potencias de igual exponente**
- `A-M1-NUM-03-08`: **Conversión de potencia de exponente racional a raíz**
- `A-M1-NUM-03-09`: **Conversión de raíz enésima a potencia de exponente racional**
- `A-M1-NUM-03-10`: **Existencia de raíces enésimas en los números reales**
- `A-M1-NUM-03-12`: **División de raíces de igual índice**
- `A-M1-NUM-03-13`: **Propiedad de raíz de una raíz**
- `A-M1-NUM-03-16`: **Racionalización de denominadores con raíz enésima no cuadrada**

### Probabilidad Y Estadistica (11 sin cobertura)

- `A-M1-PROB-01-06`: **Construcción de gráficos de barras**
- `A-M1-PROB-01-12`: **Cálculo de ángulos para construcción de gráficos circulares**
- `A-M1-PROB-01-13`: **Selección del gráfico adecuado**
- `A-M1-PROB-02-10`: **Selección y justificación de la medida adecuada**
- `A-M1-PROB-03-02`: **Concepto de Percentiles**
- `A-M1-PROB-03-04`: **Cálculo de Percentiles en datos no agrupados**
- `A-M1-PROB-03-06`: **Interpretación de Percentiles en contexto**
- `A-M1-PROB-03-09`: **Comparación de distribuciones mediante Diagramas de Cajón**
- `A-M1-PROB-04-06`: **Aplicación de la regla aditiva para eventos no mutuamente excluyentes**
- `A-M1-PROB-04-08`: **Aplicación de la regla multiplicativa para eventos independientes**
- `A-M1-PROB-04-11`: **Cálculo de probabilidad condicional por fórmula algebraica**

---

## Resumen de Brechas de Dificultad

| Dificultad Faltante | Cantidad de Átomos |
|---------------------|-------------------|
| Low | 59 de 130 cubiertos |
| Medium | 30 de 130 cubiertos |
| High | 130 de 130 cubiertos ⚠️ |

## Tabla de Cobertura Directa por Átomo

| Átomo | Título | Low | Medium | High |
|-------|--------|-----|--------|------|
| `A-M1-ALG-01-01` | Traducción bidireccional entre leng | 15 | 16 | ❌ |
| `A-M1-ALG-01-02` | Evaluación de expresiones algebraic | 1 | 6 | ❌ |
| `A-M1-ALG-01-04` | Suma y resta de polinomios | 2 | 3 | ❌ |
| `A-M1-ALG-01-05` | Multiplicación de monomios y polino | 1 | 1 | ❌ |
| `A-M1-ALG-01-08` | Desarrollo de cuadrado de binomio | 1 | ❌ | ❌ |
| `A-M1-ALG-01-10` | Desarrollo de suma por diferencia | 1 | ❌ | ❌ |
| `A-M1-ALG-01-12` | Factorización por factor común | ❌ | 1 | ❌ |
| `A-M1-ALG-01-15` | Factorización de trinomios de la fo | 2 | ❌ | ❌ |
| `A-M1-ALG-01-17` | Modelado geométrico con expresiones | ❌ | 5 | ❌ |
| `A-M1-ALG-01-18` | Detección de errores en manipulació | ❌ | 4 | ❌ |
| `A-M1-ALG-02-02` | Constante de Proporcionalidad Direc | ❌ | 1 | ❌ |
| `A-M1-ALG-02-03` | Representación Tabular de Proporcio | 2 | ❌ | ❌ |
| `A-M1-ALG-02-04` | Representación Gráfica de Proporcio | 1 | ❌ | ❌ |
| `A-M1-ALG-02-05` | Modelado Algebraico de Proporcional | 1 | 4 | ❌ |
| `A-M1-ALG-02-06` | Resolución de Problemas de Proporci | 8 | 4 | ❌ |
| `A-M1-ALG-03-03` | Resolución de ecuaciones lineales b | 6 | 4 | ❌ |
| `A-M1-ALG-03-05` | Traducción de lenguaje natural a ec | ❌ | 6 | ❌ |
| `A-M1-ALG-03-06` | Resolución de problemas contextuali | 2 | 8 | ❌ |
| `A-M1-ALG-03-10` | Interpretación de gráficos de inecu | 1 | ❌ | ❌ |
| `A-M1-ALG-03-11` | Resolución de inecuaciones lineales | ❌ | 1 | ❌ |
| `A-M1-ALG-03-14` | Traducción de lenguaje natural a in | ❌ | 2 | ❌ |
| `A-M1-ALG-03-15` | Resolución de problemas contextuali | ❌ | 2 | ❌ |
| `A-M1-ALG-03-16` | Análisis de errores en resolución d | ❌ | 3 | ❌ |
| `A-M1-ALG-04-02` | Interpretación Geométrica de Sistem | ❌ | 1 | ❌ |
| `A-M1-ALG-04-05` | Resolución Algebraica por Método de | 1 | ❌ | ❌ |
| `A-M1-ALG-04-07` | Resolución Algebraica por Método de | 1 | 1 | ❌ |
| `A-M1-ALG-04-08` | Modelado de Situaciones con Sistema | 2 | 3 | ❌ |
| `A-M1-ALG-05-01` | Concepto de Función Lineal | 1 | ❌ | ❌ |
| `A-M1-ALG-05-02` | Concepto de Función Afín | 1 | ❌ | ❌ |
| `A-M1-ALG-05-04` | Evaluación de Funciones Lineales y  | 1 | ❌ | ❌ |
| `A-M1-ALG-05-06` | Concepto de Pendiente (m) | 1 | ❌ | ❌ |
| `A-M1-ALG-05-11` | Formulación de Modelos Lineales y A | 4 | 3 | ❌ |
| `A-M1-ALG-05-12` | Interpretación de Parámetros en Con | 2 | 1 | ❌ |
| `A-M1-ALG-05-13` | Resolución de Problemas Contextuali | 1 | 1 | ❌ |
| `A-M1-ALG-06-02` | Resolución de ecuaciones cuadrática | ❌ | 1 | ❌ |
| `A-M1-ALG-06-10` | Análisis de los parámetros 'a' y 'c | 1 | ❌ | ❌ |
| `A-M1-ALG-06-11` | Análisis del parámetro 'b' en la fu | 1 | 1 | ❌ |
| `A-M1-ALG-06-12` | Resolución de problemas de optimiza | ❌ | 1 | ❌ |
| `A-M1-ALG-06-13` | Resolución de problemas de contexto | ❌ | 1 | ❌ |
| `A-M1-GEO-01-03` | Cálculo de un cateto mediante Teore | 1 | ❌ | ❌ |
| `A-M1-GEO-01-04` | Modelado de situaciones con Teorema | ❌ | 1 | ❌ |
| `A-M1-GEO-01-05` | Cálculo de perímetros de polígonos  | 1 | 1 | ❌ |
| `A-M1-GEO-01-08` | Cálculo del área de paralelogramos  | ❌ | 3 | ❌ |
| `A-M1-GEO-01-10` | Cálculo del área de trapecios | ❌ | 2 | ❌ |
| `A-M1-GEO-01-11` | Cálculo del área de círculos | ❌ | 1 | ❌ |
| `A-M1-GEO-01-12` | Distinción conceptual entre perímet | 1 | 1 | ❌ |
| `A-M1-GEO-01-13` | Resolución de problemas integrados  | ❌ | 3 | ❌ |
| `A-M1-GEO-01-14` | Argumentación y validación de resul | ❌ | 5 | ❌ |
| `A-M1-GEO-02-01` | Distinción conceptual entre Área de | ❌ | 1 | ❌ |
| `A-M1-GEO-02-02` | Redes de construcción de prismas re | ❌ | 1 | ❌ |
| `A-M1-GEO-02-05` | Cálculo de área de superficie de pr | ❌ | 1 | ❌ |
| `A-M1-GEO-02-06` | Concepto de volumen en prismas rect | ❌ | 3 | ❌ |
| `A-M1-GEO-02-13` | Cálculo de volumen de cilindros | 1 | ❌ | ❌ |
| `A-M1-GEO-02-15` | Resolución de problemas contextuali | ❌ | 4 | ❌ |
| `A-M1-GEO-02-16` | Resolución de problemas contextuali | ❌ | 1 | ❌ |
| `A-M1-GEO-03-02` | Localización e identificación de pu | ❌ | 1 | ❌ |
| `A-M1-GEO-03-03` | Vectores de traslación en el plano  | 1 | ❌ | ❌ |
| `A-M1-GEO-03-04` | Traslación de un punto mediante un  | ❌ | 2 | ❌ |
| `A-M1-GEO-03-05` | Traslación de figuras geométricas p | 2 | ❌ | ❌ |
| `A-M1-GEO-03-06` | Concepto de reflexión (simetría axi | ❌ | 2 | ❌ |
| `A-M1-GEO-03-07` | Reflexión de un punto respecto a lo | ❌ | 1 | ❌ |
| `A-M1-GEO-03-09` | Concepto de rotación | ❌ | 1 | ❌ |
| `A-M1-GEO-03-10` | Rotación de un punto respecto al or | ❌ | 1 | ❌ |
| `A-M1-GEO-03-12` | Identificación de transformaciones  | 1 | 1 | ❌ |
| `A-M1-GEO-03-13` | Resolución de problemas con isometr | ❌ | 4 | ❌ |
| `A-M1-NUM-01-03` | Orden y comparación de números ente | 2 | ❌ | ❌ |
| `A-M1-NUM-01-04` | Adición de números enteros | 1 | 2 | ❌ |
| `A-M1-NUM-01-05` | Sustracción de números enteros | ❌ | 5 | ❌ |
| `A-M1-NUM-01-06` | Multiplicación de números enteros | ❌ | 2 | ❌ |
| `A-M1-NUM-01-07` | División de números enteros | 1 | ❌ | ❌ |
| `A-M1-NUM-01-08` | Modelado de situaciones con números | ❌ | 3 | ❌ |
| `A-M1-NUM-01-09` | Resolución de problemas con números | 3 | 2 | ❌ |
| `A-M1-NUM-01-10` | Concepto y representación de número | 1 | ❌ | ❌ |
| `A-M1-NUM-01-11` | Simplificación de fracciones | ❌ | 1 | ❌ |
| `A-M1-NUM-01-15` | Orden y comparación de fracciones | 2 | ❌ | ❌ |
| `A-M1-NUM-01-16` | Orden y comparación de decimales | 1 | 1 | ❌ |
| `A-M1-NUM-01-18` | Adición y sustracción de fracciones | ❌ | 1 | ❌ |
| `A-M1-NUM-01-19` | Multiplicación de fracciones | 3 | 2 | ❌ |
| `A-M1-NUM-01-20` | División de fracciones | ❌ | 1 | ❌ |
| `A-M1-NUM-01-21` | Adición y sustracción de números de | 1 | 1 | ❌ |
| `A-M1-NUM-01-22` | Multiplicación de números decimales | 2 | 2 | ❌ |
| `A-M1-NUM-01-23` | División de números decimales | 2 | 2 | ❌ |
| `A-M1-NUM-01-24` | Modelado de situaciones con números | 1 | ❌ | ❌ |
| `A-M1-NUM-01-25` | Resolución de problemas con números | 3 | 11 | ❌ |
| `A-M1-NUM-02-02` | Conversión de porcentaje a fracción | 1 | 1 | ❌ |
| `A-M1-NUM-02-03` | Conversión de porcentaje a número d | 1 | ❌ | ❌ |
| `A-M1-NUM-02-04` | Conversión de número decimal a porc | ❌ | 1 | ❌ |
| `A-M1-NUM-02-06` | Cálculo directo del porcentaje de u | 3 | 3 | ❌ |
| `A-M1-NUM-02-07` | Determinación del porcentaje entre  | 2 | 2 | ❌ |
| `A-M1-NUM-02-08` | Cálculo de la cantidad total dado u | 3 | 1 | ❌ |
| `A-M1-NUM-02-09` | Aplicación de aumentos porcentuales | 1 | 1 | ❌ |
| `A-M1-NUM-02-10` | Aplicación de disminuciones porcent | 1 | 1 | ❌ |
| `A-M1-NUM-02-11` | Resolución de problemas contextuali | 3 | 4 | ❌ |
| `A-M1-NUM-02-12` | Evaluación de la validez de afirmac | ❌ | 1 | ❌ |
| `A-M1-NUM-03-01` | Potencias de base racional con expo | 6 | 5 | ❌ |
| `A-M1-NUM-03-04` | División de potencias de igual base | ❌ | 1 | ❌ |
| `A-M1-NUM-03-05` | Potencia de una potencia con base r | ❌ | 1 | ❌ |
| `A-M1-NUM-03-06` | Multiplicación de potencias de igua | ❌ | 1 | ❌ |
| `A-M1-NUM-03-11` | Multiplicación de raíces de igual í | 1 | ❌ | ❌ |
| `A-M1-NUM-03-14` | Descomposición y simplificación de  | 1 | 1 | ❌ |
| `A-M1-NUM-03-15` | Racionalización de denominadores co | 1 | ❌ | ❌ |
| `A-M1-NUM-03-17` | Modelado de situaciones con potenci | 1 | 2 | ❌ |
| `A-M1-NUM-03-18` | Resolución de problemas integrados  | ❌ | 1 | ❌ |
| `A-M1-PROB-01-01` | Concepto de tabla de frecuencia par | 2 | ❌ | ❌ |
| `A-M1-PROB-01-02` | Cálculo de frecuencia absoluta en d | 2 | ❌ | ❌ |
| `A-M1-PROB-01-03` | Cálculo de frecuencia relativa | 2 | ❌ | ❌ |
| `A-M1-PROB-01-05` | Interpretación de información en gr | 1 | 2 | ❌ |
| `A-M1-PROB-01-08` | Interpretación de información en gr | ❌ | 4 | ❌ |
| `A-M1-PROB-01-09` | Construcción de gráficos de línea | ❌ | 1 | ❌ |
| `A-M1-PROB-01-11` | Interpretación de información en gr | ❌ | 4 | ❌ |
| `A-M1-PROB-01-15` | Cálculo del promedio aritmético | 2 | 3 | ❌ |
| `A-M1-PROB-01-16` | Interpretación del promedio en cont | ❌ | 1 | ❌ |
| `A-M1-PROB-01-17` | Resolución de problemas inversos de | ❌ | 2 | ❌ |
| `A-M1-PROB-01-18` | Evaluación de afirmaciones basadas  | 4 | 11 | ❌ |
| `A-M1-PROB-02-02` | Cálculo de la media aritmética | 1 | 1 | ❌ |
| `A-M1-PROB-02-03` | Concepto de mediana y orden | ❌ | 1 | ❌ |
| `A-M1-PROB-02-04` | Cálculo de la mediana (cantidad imp | ❌ | 2 | ❌ |
| `A-M1-PROB-02-07` | Determinación de la moda | 1 | 1 | ❌ |
| `A-M1-PROB-02-09` | Cálculo del rango | 1 | ❌ | ❌ |
| `A-M1-PROB-02-11` | Comparación de grupos de datos medi | ❌ | 2 | ❌ |
| `A-M1-PROB-02-12` | Resolución de problemas contextuale | ❌ | 3 | ❌ |
| `A-M1-PROB-03-03` | Cálculo de Cuartiles en datos no ag | ❌ | 1 | ❌ |
| `A-M1-PROB-03-05` | Interpretación de Cuartiles en cont | ❌ | 1 | ❌ |
| `A-M1-PROB-03-07` | Elementos del Diagrama de Cajón (Bo | ❌ | 2 | ❌ |
| `A-M1-PROB-03-08` | Construcción de Diagramas de Cajón | ❌ | 1 | ❌ |
| `A-M1-PROB-04-01` | Concepto de probabilidad clásica (L | 3 | ❌ | ❌ |
| `A-M1-PROB-04-02` | Cálculo de probabilidad de un event | 3 | 2 | ❌ |
| `A-M1-PROB-04-05` | Aplicación de la regla aditiva para | 2 | ❌ | ❌ |
| `A-M1-PROB-04-10` | Cálculo de probabilidad condicional | ❌ | 1 | ❌ |
| `A-M1-PROB-04-12` | Aplicación de la regla multiplicati | ❌ | 1 | ❌ |