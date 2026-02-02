"""
Funciones de scoring y diagnóstico para la prueba diagnóstica MST.

Incluye:
- Cálculo de puntaje PAES
- Diagnóstico de átomos
- Generación de plan de estudio
"""

import json
from pathlib import Path
from typing import Dict, List

from .config import Route, get_paes_score
from .engine import Response, ResponseType


def calculate_paes_score(
    route: Route,
    r1_correct: int,
    stage2_correct: int
) -> Dict:
    """
    Calcula el puntaje PAES estimado.

    Args:
        route: Ruta del estudiante (A, B, C)
        r1_correct: Correctas en R1
        stage2_correct: Correctas en Etapa 2

    Returns:
        Dict con puntaje estimado e intervalo de confianza
    """
    total_correct = r1_correct + stage2_correct
    score, range_min, range_max = get_paes_score(route, total_correct)

    return {
        "puntaje_estimado": score,
        "rango_min": range_min,
        "rango_max": range_max,
        "total_correctas": total_correct,
        "ruta": route.value,
        "nivel": _get_level(score),
    }


def _get_level(score: int) -> str:
    """Determina el nivel pedagógico según el puntaje"""
    if score < 450:
        return "Muy Inicial"
    elif score < 500:
        return "Inicial"
    elif score < 550:
        return "Intermedio Bajo"
    elif score < 600:
        return "Intermedio"
    elif score < 650:
        return "Intermedio Alto"
    elif score < 700:
        return "Alto"
    else:
        return "Muy Alto"


def diagnose_atoms(responses: List[Response]) -> List[Dict]:
    """
    Genera diagnósticos por átomo basados en las respuestas.

    Para cada pregunta, carga los átomos asociados y determina su estado
    basándose en la respuesta del estudiante.

    Args:
        responses: Lista de respuestas del estudiante

    Returns:
        Lista de diagnósticos por átomo
    """
    diagnoses = []
    base_path = Path(__file__).parent.parent / "data" / "pruebas" / "finalizadas"

    for response in responses:
        question = response.question
        metadata_path = base_path / question.exam / "qti" / question.question_id / "metadata_tags.json"

        if not metadata_path.exists():
            continue

        try:
            with open(metadata_path) as f:
                metadata = json.load(f)

            atoms = metadata.get("selected_atoms", [])

            for atom in atoms:
                atom_id = atom.get("atom_id", "unknown")
                atom_title = atom.get("atom_title", "Sin título")
                relevance = atom.get("relevance", "primary")

                # Solo considerar átomos primarios para diagnóstico
                if relevance != "primary":
                    continue

                # Determinar estado
                if response.response_type == ResponseType.CORRECT:
                    status = "dominado"
                    include_in_plan = False
                    instruction_type = None
                elif response.response_type == ResponseType.DONT_KNOW:
                    status = "gap"
                    include_in_plan = True
                    instruction_type = "enseñar"
                else:
                    status = "misconception"
                    include_in_plan = True
                    instruction_type = "corregir"

                diagnoses.append({
                    "atom_id": atom_id,
                    "atom_title": atom_title,
                    "respuesta": response.response_type.value,
                    "estado": status,
                    "incluir_en_plan": include_in_plan,
                    "tipo_instruccion": instruction_type,
                })

        except (json.JSONDecodeError, KeyError):
            continue

    return diagnoses


def generate_axis_diagnosis(responses: List[Response]) -> Dict[str, Dict]:
    """
    Genera diagnóstico por eje temático.

    Returns:
        Dict con rendimiento por eje
    """
    axis_stats: Dict[str, Dict] = {}

    for response in responses:
        axis_name = response.question.axis.value

        if axis_name not in axis_stats:
            axis_stats[axis_name] = {
                "correct": 0,
                "total": 0,
                "dont_know": 0,
                "incorrect": 0,
            }

        axis_stats[axis_name]["total"] += 1

        if response.response_type == ResponseType.CORRECT:
            axis_stats[axis_name]["correct"] += 1
        elif response.response_type == ResponseType.DONT_KNOW:
            axis_stats[axis_name]["dont_know"] += 1
        else:
            axis_stats[axis_name]["incorrect"] += 1

    # Calcular porcentajes y estados
    result = {}
    for axis, stats in axis_stats.items():
        pct = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0

        if pct >= 75:
            status = "fortaleza"
            icon = "✓"
        elif pct >= 50:
            status = "en_desarrollo"
            icon = ""
        else:
            status = "reforzar"
            icon = "⚠️"

        result[axis] = {
            "porcentaje": round(pct),
            "correctas": stats["correct"],
            "total": stats["total"],
            "status": status,
            "icon": icon,
        }

    return result


def generate_skill_diagnosis(responses: List[Response]) -> Dict[str, Dict]:
    """
    Genera diagnóstico por habilidad PAES.

    Returns:
        Dict con rendimiento por habilidad
    """
    skill_stats: Dict[str, Dict] = {}

    for response in responses:
        skill_name = response.question.skill.value

        if skill_name not in skill_stats:
            skill_stats[skill_name] = {"correct": 0, "total": 0}

        skill_stats[skill_name]["total"] += 1
        if response.response_type == ResponseType.CORRECT:
            skill_stats[skill_name]["correct"] += 1

    result = {}
    for skill, stats in skill_stats.items():
        pct = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0

        result[skill] = {
            "porcentaje": round(pct),
            "correctas": stats["correct"],
            "total": stats["total"],
        }

    return result


def generate_study_plan(atom_diagnoses: List[Dict]) -> Dict:
    """
    Genera un plan de estudio basado en los diagnósticos de átomos.

    Returns:
        Dict con átomos a aprender y corregir
    """
    to_learn = []
    to_correct = []

    for diagnosis in atom_diagnoses:
        if not diagnosis["incluir_en_plan"]:
            continue

        item = {
            "atom_id": diagnosis["atom_id"],
            "atom_title": diagnosis["atom_title"],
        }

        if diagnosis["tipo_instruccion"] == "enseñar":
            to_learn.append(item)
        else:
            to_correct.append(item)

    return {
        "por_aprender": to_learn,
        "por_corregir": to_correct,
        "total_items": len(to_learn) + len(to_correct),
    }
