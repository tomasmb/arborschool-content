"""Shared structural-profile inference for hard-variant generation.

This module centralizes task-shape and operation-signature inference so the
planner, generator, and validator reason over the same source fingerprint.
"""

from __future__ import annotations

import re
from typing import Any

from app.question_variants.contracts.contract_features import (
    infer_argument_polarity,
    infer_auxiliary_transformations,
    infer_base_domain,
    infer_claim_archetype,
    infer_data_burden_score,
    infer_extremum_polarity,
    infer_formula_shape,
    infer_graph_rate_frame,
    infer_justification_archetype,
    infer_model_family,
    infer_measure_transition,
    infer_percentage_band,
    infer_percentage_change_pattern,
    infer_parameter_statement_form,
    infer_power_base_family,
    infer_presentation_style,
    infer_proportional_reasoning_mode,
    infer_response_mode,
    infer_reference_relation_count,
    infer_rate_reference_frame,
    infer_representation_series_count,
    infer_result_property_type,
    infer_selection_load,
    infer_statistic_target_domain,
)
from app.question_variants.contracts.family_catalog import (
    get_family_spec_by_id,
    infer_non_mechanizable_expectation,
    resolve_family_spec,
)


def build_construct_contract(
    question_text: str,
    qti_xml: str,
    has_visual_support: bool,
    primary_atoms: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
    choices: list[str] | None = None,
    correct_answer: str = "",
) -> dict[str, Any]:
    metadata = metadata or {}
    choices = choices or []
    main_skill = metadata.get("habilidad_principal", {}).get("habilidad_principal", "")
    profile = build_structural_profile(question_text, qti_xml, has_visual_support, primary_atoms, main_skill)
    difficulty = metadata.get("difficulty", {})

    evidence_mode = "symbolic_or_textual"
    explicit_dataset_policy = "optional"
    representation_must_remain_primary = False
    cognitive_action = infer_cognitive_action(profile, primary_atoms, main_skill)
    solution_structure = infer_solution_structure(profile, primary_atoms, metadata)
    distractor_archetypes = infer_distractor_archetypes(choices, correct_answer, profile, solution_structure)
    correct_claim_archetype = infer_claim_archetype(correct_answer)
    correct_justification_archetype = infer_justification_archetype(correct_answer, profile)
    response_mode = infer_response_mode(choices, correct_answer)
    auxiliary_transformations = infer_auxiliary_transformations(question_text, metadata)
    reference_relation_count = infer_reference_relation_count(question_text)
    data_burden_score = infer_data_burden_score(question_text, profile)
    formula_shape = infer_formula_shape(question_text, qti_xml, profile)
    argument_polarity = infer_argument_polarity(question_text, profile)
    model_family = infer_model_family(question_text, qti_xml, profile)
    statistic_target_domain = infer_statistic_target_domain(question_text, profile)
    percentage_band = infer_percentage_band(question_text, profile)
    percentage_change_pattern = infer_percentage_change_pattern(question_text, profile)
    selection_load = infer_selection_load(question_text, qti_xml, profile)
    base_domain = infer_base_domain(question_text, profile)
    power_base_family = infer_power_base_family(question_text, profile)
    result_property_type = infer_result_property_type(question_text, profile)
    measure_transition = infer_measure_transition(question_text, profile)
    rate_reference_frame = infer_rate_reference_frame(correct_answer, profile)
    parameter_statement_form = infer_parameter_statement_form(correct_answer, profile)
    extremum_polarity = infer_extremum_polarity(question_text, profile)
    presentation_style = infer_presentation_style(question_text, qti_xml, profile)
    representation_series_count = infer_representation_series_count(question_text, qti_xml, profile)
    graph_rate_frame = infer_graph_rate_frame(question_text, qti_xml, profile)
    proportional_reasoning_mode = infer_proportional_reasoning_mode(question_text, correct_answer, profile)

    must_preserve_distractor_logic = profile["claim_evaluation"] or (
        profile["operation_signature"] in {"direct_percentage_calculation", "percentage_increase_application"}
        and bool(distractor_archetypes)
    )

    if profile["claim_evaluation"]:
        evidence_mode = "explicit_dataset_and_claims"
        explicit_dataset_policy = "required"
    elif profile["representation_interpretation"]:
        evidence_mode = "representation_primary"
        explicit_dataset_policy = "must_not_replace_representation"
        representation_must_remain_primary = True
    elif profile["visual_role"] == "data_bearing":
        evidence_mode = "visual_support_with_self_containment"
        explicit_dataset_policy = "required_or_described"
    elif has_visual_support:
        evidence_mode = "visual_structural_support"
        explicit_dataset_policy = "not_required_if_geometry_is_explicit"

    return {
        "primary_atoms": [atom.get("atom_id") for atom in primary_atoms],
        "primary_atom_titles": [atom.get("atom_title") for atom in primary_atoms],
        "family_id": profile["family_id"],
        "allowed_variant_shapes": list(profile.get("allowed_variant_shapes", [])),
        "non_mechanizable_expectation": infer_non_mechanizable_expectation(str(profile["family_id"])),
        "main_skill": main_skill,
        "difficulty_level": difficulty.get("level", ""),
        "difficulty_score": difficulty.get("score"),
        "task_form": profile["task_form"],
        "operation_signature": profile["operation_signature"],
        "requires_direct_computation": profile["requires_direct_computation"],
        "allows_unknowns": not profile["must_not_introduce_algebraic_unknowns"],
        "requires_visual_support": has_visual_support,
        "visual_role": profile["visual_role"],
        "representation_interpretation": profile["representation_interpretation"],
        "claim_evaluation": profile["claim_evaluation"],
        "cognitive_action": cognitive_action,
        "solution_structure": solution_structure,
        "auxiliary_transformations": auxiliary_transformations,
        "reference_relation_count": reference_relation_count,
        "data_burden_score": data_burden_score,
        "formula_shape": formula_shape,
        "argument_polarity": argument_polarity,
        "model_family": model_family,
        "statistic_target_domain": statistic_target_domain,
        "percentage_band": percentage_band,
        "percentage_change_pattern": percentage_change_pattern,
        "selection_load": selection_load,
        "base_domain": base_domain,
        "power_base_family": power_base_family,
        "result_property_type": result_property_type,
        "measure_transition": measure_transition,
        "rate_reference_frame": rate_reference_frame,
        "parameter_statement_form": parameter_statement_form,
        "extremum_polarity": extremum_polarity,
        "presentation_style": presentation_style,
        "representation_series_count": representation_series_count,
        "graph_rate_frame": graph_rate_frame,
        "proportional_reasoning_mode": proportional_reasoning_mode,
        "response_mode": response_mode,
        "evidence_mode": evidence_mode,
        "explicit_dataset_policy": explicit_dataset_policy,
        "representation_must_remain_primary": representation_must_remain_primary,
        "must_preserve_distractor_logic": must_preserve_distractor_logic,
        "distractor_archetypes": distractor_archetypes,
        "correct_claim_archetype": correct_claim_archetype,
        "correct_justification_archetype": correct_justification_archetype,
        "hard_constraints": _build_hard_constraints(profile, has_visual_support),
    }


