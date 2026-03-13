"""Variant planning phase for hard, non-mechanizable variants.

Creates structured blueprints that keep construct alignment while forcing
deeper reasoning than superficial number/context swaps.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from app.question_variants.llm_service import build_text_service
from app.question_variants.models import PipelineConfig, SourceQuestion, VariantBlueprint


class VariantPlanner:
    """Generates structured blueprints before QTI generation."""

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self.service = build_text_service(
            self.config.planner_provider,
            self.config.planner_model,
        )

    def plan_variants(
        self,
        source: SourceQuestion,
        num_variants: Optional[int] = None,
    ) -> List[VariantBlueprint]:
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
            plans = []

        if not plans:
            return self._fallback_plans(source, n)
        return plans[:n]

    def _build_planning_prompt(self, source: SourceQuestion, n: int) -> str:
        diff = source.difficulty
        diff_text = f"{diff.get('level', 'Medium')} (score: {diff.get('score', 0.5)})"

        atoms_desc = []
        for atom in source.primary_atoms:
            title = atom.get("atom_title", "N/A")
            reasoning = atom.get("reasoning", "")
            atoms_desc.append(f"- {title}: {reasoning}")
        atoms_text = "\n".join(atoms_desc) if atoms_desc else "- No atoms specified"

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
</reglas>

<pregunta_fuente>
ID: {source.question_id}
Texto: {source.question_text}
Opciones: {json.dumps(source.choices, ensure_ascii=False)}
Respuesta correcta: {source.correct_answer}
Concepto/atom principal:
{atoms_text}
Dificultad fuente: {diff_text}
</pregunta_fuente>

<task>
Genera exactamente {n} blueprints para variantes.
Cada blueprint debe ser distinto de los demas.
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
        plans: List[VariantBlueprint] = []
        for i in range(n):
            plans.append(
                VariantBlueprint(
                    variant_id=f"{source.question_id}_v{i + 1}",
                    scenario_description=f"Variante {i + 1} del mismo constructo con cambio estructural controlado.",
                    non_mechanizable_axes=["forma_pregunta", "distractor_dominante"],
                    required_reasoning="Requiere justificar el metodo y evitar aplicacion mecanica.",
                    difficulty_target="equal_or_harder",
                    requires_image=False,
                    image_description="",
                )
            )
        return plans
