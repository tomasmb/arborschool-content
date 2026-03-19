"""Variant planning phase for hard, non-mechanizable variants.

Creates structured blueprints that keep construct alignment while forcing
deeper reasoning than superficial number/context swaps.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

from app.question_variants.contracts.family_specs import build_family_prompt_rules
from app.question_variants.llm_service import build_text_service
from app.question_variants.models import PipelineConfig, SourceQuestion, VariantBlueprint
from app.question_variants.prompt_context import build_prompt_source_snapshot
from app.question_variants.contracts.structural_profile import build_construct_contract, build_structural_profile


class VariantPlanner:
    """Generates structured blueprints before QTI generation."""

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self.last_error: str | None = None
        self.used_fallback: bool = False
        self.service = build_text_service(
            self.config.planner_provider,
            self.config.planner_model,
            timeout_seconds=self.config.llm_request_timeout_seconds,
            max_attempts=self.config.llm_max_attempts,
        )

    def plan_variants(
        self,
        source: SourceQuestion,
        num_variants: Optional[int] = None,
    ) -> List[VariantBlueprint]:
        self.last_error = None
        self.used_fallback = False
        n = num_variants or self.config.variants_per_question
        prompt = self._build_planning_prompt(source, n)
        print(f"  Planning {n} hard variants for {source.question_id}...")

        try:
            response = self.service.generate_text(
                prompt,
                response_mime_type="application/json",
                temperature=0.0,
            )
            plans = self._parse_response(response)
        except Exception as exc:
            print(f"  ⚠️ Planner failed, using fallback plans: {exc}")
            self.last_error = str(exc)
            self.used_fallback = True
            plans = []

        if not plans:
            self.used_fallback = True
            return self._fallback_plans(source, n)
        return plans[:n]

    def _build_planning_prompt(self, source: SourceQuestion, n: int) -> str:
        diff = source.difficulty
        diff_text = f"{diff.get('level', 'Medium')} (score: {diff.get('score', 0.5)})"
        structural_profile = self._build_structural_profile(source)
        construct_contract = build_construct_contract(
            source.question_text,
            source.qti_xml,
            bool(source.image_urls),
            source.primary_atoms,
            source.metadata,
            source.choices,
            source.correct_answer,
        )
        visual_context = self._extract_visual_context(source.qti_xml)
        atoms_desc = []
        for atom in source.primary_atoms:
            title = atom.get("atom_title", "N/A")
            reasoning = atom.get("reasoning", "")
            atoms_desc.append(f"- {title}: {reasoning}")
        atoms_text = "\n".join(atoms_desc) if atoms_desc else "- No atoms specified"
        source_snapshot = build_prompt_source_snapshot(
            question_id=source.question_id,
            question_text=source.question_text,
            choices=source.choices,
            correct_answer=source.correct_answer,
            difficulty_text=diff_text,
            atoms_text=atoms_text,
            construct_contract=construct_contract,
            structural_profile=structural_profile,
            visual_context=visual_context,
        )
        family_rules = "\n".join(
            f"{idx}. {rule}" for idx, rule in enumerate(build_family_prompt_rules(construct_contract), start=8)
        )

        return f"""
<role>
Eres diseñador experto de evaluaciones PAES.
Debes planificar variantes NO MECANIZABLES de una pregunta fuente.
</role>

<reglas>
1. Cada variante debe evaluar EXACTAMENTE el mismo constructo.
2. La dificultad debe ser igual o ligeramente mayor, nunca menor.
3. No se permite variante por solo cambio de numeros/contexto superficial.
4. Cada variante debe cambiar al menos 2 ejes estructurales:
   - representacion (tabla/grafico/texto/diagrama),
   - forma de pregunta (directa/inferencial),
   - distractor dominante,
   - orden o dependencia de pasos.
5. Debe exigir comprension del por que del metodo, no receta mecanica.
6. Si la fuente evalua afirmaciones basadas en datos, la variante debe seguir
   evaluando afirmaciones sobre un conjunto de datos explicito y autocontenido.
7. Si la firma operacional es "direct_percentage_calculation", la variante debe
   seguir siendo un calculo directo de porcentaje, no una modelacion de varios pasos.
8. Respeta también la accion cognitiva y la estructura de solucion del contrato.
   Ejemplo: "interpret_representation" no se puede convertir en "compute_value" puro;
   "direct_single_step" no se puede convertir en "integrated_multi_step".
9. No aumentes la cantidad de transformaciones auxiliares respecto de la fuente
    (por ejemplo, conversiones de unidad, cambio de representación numérica o pasos intermedios adicionales).
10. Si el contrato incluye "distractor_archetypes", conserva esos mismos arquetipos de error
    aunque cambien los valores o el contexto. No reemplaces distractores conceptuales por distractores aleatorios.
11. Tampoco aumentes la carga de relaciones de referencia de la fuente: no agregues tablas de equivalencias,
    múltiples tasas de conversión ni listados de referencias si la fuente no los necesita.
12. Si la firma operacional es "descriptive_statistics", no aumentes artificialmente la cantidad de datos
    o frecuencias a procesar; conserva la misma escala de carga de datos que en la fuente.
{family_rules}
</reglas>

{source_snapshot}

