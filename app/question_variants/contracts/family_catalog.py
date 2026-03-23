"""Explicit family catalog for official-question construct coverage."""

from __future__ import annotations

from typing import Any


LOW_NON_MECHANIZABLE_FAMILIES = {
    "direct_proportion_reasoning",
    "direct_percentage_calculation",
    "ten_power_zero_composition",
    "algebraic_expression_evaluation",
    "integer_operations",
    "decimal_number_operations",
    "rational_number_operations",
    "simple_probability",
}

HIGH_NON_MECHANIZABLE_FAMILIES = {
    "graph_interpretation",
    "argumentation_evaluation",
    "property_justification",
    "algebraic_model_translation",
}


DIRECT_PROPORTION_SHAPES = [
    {
        "shape_id": "structured_case_record",
        "description": "Presentar los datos en un registro breve o listado estructurado, manteniendo exactamente una sola relación proporcional directa.",
        "required_changes": ["Presentación en registro o lista", "Contexto y magnitudes nuevas"],
        "forbidden_changes": ["Agregar conversiones", "Convertirlo en fórmula afín o ecuación con término fijo"],
    },
    {
        "shape_id": "consistency_check",
        "description": "Pedir identificar qué resultado o registro es consistente con una razón/proporción dada, en lugar de pedir sólo el valor final.",
        "required_changes": ["Forma de pregunta basada en consistencia", "Distractores con errores de escala plausibles"],
        "forbidden_changes": ["Agregar una segunda relación proporcional", "Introducir pasos auxiliares extra"],
    },
]

ALGEBRAIC_EXPRESSION_SHAPES = [
    {
        "shape_id": "verbal_formula_rule",
        "description": "Reexpresar la regla de sustitución en formato verbal manteniendo una sustitución puramente multiplicativa o del mismo tipo exacto de la fuente.",
        "required_changes": ["Presentación verbal o contextual de la regla", "Valores y contexto nuevos"],
        "forbidden_changes": ["Cambiar la forma algebraica base", "Convertirla en ecuación a resolver"],
    },
    {
        "shape_id": "formula_card_context",
        "description": "Mantener una fórmula o tarjeta de regla explícita, pero cambiar el contexto y el foco de lectura dentro de la misma sustitución directa.",
        "required_changes": ["Nueva tarjeta o fórmula equivalente", "Nueva lectura del dato a sustituir"],
        "forbidden_changes": ["Agregar incógnitas", "Aumentar la cantidad de pasos"],
    },
]

PARAMETER_INTERPRETATION_SHAPES = [
    {
        "shape_id": "operational_statement",
        "description": "Interpretar el parámetro mediante una afirmación operacional contextual sobre cómo cambia una magnitud ante un cambio fijo de la otra.",
        "required_changes": ["Afirmación contextual", "Evitar la recitación literal del parámetro"],
        "forbidden_changes": ["Comparar dos casos distintos", "Convertirlo en cálculo directo de resultado final"],
    },
    {
        "shape_id": "claim_selection_prompt",
        "description": "Plantear varias afirmaciones interpretativas y pedir seleccionar la que representa correctamente el significado del parámetro.",
        "required_changes": ["Opciones en formato de afirmación", "Distractores de interpretación plausibles"],
        "forbidden_changes": ["Mantener el mismo marco interrogativo literal de la fuente", "Resolver un caso numérico extenso"],
    },
]

PERCENTAGE_CONTEXT_SHAPES = [
    {
        "shape_id": "ledger_context",
        "description": "Presentar el caso como un breve registro narrativo o desglose contextual, manteniendo el mismo patrón porcentual de la fuente.",
        "required_changes": ["Contexto narrativo nuevo", "Presentación tipo registro o desglose"],
        "forbidden_changes": ["Cambiar la secuencia/polaridad de cambios porcentuales", "Introducir una base extra no presente en la fuente"],
    },
    {
        "shape_id": "decision_statement",
        "description": "Pedir elegir la afirmación o resultado contextual coherente con la aplicación porcentual, en vez de repetir la misma pregunta directa.",
        "required_changes": ["Forma de pregunta basada en decisión o afirmación", "Distractores con errores porcentuales plausibles"],
        "forbidden_changes": ["Aumentar la cantidad de pasos", "Cambiar el tipo de variación porcentual"],
    },
]

GRAPH_INTERPRETATION_SHAPES = [
    {
        "shape_id": "single_series_visual_claim",
        "description": "Mantener una representación primaria de una sola serie y pedir validar una afirmación breve sobre la lectura central del gráfico.",
        "required_changes": ["Afirmaciones nuevas", "Valores o rótulos nuevos en la representación"],
        "forbidden_changes": ["Agregar series extra", "Reemplazar la evidencia primaria por una lista que regale la respuesta"],
    },
    {
        "shape_id": "extremum_focus",
        "description": "Cambiar el foco puntual de lectura hacia identificar el máximo o mínimo relevante dentro de la misma representación primaria.",
        "required_changes": ["Nuevo foco de lectura", "Distractores visuales plausibles"],
        "forbidden_changes": ["Cambiar la polaridad extrema", "Eliminar la necesidad de interpretar la representación"],
    },
]

