# Prompt Completo de Validación - M1-ALG-01

Este prompt contiene todos los datos necesarios para validar los átomos.
Cópialo completo y úsalo en OpenAI o Gemini.

---

<role>
Eres un experto evaluador de diseño instruccional y granularidad de aprendizaje.
Tu tarea es evaluar la calidad de átomos de aprendizaje generados a partir de un estándar curricular.
</role>

<context>
## Estándar Canónico

{
  "id": "M1-ALG-01",
  "eje": "algebra_y_funciones",
  "unidad_temario": "Expresiones algebraicas",
  "titulo": "Expresiones algebraicas",
  "descripcion_general": "Este contenido se centra en la comprensión y manipulación de expresiones algebraicas, abarcando desde el reconocimiento y aplicación de productos notables hasta la factorización y el desarrollo de expresiones. Se profundiza en la operatoria básica (suma, resta, multiplicación y división simple) con polinomios y monomios, y se aplica este conocimiento a la resolución de problemas en diversos contextos, fomentando la traducción entre el lenguaje natural y el matemático.",
  "incluye": [
    "Identificación y aplicación de productos notables (ej. cuadrado de binomio, suma por diferencia, cubo de binomio).",
    "Desarrollo de expresiones algebraicas utilizando productos notables y la propiedad distributiva.",
    "Factorización de expresiones algebraicas (ej. factor común, trinomio cuadrado perfecto, diferencia de cuadrados, trinomios de la forma x^2+bx+c).",
    "Realización de operaciones de suma, resta, multiplicación y división simple con expresiones algebraicas.",
    "Simplificación de expresiones algebraicas mediante factorización y operatoria.",
    "Resolución de problemas contextualizados que requieren el uso y manipulación de expresiones algebraicas."
  ],
  "no_incluye": [
    "Resolución de ecuaciones o inecuaciones algebraicas (corresponde a otras unidades temáticas).",
    "Operaciones con fracciones algebraicas complejas (más allá de la simplificación básica de monomios o binomios simples).",
    "División de polinomios por polinomios de grado mayor a uno.",
    "Conceptos de funciones algebraicas (dominio, recorrido, gráfica) o sus transformaciones.",
    "Demostraciones formales de identidades algebraicas complejas o teoremas."
  ],
  "subcontenidos_clave": [
    "Reconocimiento de patrones de productos notables.",
    "Aplicación de fórmulas de productos notables para desarrollar expresiones.",
    "Identificación de factores comunes en expresiones algebraicas.",
    "Factorización de trinomios y binomios especiales.",
    "Suma y resta de monomios y polinomios.",
    "Multiplicación de monomios y polinomios.",
    "División de monomios y polinomios por monomios.",
    "Traducción de enunciados verbales a expresiones algebraicas.",
    "Evaluación de expresiones algebraicas para valores numéricos dados."
  ],
  "ejemplos_conceptuales": [
    "Comprender que el área de un cuadrado de lado (x+y) se puede expresar como (x+y)^2 y desarrollar su significado geométrico.",
    "Visualizar la factorización de x^2 - y^2 como la diferencia de dos áreas cuadradas que se reconfiguran en un rectángulo de lados (x-y) y (x+y).",
    "Interpretar una expresión como 2x + 3y como el costo total de comprar 'x' unidades de un producto a $2 cada uno y 'y' unidades de otro a $3 cada uno."
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
        "Interpreta los parámetros y suposiciones de un modelo matemático.",
        "Ajusta modelos matemáticos de acuerdo a una situación planteada.",
        "Evalúa modelos matemáticos de acuerdo a una situación planteada."
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
        "Identifica en procedimientos o demostraciones matemáticas la existencia de errores.",
        "Evalúa la validez de una deducción, reconociendo si una afirmación se puede concluir de otras afirmaciones."
      ]
    }
  ],
  "fuentes_temario": {
    "conocimientos_path": "conocimientos.algebra_y_funciones.unidades[0]",
    "descripciones_originales": [
      "Productos notables.",
      "Factorizaciones y desarrollo de expresiones algebraicas.",
      "Operatoria con expresiones algebraicas.",
      "Problemas que involucren expresiones algebraicas en diversos contextos."
    ]
  }
}

## Átomos Generados