def build_structural_profile(
    question_text: str,
    qti_xml: str,
    has_visual_support: bool,
    primary_atoms: list[dict[str, Any]],
    main_skill: str = "",
) -> dict[str, bool | str]:
    text = question_text.lower()
    xml = qti_xml.lower()
    atom_titles = [str(a.get("atom_title", "")).lower() for a in primary_atoms]
    atom_hints = _collect_atom_hints(primary_atoms)
    skill = str(main_skill or "").upper()
    family_spec = resolve_family_spec(atom_hints, skill)
    if looks_like_zero_button_composition(text, xml):
        family_spec = get_family_spec_by_id("ten_power_zero_composition")
    if looks_like_place_value_decomposition(text, xml):
        family_spec = get_family_spec_by_id("algebraic_model_translation")

    asks_error_step = "¿en qué paso" in text or "en que paso" in text or "primer error" in text
    has_unknown = any(token in xml for token in ("<mi>x</mi>", "<mi>y</mi>", "<mi>z</mi>"))
    asks_value_of_unknown = _asks_to_solve_unknown(text)
    representation_interpretation = skill == "REP" or any(
        marker in " ".join(atom_titles)
        for marker in ("representación gráfica", "representacion grafica", "gráfico", "grafico", "pendiente")
    )
    requires_direct_computation = any("cálculo directo" in title or "calculo directo" in title for title in atom_titles)
    operation_signature = str(family_spec.get("operation_signature") or infer_operation_signature(atom_titles, skill))
    claim_evaluation = (
        operation_signature in {"data_claim_evaluation", "argumentation_evaluation"}
        or (
            any("afirmaciones basadas en datos" in title for title in atom_titles) or looks_like_claim_evaluation(text)
        )
        and operation_signature
        not in {
            "direct_percentage_calculation",
            "percentage_increase_application",
            "direct_proportion_reasoning",
            "parameter_interpretation",
            "graph_interpretation",
        }
    )
    substitute_expression = (
        operation_signature == "algebraic_expression_evaluation"
        or ("ecuación:" in text or "equacion:" in text or "se utiliza la siguiente ecuación" in text or "se utiliza la siguiente expresion" in text)
        and ("si " in text and any(token in text for token in (" es ", " son ", " equivale", "equivalente")))
        and not asks_value_of_unknown
    )
    visual_role = infer_visual_role(question_text, qti_xml, primary_atoms, main_skill, has_visual_support)

    return {
        "task_form": (
            "error_analysis"
            if asks_error_step
            else "solve_for_unknown"
            if asks_value_of_unknown or operation_signature == "linear_equation_resolution"
            else "claim_evaluation"
            if (
                operation_signature in {"data_claim_evaluation", "argumentation_evaluation"}
                or (
                    claim_evaluation
                    and operation_signature
                    not in {
                        "direct_percentage_calculation",
                        "percentage_increase_application",
                        "direct_proportion_reasoning",
                        "parameter_interpretation",
                    }
                )
            )
            else "substitute_expression"
            if substitute_expression
            else "representation_interpretation"
            if representation_interpretation or operation_signature == "graph_interpretation"
            else "direct_resolution"
        ),
        "family_id": str(family_spec.get("family_id") or ""),
        "operation_signature": operation_signature,
        "allowed_variant_shapes": list(family_spec.get("allowed_variant_shapes", [])),
        "introduces_unknowns": has_unknown or asks_value_of_unknown,
        "must_not_introduce_algebraic_unknowns": not (has_unknown or asks_value_of_unknown),
        "claim_evaluation": claim_evaluation,
        "representation_interpretation": representation_interpretation,
        "visual_role": visual_role,
        "requires_direct_computation": requires_direct_computation,
        "appears_multi_step": appears_multi_step(text),
        "expects_explicit_dataset": claim_evaluation or visual_role == "data_bearing",
        "has_explicit_dataset": has_explicit_dataset(text, xml),
        "extra_base_quantity": has_extra_base_quantity(text) if operation_signature == "direct_percentage_calculation" else False,
    }