ARGUMENTATION_SHAPES = [
    {
        "shape_id": "claim_archetype_switch",
        "description": "Mantener la evaluación de afirmaciones, pero cambiar el arquetipo semántico de la afirmación correcta respecto de la fuente.",
        "required_changes": ["Nuevo arquetipo de afirmación correcta", "Distractores coherentes con el nuevo arquetipo"],
        "forbidden_changes": ["Repetir la misma afirmación correcta con números nuevos", "Convertirlo en cálculo directo"],
    },
    {
        "shape_id": "false_claim_hunt",
        "description": "Invertir la polaridad local de las opciones para pedir identificar la afirmación incorrecta dentro del mismo conjunto de datos o evidencia.",
        "required_changes": ["Polaridad local de la pregunta", "Reescritura completa de opciones"],
        "forbidden_changes": ["Cambiar el dataset o la evidencia por cálculo puro", "Eliminar la lectura argumentativa"],
    },
]

TEN_POWER_ZERO_SHAPES = [
    {
        "shape_id": "keypad_record",
        "description": "Presentar un registro o secuencia de teclas/pasos abreviados y pedir identificar cuál produce correctamente la composición de ceros o potencia de 10 buscada.",
        "required_changes": ["Formato de registro o secuencia", "Distractores de orden/composición plausibles"],
        "forbidden_changes": ["Preguntar exactamente el mismo valor final con otro contexto", "Cambiar base 10 por otra base o propiedad general distinta"],
    },
    {
        "shape_id": "display_equivalence_check",
        "description": "Pedir reconocer qué atajo, botón o representación produce un resultado equivalente a la composición de ceros dada, manteniendo base 10 y foco operacional.",
        "required_changes": ["Forma de pregunta basada en equivalencia operativa", "Opciones que contrastan errores típicos de cantidad de ceros"],
        "forbidden_changes": ["Volver a una pregunta directa de cálculo idéntica a la fuente", "Transformarlo en justificación teórica de propiedades"],
    },
]

TRINOMIAL_FACTORIZATION_SHAPES = [
    {
        "shape_id": "contextual_dimension_pair",
        "description": "Reformular el trinomio como una medida de área/producto y pedir identificar la pareja de dimensiones o factores coherente con la expresión.",
        "required_changes": ["Contexto geométrico o dimensional", "Opciones como parejas/factores equivalentes"],
        "forbidden_changes": ["Agregar cambio de variable", "Convertirlo en simplificación racional o ecuación a resolver"],
    },
    {
        "shape_id": "factor_consistency_check",
        "description": "Pedir identificar qué descomposición o pareja de factores cumple simultáneamente la suma y el producto requeridos por el trinomio.",
        "required_changes": ["Forma de pregunta basada en consistencia", "Distractores con errores plausibles de suma/producto"],
        "forbidden_changes": ["Repetir la misma pregunta de equivalencia literal", "Agregar expansión algebraica larga como tarea principal"],
    },
]

GEOMETRY_MEASUREMENT_SHAPES = [
    {
        "shape_id": "embedded_shape_transfer",
        "description": "Mantener la misma relación geométrica central, pero presentarla a través de una figura inscrita, circunscrita o contenida que obligue a transferir una medida intermedia breve.",
        "required_changes": ["Relación entre figuras", "Nueva medida objetivo dentro del mismo constructo geométrico"],
        "forbidden_changes": ["Agregar un teorema nuevo", "Cambiar a una familia geométrica distinta"],
    },
    {
        "shape_id": "measurement_claim_selection",
        "description": "Pedir seleccionar el resultado o afirmación geométrica coherente con la medida calculada, en vez de repetir la misma pregunta directa por el valor final.",
        "required_changes": ["Forma de pregunta basada en afirmación o selección", "Distractores con errores de fórmula o medida plausibles"],
        "forbidden_changes": ["Eliminar la aplicación de la fórmula central", "Introducir varias cadenas de cálculo ajenas a la fuente"],
    },
]

CONDITIONAL_PROBABILITY_SHAPES = [
    {
        "shape_id": "reduced_sample_space_record",
        "description": "Presentar el caso como un registro breve o selección sucesiva donde la segunda probabilidad depende explícitamente del resultado de la primera.",
        "required_changes": ["Registro de extracción/selección sucesiva", "Distractores con errores de espacio muestral no actualizado"],
        "forbidden_changes": ["Reducirlo a probabilidad simple independiente", "Introducir combinatoria avanzada innecesaria"],
    },
    {
        "shape_id": "conditional_claim_check",
        "description": "Pedir identificar qué afirmación o cálculo representa correctamente la probabilidad condicionada dentro del mismo espacio muestral dependiente.",
        "required_changes": ["Forma de pregunta basada en afirmación/cálculo", "Distractores que confunden total inicial con total condicionado"],
        "forbidden_changes": ["Eliminar la condición del evento previo", "Transformarlo en puro conteo sin dependencia"],
    },
]