[
  {
    "id": "A-M1-ALG-01-01",
    "eje": "algebra_y_funciones",
    "standard_ids": [
      "M1-ALG-01"
    ],
    "habilidad_principal": "representar",
    "habilidades_secundarias": [],
    "tipo_atomico": "concepto",
    "titulo": "Elementos de expresiones algebraicas",
    "descripcion": "El estudiante identifica y define los componentes básicos de una expresión algebraica (término, coeficiente numérico, factor literal y grado) para distinguir entre monomios y polinomios.",
    "criterios_atomicos": [
      "Identifica el coeficiente numérico y el factor literal en un término dado.",
      "Determina el grado de un término algebraico.",
      "Clasifica expresiones algebraicas según su número de términos (monomio, binomio, trinomio, polinomio)."
    ],
    "ejemplos_conceptuales": [
      "En el término -3x^2y, el coeficiente es -3 y el factor literal es x^2y.",
      "La expresión 2a + 3b es un binomio."
    ],
    "prerrequisitos": [],
    "notas_alcance": [
      "Se limita a definiciones básicas necesarias para la operatoria posterior.",
      "No incluye análisis de polinomios de múltiples variables complejos más allá de la identificación visual."
    ]
  },
  {
    "id": "A-M1-ALG-01-02",
    "eje": "algebra_y_funciones",
    "standard_ids": [
      "M1-ALG-01"
    ],
    "habilidad_principal": "representar",
    "habilidades_secundarias": [
      "modelar"
    ],
    "tipo_atomico": "representacion",
    "titulo": "Traducción de lenguaje natural a algebraico",
    "descripcion": "El estudiante traduce enunciados verbales simples y compuestos a expresiones algebraicas, utilizando variables para representar cantidades desconocidas.",
    "criterios_atomicos": [
      "Escribe una expresión algebraica que representa un enunciado verbal simple (ej. 'el doble de un número').",
      "Construye expresiones algebraicas a partir de situaciones descritas en lenguaje natural que involucran más de una operación."
    ],
    "ejemplos_conceptuales": [
      "Traducir 'la suma del cuadrado de un número y su triple' como x^2 + 3x.",
      "Expresar 'el perímetro de un rectángulo de largo x y ancho y' como 2x + 2y."
    ],
    "prerrequisitos": [
      "A-M1-ALG-01-01"
    ],
    "notas_alcance": [
      "Se enfoca en la construcción de la expresión, no en la resolución de ecuaciones.",
      "Incluye contextos cotidianos y geométricos simples."
    ]
  },
  {
    "id": "A-M1-ALG-01-03",
    "eje": "algebra_y_funciones",
    "standard_ids": [
      "M1-ALG-01"
    ],
    "habilidad_principal": "representar",
    "habilidades_secundarias": [],
    "tipo_atomico": "representacion",
    "titulo": "Traducción de lenguaje algebraico a natural",
    "descripcion": "El estudiante interpreta expresiones algebraicas dadas y las expresa en lenguaje natural o describe la relación matemática que representan.",
    "criterios_atomicos": [
      "Describe verbalmente el significado de una expresión algebraica dada.",
      "Asocia una expresión algebraica con una descripción verbal correspondiente."
    ],
    "ejemplos_conceptuales": [
      "Interpretar 2(x+y) como 'el doble de la suma de dos números'.",
      "Describir x/2 - 1 como 'la mitad de un número disminuida en uno'."
    ],
    "prerrequisitos": [
      "A-M1-ALG-01-01"
    ],
    "notas_alcance": [
      "Operación inversa a la traducción natural-algebraica, evaluable por separado."
    ]
  },
  {
    "id": "A-M1-ALG-01-04",
    "eje": "algebra_y_funciones",
    "standard_ids": [
      "M1-ALG-01"
    ],
    "habilidad_principal": "resolver_problemas",
    "habilidades_secundarias": [],
    "tipo_atomico": "procedimiento",
    "titulo": "Evaluación de expresiones algebraicas",
    "descripcion": "El estudiante calcula el valor numérico de una expresión algebraica sustituyendo las variables por valores numéricos específicos y respetando la jerarquía de operaciones.",
    "criterios_atomicos": [
      "Sustituye correctamente valores numéricos en las variables de una expresión.",
      "Calcula el resultado final respetando la jerarquía de operaciones y reglas de signos."
    ],
    "ejemplos_conceptuales": [
      "Evaluar 3x - 2y para x=2, y=-1.",
      "Calcular el valor de a^2 + b para a=3 y b=5."
    ],
    "prerrequisitos": [
      "A-M1-ALG-01-01"
    ],
    "notas_alcance": [
      "Incluye enteros, decimales y fracciones simples como valores de entrada.",
      "Requiere dominio previo de aritmética básica (números enteros y racionales)."
    ]
  },
  {
    "id": "A-M1-ALG-01-05",
    "eje": "algebra_y_funciones",
    "standard_ids": [
      "M1-ALG-01"
    ],
    "habilidad_principal": "resolver_problemas",
    "habilidades_secundarias": [],
    "tipo_atomico": "procedimiento",
    "titulo": "Reducción de términos semejantes",
    "descripcion": "El estudiante simplifica expresiones algebraicas sumando o restando los coeficientes de términos que tienen el mismo factor literal.",
    "criterios_atomicos": [
      "Identifica términos semejantes en una expresión algebraica.",
      "Reduce expresiones algebraicas aplicando suma y resta de coeficientes a términos semejantes."
    ],
    "ejemplos_conceptuales": [
      "Simplificar 3a + 2b - a + 5b como 2a + 7b.",
      "Reducir 4x^2 + 3x - 2x^2 como 2x^2 + 3x."
    ],
    "prerrequisitos": [
      "A-M1-ALG-01-01"
    ],
    "notas_alcance": [
      "Base para la suma y resta de polinomios.",
      "Incluye uso de paréntesis para agrupar términos."
    ]
  },
  {
    "id": "A-M1-ALG-01-06",
    "eje": "algebra_y_funciones",
    "standard_ids": [
      "M1-ALG-01"
    ],
    "habilidad_principal": "resolver_problemas",
    "habilidades_secundarias": [],
    "tipo_atomico": "procedimiento",
    "titulo": "Multiplicación de monomios",
    "descripcion": "El estudiante multiplica dos o más monomios aplicando las propiedades de las potencias y la multiplicación de coeficientes.",
    "criterios_atomicos": [
      "Multiplica los coeficientes numéricos respetando la regla de los signos.",
      "Aplica la propiedad de multiplicación de potencias de igual base para la parte literal."
    ],
    "ejemplos_conceptuales": [
      "Multiplicar (3x^2) por (-2x^3) para obtener -6x^5.",
      "Calcular (2ab)(3a^2) = 6a^3b."
    ],
    "prerrequisitos": [
      "A-M1-ALG-01-01"
    ],
    "notas_alcance": [
      "Requiere conocimiento previo de propiedades de potencias."
    ]
  },
  {
    "id": "A-M1-ALG-01-07",
    "eje": "algebra_y_funciones",
    "standard_ids": [
      "M1-ALG-01"
    ],
    "habilidad_principal": "resolver_problemas",
    "habilidades_secundarias": [],
    "tipo_atomico": "procedimiento",
    "titulo": "Multiplicación de monomio por polinomio",
    "descripcion": "El estudiante aplica la propiedad distributiva para multiplicar un monomio por cada término de un polinomio.",
    "criterios_atomicos": [
      "Aplica la propiedad distributiva correctamente.",
      "Obtiene el polinomio resultante realizando las multiplicaciones de monomios correspondientes."
    ],
    "ejemplos_conceptuales": [
      "Desarrollar 2x(x + 3y) como 2x^2 + 6xy.",
      "Multiplicar -3a(a - b + 2) = -3a^2 + 3ab - 6a."
    ],
    "prerrequisitos": [
      "A-M1-ALG-01-06"
    ],
    "notas_alcance": [
      "Paso fundamental antes de la multiplicación de polinomios."
    ]
  },
  {
    "id": "A-M1-ALG-01-08",
    "eje": "algebra_y_funciones",
    "standard_ids": [
      "M1-ALG-01"
    ],
    "habilidad_principal": "resolver_problemas",
    "habilidades_secundarias": [],
    "tipo_atomico": "procedimiento",
    "titulo": "Multiplicación de polinomios",
    "descripcion": "El estudiante multiplica dos polinomios aplicando la propiedad distributiva término a término y reduciendo términos semejantes si es necesario.",
    "criterios_atomicos": [
      "Multiplica cada término del primer polinomio por cada término del segundo polinomio.",
      "Reduce los términos semejantes en el resultado final."
    ],
    "ejemplos_conceptuales": [
      "Multiplicar (x + 2)(x + 3) obteniendo x^2 + 5x + 6.",
      "Desarrollar (a + b)(c + d) = ac + ad + bc + bd."
    ],
    "prerrequisitos": [
      "A-M1-ALG-01-05",
      "A-M1-ALG-01-07"
    ],
    "notas_alcance": [
      "Incluye binomio por binomio y binomio por trinomio.",
      "Se distingue de los productos notables por ser el algoritmo general."
    ]
  },
  {
    "id": "A-M1-ALG-01-09",
    "eje": "algebra_y_funciones",
    "standard_ids": [
      "M1-ALG-01"
    ],
    "habilidad_principal": "resolver_problemas",
    "habilidades_secundarias": [],
    "tipo_atomico": "procedimiento",
    "titulo": "División de monomios",
    "descripcion": "El estudiante divide un monomio por otro monomio simplificando coeficientes y aplicando propiedades de potencias (resta de exponentes).",
    "criterios_atomicos": [
      "Simplifica o divide los coeficientes numéricos.",
      "Aplica la propiedad de división de potencias de igual base para las variables."
    ],
    "ejemplos_conceptuales": [
      "Dividir 8x^5 entre 2x^2 para obtener 4x^3.",
      "Simplificar (15a^3b^2) / (3ab)."
    ],
    "prerrequisitos": [
      "A-M1-ALG-01-01"
    ],
    "notas_alcance": [
      "Se asume que el divisor es distinto de cero.",
      "Resultados con exponentes enteros (positivos o cero en este nivel introductorio)."
    ]
  },
  {
    "id": "A-M1-ALG-01-10",
    "eje": "algebra_y_funciones",
    "standard_ids": [
      "M1-ALG-01"
    ],
    "habilidad_principal": "resolver_problemas",
    "habilidades_secundarias": [],
    "tipo_atomico": "procedimiento",
    "titulo": "División de polinomio por monomio",
    "descripcion": "El estudiante divide un polinomio por un monomio, dividiendo cada término del polinomio por el monomio divisor.",
    "criterios_atomicos": [
      "Distribuye el divisor monomio a cada término del polinomio.",
      "Realiza las divisiones de monomios resultantes correctamente."
    ],
    "ejemplos_conceptuales": [
      "Dividir (4x^3 + 6x^2) entre 2x obteniendo 2x^2 + 3x.",
      "Simplificar (9a^2b - 3ab) / 3ab."
    ],
    "prerrequisitos": [
      "A-M1-ALG-01-09"
    ],
    "notas_alcance": [
      "Excluye explícitamente la división de polinomio por polinomio (ej. Ruffini o división larga) según el estándar."
    ]
  },
  {
    "id": "A-M1-ALG-01-11",
    "eje": "algebra_y_funciones",
    "standard_ids": [
      "M1-ALG-01"
    ],
    "habilidad_principal": "resolver_problemas",
    "habilidades_secundarias": [],
    "tipo_atomico": "concepto_procedimental",
    "titulo": "Producto notable: Cuadrado de binomio",
    "descripcion": "El estudiante reconoce y desarrolla el cuadrado de un binomio utilizando la fórmula específica (cuadrado del primero, más/menos el doble del primero por el segundo, más el cuadrado del segundo) sin recurrir a la multiplicación término a término.",
    "criterios_atomicos": [
      "Identifica expresiones que corresponden a un cuadrado de binomio (a ± b)^2.",
      "Aplica la fórmula (a ± b)^2 = a^2 ± 2ab + b^2 para desarrollar la expresión."
    ],
    "ejemplos_conceptuales": [
      "Desarrollar (x + 3)^2 como x^2 + 6x + 9.",
      "Calcular (2a - 5)^2 aplicando la fórmula."
    ],
    "prerrequisitos": [
      "A-M1-ALG-01-06"
    ],
    "notas_alcance": [
      "El foco es el uso del patrón/fórmula, no la multiplicación distributiva general."
    ]
  },
  {
    "id": "A-M1-ALG-01-12",
    "eje": "algebra_y_funciones",
    "standard_ids": [
      "M1-ALG-01"
    ],
    "habilidad_principal": "resolver_problemas",
    "habilidades_secundarias": [],
    "tipo_atomico": "concepto_procedimental",
    "titulo": "Producto notable: Suma por diferencia",
    "descripcion": "El estudiante reconoce y desarrolla el producto de una suma por su diferencia utilizando la fórmula de diferencia de cuadrados.",
    "criterios_atomicos": [
      "Identifica la estructura (a + b)(a - b).",
      "Aplica la fórmula (a + b)(a - b) = a^2 - b^2 para obtener el resultado directo."
    ],
    "ejemplos_conceptuales": [
      "Desarrollar (x + 4)(x - 4) como x^2 - 16.",
      "Calcular (3y + 2)(3y - 2) = 9y^2 - 4."
    ],
    "prerrequisitos": [
      "A-M1-ALG-01-06"
    ],
    "notas_alcance": [
      "Se evalúa la aplicación directa del patrón."
    ]
  },
  {
    "id": "A-M1-ALG-01-13",
    "eje": "algebra_y_funciones",
    "standard_ids": [
      "M1-ALG-01"
    ],
    "habilidad_principal": "resolver_problemas",
    "habilidades_secundarias": [],
    "tipo_atomico": "concepto_procedimental",
    "titulo": "Producto notable: Cubo de binomio",
    "descripcion": "El estudiante reconoce y desarrolla el cubo de un binomio utilizando la fórmula correspondiente.",
    "criterios_atomicos": [
      "Identifica expresiones de la forma (a ± b)^3.",
      "Aplica la fórmula (a ± b)^3 = a^3 ± 3a^2b + 3ab^2 ± b^3."
    ],
    "ejemplos_conceptuales": [
      "Desarrollar (x + 2)^3 como x^3 + 6x^2 + 12x + 8.",
      "Aplicar la fórmula para (y - 1)^3."
    ],
    "prerrequisitos": [
      "A-M1-ALG-01-06"
    ],
    "notas_alcance": [
      "Se limita a coeficientes manejables para cálculo mental o simple."
    ]
  },
  {
    "id": "A-M1-ALG-01-14",
    "eje": "algebra_y_funciones",
    "standard_ids": [
      "M1-ALG-01"
    ],
    "habilidad_principal": "resolver_problemas",
    "habilidades_secundarias": [],
    "tipo_atomico": "concepto_procedimental",
    "titulo": "Producto notable: Binomios con término común",
    "descripcion": "El estudiante desarrolla el producto de dos binomios que comparten un término común utilizando el patrón (x+a)(x+b) = x^2 + (a+b)x + ab.",
    "criterios_atomicos": [
      "Identifica el término común y los términos no comunes.",
      "Aplica el patrón para obtener el trinomio resultante sin multiplicar término a término."
    ],
    "ejemplos_conceptuales": [
      "Desarrollar (x + 3)(x + 5) como x^2 + 8x + 15.",
      "Calcular (x - 2)(x + 4) sumando y multiplicando los términos no comunes."
    ],
    "prerrequisitos": [
      "A-M1-ALG-01-06"
    ],
    "notas_alcance": [
      "Prerrequisito conceptual para la factorización de trinomios de la forma x^2+bx+c."
    ]
  },
  {
    "id": "A-M1-ALG-01-15",
    "eje": "algebra_y_funciones",
    "standard_ids": [
      "M1-ALG-01"
    ],
    "habilidad_principal": "representar",
    "habilidades_secundarias": [
      "argumentar"
    ],
    "tipo_atomico": "representacion",
    "titulo": "Interpretación geométrica de productos notables",
    "descripcion": "El estudiante asocia expresiones algebraicas de productos notables con áreas de figuras geométricas (cuadrados y rectángulos) para visualizar las identidades.",
    "criterios_atomicos": [
      "Relaciona (a+b)^2 con el área de un cuadrado de lado (a+b) compuesto por sub-áreas.",
      "Interpreta la diferencia de cuadrados como una reconfiguración de áreas rectangulares."
    ],
    "ejemplos_conceptuales": [
      "Visualizar que un cuadrado de lado (a+b) contiene un cuadrado a^2, un cuadrado b^2 y dos rectángulos ab.",
      "Representar x(x+2) como el área de un rectángulo."
    ],
    "prerrequisitos": [
      "A-M1-ALG-01-11",
      "A-M1-ALG-01-12"
    ],
    "notas_alcance": [
      "Enfoque visual/conceptual, no de cálculo numérico."
    ]
  },
  {
    "id": "A-M1-ALG-01-16",
    "eje": "algebra_y_funciones",
    "standard_ids": [
      "M1-ALG-01"
    ],
    "habilidad_principal": "resolver_problemas",
    "habilidades_secundarias": [],
    "tipo_atomico": "procedimiento",
    "titulo": "Factorización por factor común",
    "descripcion": "El estudiante factoriza expresiones algebraicas identificando y extrayendo el máximo factor común (numérico y/o literal) de todos los términos.",
    "criterios_atomicos": [
      "Identifica el máximo factor común entre los términos de un polinomio.",
      "Reescribe la expresión como el producto del factor común y el polinomio restante."
    ],
    "ejemplos_conceptuales": [
      "Factorizar 4x^2 + 6x como 2x(2x + 3).",
      "Extraer factor común en 3a^2b - 9ab^2."
    ],
    "prerrequisitos": [
      "A-M1-ALG-01-09"
    ],
    "notas_alcance": [
      "Incluye factor común monomio y polinomio simple (ej. a(x+y) + b(x+y))."
    ]
  },
  {
    "id": "A-M1-ALG-01-17",
    "eje": "algebra_y_funciones",
    "standard_ids": [
      "M1-ALG-01"
    ],
    "habilidad_principal": "resolver_problemas",
    "habilidades_secundarias": [],
    "tipo_atomico": "procedimiento",
    "titulo": "Factorización de diferencia de cuadrados",
    "descripcion": "El estudiante factoriza binomios que corresponden a una diferencia de cuadrados perfectos, reescribiéndolos como suma por diferencia.",
    "criterios_atomicos": [
      "Reconoce una expresión como diferencia de dos cuadrados (a^2 - b^2).",
      "Factoriza la expresión en la forma (a + b)(a - b)."
    ],
    "ejemplos_conceptuales": [
      "Factorizar x^2 - 25 como (x + 5)(x - 5).",
      "Factorizar 4y^2 - 9z^2."
    ],
    "prerrequisitos": [
      "A-M1-ALG-01-12"
    ],
    "notas_alcance": [
      "Operación inversa al producto notable suma por diferencia."
    ]
  },
  {
    "id": "A-M1-ALG-01-18",
    "eje": "algebra_y_funciones",
    "standard_ids": [
      "M1-ALG-01"
    ],
    "habilidad_principal": "resolver_problemas",
    "habilidades_secundarias": [],
    "tipo_atomico": "procedimiento",
    "titulo": "Factorización de trinomio cuadrado perfecto",
    "descripcion": "El estudiante identifica y factoriza trinomios que son cuadrados perfectos, expresándolos como el cuadrado de un binomio.",
    "criterios_atomicos": [
      "Verifica si un trinomio cumple las condiciones de cuadrado perfecto (extremos cuadrados, término central doble producto).",
      "Factoriza el trinomio como (a ± b)^2."
    ],
    "ejemplos_conceptuales": [
      "Factorizar x^2 + 10x + 25 como (x + 5)^2.",
      "Identificar que x^2 + 6x + 9 es un cuadrado perfecto."
    ],
    "prerrequisitos": [
      "A-M1-ALG-01-11"
    ],
    "notas_alcance": [
      "Operación inversa al cuadrado de binomio."
    ]
  },
  {
    "id": "A-M1-ALG-01-19",
    "eje": "algebra_y_funciones",
    "standard_ids": [
      "M1-ALG-01"
    ],
    "habilidad_principal": "resolver_problemas",
    "habilidades_secundarias": [],
    "tipo_atomico": "procedimiento",
    "titulo": "Factorización de trinomios de la forma x^2+bx+c",
    "descripcion": "El estudiante factoriza trinomios cuadráticos mónicos buscando dos números que sumados den el coeficiente lineal 'b' y multiplicados den el término independiente 'c'.",
    "criterios_atomicos": [
      "Identifica los coeficientes b y c en el trinomio.",
      "Encuentra dos números que cumplan la condición de suma y producto.",
      "Expresa el trinomio como producto de dos binomios (x + p)(x + q)."
    ],
    "ejemplos_conceptuales": [
      "Factorizar x^2 + 7x + 12 buscando números que sumen 7 y multipliquen 12 (3 y 4).",
      "Resultado: (x + 3)(x + 4)."
    ],
    "prerrequisitos": [
      "A-M1-ALG-01-14"
    ],
    "notas_alcance": [
      "Se limita a trinomios mónicos (coeficiente de x^2 es 1).",
      "Requiere dominio de aritmética de enteros."
    ]
  },
  {
    "id": "A-M1-ALG-01-20",
    "eje": "algebra_y_funciones",
    "standard_ids": [
      "M1-ALG-01"
    ],
    "habilidad_principal": "resolver_problemas",
    "habilidades_secundarias": [],
    "tipo_atomico": "procedimiento",
    "titulo": "Simplificación de expresiones algebraicas racionales simples",
    "descripcion": "El estudiante simplifica fracciones algebraicas factorizando numerador y denominador y cancelando factores comunes.",
    "criterios_atomicos": [
      "Factoriza correctamente el numerador y el denominador de la fracción algebraica.",
      "Simplifica la fracción cancelando los factores idénticos."
    ],
    "ejemplos_conceptuales": [
      "Simplificar (x^2 - 9) / (x + 3) factorizando el numerador como (x+3)(x-3).",
      "Resultado: x - 3."
    ],
    "prerrequisitos": [
      "A-M1-ALG-01-16",
      "A-M1-ALG-01-17",
      "A-M1-ALG-01-18",
      "A-M1-ALG-01-19"
    ],
    "notas_alcance": [
      "Se limita a casos donde la factorización es directa y los factores son monomios o binomios simples.",
      "No incluye operaciones complejas (suma/resta) entre fracciones algebraicas, solo simplificación de una fracción dada."
    ]
  },
  {
    "id": "A-M1-ALG-01-21",
    "eje": "algebra_y_funciones",
    "standard_ids": [
      "M1-ALG-01"
    ],
    "habilidad_principal": "modelar",
    "habilidades_secundarias": [
      "resolver_problemas"
    ],
    "tipo_atomico": "concepto_procedimental",
    "titulo": "Resolución de problemas contextualizados con expresiones algebraicas",
    "descripcion": "El estudiante modela y resuelve situaciones problemáticas de diversos contextos (geométricos, cotidianos) utilizando expresiones algebraicas, operaciones y propiedades aprendidas.",
    "criterios_atomicos": [
      "Identifica las variables relevantes en el problema contextualizado.",
      "Construye un modelo algebraico (expresión) que representa la situación.",
      "Aplica operaciones o evaluaciones necesarias para responder la pregunta del problema.",
      "Interpreta el resultado matemático en el contexto de la situación original."
    ],
    "ejemplos_conceptuales": [
      "Determinar una expresión para el área de un terreno rectangular si el largo excede en 3 metros al ancho.",
      "Calcular el costo total de una compra con precios variables representados algebraicamente."
    ],
    "prerrequisitos": [
      "A-M1-ALG-01-02",
      "A-M1-ALG-01-04",
      "A-M1-ALG-01-08"
    ],
    "notas_alcance": [
      "Átomo integrador.",
      "Los problemas deben resolverse mediante manipulación de expresiones, no necesariamente ecuaciones complejas."
    ]
  }
]
</context>

