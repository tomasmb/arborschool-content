"""Family-specific prompt rules for the hard-variants pipeline."""

from __future__ import annotations

from typing import Any

from app.question_variants.contracts.family_catalog import get_family_spec_by_id


def build_family_prompt_rules(contract: dict[str, Any]) -> list[str]:
    """Return only the prompt rules relevant to the current construct contract."""
    task_form = str(contract.get("task_form") or "")
    op = str(contract.get("operation_signature") or "")
    family_id = str(contract.get("family_id") or "")
    rules: list[str] = []
    family_spec = get_family_spec_by_id(family_id)

    for rule in family_spec.get("prompt_rules", ()):
        if rule not in rules:
            rules.append(rule)

    if task_form == "error_analysis":
        rules.append(
            'Si la fuente es "error_analysis", la variante debe seguir preguntando por el primer error o paso incorrecto.'
        )
    if contract.get("representation_must_remain_primary"):
        rules.append(
            'Si el contrato dice "representation_primary", no reemplaces la interpretación de representación por una tabla o lista que permita responder sin interpretarla.'
        )
        if not contract.get("requires_visual_support"):
            rules.append(
                "Si la fuente no trae apoyo visual, no inventes gráficos, tablas o figuras nuevas. Mantén la representación primaria en texto estructurado, MathML o registro simbólico."
            )
    if contract.get("must_preserve_distractor_logic"):
        rules.append(
            "Debes preservar los mismos arquetipos de distractor: no reemplaces trampas conceptuales por valores arbitrarios."
        )
    if "must_preserve_standard_trinomial_form" in (contract.get("hard_constraints") or []):
        rules.append(
            "Mantén un trinomio expandido x^2 + bx + c; no reescribas en formas desplazadas, racionales ni equivalentes que aumenten dificultad."
        )
    if task_form == "substitute_expression":
        rules.append(
            "Conserva la misma forma algebraica de sustitución del contrato; una sustitución multiplicativa no debe transformarse en una regla afín con término fijo."
        )
        rules.append(
            "Evita repetir exactamente el mismo estilo de presentación; si la fuente usa fórmula simbólica + referencia, cambia a una formulación verbal o estructurada."
        )
    if task_form == "solve_for_unknown":
        rules.append(
            "Conserva la misma familia de modelo del contrato, por ejemplo relación cociente vs relación afín."
        )
    if task_form == "claim_evaluation":
        rules.append(
            "La variante debe seguir evaluando afirmaciones sobre un conjunto de datos explícito y autocontenido."
        )
        rules.append(
            "No basta con cambiar etiquetas o contexto: cambia de verdad la organización de la evidencia o el arquetipo de afirmación correcta."
        )
        if str(contract.get("non_mechanizable_expectation") or "") == "high":
            rules.append(
                "En esta familia no basta con invertir la polaridad local de VERDADERA/FALSA: también debes cambiar el arquetipo central de la afirmación correcta o la forma de organizar la evidencia."
            )
        source_claim_archetype = str(contract.get("correct_claim_archetype") or "")
        if source_claim_archetype and source_claim_archetype != "other_claim":
            rules.append(
                f"La afirmación correcta NO puede repetir el mismo arquetipo semántico de la fuente ({source_claim_archetype}). "
                "Debes elegir un arquetipo distinto dentro del mismo constructo."
            )
    if op in {"direct_percentage_calculation", "percentage_increase_application"}:
        rules.append(
            "Debe seguir siendo un aumento/cálculo porcentual directo, no una modelación de varios pasos ni una interpretación abierta."
        )
        rules.append(
            "Conserva la misma banda de magnitud porcentual y la misma carga de selección de datos del contrato."
        )
        rules.append(
            "Si la fuente entrega directamente la cantidad base, no conviertas la variante en una búsqueda entre varios registros, días o categorías."
        )
        rules.append(
            "Si el objetivo es des-mecanizar una fuente muy directa, prefiere cambiar la forma de pregunta a selección de afirmación o consistencia contextual en vez de repetir otra pregunta literal por el valor final."
        )
        rules.append(
            "Los distractores numéricos deben ser plausibles y de la misma escala que la respuesta correcta."
        )
    if op == "property_justification":
        rules.append(
            "Conserva la misma polaridad argumentativa del contrato: no cambies una justificación válida por una refutación, ni al revés."
        )
        rules.append(
            "La justificación correcta no puede repetir la misma receta verbal; cambia de verdad el dominio de la base, la propiedad final o el tipo de explicación decisiva."
        )
        power_family = str(contract.get("power_base_family") or "not_applicable")
        if power_family not in {"not_applicable", "generic_power_family"}:
            rules.append(
                f"Conserva la misma familia de base del contrato ({power_family}). No la reemplaces por otra base que cambie el mecanismo central de la justificación."
            )
        if str(contract.get("power_base_family") or "") == "ten_power_zero_composition":
            rules.append(
                "Si la fuente construye una potencia de 10 mediante botones o grupos de ceros, la variante debe seguir trabajando con base 10 y composición de ceros, no con otra base ni con factorización de otra potencia."
            )
            rules.append(
                "Mantén el mismo mecanismo central: seleccionar una combinación de grupos de ceros que compone el exponente total."
            )
    if op == "ten_power_zero_composition":
        rules.append(
            "La variante debe seguir construyendo una potencia de 10 mediante combinación de grupos de ceros o botones equivalentes, no justificar propiedades generales de potencias."
        )
        rules.append(
            "No cambies la tarea a una explicación verbal de reglas de exponentes; debe seguir siendo selección de la secuencia correcta de ingreso/composición."
        )
        rules.append(
            "Para que no quede mecanizable, cambia la forma de presentación o el patrón de distractores, pero mantén base 10 y el recuento total de ceros como foco central."
        )
    if op == "descriptive_statistics":
        rules.append(
            "Conserva una carga de datos comparable a la fuente y el mismo dominio estadístico objetivo."
        )
    if op == "trinomial_factorization":
        rules.append(
            "La variante debe seguir siendo factorización de trinomio, no simplificación racional ni otro álgebra."
        )
    if op == "parameter_interpretation":
        rules.append(
            "La variante debe seguir pidiendo interpretar el significado de un coeficiente, parámetro o variable, no resolver el modelo completo."
        )
        rules.append(
            "Conserva el mismo tipo de parámetro interpretado: tasa, pendiente, intercepto, valor inicial o rol de variable, según indique el contrato."
        )
        rules.append(
            "No repitas el mismo marco interrogativo directo de la fuente; cambia la forma de presentación, por ejemplo a selección de afirmación, inferencia contextual o comparación breve."
        )
        rules.append(
            "Si la fuente interpreta la tasa por cada 1 unidad, evita conservar exactamente ese mismo marco; prefiere una tasa equivalente sobre 10 o 100 unidades, o una afirmación contextual equivalente."
        )
        rules.append(
            "Si la fuente formula la opción correcta como tasa literal ('por cada ...'), intenta mover la variante a una afirmación contextual equivalente, no a otra tasa verbal casi idéntica."
        )
        rules.append(
            "No incluyas dos opciones equivalentes expresadas en unidades distintas; debe existir una sola interpretación correcta del parámetro."
        )
        rules.append(
            "Cuando el parámetro representa una tasa, materializa al menos un eje no mecanizable como caso concreto verificable: la opción correcta debe describir una situación específica o decisión contextual, no sólo recitar la tasa."
        )
        rules.append(
            "Si cambias la forma de pregunta, no basta con pasar de '¿Cómo se interpreta?' a '¿Cuál afirmación...?': el nuevo ítem debe apoyarse en un caso o escenario concreto que obligue a comprender el significado práctico del parámetro."
        )
        rules.append(
            "No conviertas la interpretación directa del coeficiente en una comparación entre dos casos ('si dos personas difieren en...', 'una diferencia de ... implica ...'). Eso evalúa aplicación de variación, no el mismo foco interpretativo."
        )
        rules.append(
            "Evita distractores puramente literales o simétricos del tipo 'es N veces'; prefiere distractores contextualizados que expresen una interpretación plausible pero incorrecta del mismo caso."
        )
        rules.append(
            "Evita equivalencias demasiado obvias del tipo '100 unidades -> 4 unidades' como única novedad. Si usas un caso concreto, preséntalo como registro, nota operativa o situación aplicada, no como simple escalamiento mecánico."
        )
        rules.append(
            "No fijes en el enunciado un caso estándar específico ('estanque de 1000 litros', 'paciente de 10 kg', etc.) para luego pedir la opción que solo calcula ese caso. Eso desplaza la tarea hacia aplicación directa del modelo."
        )
        rules.append(
            "Si usas un registro o nota operativa, la comprensión debe seguir centrada en el significado del coeficiente y no en resolver un caso particular dado previamente en el enunciado."
        )
    if op == "linear_equation_resolution":
        rules.append(
            "No repitas la plantilla casi intacta 'relación por paquete/unidad + dato adicional fijo + total final -> ¿cuántos x?'. Cambia al menos la forma de preguntar o el rol contextual del dato adicional."
        )
        rules.append(
            "Mantén una sola ecuación lineal del mismo tipo, pero usa un framing menos directo: por ejemplo subtotal/restante/cantidad complementaria, sin agregar pasos algebraicos nuevos."
        )
        rules.append(
            "No conviertas la incógnita en una cantidad complementaria o 'lo que quedó faltando' si eso obliga a resolver x y luego hacer una sustracción adicional."
        )
        rules.append(
            "Evita reutilizar exactamente el mismo valor numérico para la tasa del modelo y para el monto fijo o inicial del contexto; si hay coincidencias, la relación queda confusa aunque el cálculo siga siendo lineal."
        )
    if op == "simple_probability":
        rules.append(
            "La variante debe mantener el mismo tipo de probabilidad simple: casos favorables sobre casos posibles o suma de eventos excluyentes."
        )
    if op == "conditional_probability":
        rules.append(
            "La variante debe conservar la misma estructura de dependencia o reducción del espacio muestral; no la cambies por probabilidad simple independiente."
        )
    if op == "direct_proportion_reasoning":
        rules.append(
            "La variante debe seguir siendo proporcionalidad directa con la misma estructura de relación entre magnitudes."
        )
        rules.append(
            "No conviertas una razón directa o regla de tres en ecuación lineal, fórmula afín ni lectura puramente verbal sin relación entre magnitudes."
        )
        rules.append(
            "Si la fuente expresa una condición que garantiza exactitud o divisibilidad, la variante debe seguir preguntando por una condición que garantice exactitud, no por el valor calculado final."
        )
        if str(contract.get("proportional_reasoning_mode") or "") == "divisibility_condition":
            rules.append(
                "Para condiciones de divisibilidad, no repitas la misma receta literal. Cambia la representación hacia un control operativo o registro, manteniendo la condición matemática equivalente."
            )
            rules.append(
                "Los distractores deben repartirse entre un control demasiado exigente, uno insuficiente y uno desviado, sin incluir condiciones equivalentes a la correcta."
            )
    if op == "percentage_increase_application" and str(contract.get("percentage_change_pattern") or "") != "not_applicable":
        rules.append(
            "Conserva la misma polaridad y secuencia de cambios porcentuales de la fuente. Si la fuente combina alza y rebaja, la variante también debe combinar esos signos en el mismo orden."
        )
    if op == "algebraic_model_translation":
        rules.append(
            "La variante debe seguir evaluando traducción o interpretación algebraica del contexto, no resolución final del modelo."
        )
        rules.append(
            "No mezcles una consigna de descripciones o interpretaciones con opciones puramente simbólicas, ni una consigna de expresiones con opciones narrativas. La forma de pregunta y el tipo de alternativas deben ser coherentes."
        )
        rules.append(
            "Si la fuente no tiene apoyo visual, no menciones figura, tabla, gráfico o imagen. Mantén la evidencia principal en texto, número, expresión o registro breve."
        )
    if op == "isometry_transformations":
        rules.append(
            "La variante debe conservar el mismo foco en reconocer o aplicar una isometría, no derivar a cálculos geométricos adicionales."
        )
    if op == "geometry_measurement_application":
        rules.append(
            "La variante debe conservar la misma dependencia geométrica central y un nivel comparable de apoyo visual o estructural."
        )
        rules.append(
            "No cambies entre área, perímetro, volumen o relación pitagórica si la fuente fijaba una de esas relaciones como núcleo."
        )
        rules.append(
            "Si la fuente es una aplicación geométrica rutinaria, no repitas intacta la misma transición de medida conocida->pedida; cambia al menos la medida dada o la medida solicitada sin salir de la misma familia geométrica."
        )
    if op == "graph_interpretation":
        rules.append(
            "Conserva el mismo modo de respuesta del contrato, salvo que la fuente sea una lectura de razón en gráfico y cambies a afirmaciones breves manteniendo la representación como evidencia primaria."
        )
        rules.append(
            "Conserva la misma polaridad del objetivo en la representación: si la fuente pide el valor más bajo o la habilidad más débil, no la conviertas en identificar el valor más alto, y viceversa."
        )
        rules.append(
            "No aumentes la cantidad de series o conjuntos comparados si la fuente solo representa una serie. Una fuente de serie única no debe transformarse en comparación entre dos momentos o grupos."
        )
        graph_rate_frame = str(contract.get("graph_rate_frame") or "not_applicable")
        if graph_rate_frame == "direct_slope_rate":
            rules.append(
                "Si la razón pedida coincide con la pendiente directa del gráfico, no inviertas los ejes ni conviertas la interpretación en el inverso de la pendiente."
            )
            rules.append(
                "En este caso sí puedes cambiar de etiqueta a afirmación breve si eso obliga a interpretar la pendiente o el orden de razones sin regalar la respuesta."
            )
        elif graph_rate_frame == "inverse_slope_rate":
            rules.append(
                "Si la razón pedida corresponde al inverso de la pendiente, conserva esa relación y no la conviertas en lectura directa de la pendiente."
            )
    if op in {"radical_operations", "polynomial_operations", "decimal_number_operations"}:
        rules.append(
            "La variante debe seguir siendo una operatoria o transformación rutinaria de la misma familia simbólica, sin migrar a otro dominio matemático."
        )
    return rules