def _build_hard_constraints(profile: dict[str, bool | str], has_visual_support: bool) -> list[str]:
    constraints: list[str] = [
        f"task_form={profile['task_form']}",
        f"operation_signature={profile['operation_signature']}",
    ]
    if profile["must_not_introduce_algebraic_unknowns"]:
        constraints.append("must_not_introduce_algebraic_unknowns")
    if profile["claim_evaluation"]:
        constraints.append("must_keep_claim_evaluation")
        constraints.append("must_include_explicit_dataset")
        constraints.append("must_preserve_distractor_logic")
    if profile["operation_signature"] in {"direct_percentage_calculation", "percentage_increase_application"}:
        constraints.append("must_preserve_distractor_logic")
    if profile["operation_signature"] in {"algebraic_expression_evaluation", "direct_proportion_reasoning"}:
        constraints.append("must_not_add_auxiliary_transformations")
    if profile["operation_signature"] == "trinomial_factorization":
        constraints.append("must_preserve_standard_trinomial_form")
    if profile["representation_interpretation"]:
        constraints.append("must_keep_representation_as_primary_evidence")
    if profile["requires_direct_computation"]:
        constraints.append("must_preserve_direct_computation")
    if has_visual_support:
        constraints.append("must_remain_self_contained")
    return constraints