RADICAL_OPERATION_SHAPES = [
    {
        "shape_id": "equivalent_radical_selection",
        "description": "Pedir seleccionar la expresión radical equivalente correcta luego de una simplificación u operación del mismo tipo.",
        "required_changes": ["Forma de pregunta basada en equivalencia", "Distractores con errores típicos de índice/factor común"],
        "forbidden_changes": ["Convertirlo en ecuación", "Pasar a justificación abstracta de propiedades de potencias"],
    },
    {
        "shape_id": "contextual_value_check",
        "description": "Presentar un contexto breve donde la operación con radicales mantiene el mismo núcleo algebraico, pero la respuesta se expresa como una verificación de valor o representación equivalente.",
        "required_changes": ["Contexto o representación distinta", "Distractores con simplificaciones incorrectas plausibles"],
        "forbidden_changes": ["Agregar varios pasos nuevos", "Cambiar el tipo de radical u operación central"],
    },
]

ISOMETRY_SHAPES = [
    {
        "shape_id": "transformation_identification",
        "description": "Mantener la figura y pedir identificar qué isometría específica ocurrió entre dos posiciones o configuraciones.",
        "required_changes": ["Nueva configuración visual", "Distractores de isometrías plausibles"],
        "forbidden_changes": ["Agregar cálculo métrico pesado", "Cambiar la familia geométrica a coordenadas algebraicas complejas"],
    },
    {
        "shape_id": "vector_or_axis_consistency",
        "description": "Pedir elegir el eje, vector o descripción que hace consistente la misma transformación isométrica presentada en la figura.",
        "required_changes": ["Foco en eje/vector/descripción", "Distractores coherentes con errores de dirección o simetría"],
        "forbidden_changes": ["Eliminar la interpretación visual", "Convertirlo en cálculo de distancia o área"],
    },
]

POLYNOMIAL_OPERATION_SHAPES = [
    {
        "shape_id": "operation_result_selection",
        "description": "Pedir identificar el resultado correcto de una suma, resta o multiplicación de polinomios del mismo tipo, con distractores ligados a errores de término semejante o distributividad.",
        "required_changes": ["Nueva operación concreta", "Distractores de error operatorio plausibles"],
        "forbidden_changes": ["Cambiar a factorización", "Introducir expresiones racionales"],
    },
    {
        "shape_id": "term_group_consistency",
        "description": "Plantear la operación y pedir reconocer qué agrupación o combinación de términos es consistente con el resultado parcial/final correcto.",
        "required_changes": ["Forma de pregunta basada en consistencia algebraica", "Distractores por combinación incorrecta de términos semejantes"],
        "forbidden_changes": ["Volverlo una ecuación a resolver", "Agregar pasos de simplificación ajenos a la fuente"],
    },
]

INTEGER_OPERATION_SHAPES = [
    {
        "shape_id": "operation_record",
        "description": "Presentar la operatoria con enteros en un registro breve o secuencia contextual mínima, manteniendo el mismo foco de signo/precedencia.",
        "required_changes": ["Formato de registro o secuencia", "Números y contexto nuevos"],
        "forbidden_changes": ["Introducir álgebra con incógnitas", "Agregar pasos auxiliares innecesarios"],
    },
    {
        "shape_id": "result_consistency_check",
        "description": "Pedir identificar cuál resultado o afirmación es consistente con la operación entre enteros dada, en vez de repetir la misma pregunta directa.",
        "required_changes": ["Forma de pregunta basada en consistencia", "Distractores de signo/precedencia plausibles"],
        "forbidden_changes": ["Agregar una segunda operación ajena", "Cambiar a otro dominio numérico"],
    },
]

DECIMAL_OPERATION_SHAPES = [
    {
        "shape_id": "quantity_record",
        "description": "Expresar la operación o comparación decimal como un registro de cantidades o medidas breves, manteniendo el mismo foco operatorio.",
        "required_changes": ["Registro contextual breve", "Distractores con errores de alineación decimal plausibles"],
        "forbidden_changes": ["Convertirlo en porcentaje o ecuación", "Agregar varias capas de cálculo extra"],
    },
    {
        "shape_id": "comparison_consistency",
        "description": "Pedir identificar qué resultado o comparación decimal es coherente con los datos dados, en vez de repetir el mismo valor final literal.",
        "required_changes": ["Forma de pregunta basada en consistencia o comparación", "Distractores por error de posición decimal plausibles"],
        "forbidden_changes": ["Cambiar el dominio numérico", "Introducir magnitudes ajenas a la fuente"],
    },
]

SIMPLE_PROBABILITY_SHAPES = [
    {
        "shape_id": "favorable_case_check",
        "description": "Mantener el mismo espacio muestral simple y pedir reconocer qué opción representa correctamente los casos favorables o la probabilidad resultante.",
        "required_changes": ["Nueva presentación del espacio muestral", "Distractores de conteo simple plausibles"],
        "forbidden_changes": ["Introducir dependencia/condicionalidad", "Subirlo a combinatoria más compleja"],
    },
    {
        "shape_id": "probability_statement_selection",
        "description": "Plantear varias afirmaciones simples sobre la probabilidad del evento y pedir seleccionar la correcta dentro del mismo espacio muestral clásico.",
        "required_changes": ["Forma de pregunta basada en afirmación", "Distractores que confunden casos favorables y posibles"],
        "forbidden_changes": ["Cambiar a probabilidad condicional", "Agregar más de un nivel de selección"],
    },
]

