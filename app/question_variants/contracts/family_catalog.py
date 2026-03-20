"""Explicit family catalog for official-question construct coverage."""

from __future__ import annotations

from typing import Any


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
