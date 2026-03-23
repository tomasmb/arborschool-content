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
from app.question_variants.llm_service import build_reasoning_kwargs, build_text_service
from app.question_variants.models import PipelineConfig, SourceQuestion, VariantBlueprint
from app.question_variants.prompt_context import build_prompt_source_snapshot
from app.question_variants.contracts.structural_profile import build_construct_contract
from app.question_variants.shared_helpers import build_source_structural_profile, extract_visual_context


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
        construct_contract = build_construct_contract(
            source.question_text,
            source.qti_xml,
            bool(source.image_urls),
            source.primary_atoms,
            source.metadata,
            source.choices,
            source.correct_answer,
        )
        prompt = self._build_planning_prompt(source, n)
        print(f"  Planning {n} hard variants for {source.question_id}...")

        try:
            response = self.service.generate_text(
                prompt,
                response_mime_type="application/json",
                temperature=0.0,
                **build_reasoning_kwargs(
                    self.config.planner_provider,
                    self.config.planner_reasoning_level,
                ),
            )
            plans = self._parse_response(response, construct_contract=construct_contract)
        except Exception as exc:
            print(f"  ⚠️ Planner failed, using fallback plans: {exc}")
            self.last_error = str(exc)
            self.used_fallback = True
            plans = []

        if not plans:
            self.used_fallback = True
            return self._fallback_plans(source, n)
        return self._repair_blueprints(plans[:n], construct_contract)

    def _build_planning_prompt(self, source: SourceQuestion, n: int) -> str:
        diff = source.difficulty
        diff_text = f"{diff.get('level', 'Medium')} (score: {diff.get('score', 0.5)})"
        structural_profile = build_source_structural_profile(source)
        construct_contract = build_construct_contract(
            source.question_text,
            source.qti_xml,
            bool(source.image_urls),
            source.primary_atoms,
            source.metadata,
            source.choices,
            source.correct_answer,
        )
        visual_context = extract_visual_context(source.qti_xml)
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
        expectation = str(construct_contract.get("non_mechanizable_expectation") or "medium")
        min_axes = 1 if expectation == "low" else 2
        axes_policy = (
            "En esta familia intrínsecamente rutinaria, basta con materializar 1 eje estructural fuerte "
            "si la variante no queda superficial, mejora o preserva distractores plausibles y no es solo cambio de números."
            if min_axes == 1
            else "Debes materializar al menos 2 ejes estructurales relevantes o un cambio equivalente en profundidad."
        )

        allowed_shapes = construct_contract.get("allowed_variant_shapes", [])
        if allowed_shapes:
            shapes_text = json.dumps(allowed_shapes, ensure_ascii=False, indent=2)
            shapes_instruction = (
                f"POLÍTICA DE SHAPES: Debes seleccionar una 'Variant Shape' permitida "
                f"para cada variante de este catálogo:\n{shapes_text}\n"
                f"Cada variante DEBE tener un 'shape_id' distinto si generas múltiples variantes. "
                f"La 'scenario_description' de tu blueprint DEBE explicar cómo materializarás la Shape elegida y qué cambios obligatorios cubrirá."
            )
        else:
            shapes_instruction = "No hay Variant Shapes específicas para esta familia. Utiliza el estándar de la familia."
        hard_constraints = construct_contract.get("hard_constraints", []) or []
        if "must_not_add_auxiliary_transformations" in hard_constraints:
            auxiliary_policy = (
                "No aumentes la cantidad de transformaciones auxiliares respecto de la fuente: "
                "no propongas conversiones, equivalencias ni pasos intermedios adicionales."
            )
        elif expectation == "low":
            auxiliary_policy = (
                "Evita agregar transformaciones auxiliares gratuitas. Se permite, como máximo, "
                "un paso intermedio breve si ayuda a des-mecanizar la variante sin cambiar el constructo "
                "ni volverla de una banda de dificultad claramente distinta."
            )
        else:
            auxiliary_policy = (
                "Evita agregar transformaciones auxiliares gratuitas. Solo se permite un paso intermedio "
                "corto y conceptualmente justificado si mejora la no-mecanizabilidad sin alterar el método central."
            )
        hard_constraints_instruction = (
            "RESTRICCIONES DURAS DEL CONTRATO: no puedes proponer blueprints que violen estas restricciones:\n"
            + "\n".join(f"- {constraint}" for constraint in hard_constraints)
            if hard_constraints
            else ""
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
4. Cada variante debe cambiar al menos {min_axes} eje(s) estructural(es) fuertes, según la familia:
   - representacion (tabla/grafico/texto/diagrama),
   - forma de pregunta (directa/inferencial),
   - distractor dominante,
   - orden o dependencia de pasos.
   Política específica: {axes_policy}
5. Debe exigir comprension del por que del metodo, no receta mecanica.
6. Si la fuente evalua afirmaciones basadas en datos, la variante debe seguir
   evaluando afirmaciones sobre un conjunto de datos explicito y autocontenido.
7. Si la firma operacional es "direct_percentage_calculation", la variante debe
   seguir siendo un calculo directo de porcentaje, no una modelacion de varios pasos.
8. Respeta también la accion cognitiva y la estructura de solucion del contrato.
   Ejemplo: "interpret_representation" no se puede convertir en "compute_value" puro;
   "direct_single_step" no se puede convertir en "integrated_multi_step".
9. {auxiliary_policy}
10. Si el contrato incluye "distractor_archetypes", conserva esos mismos arquetipos de error
    aunque cambien los valores o el contexto. No reemplaces distractores conceptuales por distractores aleatorios.
11. Tampoco aumentes la carga de relaciones de referencia de la fuente: no agregues tablas de equivalencias,
    múltiples tasas de conversión ni listados de referencias si la fuente no los necesita.
12. Si la firma operacional es "descriptive_statistics", no aumentes artificialmente la cantidad de datos
    o frecuencias a procesar; conserva la misma escala de carga de datos que en la fuente.
{family_rules}
{shapes_instruction}
{hard_constraints_instruction}
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
      "selected_shape_id": "ID_DE_LA_SHAPE_ELEGIDA_O_standard_variant",
      "scenario_description": "Explicación de cómo este contexto materializa el Shape elegido...",
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

    # _build_structural_profile and _extract_visual_context removed:
    # now use shared_helpers.build_source_structural_profile and extract_visual_context

    def _parse_response(
        self,
        response: str,
        *,
        construct_contract: dict[str, Any] | None = None,
    ) -> List[VariantBlueprint]:
        data = self._parse_json(response)
        raw_blueprints = data.get("blueprints", []) if isinstance(data, dict) else []
        result: List[VariantBlueprint] = []
        allowed_shapes = construct_contract.get("allowed_variant_shapes", []) if construct_contract else []
        for idx, item in enumerate(raw_blueprints):
            if not isinstance(item, dict):
                continue
            variant_id = str(item.get("variant_id") or f"planned_v{idx + 1}")
            selected_shape_id = str(item.get("selected_shape_id", "standard_variant")).strip()
            if selected_shape_id == "standard_variant" and allowed_shapes:
                selected_shape_id = str(allowed_shapes[idx % len(allowed_shapes)].get("shape_id") or "standard_variant")
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
                    selected_shape_id=selected_shape_id,
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
        expectation = str(contract.get("non_mechanizable_expectation") or "medium")
        plans: List[VariantBlueprint] = []
        for i in range(n):
            allowed_shapes = contract.get("allowed_variant_shapes", []) or []
            selected_shape_id = "standard_variant"
            if allowed_shapes:
                selected_shape_id = str(allowed_shapes[i % len(allowed_shapes)].get("shape_id") or "standard_variant")
            scenario_description = f"Variante {i + 1} del mismo constructo con cambio estructural controlado."
            non_mechanizable_axes = (
                ["distractor_dominante"]
                if expectation == "low"
                else ["forma_pregunta", "distractor_dominante"]
            )
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
                    selected_shape_id=selected_shape_id,
                )
            )
        return self._repair_blueprints(plans, contract)

    def _repair_blueprints(
        self,
        blueprints: List[VariantBlueprint],
        construct_contract: dict[str, Any],
    ) -> List[VariantBlueprint]:
        """Patch planner outputs that violate deterministic family constraints."""
        family_id = str(construct_contract.get("family_id") or "")
        hard_constraints = {str(item) for item in construct_contract.get("hard_constraints", [])}
        forbids_aux_steps = "must_not_add_auxiliary_transformations" in hard_constraints
        repaired: List[VariantBlueprint] = []

        for blueprint in blueprints:
            if (
                forbids_aux_steps
                and family_id in {"algebraic_expression_evaluation", "direct_proportion_reasoning"}
                and self._mentions_auxiliary_conversion(blueprint.scenario_description)
            ):
                scenario_description = (
                    "La variante debe mantener una sola sustitución o relación directa del mismo tipo de la fuente, "
                    "cambiando la presentación a formato verbal o registro breve, pero sin equivalencias, conversiones "
                    "ni pasos auxiliares adicionales."
                )
                required_reasoning = (
                    "La comprensión exigida debe venir de interpretar correctamente la regla o relación principal "
                    "en una nueva presentación, no de agregar una segunda conversión o transformación auxiliar."
                )
                repaired.append(
                    VariantBlueprint(
                        variant_id=blueprint.variant_id,
                        scenario_description=scenario_description,
                        non_mechanizable_axes=blueprint.non_mechanizable_axes,
                        required_reasoning=required_reasoning,
                        difficulty_target=blueprint.difficulty_target,
                        requires_image=blueprint.requires_image,
                        image_description=blueprint.image_description,
                        selected_shape_id=blueprint.selected_shape_id,
                    )
                )
                continue
            if (
                family_id == "direct_percentage_calculation"
                and str(construct_contract.get("operation_signature") or "") == "direct_percentage_calculation"
                and str(construct_contract.get("presentation_style") or "") == "plain_narrative"
                and str(construct_contract.get("selection_load") or "") == "single_given_base"
                and blueprint.selected_shape_id != "decision_statement"
            ):
                repaired.append(
                    VariantBlueprint(
                        variant_id=blueprint.variant_id,
                        scenario_description=(
                            "La variante debe presentar un registro o nota contextual breve y luego pedir "
                            "seleccionar la afirmación coherente con la parte porcentual calculada, "
                            "en vez de repetir otra pregunta literal por el valor final. Los distractores deben "
                            "quedar en la misma escala de la respuesta correcta y representar errores plausibles "
                            "de coma decimal, ancla de 10 % o división incorrecta por el número del porcentaje."
                        ),
                        non_mechanizable_axes=["forma_pregunta", "distractor_dominante"],
                        required_reasoning=(
                            "La comprensión debe venir de interpretar correctamente la cantidad base y el porcentaje "
                            "dentro de un registro breve, distinguiendo la parte porcentual correcta de errores "
                            "plausibles de cálculo directo sin introducir magnitudes intermedias."
                        ),
                        difficulty_target=blueprint.difficulty_target,
                        requires_image=blueprint.requires_image,
                        image_description=blueprint.image_description,
                        selected_shape_id="decision_statement",
                    )
                )
                continue
            if (
                family_id == "algebraic_model_translation"
                and str(construct_contract.get("task_form") or "") == "representation_interpretation"
                and not construct_contract.get("requires_visual_support")
                and (
                    blueprint.requires_image
                    or self._mentions_visual_support(blueprint.scenario_description)
                    or self._mentions_visual_support(blueprint.required_reasoning)
                )
            ):
                repaired.append(
                    VariantBlueprint(
                        variant_id=blueprint.variant_id,
                        scenario_description=(
                            "La variante debe mantener una representación primaria simbólica o posicional sin agregar "
                            "gráficos, tablas ni figuras nuevas. Puede presentar una descomposición, expresión o "
                            "registro breve y luego pedir seleccionar la descripción posicional o interpretación "
                            "algebraica coherente, en vez de limitarse a otra pregunta literal por el número final."
                        ),
                        non_mechanizable_axes=["forma_pregunta", "representacion"],
                        required_reasoning=(
                            "La comprensión debe venir de leer correctamente la representación simbólica o posicional "
                            "y vincularla con una interpretación coherente de valor posicional o modelo, sin "
                            "reemplazarla por soporte visual ni reducirla a un cálculo mecánico de escritura directa."
                        ),
                        difficulty_target=blueprint.difficulty_target,
                        requires_image=False,
                        image_description="",
                        selected_shape_id="model_to_context_match",
                    )
                )
                continue
            if (
                family_id == "graph_interpretation"
                and str(construct_contract.get("graph_rate_frame") or "") == "direct_slope_rate"
                and (
                    "invers" in blueprint.scenario_description.lower()
                    or "invers" in blueprint.required_reasoning.lower()
                    or "menor pendiente" in blueprint.scenario_description.lower()
                    or "menor pendiente" in blueprint.required_reasoning.lower()
                )
            ):
                repaired.append(
                    VariantBlueprint(
                        variant_id=blueprint.variant_id,
                        scenario_description=(
                            "La variante debe seguir usando una representación gráfica donde la pendiente represente "
                            "directamente la razón pedida. Si se pregunta por el mayor rendimiento o rapidez, la "
                            "respuesta correcta debe corresponder a la recta de mayor pendiente dentro de la misma "
                            "lectura de la representación."
                        ),
                        non_mechanizable_axes=blueprint.non_mechanizable_axes,
                        required_reasoning=(
                            "El estudiante debe interpretar correctamente qué magnitudes están en cada eje, "
                            "manteniendo que la pendiente expresa directamente la razón buscada. La dificultad debe "
                            "venir del foco de lectura o de distractores visuales plausibles, no de invertir la razón."
                        ),
                        difficulty_target=blueprint.difficulty_target,
                        requires_image=blueprint.requires_image,
                        image_description=blueprint.image_description,
                        selected_shape_id=blueprint.selected_shape_id,
                    )
                )
                continue
            if (
                family_id == "graph_interpretation"
                and str(construct_contract.get("graph_rate_frame") or "") == "direct_slope_rate"
                and str(construct_contract.get("response_mode") or "") == "label_selection"
                and blueprint.selected_shape_id == "extremum_focus"
            ):
                repaired.append(
                    VariantBlueprint(
                        variant_id=blueprint.variant_id,
                        scenario_description=(
                            "La variante debe mantener un gráfico de una sola serie donde la pendiente represente "
                            "directamente la razón pedida, pero cambiar la forma de respuesta a una afirmación breve "
                            "sobre qué etiqueta corresponde al mayor rendimiento o a la mayor razón observada."
                        ),
                        non_mechanizable_axes=["representacion", "forma_pregunta"],
                        required_reasoning=(
                            "El estudiante debe interpretar la pendiente o el orden de razones dentro del gráfico "
                            "y luego validar una afirmación breve sobre cuál etiqueta representa la mayor tasa, "
                            "sin que baste repetir mecánicamente el mismo prompt de la fuente."
                        ),
                        difficulty_target=blueprint.difficulty_target,
                        requires_image=blueprint.requires_image,
                        image_description=blueprint.image_description,
                        selected_shape_id="single_series_visual_claim",
                    )
                )
                continue
            if family_id == "property_justification":
                selected_shape_id = blueprint.selected_shape_id
                if (
                    str(construct_contract.get("argument_polarity") or "") == "justify_valid_application"
                    and selected_shape_id == "invalid_reason_detection"
                ):
                    selected_shape_id = "justification_statement_selection"
                power_family = str(construct_contract.get("power_base_family") or "")
                if power_family == "binary_power_composition" and (
                    "mismo constructo" in blueprint.scenario_description.lower()
                    or "potencias de igual base" not in blueprint.scenario_description.lower()
                    or "inválida" in blueprint.scenario_description.lower()
                    or "invalida" in blueprint.scenario_description.lower()
                ):
                    repaired.append(
                        VariantBlueprint(
                            variant_id=blueprint.variant_id,
                            scenario_description=(
                                "La variante debe seguir pidiendo una justificación válida para una división entre "
                                "potencias de igual base dentro de la misma familia binaria del contrato "
                                "(por ejemplo, base 4 u 8). El resultado debe conservar una propiedad equivalente "
                                "a la fuente, como seguir siendo un número par."
                            ),
                            non_mechanizable_axes=blueprint.non_mechanizable_axes,
                            required_reasoning=(
                                "El estudiante debe usar la regla de conservar la base y restar exponentes, "
                                "manteniendo una base de la misma familia binaria y justificando por qué el "
                                "resultado preserva la propiedad pedida sin cambiar la polaridad del argumento."
                            ),
                            difficulty_target=blueprint.difficulty_target,
                            requires_image=blueprint.requires_image,
                            image_description=blueprint.image_description,
                            selected_shape_id=selected_shape_id or "justification_statement_selection",
                        )
                    )
                    continue
                if (
                    power_family == "binary_power_composition"
                    and str(construct_contract.get("result_property_type") or "") == "even_integer"
                ):
                    repaired.append(
                        VariantBlueprint(
                            variant_id=blueprint.variant_id,
                            scenario_description=(
                                "La variante debe seguir pidiendo una justificación válida para una división entre "
                                "potencias de igual base de la misma familia binaria, pero debe elegir exponentes "
                                "positivos y una base binaria distinta de la fuente, de modo que la explicación "
                                "correcta combine la resta de exponentes con la idea de que una potencia positiva "
                                "de base par sigue siendo par."
                            ),
                            non_mechanizable_axes=blueprint.non_mechanizable_axes,
                            required_reasoning=(
                                "El estudiante debe reconocer la ley de división de potencias de igual base y, "
                                "además, conectar el resultado con la paridad de una base par elevada a un "
                                "exponente entero positivo. La justificación correcta no puede quedarse solo en "
                                "copiar la misma receta verbal de la fuente."
                            ),
                            difficulty_target=blueprint.difficulty_target,
                            requires_image=blueprint.requires_image,
                            image_description=blueprint.image_description,
                            selected_shape_id=selected_shape_id or "justification_statement_selection",
                        )
                    )
                    continue
            if (
                family_id == "percentage_context_application"
                and str(construct_contract.get("operation_signature") or "") == "percentage_increase_application"
                and str(construct_contract.get("presentation_style") or "") == "plain_narrative"
                and str(construct_contract.get("selection_load") or "") == "single_given_base"
                and blueprint.selected_shape_id == "ledger_context"
            ):
                repaired.append(
                    VariantBlueprint(
                        variant_id=blueprint.variant_id,
                        scenario_description=(
                            "La variante debe presentar un registro o nota contextual breve y luego pedir "
                            "seleccionar la afirmación o resultado coherente con el aumento porcentual, "
                            "en vez de repetir una pregunta directa por el valor final. Los distractores deben "
                            "quedar en la misma escala de la respuesta correcta y representar errores plausibles "
                            "de base, incremento o sobreestimación."
                        ),
                        non_mechanizable_axes=["forma_pregunta", "distractor_dominante"],
                        required_reasoning=(
                            "La comprensión debe venir de interpretar correctamente la base y el aumento porcentual "
                            "dentro de un registro breve, descartando afirmaciones numéricas plausibles sin caer "
                            "en una receta idéntica a la fuente."
                        ),
                        difficulty_target=blueprint.difficulty_target,
                        requires_image=blueprint.requires_image,
                        image_description=blueprint.image_description,
                        selected_shape_id="decision_statement",
                    )
                )
                continue
            if family_id == "argumentation_evaluation" and blueprint.selected_shape_id == "false_claim_hunt":
                repaired.append(
                    VariantBlueprint(
                        variant_id=blueprint.variant_id,
                        scenario_description=(
                            "La variante debe reorganizar el dataset explícito en un formato distinto al de la fuente "
                            "(por ejemplo tabla, registro o listado estructurado) y pedir seleccionar la afirmación "
                            "correcta basada en un arquetipo semántico distinto al de la fuente. Las otras tres opciones "
                            "deben conservar las trampas conceptuales del ítem original sin convertirlo en cálculo directo."
                        ),
                        non_mechanizable_axes=blueprint.non_mechanizable_axes,
                        required_reasoning=(
                            "El estudiante debe contrastar parte-todo, subgrupos y operaciones válidas sobre porcentajes "
                            "a partir de una organización de evidencia nueva, distinguiendo un arquetipo de afirmación "
                            "correcta distinto del original sin perder la lógica de distractores."
                        ),
                        difficulty_target=blueprint.difficulty_target,
                        requires_image=blueprint.requires_image,
                        image_description=blueprint.image_description,
                        selected_shape_id="claim_archetype_switch",
                    )
                )
                continue
            repaired.append(blueprint)
        return repaired

    def _mentions_auxiliary_conversion(self, text: str) -> bool:
        lowered = str(text or "").lower()
        markers = (
            "equivale",
            "equivalencia",
            "conversión",
            "conversion",
            "convertir",
            "pasa a",
            "joule",
            "kilojoule",
            "kilogramo",
            "gramo",
            "miligram",
            "kilocalor",
        )
        return any(marker in lowered for marker in markers)

    def _mentions_visual_support(self, text: str) -> bool:
        lowered = str(text or "").lower()
        markers = ("gráfico", "grafico", "figura", "tabla", "diagrama", "barra", "línea", "linea")
        return any(marker in lowered for marker in markers)
