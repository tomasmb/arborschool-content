"""Family-specific deterministic repairs for variant blueprints.

Each repair function targets a known planner drift pattern. Repairs are
applied in order; the first matching repair wins for each blueprint.
"""

from __future__ import annotations

from typing import Any

from app.question_variants.models import VariantBlueprint


def repair_blueprints(
    blueprints: list[VariantBlueprint],
    construct_contract: dict[str, Any],
) -> list[VariantBlueprint]:
    """Apply deterministic family constraints to planner outputs."""
    repairs = [
        _repair_aux_step_violation,
        _repair_direct_percentage_shape,
        _repair_model_translation_visual,
        _repair_graph_slope_inversion,
        _repair_graph_extremum_focus,
        _repair_property_justification,
        _repair_percentage_increase_shape,
        _repair_argumentation_false_claim,
    ]
    repaired: list[VariantBlueprint] = []
    for bp in blueprints:
        for fn in repairs:
            patched = fn(bp, construct_contract)
            if patched is not None:
                bp = patched
                break
        repaired.append(bp)
    return repaired


# ------------------------------------------------------------------
# Individual repair functions
# ------------------------------------------------------------------


def _repair_aux_step_violation(
    bp: VariantBlueprint,
    cc: dict[str, Any],
) -> VariantBlueprint | None:
    hard = {str(c) for c in cc.get("hard_constraints", [])}
    family = str(cc.get("family_id") or "")
    if not (
        "must_not_add_auxiliary_transformations" in hard
        and family in {
            "algebraic_expression_evaluation",
            "direct_proportion_reasoning",
        }
        and _mentions_auxiliary_conversion(bp.scenario_description)
    ):
        return None
    return _patch(
        bp,
        scenario=(
            "La variante debe mantener una sola sustitución o relación "
            "directa del mismo tipo de la fuente, cambiando la presentación "
            "a formato verbal o registro breve, pero sin equivalencias, "
            "conversiones ni pasos auxiliares adicionales."
        ),
        reasoning=(
            "La comprensión exigida debe venir de interpretar correctamente "
            "la regla o relación principal en una nueva presentación, no de "
            "agregar una segunda conversión o transformación auxiliar."
        ),
    )


def _repair_direct_percentage_shape(
    bp: VariantBlueprint,
    cc: dict[str, Any],
) -> VariantBlueprint | None:
    if not (
        str(cc.get("family_id") or "") == "direct_percentage_calculation"
        and str(cc.get("operation_signature") or "")
        == "direct_percentage_calculation"
        and str(cc.get("presentation_style") or "") == "plain_narrative"
        and str(cc.get("selection_load") or "") == "single_given_base"
        and bp.selected_shape_id != "decision_statement"
    ):
        return None
    return _patch(
        bp,
        scenario=(
            "La variante debe presentar un registro o nota contextual breve "
            "y luego pedir seleccionar la afirmación coherente con la parte "
            "porcentual calculada, en vez de repetir otra pregunta literal "
            "por el valor final. Los distractores deben quedar en la misma "
            "escala de la respuesta correcta y representar errores plausibles "
            "de coma decimal, ancla de 10 % o división incorrecta por el "
            "número del porcentaje."
        ),
        axes=["forma_pregunta", "distractor_dominante"],
        reasoning=(
            "La comprensión debe venir de interpretar correctamente la "
            "cantidad base y el porcentaje dentro de un registro breve, "
            "distinguiendo la parte porcentual correcta de errores "
            "plausibles de cálculo directo sin introducir magnitudes "
            "intermedias."
        ),
        shape_id="decision_statement",
    )


def _repair_model_translation_visual(
    bp: VariantBlueprint,
    cc: dict[str, Any],
) -> VariantBlueprint | None:
    if not (
        str(cc.get("family_id") or "") == "algebraic_model_translation"
        and str(cc.get("task_form") or "") == "representation_interpretation"
        and not cc.get("requires_visual_support")
        and (
            bp.requires_image
            or _mentions_visual_support(bp.scenario_description)
            or _mentions_visual_support(bp.required_reasoning)
        )
    ):
        return None
    return _patch(
        bp,
        scenario=(
            "La variante debe mantener una representación primaria simbólica "
            "o posicional sin agregar gráficos, tablas ni figuras nuevas. "
            "Puede presentar una descomposición, expresión o registro breve "
            "y luego pedir seleccionar la descripción posicional o "
            "interpretación algebraica coherente, en vez de limitarse a otra "
            "pregunta literal por el número final."
        ),
        axes=["forma_pregunta", "representacion"],
        reasoning=(
            "La comprensión debe venir de leer correctamente la "
            "representación simbólica o posicional y vincularla con una "
            "interpretación coherente de valor posicional o modelo, sin "
            "reemplazarla por soporte visual ni reducirla a un cálculo "
            "mecánico de escritura directa."
        ),
        requires_image=False,
        image_description="",
        shape_id="model_to_context_match",
    )