ALGEBRAIC_MODEL_TRANSLATION_SHAPES = [
    {
        "shape_id": "context_to_model_match",
        "description": "Presentar una situación verbal nueva y pedir identificar la expresión, ecuación o modelo algebraico que la representa correctamente.",
        "required_changes": ["Nuevo contexto verbal", "Opciones como modelos algebraicos plausibles"],
        "forbidden_changes": ["Resolver completamente el modelo", "Cambiar la familia algebraica de fondo"],
    },
    {
        "shape_id": "model_to_context_match",
        "description": "Presentar un modelo algebraico y pedir reconocer qué situación o interpretación contextual es coherente con él.",
        "required_changes": ["Nueva lectura contextual del modelo", "Distractores de interpretación plausibles"],
        "forbidden_changes": ["Convertirlo en cálculo directo del valor final", "Agregar pasos de resolución ajenos a la fuente"],
    },
]

PROPERTY_JUSTIFICATION_SHAPES = [
    {
        "shape_id": "justification_statement_selection",
        "description": "Mantener una afirmación matemática y pedir seleccionar la justificación correcta en un formato de afirmaciones/razones distinto al de la fuente.",
        "required_changes": ["Reescritura de las razones u opciones", "Nuevo enunciado o ejemplo dentro de la misma propiedad"],
        "forbidden_changes": ["Repetir la misma justificación textual con otros números", "Cambiar de justificar a calcular solamente"],
    },
    {
        "shape_id": "invalid_reason_detection",
        "description": "Presentar varias justificaciones plausibles y pedir identificar la que es inválida o insuficiente dentro de la misma propiedad matemática.",
        "required_changes": ["Polaridad local de evaluación de razones", "Distractores basados en errores conceptuales reales"],
        "forbidden_changes": ["Eliminar la necesidad de justificar", "Cambiar la propiedad matemática central"],
    },
]


