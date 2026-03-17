"""Representative source-item smoke cases for construct-contract inference."""

from __future__ import annotations


CONTRACT_SMOKE_CASES = [
    {
        "test_id": "Prueba-invierno-2025",
        "question_id": "Q11",
        "expected": {
            "family_id": "algebraic_expression_evaluation",
            "operation_signature": "algebraic_expression_evaluation",
            "cognitive_action": "substitute_and_compute",
            "solution_structure": "formula_substitution",
        },
    },
    {
        "test_id": "Prueba-invierno-2025",
        "question_id": "Q13",
        "expected": {
            "family_id": "percentage_context_application",
            "operation_signature": "percentage_increase_application",
            "cognitive_action": "compute_value",
            "solution_structure": "routine_procedural",
        },
    },
    {
        "test_id": "Prueba-invierno-2025",
        "question_id": "Q17",
        "expected": {
            "family_id": "argumentation_evaluation",
            "operation_signature": "argumentation_evaluation",
            "cognitive_action": "evaluate_claims",
            "solution_structure": "data_to_claim_check",
        },
    },
    {
        "test_id": "Prueba-invierno-2025",
        "question_id": "Q24",
        "expected": {
            "family_id": "trinomial_factorization",
            "operation_signature": "trinomial_factorization",
            "cognitive_action": "transform_expression",
            "solution_structure": "expression_factoring",
        },
    },
    {
        "test_id": "Prueba-invierno-2025",
        "question_id": "Q28",
        "expected": {
            "family_id": "linear_equation_resolution",
            "operation_signature": "linear_equation_resolution",
            "cognitive_action": "solve_for_unknown",
            "solution_structure": "equation_resolution",
        },
    },
    {
        "test_id": "Prueba-invierno-2025",
        "question_id": "Q35",
        "expected": {
            "family_id": "graph_interpretation",
            "cognitive_action": "interpret_representation",
            "solution_structure": "representation_reading",
        },
    },
    {
        "test_id": "Prueba-invierno-2025",
        "question_id": "Q48",
        "expected": {
            "family_id": "geometry_measurement_application",
            "operation_signature": "geometry_measurement_application",
            "solution_structure": "geometry_formula_application",
        },
    },
    {
        "test_id": "Prueba-invierno-2025",
        "question_id": "Q60",
        "expected": {
            "family_id": "descriptive_statistics",
            "operation_signature": "descriptive_statistics",
            "cognitive_action": "compute_statistic",
        },
    },
    {
        "test_id": "seleccion-regular-2026",
        "question_id": "Q30",
        "expected": {
            "family_id": "parameter_interpretation",
            "operation_signature": "parameter_interpretation",
            "cognitive_action": "interpret_model",
            "solution_structure": "parameter_meaning_interpretation",
        },
    },
    {
        "test_id": "seleccion-regular-2026",
        "question_id": "Q55",
        "expected": {
            "family_id": "graph_interpretation",
            "cognitive_action": "interpret_representation",
            "solution_structure": "representation_reading",
        },
    },
    {
        "test_id": "seleccion-regular-2026",
        "question_id": "Q64",
        "expected": {
            "family_id": "geometry_measurement_application",
            "operation_signature": "geometry_measurement_application",
            "cognitive_action": "compute_value",
            "solution_structure": "geometry_formula_application",
        },
    },
]
