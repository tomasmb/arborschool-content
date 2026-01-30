"""
Configuración de la prueba diagnóstica MST PAES M1.

Este archivo contiene:
- Las 32 preguntas seleccionadas organizadas por módulo
- Reglas de routing
- Mapping de puntajes PAES
"""

from dataclasses import dataclass
from enum import Enum
from typing import List


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
# Optimizado para máxima cobertura de átomos (v2.0 - 2026-01-09)
# =============================================================================
R1_QUESTIONS: List[Question] = [
    Question("Prueba-invierno-2025", "Q28", Axis.ALG, Skill.RES, 0.45),
    Question("prueba-invierno-2026", "Q31", Axis.ALG, Skill.MOD, 0.55),
    Question("prueba-invierno-2026", "Q23", Axis.NUM, Skill.ARG, 0.45),
    Question("seleccion-regular-2025", "Q15", Axis.NUM, Skill.ARG, 0.55),
    Question("Prueba-invierno-2025", "Q46", Axis.GEO, Skill.ARG, 0.45),
    Question("prueba-invierno-2026", "Q45", Axis.GEO, Skill.ARG, 0.55),
    Question("prueba-invierno-2026", "Q58", Axis.PROB, Skill.REP, 0.45),
    Question("seleccion-regular-2026", "Q60", Axis.PROB, Skill.RES, 0.45),
]

# =============================================================================
# MÓDULO A2: RUTA BAJO (8 preguntas)
# Para estudiantes con 0-3 correctas en R1
# Optimizado para máxima cobertura de átomos (v2.0 - 2026-01-09)
# =============================================================================
A2_QUESTIONS: List[Question] = [
    Question("Prueba-invierno-2025", "Q40", Axis.ALG, Skill.RES, 0.25),
    Question("seleccion-regular-2026", "Q35", Axis.ALG, Skill.MOD, 0.25),
    Question("prueba-invierno-2026", "Q40", Axis.ALG, Skill.RES, 0.25),
    Question("seleccion-regular-2025", "Q10", Axis.NUM, Skill.RES, 0.30),
    Question("Prueba-invierno-2025", "Q6", Axis.NUM, Skill.RES, 0.30),
    Question("seleccion-regular-2025", "Q63", Axis.GEO, Skill.REP, 0.30),
    Question("prueba-invierno-2026", "Q64", Axis.PROB, Skill.ARG, 0.35),
    Question("seleccion-regular-2025", "Q54", Axis.PROB, Skill.RES, 0.25),
]

# =============================================================================
# MÓDULO B2: RUTA MEDIO (8 preguntas)
# Para estudiantes con 4-6 correctas en R1
# Optimizado para máxima cobertura de átomos (v2.0 - 2026-01-09)
# =============================================================================
B2_QUESTIONS: List[Question] = [
    Question("prueba-invierno-2026", "Q42", Axis.ALG, Skill.MOD, 0.45),
    Question("seleccion-regular-2025", "Q38", Axis.ALG, Skill.RES, 0.55),
    Question("seleccion-regular-2025", "Q36", Axis.ALG, Skill.MOD, 0.55),
    Question("seleccion-regular-2025", "Q3", Axis.NUM, Skill.ARG, 0.55),
    Question("Prueba-invierno-2025", "Q22", Axis.NUM, Skill.MOD, 0.45),
    Question("seleccion-regular-2025", "Q60", Axis.GEO, Skill.RES, 0.45),
    Question("seleccion-regular-2025", "Q55", Axis.PROB, Skill.RES, 0.55),
    Question("Prueba-invierno-2025", "Q65", Axis.PROB, Skill.REP, 0.45),
]

