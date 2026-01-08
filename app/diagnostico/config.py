"""
Configuración de la prueba diagnóstica MST PAES M1.

Este archivo contiene:
- Las 32 preguntas seleccionadas organizadas por módulo
- Reglas de routing
- Mapping de puntajes PAES
"""

from typing import Dict, List, TypedDict
from dataclasses import dataclass
from enum import Enum


class Skill(Enum):
    """Habilidades PAES M1"""
    RES = "Resolver"
    MOD = "Modelar"
    REP = "Representar"
    ARG = "Argumentar"


class Axis(Enum):
    """Ejes temáticos PAES M1"""
    ALG = "Álgebra y Funciones"
    NUM = "Números"
    GEO = "Geometría"
    PROB = "Probabilidad y Estadística"


class Route(Enum):
    """Rutas del MST"""
    A = "bajo"
    B = "medio"
    C = "alto"


@dataclass
class Question:
    """Representa una pregunta en el MST"""
    exam: str
    question_id: str
    axis: Axis
    skill: Skill
    score: float
    
    @property
    def full_path(self) -> str:
        return f"app/data/pruebas/finalizadas/{self.exam}/qti/{self.question_id}"


# =============================================================================
# MÓDULO R1: ROUTING (8 preguntas)
# Todos los estudiantes responden estas preguntas primero
# =============================================================================
R1_QUESTIONS: List[Question] = [
    Question("seleccion-regular-2025", "Q32", Axis.ALG, Skill.RES, 0.50),
    Question("seleccion-regular-2026", "Q33", Axis.ALG, Skill.MOD, 0.45),
    Question("prueba-invierno-2026", "Q7", Axis.NUM, Skill.RES, 0.50),
    Question("prueba-invierno-2026", "Q23", Axis.NUM, Skill.ARG, 0.45),
    Question("seleccion-regular-2026", "Q41", Axis.GEO, Skill.RES, 0.45),
    Question("prueba-invierno-2026", "Q48", Axis.GEO, Skill.ARG, 0.45),
    Question("seleccion-regular-2026", "Q62", Axis.PROB, Skill.RES, 0.50),
    Question("seleccion-regular-2026", "Q61", Axis.PROB, Skill.REP, 0.45),
]

# =============================================================================
# MÓDULO A2: RUTA BAJO (8 preguntas)
# Para estudiantes con 0-3 correctas en R1
# =============================================================================
A2_QUESTIONS: List[Question] = [
    Question("prueba-invierno-2026", "Q37", Axis.ALG, Skill.RES, 0.20),
    Question("seleccion-regular-2026", "Q40", Axis.ALG, Skill.MOD, 0.25),
    Question("seleccion-regular-2026", "Q30", Axis.ALG, Skill.ARG, 0.25),
    Question("prueba-invierno-2026", "Q19", Axis.NUM, Skill.RES, 0.15),
    Question("prueba-invierno-2026", "Q18", Axis.NUM, Skill.MOD, 0.25),
    Question("prueba-invierno-2026", "Q22", Axis.GEO, Skill.RES, 0.25),
    Question("prueba-invierno-2026", "Q53", Axis.PROB, Skill.RES, 0.20),
    Question("seleccion-regular-2026", "Q54", Axis.PROB, Skill.REP, 0.25),
]

# =============================================================================
# MÓDULO B2: RUTA MEDIO (8 preguntas)
# Para estudiantes con 4-6 correctas en R1
# =============================================================================
B2_QUESTIONS: List[Question] = [
    Question("Prueba-invierno-2025", "Q11", Axis.ALG, Skill.RES, 0.50),
    Question("prueba-invierno-2026", "Q6", Axis.ALG, Skill.MOD, 0.45),
    Question("seleccion-regular-2026", "Q47", Axis.ALG, Skill.ARG, 0.45),
    Question("Prueba-invierno-2025", "Q18", Axis.NUM, Skill.RES, 0.50),
    Question("seleccion-regular-2026", "Q5", Axis.NUM, Skill.ARG, 0.55),
    Question("seleccion-regular-2026", "Q45", Axis.GEO, Skill.RES, 0.45),
    Question("prueba-invierno-2026", "Q54", Axis.PROB, Skill.REP, 0.45),
    Question("prueba-invierno-2026", "Q57", Axis.PROB, Skill.ARG, 0.45),
]

