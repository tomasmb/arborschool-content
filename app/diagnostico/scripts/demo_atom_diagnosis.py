#!/usr/bin/env python3
"""
Demo: Visualizar diagnósticos de átomos del MST.

Simula un estudiante respondiendo el diagnóstico y muestra:
- Átomos dominados
- Átomos con gaps (necesitan enseñar)
- Átomos con misconceptions (necesitan corregir)

Uso:
    python -m app.diagnostico.scripts.demo_atom_diagnosis
"""

import random

from app.diagnostico.engine import MSTEngine, Response, ResponseType


def simulate_responses(questions, correct_rate=0.5, dont_know_rate=0.1):
    """Simula respuestas de un estudiante."""
    responses = []
    for q in questions:
        rand = random.random()
        if rand < correct_rate:
            resp_type = ResponseType.CORRECT
        elif rand < correct_rate + dont_know_rate:
            resp_type = ResponseType.DONT_KNOW
        else:
            resp_type = ResponseType.INCORRECT
        responses.append(Response(question=q, response_type=resp_type))
    return responses


def print_diagnosis_report(result):
    """Imprime reporte de diagnóstico por átomo."""
    print("\n" + "=" * 70)
    print("📊 DIAGNÓSTICO POR ÁTOMO")
    print("=" * 70)

    # Group by status
    dominados = [a for a in result.atom_diagnoses if a.status == "dominado"]
    gaps = [a for a in result.atom_diagnoses if a.status == "gap"]
    misconceptions = [a for a in result.atom_diagnoses if a.status == "misconception"]

    print(f"\n✅ DOMINADOS ({len(dominados)} átomos)")
    print("-" * 50)
    for atom in dominados[:10]:  # Show first 10
        print(f"   • {atom.atom_id}: {atom.atom_title[:50]}...")
    if len(dominados) > 10:
        print(f"   ... y {len(dominados) - 10} más")

    print(f"\n❓ GAPS - Necesitan enseñar ({len(gaps)} átomos)")
    print("-" * 50)
    for atom in gaps:
        print(f"   • {atom.atom_id}: {atom.atom_title}")
        print(f"     → Recomendación: {atom.instruction_type}")

    print(f"\n❌ MISCONCEPTIONS - Necesitan corregir ({len(misconceptions)} átomos)")
    print("-" * 50)
    for atom in misconceptions:
        print(f"   • {atom.atom_id}: {atom.atom_title}")
        print(f"     → Recomendación: {atom.instruction_type}")

    # Plan de estudio
    plan_atoms = [a for a in result.atom_diagnoses if a.include_in_plan]
    print(f"\n📚 PLAN DE ESTUDIO ({len(plan_atoms)} átomos a trabajar)")
    print("-" * 50)
    for i, atom in enumerate(plan_atoms, 1):
        icon = "🔧" if atom.status == "misconception" else "📖"
        action = "Corregir" if atom.status == "misconception" else "Enseñar"
        print(f"   {i}. {icon} [{action}] {atom.atom_title}")

    # Estimación de tiempo
    tiempo_total = len(plan_atoms) * 15  # 15 min por átomo
    horas = tiempo_total // 60
    minutos = tiempo_total % 60
    print(f"\n⏱️  TIEMPO ESTIMADO: {horas}h {minutos}min ({len(plan_atoms)} átomos × 15 min)")

    print("\n" + "=" * 70)


def main():
    print("🎯 DEMO: Diagnóstico de Átomos MST")
    print("=" * 70)

    engine = MSTEngine()

    # Fase 1: Routing
    print("\n📝 ETAPA 1: Routing (8 preguntas)")
    r1_questions = engine.get_routing_questions()

    # Simular con 50% correctas (típico estudiante medio)
    r1_responses = simulate_responses(r1_questions, correct_rate=0.5, dont_know_rate=0.1)
    route = engine.record_r1_responses(r1_responses)

    r1_correct = sum(1 for r in r1_responses if r.is_correct)
    print(f"   Correctas: {r1_correct}/8")
    print(f"   Ruta asignada: {route.value.upper()}")

    # Fase 2: Módulo según ruta
    print(f"\n📝 ETAPA 2: Módulo {route.name} (8 preguntas)")
    stage2_questions = engine.get_stage2_questions()

    # Simular respuestas etapa 2
    stage2_responses = simulate_responses(stage2_questions, correct_rate=0.5, dont_know_rate=0.1)
    engine.record_stage2_responses(stage2_responses)

    s2_correct = sum(1 for r in stage2_responses if r.is_correct)
    print(f"   Correctas: {s2_correct}/8")

    # Obtener resultado completo
    result = engine.get_result()

    # Mostrar resumen
    print("\n" + "=" * 70)
    print("📈 RESUMEN")
    print("=" * 70)
    print(f"   Total correctas: {result.total_correct}/16")
    print(f"   Puntaje PAES estimado: {result.paes_score} ({result.paes_range_min}-{result.paes_range_max})")

    # Mostrar diagnóstico por átomo
    print_diagnosis_report(result)


if __name__ == "__main__":
    main()