def _repair_graph_slope_inversion(
    bp: VariantBlueprint,
    cc: dict[str, Any],
) -> VariantBlueprint | None:
    if not (
        str(cc.get("family_id") or "") == "graph_interpretation"
        and str(cc.get("graph_rate_frame") or "") == "direct_slope_rate"
        and _matches_slope_inversion(bp)
    ):
        return None
    return _patch(
        bp,
        scenario=(
            "La variante debe seguir usando una representación gráfica donde "
            "la pendiente represente directamente la razón pedida. Si se "
            "pregunta por el mayor rendimiento o rapidez, la respuesta "
            "correcta debe corresponder a la recta de mayor pendiente dentro "
            "de la misma lectura de la representación."
        ),
        reasoning=(
            "El estudiante debe interpretar correctamente qué magnitudes "
            "están en cada eje, manteniendo que la pendiente expresa "
            "directamente la razón buscada. La dificultad debe venir del "
            "foco de lectura o de distractores visuales plausibles, no de "
            "invertir la razón."
        ),
    )


def _repair_graph_extremum_focus(
    bp: VariantBlueprint,
    cc: dict[str, Any],
) -> VariantBlueprint | None:
    if not (
        str(cc.get("family_id") or "") == "graph_interpretation"
        and str(cc.get("graph_rate_frame") or "") == "direct_slope_rate"
        and str(cc.get("response_mode") or "") == "label_selection"
        and bp.selected_shape_id == "extremum_focus"
    ):
        return None
    return _patch(
        bp,
        scenario=(
            "La variante debe mantener un gráfico de una sola serie donde "
            "la pendiente represente directamente la razón pedida, pero "
            "cambiar la forma de respuesta a una afirmación breve sobre qué "
            "etiqueta corresponde al mayor rendimiento o a la mayor razón "
            "observada."
        ),
        axes=["representacion", "forma_pregunta"],
        reasoning=(
            "El estudiante debe interpretar la pendiente o el orden de "
            "razones dentro del gráfico y luego validar una afirmación "
            "breve sobre cuál etiqueta representa la mayor tasa, sin que "
            "baste repetir mecánicamente el mismo prompt de la fuente."
        ),
        shape_id="single_series_visual_claim",
    )


def _repair_property_justification(
    bp: VariantBlueprint,
    cc: dict[str, Any],
) -> VariantBlueprint | None:
    if str(cc.get("family_id") or "") != "property_justification":
        return None

    shape = bp.selected_shape_id
    if (
        str(cc.get("argument_polarity") or "") == "justify_valid_application"
        and shape == "invalid_reason_detection"
    ):
        shape = "justification_statement_selection"

    power_family = str(cc.get("power_base_family") or "")
    if power_family != "binary_power_composition":
        return None

    low = bp.scenario_description.lower()
    generic_drift = (
        "mismo constructo" in low
        or "potencias de igual base" not in low
        or "inválida" in low
        or "invalida" in low
    )
    if generic_drift:
        return _patch(
            bp,
            scenario=(
                "La variante debe seguir pidiendo una justificación válida "
                "para una división entre potencias de igual base dentro de "
                "la misma familia binaria del contrato (por ejemplo, base 4 "
                "u 8). El resultado debe conservar una propiedad equivalente "
                "a la fuente, como seguir siendo un número par."
            ),
            reasoning=(
                "El estudiante debe usar la regla de conservar la base y "
                "restar exponentes, manteniendo una base de la misma "
                "familia binaria y justificando por qué el resultado "
                "preserva la propiedad pedida sin cambiar la polaridad "
                "del argumento."
            ),
            shape_id=shape or "justification_statement_selection",
        )

    if str(cc.get("result_property_type") or "") == "even_integer":
        return _patch(
            bp,
            scenario=(
                "La variante debe seguir pidiendo una justificación válida "
                "para una división entre potencias de igual base de la misma "
                "familia binaria, pero debe elegir exponentes positivos y "
                "una base binaria distinta de la fuente, de modo que la "
                "explicación correcta combine la resta de exponentes con la "
                "idea de que una potencia positiva de base par sigue "
                "siendo par."
            ),
            reasoning=(
                "El estudiante debe reconocer la ley de división de "
                "potencias de igual base y, además, conectar el resultado "
                "con la paridad de una base par elevada a un exponente "
                "entero positivo. La justificación correcta no puede "
                "quedarse solo en copiar la misma receta verbal de la "
                "fuente."
            ),
            shape_id=shape or "justification_statement_selection",
        )
    return None