def infer_operation_signature(atom_titles: list[str], main_skill: str = "") -> str:
    atom_text = " ".join(atom_titles)
    skill = str(main_skill or "").upper()
    if "afirmaciones basadas en datos" in atom_text:
        return "data_claim_evaluation"
    if "división de potencias de igual base racional" in atom_text or "division de potencias de igual base racional" in atom_text:
        return "property_justification"
    if "cálculo directo del porcentaje" in atom_text or "calculo directo del porcentaje" in atom_text:
        return "direct_percentage_calculation"
    if "aumentos porcentuales" in atom_text:
        return "percentage_increase_application"
    if "expresiones algebraicas" in atom_text:
        return "algebraic_expression_evaluation"
    if "aumentos porcentuales" in atom_text:
        return "percentage_change"
    if "ecuaciones lineales" in atom_text:
        return "linear_equation_resolution"
    if "factorización de trinomios" in atom_text or "factorizacion de trinomios" in atom_text:
        return "trinomial_factorization"
    if "mediana" in atom_text or "media aritmética" in atom_text or "media aritmetica" in atom_text:
        return "descriptive_statistics"
    if "perímetro y área" in atom_text or "perimetro y area" in atom_text:
        return "integrated_geometry_problem"
    if "representación gráfica de proporcionalidad directa" in atom_text or "representacion grafica de proporcionalidad directa" in atom_text:
        return "graph_interpretation_proportionality"
    if "números enteros" in atom_text or "numeros enteros" in atom_text:
        return "integer_operations"
    if skill == "REP":
        return "representation_interpretation"
    if skill == "ARG":
        return "argumentation_evaluation"
    return "generic_same_construct"


def looks_like_zero_button_composition(text: str, xml: str) -> bool:
    lowered = f"{text} {xml}".lower()
    button_markers = (
        "[00]",
        "[000]",
        "botón",
        "boton",
        "botones",
        "tecla 00",
        "tecla 000",
        "atajo",
        "grupo de ceros",
        "grupos de ceros",
    )
    zero_group_markers = ("[00]", "[000]", "doble cero", "triple cero", "grupo de ceros", "grupos de ceros")
    ten_markers = ("10^", "10 ", "10)", "número 1000", "numero 1000", "potencia de 10")
    return (
        any(marker in lowered for marker in button_markers)
        and any(marker in lowered for marker in zero_group_markers)
        and any(marker in lowered for marker in ten_markers)
    )


def looks_like_place_value_decomposition(text: str, xml: str) -> bool:
    lowered = f"{text} {xml}".lower()
    decomposition_markers = (
        "descomposición del número",
        "descomposicion del numero",
        "representa una descomposición",
        "representa una descomposicion",
        "descompone un número",
        "descompone un numero",
        "valor posicional",
        "formato numérico estándar",
        "formato numerico estandar",
    )
    power_ten_markers = ("10</mn>", "10&#160;", "10 ", "msup", "×10", "·10")
    power_term_count = lowered.count("msup") + lowered.count("10^") + lowered.count("·10")
    interpretation_markers = (
        "potencias de 10",
        "cantidad exacta",
        "representa la cantidad",
        "interpreta correctamente esta cantidad",
        "descomposición polinómica",
        "descomposicion polinomica",
    )
    return (
        any(marker in lowered for marker in power_ten_markers)
        and power_term_count >= 2
        and (
            any(marker in lowered for marker in decomposition_markers)
            or any(marker in lowered for marker in interpretation_markers)
        )
    )


def looks_like_claim_evaluation(text: str) -> bool:
    markers = ("afirmación", "afirmacion", "i.", "ii.", "iii.", "correcta", "incorrecta")
    hits = sum(1 for marker in markers if marker in text)
    return hits >= 3