# =============================================================================
# MÓDULO C2: RUTA ALTO (8 preguntas)
# Para estudiantes con 7-8 correctas en R1
# Optimizado para máxima cobertura de átomos (v2.0 - 2026-01-09)
# =============================================================================
C2_QUESTIONS: List[Question] = [
    Question("seleccion-regular-2026", "Q59", Axis.ALG, Skill.RES, 0.60),
    Question("seleccion-regular-2026", "Q11", Axis.ALG, Skill.MOD, 0.55),
    Question("Prueba-invierno-2025", "Q33", Axis.ALG, Skill.MOD, 0.60),
    Question("Prueba-invierno-2025", "Q56", Axis.NUM, Skill.ARG, 0.65),
    Question("seleccion-regular-2026", "Q23", Axis.NUM, Skill.RES, 0.55),
    Question("Prueba-invierno-2025", "Q50", Axis.GEO, Skill.REP, 0.55),
    Question("Prueba-invierno-2025", "Q61", Axis.PROB, Skill.ARG, 0.65),
    Question("prueba-invierno-2026", "Q60", Axis.PROB, Skill.ARG, 0.55),
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
# MAPPING DE PUNTAJES PAES (v2.1 - Ajustado por cobertura real)
# 10% de átomos no inferibles → techo real ~900
# Ruta C puede alcanzar 900, Ruta B ~800, Ruta A ~650
# =============================================================================
PAES_MAPPING = {
    Route.A: {
        # Ruta A: Solo preguntas fáciles → techo ~700
        # Total correctas (R1 + A2) → (puntaje_estimado, rango_min, rango_max)
        (0, 2): (150, 100, 200),
        (3, 4): (250, 200, 300),
        (5, 6): (350, 300, 400),
        (7, 8): (450, 400, 500),
        (9, 10): (525, 475, 575),
        (11, 12): (575, 525, 625),
        (13, 14): (625, 575, 675),
        (15, 16): (675, 625, 700),
    },
    Route.B: {
        # Ruta B: Preguntas medias → techo ~850
        (4, 5): (400, 350, 450),
        (6, 7): (475, 425, 525),
        (8, 9): (550, 500, 600),
        (10, 11): (625, 575, 675),
        (12, 13): (700, 650, 750),
        (14, 15): (775, 725, 825),
        (16, 16): (825, 775, 850),
    },
    Route.C: {
        # Ruta C: Preguntas medio-altas → techo ~900 (10% no inferible)
        (7, 8): (525, 475, 575),
        (9, 10): (600, 550, 650),
        (11, 12): (675, 625, 725),
        (13, 14): (775, 725, 825),
        (15, 15): (850, 800, 900),
        (16, 16): (900, 850, 950),
    },
}


def get_paes_score_weighted(responses: list, route: Route) -> tuple[int, int, int]:
    """
    Calcula el puntaje PAES usando fórmula ponderada (v3.0).
    
    Fórmula: PAES = 100 + 900 × score_ponderado × factor_ruta × factor_cobertura
    
    Args:
        responses: Lista de respuestas con metadata de la pregunta
        route: La ruta del estudiante (A, B, o C)
        
    Returns:
        Tuple[int, int, int]: (puntaje_estimado, rango_min, rango_max)
    """
    PESO_LOW = 1.0
    PESO_MEDIUM = 1.8
    FACTOR_RUTA = {Route.A: 0.70, Route.B: 0.85, Route.C: 1.00}
    FACTOR_COBERTURA = 0.90  # 10% de átomos no inferibles

    score_ponderado = 0
    max_score = 0

    for resp in responses:
        pregunta = resp.get('question', {})
        peso = PESO_LOW if pregunta.get('score', 0.5) <= 0.35 else PESO_MEDIUM
        max_score += peso
        if resp.get('is_correct', False):
            score_ponderado += peso

    score_normalizado = score_ponderado / max_score if max_score > 0 else 0
    factor_ruta = FACTOR_RUTA[route]

    paes_raw = 100 + 900 * score_normalizado * factor_ruta * FACTOR_COBERTURA
    puntaje = round(paes_raw)

    # Margen de error: ±50 puntos
    margin = 50
    rango_min = max(100, puntaje - margin)
    rango_max = min(1000, puntaje + margin)

    return (puntaje, rango_min, rango_max)


def get_paes_score(route: Route, total_correct: int) -> tuple[int, int, int]:
    """
    [DEPRECATED] Usa get_paes_score_weighted para mayor precisión.
    Mantiene compatibilidad con código existente usando tabla de lookup.
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

