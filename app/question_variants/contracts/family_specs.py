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
            "Los distractores numéricos deben ser plausibles y de la misma escala que la respuesta correcta."
        )
    if op == "property_justification":
        rules.append(
            "Conserva la misma polaridad argumentativa del contrato: no cambies una justificación válida por una refutación, ni al revés."
        )
        rules.append(
            "La justificación correcta no puede repetir la misma receta verbal; cambia de verdad el dominio de la base, la propiedad final o el tipo de explicación decisiva."
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
    if op == "algebraic_model_translation":
        rules.append(
            "La variante debe seguir evaluando traducción o interpretación algebraica del contexto, no resolución final del modelo."
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
            "Conserva el mismo modo de respuesta del contrato: si la fuente pide identificar una etiqueta o categoría, no la conviertas en evaluación de afirmaciones largas."
        )
    if op in {"radical_operations", "polynomial_operations", "decimal_number_operations"}:
        rules.append(
            "La variante debe seguir siendo una operatoria o transformación rutinaria de la misma familia simbólica, sin migrar a otro dominio matemático."
        )
    return rules