def _repair_percentage_increase_shape(
    bp: VariantBlueprint,
    cc: dict[str, Any],
) -> VariantBlueprint | None:
    if not (
        str(cc.get("family_id") or "") == "percentage_context_application"
        and str(cc.get("operation_signature") or "")
        == "percentage_increase_application"
        and str(cc.get("presentation_style") or "") == "plain_narrative"
        and str(cc.get("selection_load") or "") == "single_given_base"
        and bp.selected_shape_id == "ledger_context"
    ):
        return None
    return _patch(
        bp,
        scenario=(
            "La variante debe presentar un registro o nota contextual breve "
            "y luego pedir seleccionar la afirmación o resultado coherente "
            "con el aumento porcentual, en vez de repetir una pregunta "
            "directa por el valor final. Los distractores deben quedar en "
            "la misma escala de la respuesta correcta y representar errores "
            "plausibles de base, incremento o sobreestimación."
        ),
        axes=["forma_pregunta", "distractor_dominante"],
        reasoning=(
            "La comprensión debe venir de interpretar correctamente la base "
            "y el aumento porcentual dentro de un registro breve, "
            "descartando afirmaciones numéricas plausibles sin caer en una "
            "receta idéntica a la fuente."
        ),
        shape_id="decision_statement",
    )


def _repair_argumentation_false_claim(
    bp: VariantBlueprint,
    cc: dict[str, Any],
) -> VariantBlueprint | None:
    if not (
        str(cc.get("family_id") or "") == "argumentation_evaluation"
        and bp.selected_shape_id == "false_claim_hunt"
    ):
        return None
    return _patch(
        bp,
        scenario=(
            "La variante debe reorganizar el dataset explícito en un formato "
            "distinto al de la fuente (por ejemplo tabla, registro o listado "
            "estructurado) y pedir seleccionar la afirmación correcta basada "
            "en un arquetipo semántico distinto al de la fuente. Las otras "
            "tres opciones deben conservar las trampas conceptuales del ítem "
            "original sin convertirlo en cálculo directo."
        ),
        reasoning=(
            "El estudiante debe contrastar parte-todo, subgrupos y "
            "operaciones válidas sobre porcentajes a partir de una "
            "organización de evidencia nueva, distinguiendo un arquetipo de "
            "afirmación correcta distinto del original sin perder la lógica "
            "de distractores."
        ),
        shape_id="claim_archetype_switch",
    )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _patch(
    bp: VariantBlueprint,
    *,
    scenario: str | None = None,
    axes: list[str] | None = None,
    reasoning: str | None = None,
    shape_id: str | None = None,
    requires_image: bool | None = None,
    image_description: str | None = None,
) -> VariantBlueprint:
    """Return a new VariantBlueprint with selectively overridden fields."""
    return VariantBlueprint(
        variant_id=bp.variant_id,
        scenario_description=scenario if scenario is not None else bp.scenario_description,
        non_mechanizable_axes=axes if axes is not None else bp.non_mechanizable_axes,
        required_reasoning=reasoning if reasoning is not None else bp.required_reasoning,
        difficulty_target=bp.difficulty_target,
        requires_image=requires_image if requires_image is not None else bp.requires_image,
        image_description=image_description if image_description is not None else bp.image_description,
        selected_shape_id=shape_id if shape_id is not None else bp.selected_shape_id,
    )


def _mentions_auxiliary_conversion(text: str) -> bool:
    lowered = str(text or "").lower()
    markers = (
        "equivale", "equivalencia", "conversión", "conversion",
        "convertir", "pasa a", "joule", "kilojoule", "kilogramo",
        "gramo", "miligram", "kilocalor",
    )
    return any(m in lowered for m in markers)


def _mentions_visual_support(text: str) -> bool:
    lowered = str(text or "").lower()
    markers = (
        "gráfico", "grafico", "figura", "tabla",
        "diagrama", "barra", "línea", "linea",
    )
    return any(m in lowered for m in markers)


def _matches_slope_inversion(bp: VariantBlueprint) -> bool:
    low_scenario = bp.scenario_description.lower()
    low_reasoning = bp.required_reasoning.lower()
    return (
        "invers" in low_scenario
        or "invers" in low_reasoning
        or "menor pendiente" in low_scenario
        or "menor pendiente" in low_reasoning
    )
