"""
Motor de la prueba diagnóstica MST.

Maneja el flujo de la prueba:
1. Etapa 1: Routing (R1)
2. Routing: Determinar ruta según correctas
3. Etapa 2: Módulo de la ruta correspondiente
4. Cálculo de resultados
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from .config import (
    A2_QUESTIONS,
    B2_QUESTIONS,
    C2_QUESTIONS,
    R1_QUESTIONS,
    Axis,
    Question,
    Route,
    Skill,
    get_paes_score,
    get_route,
)


class ResponseType(Enum):
    """Tipos de respuesta posibles"""

    CORRECT = "correct"
    INCORRECT = "incorrect"
    DONT_KNOW = "dont_know"  # Botón "No lo sé"


@dataclass
class Response:
    """Representa una respuesta del estudiante"""

    question: Question
    response_type: ResponseType
    selected_option: Optional[str] = None  # La opción seleccionada (A, B, C, D)

    @property
    def is_correct(self) -> bool:
        return self.response_type == ResponseType.CORRECT


@dataclass
class AtomDiagnosis:
    """Diagnóstico de un átomo específico"""

    atom_id: str
    atom_title: str
    response_type: ResponseType

    @property
    def status(self) -> str:
        """
        Estados:
        - 'dominado': Respondió correctamente
        - 'gap': Dijo "No lo sé"
        - 'misconception': Respondió incorrectamente
        """
        if self.response_type == ResponseType.CORRECT:
            return "dominado"
        elif self.response_type == ResponseType.DONT_KNOW:
            return "gap"
        else:
            return "misconception"

    @property
    def include_in_plan(self) -> bool:
        """¿Incluir este átomo en el plan de estudio?"""
        return self.status != "dominado"

    @property
    def instruction_type(self) -> Optional[str]:
        """Tipo de instrucción recomendada"""
        if self.status == "gap":
            return "enseñar"
        elif self.status == "misconception":
            return "corregir"
        return None


@dataclass
class TestResult:
    """Resultado completo de la prueba diagnóstica"""

    route: Route
    r1_correct: int
    stage2_correct: int
    total_correct: int
    paes_score: int
    paes_range_min: int
    paes_range_max: int
    responses: List[Response] = field(default_factory=list)

    # Diagnósticos por dimensión
    axis_performance: Dict[Axis, float] = field(default_factory=dict)
    skill_performance: Dict[Skill, float] = field(default_factory=dict)
    atom_diagnoses: List[AtomDiagnosis] = field(default_factory=list)


class MSTEngine:
    """
    Motor de la prueba diagnóstica MST.

    Uso típico:
        engine = MSTEngine()
        r1_questions = engine.get_routing_questions()

        # ... estudiante responde R1 ...
        engine.record_r1_responses(responses)

        stage2_questions = engine.get_stage2_questions()

        # ... estudiante responde Etapa 2 ...
        engine.record_stage2_responses(responses)

        result = engine.get_result()
    """

    def __init__(self):
        self.r1_responses: List[Response] = []
        self.stage2_responses: List[Response] = []
        self._route: Optional[Route] = None

    def get_routing_questions(self) -> List[Question]:
        """Obtiene las 8 preguntas de routing (R1)"""
        return R1_QUESTIONS.copy()

    def record_r1_responses(self, responses: List[Response]) -> Route:
        """
        Registra las respuestas de R1 y determina la ruta.

        Args:
            responses: Lista de 8 respuestas para R1

        Returns:
            Route: La ruta asignada
        """
        if len(responses) != 8:
            raise ValueError(f"Se esperaban 8 respuestas, se recibieron {len(responses)}")

        self.r1_responses = responses
        correct_count = sum(1 for r in responses if r.is_correct)
        self._route = get_route(correct_count)

        return self._route

    @property
    def route(self) -> Optional[Route]:
        """La ruta asignada (None si aún no se completó R1)"""
        return self._route

    def get_stage2_questions(self) -> List[Question]:
        """
        Obtiene las 8 preguntas de la Etapa 2 según la ruta.

        Returns:
            List[Question]: Las preguntas del módulo correspondiente

        Raises:
            ValueError: Si no se ha completado R1 primero
        """
        if self._route is None:
            raise ValueError("Debe completar R1 antes de obtener preguntas de Etapa 2")

        module_map = {
            Route.A: A2_QUESTIONS,
            Route.B: B2_QUESTIONS,
            Route.C: C2_QUESTIONS,
        }

        return module_map[self._route].copy()

    def record_stage2_responses(self, responses: List[Response]) -> None:
        """
        Registra las respuestas de la Etapa 2.

        Args:
            responses: Lista de 8 respuestas para la Etapa 2
        """
        if len(responses) != 8:
            raise ValueError(f"Se esperaban 8 respuestas, se recibieron {len(responses)}")

        if self._route is None:
            raise ValueError("Debe completar R1 antes de registrar respuestas de Etapa 2")

        self.stage2_responses = responses

    def get_result(self) -> TestResult:
        """
        Calcula y devuelve el resultado completo de la prueba.

        Returns:
            TestResult: Resultado con puntaje PAES y diagnósticos
        """
        if not self.r1_responses or not self.stage2_responses:
            raise ValueError("Debe completar ambas etapas antes de obtener resultados")

        all_responses = self.r1_responses + self.stage2_responses

        # Conteos
        r1_correct = sum(1 for r in self.r1_responses if r.is_correct)
        stage2_correct = sum(1 for r in self.stage2_responses if r.is_correct)
        total_correct = r1_correct + stage2_correct

        # Puntaje PAES
        paes_score, paes_min, paes_max = get_paes_score(self._route, total_correct)

        # Diagnóstico por eje
        axis_performance = self._calculate_axis_performance(all_responses)

        # Diagnóstico por habilidad
        skill_performance = self._calculate_skill_performance(all_responses)

        # Diagnóstico por átomo
        atom_diagnoses = self._calculate_atom_diagnoses(all_responses)

        return TestResult(
            route=self._route,
            r1_correct=r1_correct,
            stage2_correct=stage2_correct,
            total_correct=total_correct,
            paes_score=paes_score,
            paes_range_min=paes_min,
            paes_range_max=paes_max,
            responses=all_responses,
            axis_performance=axis_performance,
            skill_performance=skill_performance,
            atom_diagnoses=atom_diagnoses,
        )

    def _calculate_axis_performance(self, responses: List[Response]) -> Dict[Axis, float]:
        """Calcula el porcentaje de acierto por eje temático"""
        axis_counts: Dict[Axis, Dict[str, int]] = {}

        for response in responses:
            axis = response.question.axis
            if axis not in axis_counts:
                axis_counts[axis] = {"correct": 0, "total": 0}

            axis_counts[axis]["total"] += 1
            if response.is_correct:
                axis_counts[axis]["correct"] += 1

        return {axis: counts["correct"] / counts["total"] if counts["total"] > 0 else 0 for axis, counts in axis_counts.items()}

    def _calculate_skill_performance(self, responses: List[Response]) -> Dict[Skill, float]:
        """Calcula el porcentaje de acierto por habilidad"""
        skill_counts: Dict[Skill, Dict[str, int]] = {}

        for response in responses:
            skill = response.question.skill
            if skill not in skill_counts:
                skill_counts[skill] = {"correct": 0, "total": 0}

            skill_counts[skill]["total"] += 1
            if response.is_correct:
                skill_counts[skill]["correct"] += 1

        return {skill: counts["correct"] / counts["total"] if counts["total"] > 0 else 0 for skill, counts in skill_counts.items()}

    def _calculate_atom_diagnoses(self, responses: List[Response]) -> List[AtomDiagnosis]:
        """
        Genera diagnósticos por átomo basados en las respuestas.

        Para cada respuesta:
        1. Carga metadata_tags.json de la pregunta
        2. Extrae los átomos taggeados (primary y secondary)
        3. Asigna estado según tipo de respuesta

        Returns:
            Lista de AtomDiagnosis con estado por átomo
        """
        import json
        from pathlib import Path

        # Base path for test data
        BASE_PATH = Path(__file__).parent.parent / "data" / "pruebas" / "finalizadas"

        # Track atoms already diagnosed (avoid duplicates, keep worst status)
        atom_status: Dict[str, AtomDiagnosis] = {}

        # Status priority: misconception > gap > dominado
        status_priority = {
            ResponseType.INCORRECT: 3,
            ResponseType.DONT_KNOW: 2,
            ResponseType.CORRECT: 1,
        }

        for response in responses:
            question = response.question
            metadata_path = BASE_PATH / question.exam / "qti" / question.question_id / "metadata_tags.json"

            if not metadata_path.exists():
                continue

            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
            except (json.JSONDecodeError, IOError):
                continue

            selected_atoms = metadata.get("selected_atoms", [])

            for atom_info in selected_atoms:
                atom_id = atom_info.get("atom_id", "")
                atom_title = atom_info.get("atom_title", "")
                relevance = atom_info.get("relevance", "secondary")

                if not atom_id:
                    continue

                # For primary atoms, use the actual response type
                # For secondary atoms, only mark as dominated if correct
                if relevance == "primary":
                    resp_type = response.response_type
                else:
                    # Secondary atoms: only mark dominated if correct, otherwise not evaluated
                    if response.response_type == ResponseType.CORRECT:
                        resp_type = ResponseType.CORRECT
                    else:
                        continue  # Don't diagnose secondary atoms on incorrect answers

                # Check if we already have this atom diagnosed
                if atom_id in atom_status:
                    existing = atom_status[atom_id]
                    # Keep the worse status (higher priority)
                    if status_priority[resp_type] > status_priority[existing.response_type]:
                        atom_status[atom_id] = AtomDiagnosis(
                            atom_id=atom_id,
                            atom_title=atom_title,
                            response_type=resp_type,
                        )
                else:
                    atom_status[atom_id] = AtomDiagnosis(
                        atom_id=atom_id,
                        atom_title=atom_title,
                        response_type=resp_type,
                    )

        return list(atom_status.values())