FAMILY_SPECS: list[dict[str, Any]] = [
    {
        "family_id": "property_justification",
        "atom_markers": (
            "potencias de base racional con exponente entero no negativo",
            "potencia de una potencia con base racional",
            "modelado de situaciones con potencias y raíces",
            "modelado de situaciones con potencias y raices",
        ),
        "operation_signature": "property_justification",
        "cognitive_action": "justify_property",
        "solution_structure": "property_justification",
        "prompt_rules": (
            "La variante debe seguir evaluando propiedades de potencias o raíces y la justificación del resultado, no cálculo mecánico sin argumento.",
            "Mantén la misma polaridad argumentativa: justificar una aplicación válida o refutar una inválida, según la fuente.",
        ),
        "allowed_variant_shapes": PROPERTY_JUSTIFICATION_SHAPES,
    },
    {
        "family_id": "ten_power_zero_composition",
        "atom_markers": (),
        "operation_signature": "ten_power_zero_composition",
        "cognitive_action": "compute_value",
        "solution_structure": "direct_single_step",
        "prompt_rules": (
            "La variante debe seguir construyendo una potencia de 10 mediante composición de ceros o botones equivalentes, no justificar propiedades generales de potencias.",
            "Mantén base 10 y el foco en la secuencia correcta de ingreso/composición; cambia formato de registro o distractores, no el constructo.",
        ),
        "allowed_variant_shapes": TEN_POWER_ZERO_SHAPES,
    },
    {
        "family_id": "direct_percentage_calculation",
        "atom_markers": (
            "cálculo directo del porcentaje de una cantidad",
            "calculo directo del porcentaje de una cantidad",
            "determinación del porcentaje entre dos cantidades",
            "determinacion del porcentaje entre dos cantidades",
            "cálculo de la cantidad total dado un porcentaje",
            "calculo de la cantidad total dado un porcentaje",
        ),
        "operation_signature": "direct_percentage_calculation",
        "cognitive_action": "compute_value",
        "solution_structure": "direct_single_step",
        "prompt_rules": (
            "La variante debe seguir siendo una tarea porcentual directa de un paso, sin introducir magnitudes intermedias ni selección extra de bases.",
            "Conserva la escala porcentual y el tipo de base: porcentaje de una cantidad, porcentaje entre dos cantidades o total dado porcentaje, según la fuente.",
        ),
        "allowed_variant_shapes": PERCENTAGE_CONTEXT_SHAPES,
    },
    {
        "family_id": "percentage_context_application",
        "atom_markers": (
            "resolución de problemas contextualizados con porcentajes",
            "resolucion de problemas contextualizados con porcentajes",
            "aplicación de aumentos porcentuales",
            "aplicacion de aumentos porcentuales",
            "aplicación de disminuciones porcentuales",
            "aplicacion de disminuciones porcentuales",
        ),
        "operation_signature": "percentage_increase_application",
        "cognitive_action": "compute_value",
        "solution_structure": "routine_procedural",
        "prompt_rules": (
            "La variante debe seguir siendo una aplicación porcentual contextualizada del mismo tipo, no una lectura abierta de datos ni una modelación de varios pasos.",
            "Mantén distractores plausibles de porcentaje y la misma relación base-variación de la fuente.",
        ),
        "allowed_variant_shapes": PERCENTAGE_CONTEXT_SHAPES,
    },
    {
        "family_id": "direct_proportion_reasoning",
        "atom_markers": (
            "proporción directa",
            "proporcion directa",
            "regla de tres",
            "proporcionalidad directa",
        ),
        "operation_signature": "direct_proportion_reasoning",
        "cognitive_action": "compute_value",
        "solution_structure": "proportional_setup",
        "prompt_rules": (
            "La variante debe seguir siendo una situación de proporcionalidad directa o regla de tres, no una ecuación afín ni una fórmula con término fijo.",
            "Mantén la misma cantidad de relaciones entre magnitudes; no agregues conversiones o pasos auxiliares extra.",
        ),
        "allowed_variant_shapes": DIRECT_PROPORTION_SHAPES,
    },
    {
        "family_id": "algebraic_expression_evaluation",
        "atom_markers": (
            "evaluación de expresiones algebraicas",
            "evaluacion de expresiones algebraicas",
            "a-m1-alg-01-02",
        ),
        "operation_signature": "algebraic_expression_evaluation",
        "cognitive_action": "substitute_and_compute",
        "solution_structure": "formula_substitution",
        "prompt_rules": (
            "La variante debe seguir siendo evaluación de una expresión o fórmula dada, no resolución de una ecuación.",
            "No cambies una sustitución directa por un modelo con incógnita o por un procedimiento de varios pasos.",
        ),
        "allowed_variant_shapes": ALGEBRAIC_EXPRESSION_SHAPES,
    },
    {
        "family_id": "trinomial_factorization",
        "atom_markers": (
            "factorización de trinomios de la forma x^2 + bx + c",
            "factorizacion de trinomios de la forma x^2 + bx + c",
            "desarrollo de cuadrado de binomio",
        ),
        "operation_signature": "trinomial_factorization",
        "cognitive_action": "transform_expression",
        "solution_structure": "expression_factoring",
        "prompt_rules": (
            "La variante debe seguir siendo transformación/factorización polinómica del mismo nivel, no simplificación racional ni cambio de variable más duro.",
        ),
        "allowed_variant_shapes": TRINOMIAL_FACTORIZATION_SHAPES,
    },
    {
        "family_id": "algebraic_model_translation",
        "atom_markers": (
            "traducción bidireccional entre lenguaje natural y algebraico",
            "traduccion bidireccional entre lenguaje natural y algebraico",
            "traducción de lenguaje natural a ecuaciones lineales",
            "traduccion de lenguaje natural a ecuaciones lineales",
            "traducción de lenguaje natural a inecuaciones",
            "traduccion de lenguaje natural a inecuaciones",
            "modelado de situaciones con sistemas 2x2",
            "modelado de situaciones con potencias y raíces",
            "modelado de situaciones con potencias y raices",
            "modelado algebraico de proporcionalidad directa",
            "concepto de función lineal",
            "concepto de funcion lineal",
            "modelado de situaciones con teorema de pitágoras",
            "modelado de situaciones con teorema de pitagoras",
            "interpretación geométrica de sistemas 2x2",
            "interpretacion geometrica de sistemas 2x2",
            "modelado de situaciones con sistemas 2x2",
        ),
        "operation_signature": "algebraic_model_translation",
        "cognitive_action": "interpret_model",
        "solution_structure": "model_interpretation",
        "prompt_rules": (
            "La variante debe seguir evaluando traducción, interpretación o modelación algebraica; no la conviertas en resolver completamente el modelo.",
            "Conserva la misma relación entre lenguaje, variable y expresión matemática; cambia el contexto, no la tarea principal.",
        ),
        "allowed_variant_shapes": ALGEBRAIC_MODEL_TRANSLATION_SHAPES,
    },
    {
        "family_id": "parameter_interpretation",
        "atom_markers": (
            "interpretación de parámetros en contexto",
            "interpretacion de parametros en contexto",
            "análisis del parámetro 'b' en la función cuadrática",
            "analisis del parametro 'b' en la funcion cuadratica",
            "análisis de los parámetros 'a' y 'c' en la función cuadrática",
            "analisis de los parametros 'a' y 'c' en la funcion cuadratica",
            "evaluación de funciones lineales y afines",
            "evaluacion de funciones lineales y afines",
            "formulación de modelos lineales y afines",
            "formulacion de modelos lineales y afines",
        ),
        "operation_signature": "parameter_interpretation",
        "cognitive_action": "interpret_model",
        "solution_structure": "parameter_meaning_interpretation",
        "prompt_rules": (
            "La variante debe seguir interpretando el significado de un parámetro, coeficiente o componente del modelo, no ejecutar cálculos extensos.",
            "Mantén el mismo tipo de lectura semántica del modelo: tasa, pendiente, intercepto o significado de variable, según corresponda.",
        ),
        "allowed_variant_shapes": PARAMETER_INTERPRETATION_SHAPES,
    },
    {
        "family_id": "linear_equation_resolution",
        "atom_markers": (
            "ecuaciones lineales",
            "resolución de ecuaciones lineales básicas",
            "resolucion de ecuaciones lineales basicas",
            "resolución de problemas contextualizados con ecuaciones lineales",
            "resolucion de problemas contextualizados con ecuaciones lineales",
            "resolución de problemas contextualizados con inecuaciones",
            "resolucion de problemas contextualizados con inecuaciones",
            "resolución algebraica por método de sustitución",
            "resolucion algebraica por metodo de sustitucion",
        ),
        "operation_signature": "linear_equation_resolution",
        "cognitive_action": "solve_for_unknown",
        "solution_structure": "equation_resolution",
        "prompt_rules": (
            "La variante debe seguir resolviendo una ecuación o inecuación lineal del mismo tipo; no la conviertas en sustitución de fórmula ni en problema de proporcionalidad.",
            "No agregues capas de modelación extra si la fuente ya entrega el modelo listo para resolver.",
        ),
        "allowed_variant_shapes": [
            {
                "shape_id": "contextual_mutation",
                "description": "Mantener la misma estructura abstracta de la ecuación o inecuación pero inventar un contexto narrativo 100% distinto, operando con valores numéricos y unidades nuevas.",
                "required_changes": ["Contexto narrativo", "Nombres de variables y sujetos", "Valores numéricos base en misma proporción"],
                "forbidden_changes": ["Agregar pasos de resolución al final", "Cambiar la operatoria base de ecuación a otro ente algebraico"],
                "difficulty_offset": "Mantener Dificultad (solo exige transferencia a un nuevo escenario)."
            },
            {
                "shape_id": "error_analysis",
                "description": "En lugar de pedir el resultado directo, presentar la resolución paso a paso que hizo un estudiante ficticio y pedir identificar en qué paso ocurrió un error (ej. error de signo, agrupación).",
                "required_changes": ["La pregunta ahora detecta el error", "Pasos de resolución ficticios a lo largo del ítem", "Distractores referencian a los Pasos textualmente"],
                "forbidden_changes": ["Entregar la resolución perfecta en el bloque de texto"],
                "difficulty_offset": "Aumentar dificultad (evalúa metacognición matemática)."
            },
            {
                "shape_id": "inverse_parameter_shift",
                "description": "Dar el valor de la solución final explícitamente en el enunciado, y preguntar por el valor inicial de uno de los parámetros que originalmente era un dato fijo.",
                "required_changes": ["Intercambiar Incógnita principal por dato"],
                "forbidden_changes": ["Alterar el dominio (sigue siendo de carácter lineal)"],
                "difficulty_offset": "Aumentar dificultad levemente obligando a un despeje inverso o sustitución trasera."
            }
        ],
    },
    {
        "family_id": "conditional_probability",
        "atom_markers": (
            "probabilidad condicional",
            "regla multiplicativa para eventos dependientes",
            "regla multiplicativa para eventos dependientes",
        ),
        "operation_signature": "conditional_probability",
        "cognitive_action": "apply_probability_model",
        "solution_structure": "probability_counting",
        "prompt_rules": (
            "La variante debe conservar el mismo tipo de dependencia o reducción del espacio muestral; no la bajes a probabilidad simple ni la subas a combinatoria avanzada.",
        ),
        "allowed_variant_shapes": CONDITIONAL_PROBABILITY_SHAPES,
    },
    {
        "family_id": "simple_probability",
        "atom_markers": (
            "cálculo de probabilidad de un evento simple",
            "calculo de probabilidad de un evento simple",
            "concepto de probabilidad clásica",
            "concepto de probabilidad clasica",
            "regla aditiva para eventos mutuamente excluyentes",
        ),
        "operation_signature": "simple_probability",
        "cognitive_action": "apply_probability_model",
        "solution_structure": "probability_counting",
        "prompt_rules": (
            "La variante debe seguir siendo de probabilidad simple o clásica, con el mismo tipo de espacio muestral y sin introducir probabilidad condicional ni combinatoria más dura.",
            "Mantén la misma estructura de conteo: casos favorables sobre casos posibles o suma de eventos excluyentes, según corresponda.",
        ),
        "allowed_variant_shapes": SIMPLE_PROBABILITY_SHAPES,
    },
    {
        "family_id": "radical_operations",
        "atom_markers": (
            "multiplicación de raíces de igual índice",
            "multiplicacion de raices de igual indice",
            "descomposición y simplificación de raíces enésimas",
            "descomposicion y simplificacion de raices enesimas",
            "resolución de problemas de contexto mediante raíces o evaluación",
            "resolucion de problemas de contexto mediante raices o evaluacion",
        ),
        "operation_signature": "radical_operations",
        "cognitive_action": "transform_expression",
        "solution_structure": "expression_transformation",
        "prompt_rules": (
            "La variante debe seguir operando con raíces del mismo tipo y no convertirse en ecuaciones o potencias justificativas.",
        ),
        "allowed_variant_shapes": RADICAL_OPERATION_SHAPES,
    },
    {
        "family_id": "descriptive_statistics",
        "atom_markers": (
            "promedio aritmético",
            "promedio aritmetico",
            "media aritmética",
            "media aritmetica",
            "frecuencia absoluta",
            "frecuencia relativa",
            "moda",
            "mediana",
            "cuartiles",
            "diagrama de cajón",
            "diagrama de cajon",
            "comparación de grupos de datos mediante medidas",
            "comparacion de grupos de datos mediante medidas",
            "resolución de problemas contextuales con medidas de tendencia y rango",
            "resolucion de problemas contextuales con medidas de tendencia y rango",
            "resolución de problemas inversos de promedio",
            "resolucion de problemas inversos de promedio",
        ),
        "operation_signature": "descriptive_statistics",
        "cognitive_action": "compute_statistic",
        "solution_structure": "statistic_computation",
        "prompt_rules": (
            "La variante debe conservar la misma medida estadística objetivo o la misma comparación estadística central; no la cambies por otra medida.",
            "No aumentes artificialmente la carga de datos, frecuencias o categorías respecto de la fuente.",
        ),
        "allowed_variant_shapes": [
            {
                "shape_id": "distractor_focus",
                "description": "Mantener la representación original (ej. gráfico, tabla, caja) con nuevos valores, PERO enfocar la pregunta en aislar un sesgo o trampa estadística clásica (ej. confundir dispersión/rango con cantidad, entender frecuencias cruzadas).",
                "required_changes": ["Re-enfoque de la pregunta puntual para cazar el sesgo", "Distractores que mimetizan exactamente esos errores lógicos"],
                "forbidden_changes": ["Cambiar el constructo o tipo de gráfico visualmente exigido"],
                "difficulty_offset": "Aumentar la demanda lógica o conceptual."
            },
            {
                "shape_id": "polarity_switch_analysis",
                "description": "Cambiar radicalmente la polaridad de las afirmaciones deducibles. Si la fuente pide 'cuál afirmación es siempre verdadera' cambiar el contexto empírico e inventar 4 opciones plausibles donde deba elegirse la FALSA.",
                "required_changes": ["Polaridad conceptual", "Las 4 elecciones deben reescribirse enteras"],
                "forbidden_changes": ["Convertir el ejercicio en uno de sumas calculadas netas"],
                "difficulty_offset": "Aumentar, requiere capacidad de falsación exhaustiva."
            },
            {
                "shape_id": "dataset_inversion",
                "description": "Darle al alumno la conclusión estadística o medidas abstractas base en el enunciado, y exigirle que determine cuál de las alternativas (presentadas como configuraciones o propiedades de un dataset) genera ese resultado.",
                "required_changes": ["Invertir Causa (dataset) y Efecto (medida estadistica)"],
                "forbidden_changes": ["Cambiar la métrica objetivo principal"],
                "difficulty_offset": "Aumentar, lectura estadística trasera mucho más profunda."
            },
            {
                "shape_id": "subgroup_comparison",
                "description": "Transformar el dataset en una sub-agrupación muy simétrica (ej. Curso A vs Curso B). Pedir una rápida conclusión comparativa de la misma medida sobre ambos grupos (ej. Cuál tiene mayor dispersión relativa).",
                "required_changes": ["Estructura del dataset de un nivel a nivel dual", "Forma de la pregunta hacia comparación visual o teórica simple"],
                "forbidden_changes": ["No añadir operaciones aritméticas extensas de cientos de datos"],
                "difficulty_offset": "Mayor dificultad abstracta."
            }
        ],
    },
    {
        "family_id": "decimal_number_operations",
        "atom_markers": (
            "adición y sustracción de números decimales",
            "adicion y sustraccion de numeros decimales",
            "orden y comparación de decimales",
            "orden y comparacion de decimales",
        ),
        "operation_signature": "decimal_number_operations",
        "cognitive_action": "compute_value",
        "solution_structure": "routine_procedural",
        "prompt_rules": (
            "La variante debe seguir siendo operatoria o comparación con decimales, sin trasladarse a porcentajes, ecuaciones ni funciones.",
        ),
        "allowed_variant_shapes": DECIMAL_OPERATION_SHAPES,
    },
    {
        "family_id": "isometry_transformations",
        "atom_markers": (
            "isometrías",
            "isometrias",
            "reflexión",
            "reflexion",
            "simetría axial",
            "simetria axial",
            "transformaciones isométricas",
            "transformaciones isometricas",
            "vectores de traslación",
            "vectores de traslacion",
            "traslación de un punto mediante un vector",
            "traslacion de un punto mediante un vector",
        ),
        "operation_signature": "isometry_transformations",
        "cognitive_action": "identify_transformation",
        "solution_structure": "isometry_identification",
        "prompt_rules": (
            "La variante debe seguir evaluando reconocimiento o aplicación directa de una isometría, no cálculo de áreas, distancias ni álgebra de coordenadas más pesada.",
            "Conserva el mismo tipo de transformación geométrica dominante: reflexión, traslación o identificación de isometría.",
        ),
        "allowed_variant_shapes": ISOMETRY_SHAPES,
    },
    {
        "family_id": "geometry_measurement_application",
        "atom_markers": (
            "perímetro y área",
            "perimetro y area",
            "cálculo del área de trapecios",
            "calculo del area de trapecios",
            "cálculo del área de paralelogramos",
            "calculo del area de paralelogramos",
            "cubos y paralelepípedos",
            "cubos y paralelepipedos",
            "teorema de pitágoras",
            "teorema de pitagoras",
            "cateto mediante teorema de pitágoras",
            "cateto mediante teorema de pitagoras",
            "cálculo de perímetros de polígonos básicos",
            "calculo de perimetros de poligonos basicos",
            "prismas generales y cilindros",
            "concepto de volumen en prismas rectos",
            "cálculo de volumen de cilindros",
            "calculo de volumen de cilindros",
        ),
        "operation_signature": "geometry_measurement_application",
        "cognitive_action": "compute_value",
        "solution_structure": "geometry_formula_application",
        "prompt_rules": (
            "La variante debe seguir aplicando la misma relación geométrica central o la misma fórmula geométrica, sin agregar teoremas o pasos auxiliares nuevos.",
            "Si la fuente usa una figura como soporte estructural, conserva ese rol y no conviertas el ítem en una pura lista numérica.",
        ),
        "allowed_variant_shapes": GEOMETRY_MEASUREMENT_SHAPES,
    },
    {
        "family_id": "integer_operations",
        "atom_markers": (
            "números enteros",
            "numeros enteros",
            "adición de números enteros",
            "adicion de numeros enteros",
            "sustracción de números enteros",
            "sustraccion de numeros enteros",
            "multiplicación de números enteros",
            "multiplicacion de numeros enteros",
        ),
        "operation_signature": "integer_operations",
        "cognitive_action": "compute_value",
        "solution_structure": "routine_procedural",
        "prompt_rules": (
            "La variante debe seguir siendo operatoria con enteros y los mismos focos de signo/precedencia; no la conviertas en álgebra con incógnitas.",
        ),
        "allowed_variant_shapes": INTEGER_OPERATION_SHAPES,
    },
    {
        "family_id": "rational_number_operations",
        "atom_markers": (
            "números racionales",
            "numeros racionales",
        ),
        "operation_signature": "rational_number_operations",
        "cognitive_action": "compute_value",
        "solution_structure": "routine_procedural",
        "prompt_rules": (
            "La variante debe seguir siendo operatoria con números racionales del mismo tipo, sin derivar a ecuaciones o funciones.",
        ),
    },
    {
        "family_id": "polynomial_operations",
        "atom_markers": (
            "suma y resta de polinomios",
            "multiplicación de monomios y polinomios",
            "multiplicacion de monomios y polinomios",
        ),
        "operation_signature": "polynomial_operations",
        "cognitive_action": "transform_expression",
        "solution_structure": "expression_transformation",
        "prompt_rules": (
            "La variante debe seguir siendo operación directa entre polinomios del mismo tipo, sin factorizar ni simplificar expresiones racionales.",
        ),
        "allowed_variant_shapes": POLYNOMIAL_OPERATION_SHAPES,
    },
    {
        "family_id": "graph_interpretation",
        "atom_markers": (
            "gráficos de línea",
            "graficos de linea",
            "gráficos de barras",
            "graficos de barras",
            "representación gráfica",
            "representacion grafica",
            "pendiente e intercepto",
        ),
        "operation_signature": "graph_interpretation",
        "cognitive_action": "interpret_representation",
        "solution_structure": "representation_reading",
        "prompt_rules": (
            "La variante debe seguir exigiendo lectura e interpretación de una representación, no reemplazarla por una tabla que regale la respuesta.",
        ),
        "allowed_variant_shapes": GRAPH_INTERPRETATION_SHAPES,
    },
]


