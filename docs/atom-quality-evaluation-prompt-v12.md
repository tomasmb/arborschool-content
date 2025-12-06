<role>
Eres un experto evaluador de diseño instruccional y granularidad de aprendizaje.
Tu tarea es evaluar la calidad de átomos de aprendizaje generados a partir de un estándar curricular.
</role>

<context>
## Estándar Canónico

{
  "id": "M1-NUM-01",
  "eje": "numeros",
  "unidad_temario": "Conjunto de los números enteros y racionales",
  "titulo": "Números Enteros y Racionales",
  "descripcion_general": "Este contenido fundamental abarca la comprensión y aplicación de los números enteros (Z) y racionales (Q), incluyendo sus propiedades operacionales, el establecimiento de relaciones de orden y comparación, y la resolución de problemas contextualizados. Se busca que el estudiante desarrolle fluidez en el manejo de estos conjuntos numéricos, interpretando su significado en diversas situaciones y aplicando procedimientos adecuados para su manipulación.",
  "incluye": [
    "Operaciones básicas (suma, resta, multiplicación, división) con números enteros.",
    "Orden y comparación de números enteros (mayor que, menor que, igual a).",
    "Operaciones básicas (suma, resta, multiplicación, división) con números racionales (fracciones y decimales).",
    "Comparación y orden de números racionales.",
    "Resolución de problemas que involucren números enteros y racionales en contextos variados (temperaturas, deudas, proporciones, etc.)."
  ],
  "no_incluye": [
    "Concepto y operaciones con números irracionales (ej. raíz cuadrada de 2, pi).",
    "Concepto y operaciones con números reales como un conjunto unificado.",
    "Concepto y operaciones con números complejos.",
    "Demostraciones formales de propiedades de los conjuntos numéricos.",
    "Teoría de números avanzada (ej. divisibilidad, números primos más allá de la operatoria básica)."
  ],
  "subcontenidos_clave": [
    "Suma y resta de números enteros.",
    "Multiplicación y división de números enteros.",
    "Orden de números enteros en la recta numérica.",
    "Suma y resta de números racionales (fracciones y decimales).",
    "Multiplicación y división de números racionales (fracciones y decimales).",
    "Comparación de números racionales (fracciones y decimales).",
    "Resolución de problemas de la vida cotidiana con números enteros.",
    "Resolución de problemas de la vida cotidiana con números racionales."
  ],
  "ejemplos_conceptuales": [
    "Interpretar una temperatura de -5°C como un número entero negativo y compararla con 2°C.",
    "Comprender que 1/2, 0.5 y 50% son diferentes representaciones del mismo número racional.",
    "Determinar si una deuda de $15.000 es mayor o menor que una deuda de $10.000 en términos de valor absoluto y posición en la recta numérica.",
    "Comparar el rendimiento de dos equipos expresado en fracciones de partidos ganados."
  ],
  "habilidades_relacionadas": [
    {
      "habilidad_id": "resolver_problemas",
      "criterios_relevantes": [
        "Resuelve situaciones rutinarias que involucren la utilización de operatoria o procedimientos básicos.",
        "Resuelve situaciones problemáticas que requieren la utilización de estrategias para su resolución.",
        "Evalúa la validez del resultado derivado de un problema."
      ]
    },
    {
      "habilidad_id": "modelar",
      "criterios_relevantes": [
        "Usa modelos matemáticos de acuerdo a una situación dada.",
        "Interpreta los parámetros y suposiciones de un modelo matemático."
      ]
    },
    {
      "habilidad_id": "representar",
      "criterios_relevantes": [
        "Traduce del lenguaje natural al lenguaje matemático y viceversa.",
        "Interpreta información de diferentes tipos de representaciones en términos de una situación dada.",
        "Transfiere una situación de un sistema de representación a otro."
      ]
    },
    {
      "habilidad_id": "argumentar",
      "criterios_relevantes": [
        "Evalúa la validez de argumentos propuestos en diversos contextos.",
        "Evalúa la validez de una deducción, reconociendo si una afirmación se puede concluir de otras afirmaciones."
      ]
    }
  ],
  "fuentes_temario": {
    "conocimientos_path": "conocimientos.numeros.unidades[0]",
    "descripciones_originales": [
      "Operaciones y orden en el conjunto de los números enteros.",
      "Operaciones y comparación entre números en el conjunto de los números racionales.",
      "Problemas que involucren el conjunto de los números enteros y racionales en diversos contextos."
    ]
  }
}

## Átomos Generados