<task>
Genera exactamente {n} blueprints para variantes.
Cada blueprint debe ser distinto de los demas.
Cada blueprint DEBE respetar las invariantes estructurales.
</task>

<formato_respuesta>
Devuelve SOLO JSON:
{{
  "blueprints": [
    {{
      "variant_id": "{source.question_id}_v1",
      "scenario_description": "contexto nuevo y que cambia",
      "non_mechanizable_axes": [
        "representacion",
        "forma_pregunta"
      ],
      "required_reasoning": "por que obliga a entender el metodo",
      "difficulty_target": "equal_or_harder",
      "requires_image": false,
      "image_description": ""
    }}
  ]
}}
</formato_respuesta>
"""

    def _build_structural_profile(self, source: SourceQuestion) -> Dict[str, Any]:
        profile = build_structural_profile(
            source.question_text,
            source.qti_xml,
            bool(source.image_urls),
            source.primary_atoms,
            source.metadata.get("habilidad_principal", {}).get("habilidad_principal", ""),
        )
        profile["requires_image"] = bool(source.image_urls)
        profile["allows_new_visual_representation"] = bool(source.image_urls)
        profile["must_preserve_error_analysis"] = profile["task_form"] == "error_analysis"
        profile["allows_unknowns"] = profile["introduces_unknowns"]
        return profile

    def _extract_visual_context(self, qti_xml: str) -> str:
        try:
            root = ET.fromstring(qti_xml)
        except ET.ParseError:
            return ""

        descriptions: list[str] = []
        for element in root.findall(".//{*}img"):
            alt = (element.attrib.get("alt") or "").strip()
            if alt:
                descriptions.append(alt)
        for element in root.findall(".//{*}object"):
            label = (element.attrib.get("aria-label") or element.attrib.get("label") or "").strip()
            if label:
                descriptions.append(label)
        return " | ".join(descriptions)

    def _parse_response(self, response: str) -> List[VariantBlueprint]:
        data = self._parse_json(response)
        raw_blueprints = data.get("blueprints", []) if isinstance(data, dict) else []
        result: List[VariantBlueprint] = []
        for idx, item in enumerate(raw_blueprints):
            if not isinstance(item, dict):
                continue
            variant_id = str(item.get("variant_id") or f"planned_v{idx + 1}")
            result.append(
                VariantBlueprint(
                    variant_id=variant_id,
                    scenario_description=str(item.get("scenario_description", "")).strip(),
                    non_mechanizable_axes=[
                        str(x).strip()
                        for x in item.get("non_mechanizable_axes", [])
                        if str(x).strip()
                    ],
                    required_reasoning=str(item.get("required_reasoning", "")).strip(),
                    difficulty_target=str(item.get("difficulty_target", "equal_or_harder")).strip(),
                    requires_image=bool(item.get("requires_image", False)),
                    image_description=str(item.get("image_description", "")).strip(),
                )
            )
        return result

    def _parse_json(self, text: str) -> Dict[str, Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            cleaned = re.sub(r'\\(?![/"\\\bfnrtu])', r"\\\\", text)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                return {}

    def _fallback_plans(self, source: SourceQuestion, n: int) -> List[VariantBlueprint]:
        contract = build_construct_contract(
            source.question_text,
            source.qti_xml,
            bool(source.image_urls),
            source.primary_atoms,
            source.metadata,
            source.choices,
            source.correct_answer,
        )
        operation_signature = str(contract.get("operation_signature") or "")
        plans: List[VariantBlueprint] = []
        for i in range(n):
            scenario_description = f"Variante {i + 1} del mismo constructo con cambio estructural controlado."
            non_mechanizable_axes = ["forma_pregunta", "distractor_dominante"]
            required_reasoning = "Requiere justificar el metodo y evitar aplicacion mecanica."
            if operation_signature == "parameter_interpretation":
                scenario_description = (
                    "La variante debe seguir interpretando directamente el coeficiente del modelo en un caso concreto "
                    "o afirmación contextual única, sin comparar diferencias entre dos personas, objetos o situaciones."
                )
                non_mechanizable_axes = ["forma_pregunta", "distractor_dominante"]
                required_reasoning = (
                    "Obliga a comprender el significado práctico del coeficiente en un caso único o agrupado, "
                    "sin convertirlo en una aplicación de variación entre dos casos."
                )
            elif operation_signature == "linear_equation_resolution":
                scenario_description = (
                    "La variante debe mantener una sola ecuación lineal contextualizada del mismo tipo, pero cambiar "
                    "la forma de presentar el contexto o el rol del dato adicional fijo sin pedir una cantidad complementaria "
                    "ni agregar un paso final extra después de resolver la incógnita."
                )
                non_mechanizable_axes = ["forma_pregunta", "distractor_dominante"]
                required_reasoning = (
                    "Exige distinguir correctamente el término fijo y la relación proporcional dentro de una sola "
                    "ecuación lineal, manteniendo la misma dificultad algebraica y evitando plantillas casi idénticas."
                )
            plans.append(
                VariantBlueprint(
                    variant_id=f"{source.question_id}_v{i + 1}",
                    scenario_description=scenario_description,
                    non_mechanizable_axes=non_mechanizable_axes,
                    required_reasoning=required_reasoning,
                    difficulty_target="equal_or_harder",
                    requires_image=False,
                    image_description="",
                )
            )
        return plans