# =============================================================================
# MÓDULO C2: RUTA ALTO (8 preguntas)
# Para estudiantes con 7-8 correctas en R1
# =============================================================================
C2_QUESTIONS: List[Question] = [
    Question("seleccion-regular-2026", "Q27", Axis.ALG, Skill.RES, 0.65),
    Question("seleccion-regular-2026", "Q48", Axis.ALG, Skill.MOD, 0.65),
    Question("prueba-invierno-2026", "Q36", Axis.ALG, Skill.ARG, 0.55),
    Question("seleccion-regular-2025", "Q23", Axis.NUM, Skill.MOD, 0.65),
    Question("Prueba-invierno-2025", "Q56", Axis.NUM, Skill.ARG, 0.65),
    Question("seleccion-regular-2025", "Q65", Axis.GEO, Skill.ARG, 0.60),
    Question("Prueba-invierno-2025", "Q61", Axis.PROB, Skill.ARG, 0.65),
    Question("seleccion-regular-2026", "Q53", Axis.PROB, Skill.REP, 0.60),
]


# =============================================================================
# CONFIGURACIÓN MST
# =============================================================================
MST_CONFIG = {
    "modules": {
        "R1": R1_QUESTIONS,
        "A2": A2_QUESTIONS,
        "B2": B2_QUESTIONS,
        "C2": C2_QUESTIONS,
    },
    "total_questions_per_student": 16,
    "routing_module": "R1",
    "stage_2_modules": ["A2", "B2", "C2"],
}


# =============================================================================
# REGLAS DE ROUTING
# =============================================================================
ROUTING_RULES = {
    "cuts": {
        (0, 3): Route.A,   # 0-3 correctas → Ruta A (bajo)
        (4, 6): Route.B,   # 4-6 correctas → Ruta B (medio)
        (7, 8): Route.C,   # 7-8 correctas → Ruta C (alto)
    }
}


def get_route(r1_correct: int) -> Route:
    """
    Determina la ruta según las respuestas correctas en R1.
    
    Args:
        r1_correct: Número de respuestas correctas en R1 (0-8)
        
    Returns:
        Route: La ruta asignada (A, B, o C)
    """
    if r1_correct < 0 or r1_correct > 8:
        raise ValueError(f"r1_correct debe estar entre 0 y 8, recibido: {r1_correct}")
    
    for (min_val, max_val), route in ROUTING_RULES["cuts"].items():
        if min_val <= r1_correct <= max_val:
            return route
    
    raise ValueError(f"No se encontró ruta para {r1_correct} correctas")


# =============================================================================
# MAPPING DE PUNTAJES PAES
# =============================================================================
PAES_MAPPING = {
    Route.A: {
        # Total correctas (R1 + A2) → (puntaje_estimado, rango_min, rango_max)
        (0, 3): (420, 380, 460),
        (4, 5): (470, 440, 500),
        (6, 7): (495, 460, 525),
        (8, 9): (520, 490, 555),
        (10, 11): (545, 510, 580),
    },
    Route.B: {
        (7, 8): (525, 500, 555),
        (9, 10): (565, 540, 595),
        (11, 12): (590, 560, 620),
        (13, 14): (620, 595, 650),
        (15, 16): (650, 625, 680),
    },
    Route.C: {
        (12, 13): (635, 600, 670),
        (14, 14): (665, 630, 700),
        (15, 15): (690, 650, 730),
        (16, 16): (715, 670, 760),
    },
}


def get_paes_score(route: Route, total_correct: int) -> tuple[int, int, int]:
    """
    Calcula el puntaje PAES estimado según la ruta y total de correctas.
    
    Args:
        route: La ruta del estudiante (A, B, o C)
        total_correct: Total de respuestas correctas (R1 + Etapa 2)
        
    Returns:
        Tuple[int, int, int]: (puntaje_estimado, rango_min, rango_max)
    """
    route_mapping = PAES_MAPPING[route]
    
    for (min_val, max_val), scores in route_mapping.items():
        if min_val <= total_correct <= max_val:
            return scores
    
    # Si no hay match exacto, usar el límite más cercano
    all_ranges = list(route_mapping.keys())
    min_range = min(r[0] for r in all_ranges)
    max_range = max(r[1] for r in all_ranges)
    
    if total_correct < min_range:
        return route_mapping[all_ranges[0]]
    else:
        return route_mapping[all_ranges[-1]]