[
  {
    "id": "A-M1-NUM-01-01",
    "eje": "numeros",
    "standard_ids": [
      "M1-NUM-01"
    ],
    "habilidad_principal": "representar",
    "habilidades_secundarias": [],
    "tipo_atomico": "concepto",
    "titulo": "Concepto y representación de números enteros",
    "descripcion": "El estudiante identifica, define y representa números enteros (positivos, negativos y el cero) en la recta numérica, comprendiendo su naturaleza como extensión de los naturales para representar situaciones de deuda, profundidad o temperatura bajo cero.",
    "criterios_atomicos": [
      "Identifica números enteros en situaciones cotidianas o matemáticas.",
      "Ubica correctamente números enteros positivos y negativos en la recta numérica.",
      "Reconoce el cero como el origen y punto de referencia neutro."
    ],
    "ejemplos_conceptuales": [
      "Ubicar -3, 0 y 5 en una recta numérica.",
      "Asociar '5 grados bajo cero' con el número -5."
    ],
    "prerrequisitos": [],
    "notas_alcance": [
      "No incluye operaciones.",
      "Se limita a la identificación y ubicación posicional."
    ]
  },
  {
    "id": "A-M1-NUM-01-02",
    "eje": "numeros",
    "standard_ids": [
      "M1-NUM-01"
    ],
    "habilidad_principal": "representar",
    "habilidades_secundarias": [],
    "tipo_atomico": "concepto_procedimental",
    "titulo": "Valor absoluto de números enteros",
    "descripcion": "El estudiante interpreta y calcula el valor absoluto de un número entero como su distancia al cero en la recta numérica, sin considerar su signo.",
    "criterios_atomicos": [
      "Calcula el valor absoluto de números enteros positivos y negativos.",
      "Interpreta el valor absoluto como una medida de distancia o magnitud no dirigida."
    ],
    "ejemplos_conceptuales": [
      "Determinar que |-5| = 5 y |5| = 5.",
      "Comprender que una deuda de $1000 (|-1000|) tiene la misma magnitud que un haber de $1000."
    ],
    "prerrequisitos": [
      "A-M1-NUM-01-01"
    ],
    "notas_alcance": [
      "Solo números enteros.",
      "No incluye ecuaciones con valor absoluto."
    ]
  },
  {
    "id": "A-M1-NUM-01-03",
    "eje": "numeros",
    "standard_ids": [
      "M1-NUM-01"
    ],
    "habilidad_principal": "argumentar",
    "habilidades_secundarias": [
      "representar"
    ],
    "tipo_atomico": "concepto_procedimental",
    "titulo": "Orden y comparación de números enteros",
    "descripcion": "El estudiante compara pares o conjuntos de números enteros utilizando los símbolos de orden (>, <, =), justificando su respuesta basándose en la posición en la recta numérica o en la magnitud de los valores.",
    "criterios_atomicos": [
      "Determina la relación de orden (mayor, menor o igual) entre dos números enteros.",
      "Ordena una secuencia de números enteros de forma ascendente o descendente.",
      "Justifica por qué un número negativo con mayor valor absoluto es menor que uno con menor valor absoluto (ej: -10 < -2)."
    ],
    "ejemplos_conceptuales": [
      "Determinar que -8 < -3 porque -8 está más a la izquierda en la recta.",
      "Ordenar: -5, 2, 0, -1, 4."
    ],
    "prerrequisitos": [
      "A-M1-NUM-01-01",
      "A-M1-NUM-01-02"
    ],
    "notas_alcance": [
      "Incluye comparaciones contraintuitivas entre negativos."
    ]
  },
  {
    "id": "A-M1-NUM-01-04",
    "eje": "numeros",
    "standard_ids": [
      "M1-NUM-01"
    ],
    "habilidad_principal": "resolver_problemas",
    "habilidades_secundarias": [],
    "tipo_atomico": "procedimiento",
    "titulo": "Adición de números enteros",
    "descripcion": "El estudiante aplica el algoritmo de la suma para números enteros, distinguiendo entre casos de igual signo (suma de valores absolutos) y distinto signo (resta de valores absolutos).",
    "criterios_atomicos": [
      "Resuelve sumas de enteros con el mismo signo.",
      "Resuelve sumas de enteros con signos diferentes.",
      "Aplica correctamente la regla de los signos para la adición."
    ],
    "ejemplos_conceptuales": [
      "Calcular (-5) + (-3).",
      "Calcular (-8) + 12."
    ],
    "prerrequisitos": [
      "A-M1-NUM-01-01",
      "A-M1-NUM-01-02"
    ],
    "notas_alcance": [
      "Cálculo directo, sin contexto narrativo complejo.",
      "Números de magnitud razonable para cálculo mental o manual."
    ]
  },
  {
    "id": "A-M1-NUM-01-05",
    "eje": "numeros",
    "standard_ids": [
      "M1-NUM-01"
    ],
    "habilidad_principal": "resolver_problemas",
    "habilidades_secundarias": [],
    "tipo_atomico": "procedimiento",
    "titulo": "Sustracción de números enteros",
    "descripcion": "El estudiante transforma la sustracción de enteros en una adición del opuesto aditivo y resuelve la operación resultante.",
    "criterios_atomicos": [
      "Transforma una resta de enteros en la suma del opuesto.",
      "Resuelve sustracciones que involucran números negativos (ej: menos menos)."
    ],
    "ejemplos_conceptuales": [
      "Convertir 5 - (-3) en 5 + 3.",
      "Calcular -4 - 6."
    ],
    "prerrequisitos": [
      "A-M1-NUM-01-04"
    ],
    "notas_alcance": [
      "Se evalúa independientemente de la suma aunque se base en ella.",
      "Enfocado en el manejo del doble signo negativo."
    ]
  },
  {
    "id": "A-M1-NUM-01-06",
    "eje": "numeros",
    "standard_ids": [
      "M1-NUM-01"
    ],
    "habilidad_principal": "resolver_problemas",
    "habilidades_secundarias": [],
    "tipo_atomico": "procedimiento",
    "titulo": "Multiplicación de números enteros",
    "descripcion": "El estudiante aplica el algoritmo de la multiplicación para números enteros, utilizando la regla de los signos para determinar el signo del producto.",
    "criterios_atomicos": [
      "Calcula el producto de dos números enteros.",
      "Aplica correctamente la regla de los signos (menos por menos da más, etc.)."
    ],
    "ejemplos_conceptuales": [
      "Calcular (-4) * (-3).",
      "Calcular 5 * (-2)."
    ],
    "prerrequisitos": [
      "A-M1-NUM-01-01"
    ],
    "notas_alcance": [
      "Tablas de multiplicar básicas hasta 12x12 o cálculos manuales simples."
    ]
  },
  {
    "id": "A-M1-NUM-01-07",
    "eje": "numeros",
    "standard_ids": [
      "M1-NUM-01"
    ],
    "habilidad_principal": "resolver_problemas",
    "habilidades_secundarias": [],
    "tipo_atomico": "procedimiento",
    "titulo": "División de números enteros",
    "descripcion": "El estudiante realiza divisiones exactas de números enteros, aplicando la regla de los signos para determinar el signo del cociente.",
    "criterios_atomicos": [
      "Calcula el cociente exacto de dos números enteros.",
      "Determina el signo del resultado aplicando la regla de los signos."
    ],
    "ejemplos_conceptuales": [
      "Calcular (-20) : 4.",
      "Calcular (-15) : (-3)."
    ],
    "prerrequisitos": [
      "A-M1-NUM-01-06"
    ],
    "notas_alcance": [
      "Solo divisiones exactas (resto cero) dentro de Z."
    ]
  },
  {
    "id": "A-M1-NUM-01-08",
    "eje": "numeros",
    "standard_ids": [
      "M1-NUM-01"
    ],
    "habilidad_principal": "modelar",
    "habilidades_secundarias": [
      "representar"
    ],
    "tipo_atomico": "modelizacion",
    "titulo": "Modelado de situaciones con números enteros",
    "descripcion": "El estudiante traduce situaciones de lenguaje natural que involucran cambios, estados, deudas o posiciones relativas a expresiones matemáticas utilizando números enteros y sus operaciones.",
    "criterios_atomicos": [
      "Identifica la operación (suma, resta, multiplicación) implícita en un enunciado verbal.",
      "Traduce una situación de la vida real a una expresión numérica con enteros (ej: 'bajar 3 pisos' como -3).",
      "Interpreta los parámetros del problema para asignar signos correctos a los datos."
    ],
    "ejemplos_conceptuales": [
      "Expresar 'una deuda de 5000 que se duplica' como -5000 * 2.",
      "Modelar el cambio de temperatura de -2°C a 5°C."
    ],
    "prerrequisitos": [
      "A-M1-NUM-01-01",
      "A-M1-NUM-01-04",
      "A-M1-NUM-01-05",
      "A-M1-NUM-01-06",
      "A-M1-NUM-01-07"
    ],
    "notas_alcance": [
      "Se enfoca en el planteamiento, no necesariamente en el cálculo final.",
      "Contextos: temperatura, dinero, altitud, tiempo."
    ]
  },
  {
    "id": "A-M1-NUM-01-09",
    "eje": "numeros",
    "standard_ids": [
      "M1-NUM-01"
    ],
    "habilidad_principal": "resolver_problemas",
    "habilidades_secundarias": [
      "argumentar"
    ],
    "tipo_atomico": "concepto_procedimental",
    "titulo": "Resolución de problemas contextualizados con enteros",
    "descripcion": "El estudiante resuelve problemas completos que involucran números enteros, integrando el modelado, el cálculo operacional y la interpretación/validación del resultado en el contexto dado.",
    "criterios_atomicos": [
      "Resuelve situaciones problemáticas aplicando estrategias de cálculo con enteros.",
      "Interpreta el resultado numérico en términos del contexto (ej: qué significa un resultado negativo en el problema).",
      "Evalúa la validez del resultado obtenido."
    ],
    "ejemplos_conceptuales": [
      "Calcular el saldo final de una cuenta tras varios depósitos y retiros.",
      "Determinar la variación total de temperatura en un periodo de tiempo."
    ],
    "prerrequisitos": [
      "A-M1-NUM-01-01",
      "A-M1-NUM-01-02",
      "A-M1-NUM-01-03",
      "A-M1-NUM-01-04",
      "A-M1-NUM-01-05",
      "A-M1-NUM-01-06",
      "A-M1-NUM-01-07",
      "A-M1-NUM-01-08"
    ],
    "notas_alcance": [
      "Átomo integrador para el conjunto Z.",
      "Problemas de pasos múltiples."
    ]
  },
  {
    "id": "A-M1-NUM-01-10",
    "eje": "numeros",
    "standard_ids": [
      "M1-NUM-01"
    ],
    "habilidad_principal": "representar",
    "habilidades_secundarias": [],
    "tipo_atomico": "concepto",
    "titulo": "Concepto y representación de números racionales",
    "descripcion": "El estudiante reconoce los números racionales como aquellos que pueden expresarse como fracción a/b (con b distinto de 0), identificando sus formas fraccionarias y decimales.",
    "criterios_atomicos": [
      "Reconoce números racionales en sus distintas representaciones (fracción, decimal).",
      "Identifica que los números enteros son un subconjunto de los racionales.",
      "Representa números racionales simples en la recta numérica."
    ],
    "ejemplos_conceptuales": [
      "Identificar que -0.5, 1/2 y 3 son todos racionales.",
      "Ubicar 3/4 y -1.5 en la recta numérica."
    ],
    "prerrequisitos": [
      "A-M1-NUM-01-01"
    ],
    "notas_alcance": [
      "Incluye decimales finitos y periódicos conceptualmente.",
      "No incluye irracionales."
    ]
  },
  {
    "id": "A-M1-NUM-01-11",
    "eje": "numeros",
    "standard_ids": [
      "M1-NUM-01"
    ],
    "habilidad_principal": "representar",
    "habilidades_secundarias": [],
    "tipo_atomico": "procedimiento",
    "titulo": "Simplificación y equivalencia de fracciones",
    "descripcion": "El estudiante determina si dos fracciones son equivalentes y simplifica fracciones hasta su mínima expresión (fracción irreductible).",
    "criterios_atomicos": [
      "Identifica fracciones equivalentes mediante amplificación o simplificación.",
      "Simplifica fracciones dividiendo numerador y denominador por factores comunes.",
      "Obtiene la fracción irreductible de un número racional dado."
    ],
    "ejemplos_conceptuales": [
      "Determinar que 2/4 es equivalente a 1/2.",
      "Simplificar 15/20 a 3/4."
    ],
    "prerrequisitos": [
      "A-M1-NUM-01-10"
    ],
    "notas_alcance": [
      "Fundamental para operaciones posteriores.",
      "Incluye fracciones negativas."
    ]
  },
  {
    "id": "A-M1-NUM-01-12",
    "eje": "numeros",
    "standard_ids": [
      "M1-NUM-01"
    ],
    "habilidad_principal": "representar",
    "habilidades_secundarias": [
      "resolver_problemas"
    ],
    "tipo_atomico": "procedimiento",
    "titulo": "Conversión de fracción a decimal",
    "descripcion": "El estudiante transforma números racionales de su representación fraccionaria a decimal mediante la división del numerador por el denominador.",
    "criterios_atomicos": [
      "Realiza la división para convertir una fracción a su expresión decimal.",
      "Identifica si el decimal resultante es finito o periódico."
    ],
    "ejemplos_conceptuales": [
      "Convertir 1/4 a 0.25.",
      "Convertir 1/3 a 0.333..."
    ],
    "prerrequisitos": [
      "A-M1-NUM-01-10"
    ],
    "notas_alcance": [
      "Algoritmo de división manual o interpretación."
    ]
  },
  {
    "id": "A-M1-NUM-01-13",
    "eje": "numeros",
    "standard_ids": [
      "M1-NUM-01"
    ],
    "habilidad_principal": "representar",
    "habilidades_secundarias": [
      "resolver_problemas"
    ],
    "tipo_atomico": "procedimiento",
    "titulo": "Conversión de decimal finito a fracción",
    "descripcion": "El estudiante transforma números decimales finitos a su representación fraccionaria utilizando potencias de 10 en el denominador y simplificando el resultado.",
    "criterios_atomicos": [
      "Escribe un decimal finito como una fracción con denominador potencia de 10.",
      "Simplifica la fracción resultante hasta la irreductible."
    ],
    "ejemplos_conceptuales": [
      "Convertir 0.5 a 5/10 y luego a 1/2.",
      "Convertir 1.25 a 125/100."
    ],
    "prerrequisitos": [
      "A-M1-NUM-01-10",
      "A-M1-NUM-01-11"
    ],
    "notas_alcance": [
      "Solo decimales finitos. No incluye conversión de periódicos (requiere álgebra distinta)."
    ]
  },
  {
    "id": "A-M1-NUM-01-14",
    "eje": "numeros",
    "standard_ids": [
      "M1-NUM-01"
    ],
    "habilidad_principal": "argumentar",
    "habilidades_secundarias": [
      "representar"
    ],
    "tipo_atomico": "procedimiento",
    "titulo": "Orden y comparación de números racionales",
    "descripcion": "El estudiante compara pares o conjuntos de números racionales (fracciones y decimales) utilizando estrategias como igualar denominadores, convertir a decimal o multiplicación cruzada.",
    "criterios_atomicos": [
      "Determina la relación de orden (>, <, =) entre dos números racionales.",
      "Ordena una lista mixta de fracciones y decimales.",
      "Justifica el orden establecido utilizando una estrategia matemática válida."
    ],
    "ejemplos_conceptuales": [
      "Comparar 1/3 y 0.3.",
      "Determinar si -1/2 es mayor o menor que -3/4."
    ],
    "prerrequisitos": [
      "A-M1-NUM-01-10",
      "A-M1-NUM-01-12",
      "A-M1-NUM-01-13"
    ],
    "notas_alcance": [
      "Incluye racionales negativos."
    ]
  },
  {
    "id": "A-M1-NUM-01-15",
    "eje": "numeros",
    "standard_ids": [
      "M1-NUM-01"
    ],
    "habilidad_principal": "resolver_problemas",
    "habilidades_secundarias": [],
    "tipo_atomico": "procedimiento",
    "titulo": "Adición de fracciones",
    "descripcion": "El estudiante suma fracciones, incluyendo casos con igual y distinto denominador, utilizando el Mínimo Común Múltiplo cuando es necesario.",
    "criterios_atomicos": [
      "Resuelve sumas de fracciones con igual denominador.",
      "Resuelve sumas de fracciones con distinto denominador calculando el MCM.",
      "Simplifica el resultado de la suma si es posible."
    ],
    "ejemplos_conceptuales": [
      "Sumar 1/2 + 1/3.",
      "Sumar -2/5 + 1/5."
    ],
    "prerrequisitos": [
      "A-M1-NUM-01-04",
      "A-M1-NUM-01-11"
    ],
    "notas_alcance": [
      "Incluye fracciones negativas (operando con reglas de Z)."
    ]
  },
  {
    "id": "A-M1-NUM-01-16",
    "eje": "numeros",
    "standard_ids": [
      "M1-NUM-01"
    ],
    "habilidad_principal": "resolver_problemas",
    "habilidades_secundarias": [],
    "tipo_atomico": "procedimiento",
    "titulo": "Sustracción de fracciones",
    "descripcion": "El estudiante resta fracciones, manejando igual y distinto denominador, y aplicando las reglas de signos de los enteros en los numeradores.",
    "criterios_atomicos": [
      "Resuelve restas de fracciones con igual y distinto denominador.",
      "Aplica correctamente la sustracción cuando hay numeradores negativos.",
      "Simplifica el resultado final."
    ],
    "ejemplos_conceptuales": [
      "Restar 3/4 - 1/2.",
      "Restar 1/3 - 5/6."
    ],
    "prerrequisitos": [
      "A-M1-NUM-01-05",
      "A-M1-NUM-01-11",
      "A-M1-NUM-01-15"
    ],
    "notas_alcance": [
      "Evaluación independiente de la suma por la complejidad del orden y signos en la resta."
    ]
  },
  {
    "id": "A-M1-NUM-01-17",
    "eje": "numeros",
    "standard_ids": [
      "M1-NUM-01"
    ],
    "habilidad_principal": "resolver_problemas",
    "habilidades_secundarias": [],
    "tipo_atomico": "procedimiento",
    "titulo": "Multiplicación de fracciones",
    "descripcion": "El estudiante multiplica fracciones aplicando el algoritmo directo (numerador por numerador, denominador por denominador) y la regla de los signos.",
    "criterios_atomicos": [
      "Calcula el producto de dos o más fracciones.",
      "Aplica la regla de los signos en la multiplicación de racionales.",
      "Simplifica el resultado o simplifica antes de multiplicar."
    ],
    "ejemplos_conceptuales": [
      "Multiplicar (2/3) * (-1/5).",
      "Multiplicar 3 * (1/4)."
    ],
    "prerrequisitos": [
      "A-M1-NUM-01-06",
      "A-M1-NUM-01-11"
    ],
    "notas_alcance": [
      "Incluye multiplicación de entero por fracción."
    ]
  },
  {
    "id": "A-M1-NUM-01-18",
    "eje": "numeros",
    "standard_ids": [
      "M1-NUM-01"
    ],
    "habilidad_principal": "resolver_problemas",
    "habilidades_secundarias": [],
    "tipo_atomico": "procedimiento",
    "titulo": "División de fracciones",
    "descripcion": "El estudiante divide fracciones utilizando algoritmos como la multiplicación por el inverso multiplicativo (dar vuelta la segunda fracción) o multiplicación cruzada.",
    "criterios_atomicos": [
      "Calcula el cociente de dos fracciones.",
      "Aplica la regla de los signos en la división de racionales.",
      "Interpreta la división de fracciones compuestas (fracción sobre fracción)."
    ],
    "ejemplos_conceptuales": [
      "Dividir (1/2) : (1/3).",
      "Dividir (-2/5) : 4."
    ],
    "prerrequisitos": [
      "A-M1-NUM-01-07",
      "A-M1-NUM-01-11",
      "A-M1-NUM-01-17"
    ],
    "notas_alcance": [
      "Algoritmo distinto a la multiplicación (inversión)."
    ]
  },
  {
    "id": "A-M1-NUM-01-19",
    "eje": "numeros",
    "standard_ids": [
      "M1-NUM-01"
    ],
    "habilidad_principal": "resolver_problemas",
    "habilidades_secundarias": [],
    "tipo_atomico": "procedimiento",
    "titulo": "Adición de números decimales",
    "descripcion": "El estudiante suma números decimales alineando correctamente la coma decimal y respetando el valor posicional.",
    "criterios_atomicos": [
      "Alinea correctamente los números decimales según la coma.",
      "Realiza la suma respetando el valor posicional y el acarreo.",
      "Maneja sumas de decimales positivos y negativos."
    ],
    "ejemplos_conceptuales": [
      "Sumar 12.5 + 3.04.",
      "Sumar -2.1 + 5.5."
    ],
    "prerrequisitos": [
      "A-M1-NUM-01-04",
      "A-M1-NUM-01-10"
    ],
    "notas_alcance": [
      "Decimales finitos."
    ]
  },
  {
    "id": "A-M1-NUM-01-20",
    "eje": "numeros",
    "standard_ids": [
      "M1-NUM-01"
    ],
    "habilidad_principal": "resolver_problemas",
    "habilidades_secundarias": [],
    "tipo_atomico": "procedimiento",
    "titulo": "Sustracción de números decimales",
    "descripcion": "El estudiante resta números decimales alineando la coma, añadiendo ceros si es necesario para igualar cifras decimales y manejando el préstamo entre posiciones.",
    "criterios_atomicos": [
      "Alinea correctamente los decimales para la resta.",
      "Completa con ceros las cifras decimales faltantes para operar.",
      "Resuelve restas que involucran decimales negativos."
    ],
    "ejemplos_conceptuales": [
      "Restar 5.0 - 2.35.",
      "Restar -1.2 - 3.4."
    ],
    "prerrequisitos": [
      "A-M1-NUM-01-05",
      "A-M1-NUM-01-10",
      "A-M1-NUM-01-19"
    ],
    "notas_alcance": [
      "Evaluación independiente por la mecánica de completar ceros y préstamo."
    ]
  },
  {
    "id": "A-M1-NUM-01-21",
    "eje": "numeros",
    "standard_ids": [
      "M1-NUM-01"
    ],
    "habilidad_principal": "resolver_problemas",
    "habilidades_secundarias": [],
    "tipo_atomico": "procedimiento",
    "titulo": "Multiplicación de números decimales",
    "descripcion": "El estudiante multiplica números decimales operando como si fueran enteros y ubicando la coma en el producto final según la suma de cifras decimales de los factores.",
    "criterios_atomicos": [
      "Realiza la multiplicación numérica ignorando inicialmente la coma.",
      "Ubica correctamente la coma decimal en el resultado final contando las cifras decimales totales.",
      "Aplica la regla de los signos."
    ],
    "ejemplos_conceptuales": [
      "Multiplicar 0.2 * 0.3 (resultado 0.06).",
      "Multiplicar -1.5 * 2."
    ],
    "prerrequisitos": [
      "A-M1-NUM-01-06",
      "A-M1-NUM-01-10"
    ],
    "notas_alcance": [
      "Algoritmo distinto a la suma/resta (no requiere alinear coma)."
    ]
  },
  {
    "id": "A-M1-NUM-01-22",
    "eje": "numeros",
    "standard_ids": [
      "M1-NUM-01"
    ],
    "habilidad_principal": "resolver_problemas",
    "habilidades_secundarias": [],
    "tipo_atomico": "procedimiento",
    "titulo": "División de números decimales",
    "descripcion": "El estudiante divide números decimales transformándolos en divisiones equivalentes de enteros (moviendo la coma) o dividiendo directamente y manejando la posición decimal en el cociente.",
    "criterios_atomicos": [
      "Transforma la división de decimales para eliminar la coma del divisor.",
      "Calcula el cociente ubicando correctamente la coma decimal.",
      "Aplica la regla de los signos."
    ],
    "ejemplos_conceptuales": [
      "Dividir 4.5 : 0.5.",
      "Dividir 10 : 0.2."
    ],
    "prerrequisitos": [
      "A-M1-NUM-01-07",
      "A-M1-NUM-01-10"
    ],
    "notas_alcance": [
      "Algoritmo complejo que requiere manipulación de potencias de 10 implícita."
    ]
  },
  {
    "id": "A-M1-NUM-01-23",
    "eje": "numeros",
    "standard_ids": [
      "M1-NUM-01"
    ],
    "habilidad_principal": "modelar",
    "habilidades_secundarias": [
      "representar"
    ],
    "tipo_atomico": "modelizacion",
    "titulo": "Modelado de situaciones con números racionales",
    "descripcion": "El estudiante traduce situaciones de reparto, proporciones, medidas o variaciones continuas a expresiones matemáticas que involucran fracciones o decimales.",
    "criterios_atomicos": [
      "Identifica la necesidad de usar números racionales (no enteros) en una situación dada.",
      "Traduce enunciados verbales a expresiones con fracciones o decimales (ej: 'la mitad de' como 1/2 * X).",
      "Interpreta parámetros como tasas o proporciones en el modelo."
    ],
    "ejemplos_conceptuales": [
      "Modelar 'comprar 3/4 de kilo de pan a $1000 el kilo'.",
      "Expresar una variación de temperatura de 1.5 grados por hora."
    ],
    "prerrequisitos": [
      "A-M1-NUM-01-10",
      "A-M1-NUM-01-15",
      "A-M1-NUM-01-16",
      "A-M1-NUM-01-17",
      "A-M1-NUM-01-18",
      "A-M1-NUM-01-19",
      "A-M1-NUM-01-20",
      "A-M1-NUM-01-21",
      "A-M1-NUM-01-22"
    ],
    "notas_alcance": [
      "Enfoque en el planteamiento de la expresión matemática."
    ]
  },
  {
    "id": "A-M1-NUM-01-24",
    "eje": "numeros",
    "standard_ids": [
      "M1-NUM-01"
    ],
    "habilidad_principal": "resolver_problemas",
    "habilidades_secundarias": [
      "argumentar"
    ],
    "tipo_atomico": "concepto_procedimental",
    "titulo": "Resolución de problemas contextualizados con racionales",
    "descripcion": "El estudiante resuelve problemas de la vida cotidiana o científicos que involucran el conjunto de los racionales (Q), integrando modelado, conversión entre representaciones, operatoria y validación.",
    "criterios_atomicos": [
      "Selecciona y aplica estrategias para resolver problemas con fracciones y decimales.",
      "Realiza conversiones entre fracción y decimal si el problema lo requiere para operar.",
      "Interpreta y evalúa la validez del resultado en el contexto del problema."
    ],
    "ejemplos_conceptuales": [
      "Calcular cuánto dinero sobra después de gastar 1/3 y luego 1/2 del resto.",
      "Comparar precios unitarios expresados en diferentes unidades o formatos."
    ],
    "prerrequisitos": [
      "A-M1-NUM-01-01",
      "A-M1-NUM-01-02",
      "A-M1-NUM-01-03",
      "A-M1-NUM-01-04",
      "A-M1-NUM-01-05",
      "A-M1-NUM-01-06",
      "A-M1-NUM-01-07",
      "A-M1-NUM-01-10",
      "A-M1-NUM-01-11",
      "A-M1-NUM-01-12",
      "A-M1-NUM-01-13",
      "A-M1-NUM-01-14",
      "A-M1-NUM-01-15",
      "A-M1-NUM-01-16",
      "A-M1-NUM-01-17",
      "A-M1-NUM-01-18",
      "A-M1-NUM-01-19",
      "A-M1-NUM-01-20",
      "A-M1-NUM-01-21",
      "A-M1-NUM-01-22",
      "A-M1-NUM-01-23"
    ],
    "notas_alcance": [
      "Átomo integrador final del estándar.",
      "Requiere dominio de Z y Q."
    ]
  }
]