def has_explicit_dataset(text: str, xml: str) -> bool:
    dataset_markers = (
        "<table",
        "<qti-table",
        "porcentaje",
        "%",
        "litros",
        "kilogramos",
        "metros",
        "horas",
        "minutos",
        "segundos",
        "frecuencia",
        "datos",
    )
    lowered_text = text.lower()
    lowered_xml = xml.lower()
    has_coordinate_pairs = (
        len(re.findall(r"\(\s*\d+(?:[.,]\d+)?\s*,\s*\d+(?:[.,]\d+)?\s*\)", text)) >= 2
    )
    has_labeled_value_list = (
        len(re.findall(r"[a-záéíóúñ][^:\n]{0,30}:\s*\d+(?:[.,]\d+)?", lowered_text)) >= 3
    )
    has_table_markup = bool(re.search(r"<(?:[a-z0-9]+:)?table\b", lowered_xml))
    has_visual_markup = bool(re.search(r"<(?:[a-z0-9]+:)?(?:img|object)\b", lowered_xml))
    return (
        any(marker in lowered_xml or marker in lowered_text for marker in dataset_markers)
        or has_table_markup
        or has_visual_markup
        or has_coordinate_pairs
        or has_labeled_value_list
    )


def appears_multi_step(text: str) -> bool:
    markers = (
        "primero",
        "luego",
        "después",
        "despues",
        "a continuación",
        "posteriormente",
        "restante",
        "remanente",
        "finalmente",
    )
    return sum(1 for marker in markers if marker in text) >= 2


def has_extra_base_quantity(text: str) -> bool:
    contextual_markers = (
        "área",
        "area",
        "rectángulo",
        "rectangulo",
        "largo",
        "ancho",
        "alto",
        "volumen",
        "perímetro",
        "perimetro",
    )
    numeric_tokens = re.findall(r"\d+(?:[.,]\d+)?", text)
    return len(numeric_tokens) >= 3 or any(marker in text for marker in contextual_markers)


def infer_cognitive_action(
    profile: dict[str, bool | str],
    primary_atoms: list[dict[str, Any]],
    main_skill: str,
) -> str:
    family_spec = resolve_family_spec(
        _collect_atom_hints(primary_atoms),
        main_skill,
    )
    if family_spec.get("cognitive_action"):
        return str(family_spec["cognitive_action"])
    atom_titles = [str(atom.get("atom_title", "")).lower() for atom in primary_atoms]
    atom_text = " ".join(atom_titles)
    skill = str(main_skill or "").upper()
    if profile["claim_evaluation"]:
        return "evaluate_claims"
    if profile["operation_signature"] == "ten_power_zero_composition":
        return "compute_value"
    if profile["operation_signature"] == "property_justification":
        return "justify_property"
    if profile["representation_interpretation"] or skill == "REP":
        return "interpret_representation"
    if profile["task_form"] == "error_analysis":
        return "identify_error"
    if profile["task_form"] == "solve_for_unknown":
        return "solve_for_unknown"
    if profile["task_form"] == "substitute_expression":
        return "substitute_and_compute"
    if "factorización" in atom_text or "factorizacion" in atom_text:
        return "transform_expression"
    if "mediana" in atom_text or "media aritmética" in atom_text or "media aritmetica" in atom_text:
        return "compute_statistic"
    return "compute_value"


