"""Shared structural-profile inference for hard-variant generation.

This module centralizes task-shape and operation-signature inference so the
planner, generator, and validator reason over the same source fingerprint.
"""

from __future__ import annotations

import re
from typing import Any


def build_construct_contract(
    question_text: str,
    qti_xml: str,
    has_visual_support: bool,
    primary_atoms: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = metadata or {}
    main_skill = metadata.get("habilidad_principal", {}).get("habilidad_principal", "")
    profile = build_structural_profile(question_text, qti_xml, has_visual_support, primary_atoms, main_skill)
    difficulty = metadata.get("difficulty", {})

    evidence_mode = "symbolic_or_textual"
    explicit_dataset_policy = "optional"
    representation_must_remain_primary = False
    cognitive_action = infer_cognitive_action(profile, primary_atoms, main_skill)
    solution_structure = infer_solution_structure(profile, primary_atoms, metadata)

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
        "evidence_mode": evidence_mode,
        "explicit_dataset_policy": explicit_dataset_policy,
        "representation_must_remain_primary": representation_must_remain_primary,
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
    skill = str(main_skill or "").upper()

    asks_error_step = "¿en qué paso" in text or "en que paso" in text or "primer error" in text
    has_unknown = any(token in xml for token in ("<mi>x</mi>", "<mi>y</mi>", "<mi>z</mi>"))
    asks_value_of_unknown = _asks_to_solve_unknown(text)
    claim_evaluation = any("afirmaciones basadas en datos" in title for title in atom_titles) or looks_like_claim_evaluation(text)
    representation_interpretation = skill == "REP" or any(
        marker in " ".join(atom_titles)
        for marker in ("representación gráfica", "representacion grafica", "gráfico", "grafico", "pendiente")
    )
    requires_direct_computation = any("cálculo directo" in title or "calculo directo" in title for title in atom_titles)
    operation_signature = infer_operation_signature(atom_titles, skill)
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
            else "substitute_expression"
            if substitute_expression
            else "claim_evaluation"
            if claim_evaluation
            else "representation_interpretation"
            if representation_interpretation
            else "direct_resolution"
        ),
        "operation_signature": operation_signature,
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
    return any(marker in xml or marker in text for marker in dataset_markers)


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
    atom_titles = [str(atom.get("atom_title", "")).lower() for atom in primary_atoms]
    atom_text = " ".join(atom_titles)
    skill = str(main_skill or "").upper()
    if profile["claim_evaluation"]:
        return "evaluate_claims"
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
    atom_titles = [str(atom.get("atom_title", "")).lower() for atom in primary_atoms]
    atom_text = " ".join(atom_titles)
    difficulty_analysis = str(metadata.get("difficulty", {}).get("analysis", "")).lower()

    if profile["claim_evaluation"]:
        return "data_to_claim_check"
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
    if "múltiples pasos" in difficulty_analysis or "varios pasos" in difficulty_analysis or "proceso de dos pasos" in difficulty_analysis:
        return "guided_multi_step"
    if profile["requires_direct_computation"]:
        return "direct_single_step"
    return "routine_procedural"


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