</context>

<task>
Evalúa la calidad de los átomos generados según los siguientes criterios:

1. **Fidelidad**: ¿Los átomos cubren completamente el estándar sin agregar contenido fuera de alcance?
2. **Granularidad**: ¿Cada átomo cumple los 6 criterios de granularidad atómica?
3. **Completitud**: ¿Se cubren todos los aspectos del estándar (conceptuales y procedimentales)?
4. **Calidad del contenido**: ¿Las descripciones, criterios y ejemplos son claros y apropiados?
5. **Prerrequisitos**: ¿Los prerrequisitos están correctamente identificados y son exhaustivos en átomos integradores?
6. **Cobertura**: ¿No hay duplicaciones ni áreas faltantes?
</task>

<rules>
1. Evalúa cada átomo individualmente y luego el conjunto completo.
2. Identifica problemas específicos con ejemplos concretos.
3. Proporciona recomendaciones accionables.
4. Usa el formato JSON estructurado especificado.
</rules>

<output_format>
Responde SOLO con un objeto JSON válido con esta estructura:

{
  "evaluation_summary": {
    "total_atoms": <número>,
    "atoms_passing_all_checks": <número>,
    "atoms_with_issues": <número>,
    "overall_quality": "excellent" | "good" | "needs_improvement",
    "coverage_assessment": "complete" | "incomplete",
    "granularity_assessment": "appropriate" | "too_coarse" | "too_fine"
  },
  "atoms_evaluation": [
    {
      "atom_id": "<id>",
      "overall_score": "excellent" | "good" | "needs_improvement",
      "fidelity": {
        "score": "pass" | "warning" | "fail",
        "issues": ["<problema 1>", "<problema 2>"]
      },
      "granularity": {
        "score": "pass" | "warning" | "fail",
        "issues": ["<problema 1>", "<problema 2>"],
        "checks": {
          "single_cognitive_intention": true | false,
          "reasonable_working_memory": true | false,
          "prerequisite_independence": true | false,
          "assessment_independence": true | false,
          "generalization_boundary": true | false,
          "integrator_validity": true | false
        }
      },
      "completeness": {
        "score": "pass" | "warning" | "fail",
        "issues": ["<problema 1>", "<problema 2>"]
      },
      "content_quality": {
        "score": "pass" | "warning" | "fail",
        "issues": ["<problema 1>", "<problema 2>"]
      },
      "prerequisites": {
        "score": "pass" | "warning" | "fail",
        "issues": ["<problema 1>", "<problema 2>"]
      },
      "recommendations": ["<recomendación 1>", "<recomendación 2>"]
    }
  ],
  "coverage_analysis": {
    "standards_covered": ["<standard_id>"],
    "coverage_completeness": "complete" | "incomplete",
    "missing_areas": ["<área faltante 1>", "<área faltante 2>"],
    "duplication_issues": ["<problema 1>", "<problema 2>"],
    "conceptual_coverage": "present" | "missing",
    "procedural_coverage": "present" | "missing"
  },
  "global_recommendations": [
    "<recomendación global 1>",
    "<recomendación global 2>"
  ]
}
</output_format>

<final_instruction>
Basándote en el estándar y los átomos generados, realiza una evaluación exhaustiva.
Identifica problemas específicos, especialmente relacionados con:
- Separación de procedimientos con estrategias cognitivas diferentes
- Separación de versiones simples vs complejas del mismo procedimiento
- Prerrequisitos exhaustivos en átomos integradores (tanto conceptuales como procedimentales)
- Independencia de evaluación (si dos cosas pueden evaluarse por separado, deben ser átomos separados)
- Consistencia entre habilidad_principal y criterios_atomicos
- Uso adecuado de notas_alcance para acotar complejidad sin exceder el estándar

Responde SOLO con el JSON, sin explicaciones adicionales.
</final_instruction>