<task>
Evalúa la calidad de los átomos generados considerando:

1. **Fidelidad**: ¿Los átomos cubren completamente el estándar sin agregar contenido fuera de alcance?
2. **Granularidad**: ¿Cada átomo cumple los 6 criterios de granularidad atómica?
3. **Completitud y Cobertura del Estándar (CRÍTICO)**: 
   - Verifica punto por punto que CADA elemento del estándar esté representado en los átomos:
     * Revisa cada ítem en "incluye" del estándar y verifica que haya átomos que lo cubran
     * Revisa cada "subcontenidos_clave" y verifica que esté representado
     * Revisa las "habilidades_relacionadas" y verifica que se reflejen en los átomos
     * Verifica que los "ejemplos_conceptuales" del estándar puedan ser abordados con los átomos generados
   - Identifica específicamente qué elementos del estándar NO están cubiertos por ningún átomo
   - Verifica que no haya contenido en los átomos que esté explícitamente en "no_incluye" del estándar
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
    "procedural_coverage": "present" | "missing",
    "standard_items_coverage": {
      "includes_covered": {
        "<item del campo 'incluye'>": "covered" | "missing" | "partially_covered",
        "<item del campo 'incluye'>": "covered" | "missing" | "partially_covered"
      },
      "subcontenidos_covered": {
        "<subcontenido clave>": "covered" | "missing" | "partially_covered",
        "<subcontenido clave>": "covered" | "missing" | "partially_covered"
      },
      "habilidades_covered": {
        "<habilidad_id>": "covered" | "missing" | "partially_covered",
        "<habilidad_id>": "covered" | "missing" | "partially_covered"
      }
    }
  },
  "global_recommendations": [
    "<recomendación global 1>",
    "<recomendación global 2>"
  ]
}
</output_format>