def infer_solution_structure(
    profile: dict[str, bool | str],
    primary_atoms: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> str:
    family_spec = resolve_family_spec(
        _collect_atom_hints(primary_atoms),
        str(metadata.get("habilidad_principal", {}).get("habilidad_principal", "")),
    )
    if family_spec.get("solution_structure"):
        return str(family_spec["solution_structure"])
    atom_titles = [str(atom.get("atom_title", "")).lower() for atom in primary_atoms]
    atom_text = " ".join(atom_titles)
    difficulty_analysis = str(metadata.get("difficulty", {}).get("analysis", "")).lower()

    if profile["claim_evaluation"]:
        return "data_to_claim_check"
    if profile["operation_signature"] == "ten_power_zero_composition":
        return "direct_single_step"
    if profile["operation_signature"] == "property_justification":
        return "property_justification"
    if profile["representation_interpretation"]:
        return "representation_reading"
    if profile["task_form"] == "error_analysis":
        return "error_localization"
    if profile["task_form"] == "solve_for_unknown":
        return "equation_resolution"
    if profile["task_form"] == "substitute_expression":
        return "formula_substitution"
    if "integrados" in atom_text or "perímetro y área" in atom_text or "perimetro y area" in atom_text:
        return "integrated_multi_step"
    if "factorización" in atom_text or "factorizacion" in atom_text:
        return "expression_factoring"
    if "múltiples pasos" in difficulty_analysis or "varios pasos" in difficulty_analysis or "proceso de dos pasos" in difficulty_analysis:
        return "guided_multi_step"
    if profile["requires_direct_computation"]:
        return "direct_single_step"
    return "routine_procedural"


def infer_distractor_archetypes(
    choices: list[str],
    correct_answer: str,
    profile: dict[str, bool | str],
    solution_structure: str,
) -> list[str]:
    archetypes: list[str] = []
    lowered_choices = [choice.lower() for choice in choices]
    lowered_correct = correct_answer.lower()
    wrong_choices = [choice for choice in lowered_choices if choice != lowered_correct]

    if profile["claim_evaluation"]:
        if any(
            marker in choice
            for choice in wrong_choices
            for marker in ("en conjunto", "conjunto", "conjunta", "juntas", "sumadas", "al sumar")
        ):
            archetypes.append("combined_subgroups_vs_main_group")
        if any(
            marker in choice
            for choice in wrong_choices
            for marker in (
                "se debe realizar la operación",
                "se debe realizar la operacion",
                "se debe multiplicar",
                "se debe dividir",
                "se debe calcular multiplicando",
            )
        ):
            archetypes.append("wrong_percentage_base_operation")
        if any(
            "%" in choice
            and any(
                marker in choice
                for marker in (
                    "del total",
                    "del agua",
                    "del país",
                    "del pais",
                    "total del país",
                    "total del pais",
                    "totales",
                    "ingresos totales",
                    "generación eléctrica total",
                )
            )
            for choice in wrong_choices
        ):
            archetypes.append("subgroup_vs_total_confusion")
    elif profile["operation_signature"] in {"direct_percentage_calculation", "percentage_increase_application"}:
        if all(_extract_primary_numeric_value(choice) is not None for choice in choices):
            archetypes.extend(["increment_only", "base_plus_increment", "gross_overestimate"])
    elif solution_structure in {"guided_multi_step", "data_to_claim_check"}:
        archetypes.append("intermediate_result_confusion")

    return archetypes


def _extract_primary_numeric_value(text: str) -> float | None:
    match = re.search(r"\d+(?:[.,]\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", "."))
    except ValueError:
        return None


def infer_visual_role(
    question_text: str,
    qti_xml: str,
    primary_atoms: list[dict[str, Any]],
    main_skill: str,
    has_visual_support: bool,
) -> str:
    if not has_visual_support:
        return "none"

    text = question_text.lower()
    xml = qti_xml.lower()
    atom_titles = [str(atom.get("atom_title", "")).lower() for atom in primary_atoms]
    atom_text = " ".join(atom_titles)
    skill = str(main_skill or "").upper()

    if "afirmaciones basadas en datos" in atom_text:
        return "data_bearing"
    if skill == "REP" or "representación gráfica" in atom_text or "representacion grafica" in atom_text:
        return "representation_primary"
    if any(marker in text or marker in xml for marker in ("gráfico", "grafico", "infografía", "infografia", "tabla de datos", "porcentajes")):
        return "data_bearing"
    if any(marker in text or marker in xml for marker in ("figura adjunta", "esquema", "círculo inscrito", "circulo inscrito", "caja de pizza", "triángulo", "triangulo")):
        return "structural_illustration"
    return "generic_visual_support"


def _asks_to_solve_unknown(text: str) -> bool:
    solve_markers = (
        "valor de x",
        "valor de y",
        "valor de z",
        "resolver la ecuación",
        "resolver la ecuacion",
        "solución de la ecuación",
        "solucion de la ecuacion",
        "¿cuál es x",
        "¿cuál es y",
        "¿cuál es z",
    )
    return any(marker in text for marker in solve_markers)


def _collect_atom_hints(primary_atoms: list[dict[str, Any]]) -> list[str]:
    """Collect normalized atom titles and ids for family resolution."""
    hints: list[str] = []
    for atom in primary_atoms:
        title = str(atom.get("atom_title", "")).strip().lower()
        atom_id = str(atom.get("atom_id", "")).strip().lower()
        if title:
            hints.append(title)
        if atom_id:
            hints.append(atom_id)
    return hints
