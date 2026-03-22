"""Curated deterministic regression cases for the hard-variants pipeline."""

from __future__ import annotations


STRUCTURAL_REGRESSION_CASES = [
    {
        "name": "Q28 approved quotient relation",
        "test_id": "Prueba-invierno-2025",
        "question_id": "Q28",
        "variant_xml_path": (
            "app/data/pruebas/hard_variants/benchmarks/"
            "gemini-gemini-openai-rejects-v3/Prueba-invierno-2025/Q28/variants/approved/Q28_v1/question.xml"
        ),
        "expected_ok": True,
    },
    {
        "name": "Q35 approved representation evidence",
        "test_id": "Prueba-invierno-2025",
        "question_id": "Q35",
        "variant_xml_path": (
            "app/data/pruebas/hard_variants/benchmarks/"
            "gemini-gemini-evidence-contract-smoke/Prueba-invierno-2025/Q35/variants/approved/Q35_v1/question.xml"
        ),
        "expected_ok": True,
    },
    {
        "name": "Q48 approved structural illustration",
        "test_id": "Prueba-invierno-2025",
        "question_id": "Q48",
        "variant_xml_path": (
            "app/data/pruebas/hard_variants/benchmarks/"
            "gemini-gemini-taxonomy-fix-smoke/Prueba-invierno-2025/Q48/variants/approved/Q48_v1/question.xml"
        ),
        "expected_ok": True,
    },
    {
        "name": "Q55 approved textual dataset fallback",
        "test_id": "seleccion-regular-2026",
        "question_id": "Q55",
        "variant_xml_path": (
            "app/data/pruebas/hard_variants/benchmarks/"
            "sample-q55-gemini-180-v4/seleccion-regular-2026/Q55/variants/approved/Q55_v1/question.xml"
        ),
        "expected_ok": True,
    },
    {
        "name": "Q55 approved single-series graph preservation",
        "test_id": "seleccion-regular-2026",
        "question_id": "Q55",
        "variant_xml_path": (
            "app/data/pruebas/hard_variants/benchmarks/"
            "sample-q55-v7/seleccion-regular-2026/Q55/variants/approved/Q55_v1/question.xml"
        ),
        "expected_ok": True,
    },
    {
        "name": "Q11 rejected affine substitution drift",
        "test_id": "Prueba-invierno-2025",
        "question_id": "Q11",
        "variant_xml_path": (
            "app/data/pruebas/hard_variants/benchmarks/"
            "gemini-gemini-family-repairs-v11/Prueba-invierno-2025/Q11/variants/approved/Q11_v1/question.xml"
        ),
        "expected_ok": False,
        "reason_contains": "forma algebraica de sustitución",
    },
    {
        "name": "Q14 rejected repeated claim archetype",
        "test_id": "Prueba-invierno-2025",
        "question_id": "Q14",
        "variant_xml_path": (
            "app/data/pruebas/hard_variants/benchmarks/"
            "gemini-gemini-diverse-contract-smoke/Prueba-invierno-2025/Q14/variants/rejected/Q14_v1/question.xml"
        ),
        "expected_ok": False,
        "reason_contains": "arquetipo semántico decisivo",
    },
    {
        "name": "Q24 rejected shifted factoring form",
        "test_id": "Prueba-invierno-2025",
        "question_id": "Q24",
        "variant_xml_path": (
            "app/data/pruebas/hard_variants/benchmarks/"
            "gemini-gemini-diverse-contract-smoke/Prueba-invierno-2025/Q24/variants/rejected/Q24_v1/question.xml"
        ),
        "expected_ok": False,
        "reason_contains": "formas desplazadas",
    },
    {
        "name": "Q60 rejected stats-domain drift",
        "test_id": "Prueba-invierno-2025",
        "question_id": "Q60",
        "variant_xml_path": (
            "app/data/pruebas/hard_variants/benchmarks/"
            "gemini-gemini-structural-families-v4/Prueba-invierno-2025/Q60/variants/rejected/Q60_v1/question.xml"
        ),
        "expected_ok": False,
        "reason_contains": "dominio estadístico objetivo",
    },
    {
        "name": "Q30 repaired grouped-rate interpretation",
        "test_id": "seleccion-regular-2026",
        "question_id": "Q30",
        "variant_xml_path": (
            "app/data/pruebas/hard_variants/benchmarks/"
            "sample-crossfamily-2026-v3/seleccion-regular-2026/Q30/variants/rejected/Q30_v1/question.xml"
        ),
        "expected_ok": True,
    },
    {
        "name": "Q30 approved operational variation interpretation",
        "test_id": "seleccion-regular-2026",
        "question_id": "Q30",
        "variant_xml_path": (
            "app/data/pruebas/hard_variants/benchmarks/"
            "sample-q30-v19/seleccion-regular-2026/Q30/variants/approved/Q30_v1/question.xml"
        ),
        "expected_ok": True,
    },
]