<final_instruction>
Basándote en el estándar y los átomos generados, realiza una evaluación exhaustiva.

**PASO 1 - Verificación de Cobertura Completa del Estándar (HACER PRIMERO)**:
1. Toma cada elemento del campo "incluye" del estándar y verifica que haya al menos un átomo que lo cubra
2. Toma cada "subcontenidos_clave" y verifica que esté representado en los átomos
3. Toma cada "habilidad_id" en "habilidades_relacionadas" y verifica que haya átomos que la desarrollen
4. Identifica específicamente qué elementos del estándar NO están cubiertos (si los hay)
5. Verifica que ningún átomo incluya contenido explícitamente mencionado en "no_incluye"

**PASO 2 - Evaluación de Calidad Individual y Global**:
Identifica problemas específicos, especialmente relacionados con:
- Separación de procedimientos con estrategias cognitivas diferentes
- Separación de versiones simples vs complejas del mismo procedimiento
- Prerrequisitos exhaustivos en átomos integradores (tanto conceptuales como procedimentales)
- Uso de métodos estándar preferentes (evitar métodos alternativos inusuales o confusos)
- Separación de representaciones diferentes que requieren estrategias cognitivas distintas
- Consistencia entre habilidad_principal y criterios_atomicos
- Separación correcta de variantes con algoritmos fundamentalmente distintos (ej: decimal finito vs periódico)