def resolve_family_spec(atom_titles: list[str], main_skill: str = "") -> dict[str, Any]:
    """Resolve the best-matching family spec from primary atom titles and skill."""
    normalized_titles = [str(title).lower() for title in atom_titles]
    haystack = " | ".join(normalized_titles)
    skill = str(main_skill or "").upper()

    if skill == "REP" or any(
        marker in haystack
        for marker in (
            "representación gráfica",
            "representacion grafica",
            "gráficos de línea",
            "graficos de linea",
            "gráficos de barras",
            "graficos de barras",
            "diagramas de cajón",
            "diagrama de cajon",
        )
    ):
        for spec in FAMILY_SPECS:
            if spec["family_id"] == "graph_interpretation":
                return dict(spec)

    for spec in FAMILY_SPECS:
        if any(marker in haystack for marker in spec["atom_markers"]):
            return dict(spec)

    if skill == "ARG":
        return {
            "family_id": "argumentation_evaluation",
            "operation_signature": "argumentation_evaluation",
            "cognitive_action": "evaluate_claims",
            "solution_structure": "data_to_claim_check",
            "prompt_rules": (
                "La variante debe seguir evaluando validez de afirmaciones o justificaciones, no convertirse en cálculo directo puro.",
            ),
            "allowed_variant_shapes": ARGUMENTATION_SHAPES,
        }
    return {}


def get_family_spec_by_id(family_id: str) -> dict[str, Any]:
    """Return a catalog entry by its resolved family id."""
    wanted = str(family_id or "").strip()
    if not wanted:
        return {}
    for spec in FAMILY_SPECS:
        if spec["family_id"] == wanted:
            return dict(spec)
    return {}


def infer_non_mechanizable_expectation(family_id: str) -> str:
    """Return the expected non-mechanizability ceiling for a family."""
    normalized = str(family_id or "").strip()
    if normalized in LOW_NON_MECHANIZABLE_FAMILIES:
        return "low"
    if normalized in HIGH_NON_MECHANIZABLE_FAMILIES:
        return "high"
    return "medium"