**VERIFICACIÓN CRÍTICA - MÉTODOS EQUIVALENTES**:
Antes de marcar como problema que un átomo menciona "múltiples métodos", DEBES verificar si son realmente métodos distintos o el mismo método explicado de forma diferente:
- Si dos métodos mencionados son matemáticamente equivalentes y requieren la misma estrategia cognitiva, NO es un problema
- Ejemplos de métodos equivalentes (NO son problemas):
  * "Multiplicar por el inverso multiplicativo" vs "Multiplicación cruzada" (división de fracciones) → Son el mismo método
  * "Sumar opuestos" vs "Restar" (en enteros) → Pueden ser equivalentes según el contexto
- Solo marca como problema si los métodos requieren algoritmos o estrategias cognitivas fundamentalmente distintos
- Si tienes duda, asume que son equivalentes y NO marques como problema

**VERIFICACIÓN CRÍTICA - TRANSITIVIDAD DE PRERREQUISITOS**:
Los prerrequisitos son TRANSITIVOS. Si A es prerrequisito de B, y B es prerrequisito de C, entonces C solo necesita listar B como prerrequisito, NO necesita listar A explícitamente.
- **REGLA DE ORO**: NO marques como problema si un átomo no lista un prerrequisito transitivo
- Ejemplo: Si A-01 → A-04 → A-17, entonces A-17 solo necesita listar A-04, NO A-01
- Solo marca como problema si falta un prerrequisito DIRECTO (no transitivo)
- Si un átomo requiere operar con enteros pero ya tiene un prerrequisito que a su vez requiere enteros, NO es un problema
- Si tienes duda sobre si un prerrequisito es directo o transitivo, asume que es transitivo y NO marques como problema

**IMPORTANTE**: Si encuentras elementos del estándar que NO están cubiertos por ningún átomo, esto es un problema crítico que debe reportarse en "missing_areas" y debe afectar el "coverage_completeness" a "incomplete".
</final_instruction>
