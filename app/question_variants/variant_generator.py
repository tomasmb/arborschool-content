"""Variant question generator.

This module generates pedagogically-sound variant questions from source
exemplars, guided by planning blueprints that enforce same-construct
alignment with non-mechanizable structural variation.
"""

import json
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

from app.question_variants.contracts.family_specs import build_family_prompt_rules
from app.question_variants.llm_service import build_reasoning_kwargs, build_text_service
from app.question_variants.models import (
    PipelineConfig,
    SourceQuestion,
    VariantBlueprint,
    VariantQuestion,
)
from app.question_variants.prompt_context import build_prompt_source_snapshot
from app.question_variants.contracts.structural_profile import build_construct_contract
from app.question_variants.postprocess.generation_parsing import parse_generation_response
from app.question_variants.shared_helpers import build_source_structural_profile, extract_visual_context

class VariantGenerator:
    """Generates variant questions from source exemplars."""

    def __init__(self, config: Optional[PipelineConfig] = None):
        """Initialize the generator.

        Args:
            config: Pipeline configuration. Uses defaults if not provided.
        """
        self.config = config or PipelineConfig()
        self.last_error: str | None = None
        self.service = build_text_service(
            self.config.generator_provider,
            self.config.generator_model,
            timeout_seconds=self.config.llm_request_timeout_seconds,
            max_attempts=self.config.llm_max_attempts,
        )

    def generate_variants(
        self,
        source: SourceQuestion,
        num_variants: Optional[int] = None,
        blueprints: Optional[List[VariantBlueprint]] = None,
    ) -> List[VariantQuestion]:
        """Generate variant questions from a source question.

        Args:
            source: The source question to create variants from
            num_variants: Number of variants to generate (uses config default if not specified)

        Returns:
            List of generated variant questions (unvalidated)
        """
        self.last_error = None
        n = num_variants or self.config.variants_per_question

        print(f"  Generating {n} variants for {source.question_id}...")

        try:
            if blueprints:
                variants = self._generate_from_blueprints(source, blueprints[:n])
            else:
                prompt = self._build_generation_prompt(source, n, None)
                variants_data = self._generate_variant_payloads(prompt, source)
                variants = self._to_variant_objects(source, variants_data, None)

            print(f"  ✅ Generated {len(variants)} variants")
            return variants

        except Exception as e:
            print(f"  ❌ Error generating variants: {e}")
            self.last_error = str(e)
            import traceback

            traceback.print_exc()
            return []

    def _generate_from_blueprints(self, source: SourceQuestion, blueprints: List[VariantBlueprint]) -> List[VariantQuestion]:
        variants: List[VariantQuestion] = []
        for blueprint in blueprints:
            try:
                prompt = self._build_generation_prompt(source, 1, [blueprint])
                variants_data = self._generate_variant_payloads(prompt, source)
                generated = self._to_variant_objects(source, variants_data[:1], [blueprint])
                if generated:
                    variants.extend(generated)
                else:
                    self.last_error = f"No se pudo parsear la variante {blueprint.variant_id}"
                    print(f"  ⚠️ {self.last_error}")
            except Exception as e:
                self.last_error = str(e)
                print(f"  ⚠️ Error generating {blueprint.variant_id}: {e}")
        return variants

    def _generate_variant_payloads(self, prompt: str, source: SourceQuestion) -> List[Dict[str, Any]]:
        response = self.service.generate_text(
            prompt,
            response_mime_type="application/json",
            temperature=self.config.temperature,
            **build_reasoning_kwargs(
                self.config.generator_provider,
                self.config.generator_reasoning_level,
            ),
        )
        variants_data = self._parse_response(response, source)
        if variants_data:
            return variants_data

        retry_prompt = (
            f"{prompt}\n\n<correccion_formato>\n"
            "Tu respuesta anterior no fue parseable. Reintenta devolviendo SOLO JSON válido, "
            "sin texto adicional, markdown ni explicación fuera del objeto JSON.\n"
            "</correccion_formato>\n"
        )
        retry_response = self.service.generate_text(
            retry_prompt,
            response_mime_type="application/json",
            temperature=0.1,
            **build_reasoning_kwargs(
                self.config.generator_provider,
                self.config.generator_reasoning_level,
            ),
        )
        return self._parse_response(retry_response, source)

    def _to_variant_objects(
        self,
        source: SourceQuestion,
        variants_data: List[Dict[str, Any]],
        blueprints: Optional[List[VariantBlueprint]],
    ) -> List[VariantQuestion]:
        variants: List[VariantQuestion] = []
        for i, vdata in enumerate(variants_data):
            if blueprints and i < len(blueprints):
                variant_id = blueprints[i].variant_id
            else:
                variant_id = f"{source.question_id}_v{i + 1}"
            variant = VariantQuestion(
                variant_id=variant_id,
                source_question_id=source.question_id,
                source_test_id=source.test_id,
                qti_xml=vdata.get("qti_xml", ""),
                metadata=self._build_variant_metadata(
                    source,
                    vdata,
                    blueprints[i] if blueprints and i < len(blueprints) else None,
                ),
            )
            variants.append(variant)
        return variants

    def _build_generation_prompt(
        self,
        source: SourceQuestion,
        n: int,
        blueprints: Optional[List[VariantBlueprint]] = None,
    ) -> str:
        """Build the restrictive generation prompt."""

        # Extract atom info for context
        atoms_desc = []
        for atom in source.primary_atoms:
            atoms_desc.append(f"- {atom.get('atom_title', 'N/A')}: {atom.get('reasoning', '')}")
        atoms_text = "\n".join(atoms_desc) if atoms_desc else "No atoms specified"

        # Get difficulty info
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
        # Check for image info and add instruction if decorative
        image_info = source.metadata.get("image_info", {})
        image_instruction = ""
        if image_info.get("image_type") == "decorative":
            image_instruction = (
                "7. ESTA PREGUNTA CONTIENE UNA IMAGEN DECORATIVA (Support visual). "
                "DEBES INCLUIR LA ETIQUETA <img ...> EXACTAMENTE IGUAL QUE EN LA "
                "ORIGINAL dentro del texto."
            )
        elif source.image_urls:
            image_instruction = (
                "7. ESTA PREGUNTA DEPENDE DE SOPORTE VISUAL. Si el contrato requiere interpretación de representación "
                "(ej. gráficos, infografías, geometría), DEBES MANTENER la representación visual como evidencia primaria. "
                "NO la reemplaces por una tabla o lista de texto explícita que evite la interpretación visual. "
                "Para la nueva imagen, incluye una etiqueta <img src='requiere_nueva_imagen.png' alt='[DESCRIBE EXACTAMENTE "
                "CÓMO DEBE DIBUJARSE LA NUEVA IMAGEN, CON TODOS LOS DATOS Y FORMAS NECESARIAS]'/>."
            )
        else:
            image_instruction = (
                "7. LA PREGUNTA FUENTE NO USA SOPORTE VISUAL. "
                "NO introduzcas figura, gráfico, diagrama, infografía, tabla ni imagen en la variante."
            )

        blueprint_instruction = ""
        if blueprints:
            blueprint_payload = []
            for bp in blueprints[:n]:
                blueprint_payload.append(
                    {
                        "variant_id": bp.variant_id,
                        "scenario_description": bp.scenario_description,
                        "non_mechanizable_axes": bp.non_mechanizable_axes,
                        "required_reasoning": bp.required_reasoning,
                        "difficulty_target": bp.difficulty_target,
                        "requires_image": bp.requires_image,
                        "image_description": bp.image_description,
                    }
                )
            blueprint_instruction = (
                "8. DEBES respetar exactamente estos blueprints por variante "
                "(mismo orden):\n"
                f"{json.dumps(blueprint_payload, ensure_ascii=False, indent=2)}\n"
                "Cada variante debe incorporar sus ejes no mecanizables."
            )
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
            include_qti_xml=source.qti_xml,
        )
        family_rules = "\n".join(
            f"{idx}. {rule}" for idx, rule in enumerate(build_family_prompt_rules(construct_contract), start=8)
        )
        min_axes = 1 if str(construct_contract.get("non_mechanizable_expectation") or "medium") == "low" else 2
        axes_policy = (
            "En esta familia intrínsecamente rutinaria, puede bastar con 1 eje estructural fuerte si la variante no es superficial, "
            "los distractores siguen siendo plausibles y la forma del ítem no queda casi idéntica."
            if min_axes == 1
            else "Debes materializar al menos 2 ejes estructurales relevantes o un cambio equivalente en profundidad."
        )

        hard_constraints = construct_contract.get('hard_constraints', [])
        if hard_constraints:
            constraints_list = "\n".join(f"    - {c}" for c in hard_constraints)
            constraints_instruction = f"17. RESTRICCIONES DURAS DEL CONTRATO OBLIGATORIAS:\n{constraints_list}"
        else:
            constraints_instruction = ""

        prompt = f"""
<role>
Eres un profesor de matemáticas creando variantes de ejercicios para exámenes PAES.
Tu tarea es generar variantes duras del mismo ítem, manteniendo exactamente
el constructo matemático evaluado y respetando el contrato estructural.
</role>

<reglas_estrictas>
1. La variante DEBE evaluar EXACTAMENTE el mismo concepto que la original
2. La variante DEBE mantenerse dentro del objetivo de dificultad del blueprint/contrato
   (igual o, cuando corresponda, levemente más difícil sin cambiar de constructo).
3. SOLO puedes cambiar lo que el contrato permita cambiar:
   - Valores numéricos
   - Nombres, objetos o escenario
   - Forma de presentación o ejes estructurales no mecanizables, siempre dentro del mismo contrato
4. NO puedes cambiar:
   - El tipo de operación matemática requerida
   - La cantidad de pasos para resolver
   - El nivel de abstracción o complejidad
5. La respuesta correcta DEBE poder calcularse con el MISMO procedimiento
6. Los distractores DEBEN representar errores plausibles (NO valores aleatorios)
7. DEBES respetar estas invariantes estructurales:
   {json.dumps(structural_profile, ensure_ascii=False)}
8. Si la fuente no usa incógnitas algebraicas, NO puedes introducir x, y, z ni ecuaciones a resolver.
9. Debes respetar el contrato de constructo completo, especialmente el modo de evidencia.
    Si el contrato dice "representation_primary", NO reemplaces la interpretación de representación
    por una tabla o lista de datos que permita responder sin interpretar la representación.
10. Debes respetar la accion cognitiva y la estructura de solucion del contrato.
    No conviertas una tarea de interpretacion en una de calculo directo, ni una de un paso
    en una de varios pasos, ni una de sustitucion algebraica en una modelacion distinta.
11. NO aumentes la cantidad de transformaciones auxiliares respecto de la fuente. Si el contrato
    indica 0 transformaciones auxiliares, la variante también debe resolverse sin conversiones,
    sustituciones intermedias adicionales ni cambios de representación numérica.
12. Si el contrato incluye "distractor_archetypes", conserva esos mismos arquetipos de error.
    No reemplaces distractores conceptuales por valores arbitrarios ni por errores de otro tipo.
13. NO aumentes la carga de relaciones de referencia de la fuente: no agregues múltiples equivalencias,
    tasas de cambio o listados de referencia si la fuente sólo necesita una.
14. Si las opciones son numéricas, cada distractor debe corresponder a un error concreto y explicable.
    No uses valores arbitrarios o absurdos; mantén coherencia de escala con la respuesta correcta.
15. Debes realizar de verdad al menos {min_axes} eje(s) no mecanizable(s) y poder declararlos explícitamente
    en el self-check final.
    Política específica: {axes_policy}
16. PROTECCIÓN CONTRA DRIFT DE CONSTRUCTO:
    - NO cambies la polaridad argumentativa (ej. si la fuente pide refutar, no pidas justificar).
    - NO cambies la polaridad extrema (si la fuente pide el "máximo/mayor", no pidas el "mínimo/menor").
    - NO cambies el patrón de cambio porcentual (ej. aumento vs descuento deben mantenerse).
    - NO modifiques la cantidad de series en un gráfico (si hay una serie, no agregues dos).
{family_rules}
{constraints_instruction}
</reglas_estrictas>

{image_instruction}
{blueprint_instruction}

{source_snapshot}

<tarea>
Genera exactamente {n} variantes. Cada variante DEBE:
1. Tener una respuesta correcta DIFERENTE a la original (distintos números)
2. Mantener exactamente 4 opciones (A, B, C, D) con distractores plausibles
3. Usar el MISMO formato QTI 3.0 que la original
4. Incorporar cambios no mecanizables reales dentro del contrato
   (no basta con cambio superficial de nombres o números)
5. NO agregues bloques de feedback, solución, ni retroalimentación inline
6. Antes de responder, verifica internamente que NO cambiaste la forma de tarea
   (por ejemplo, operatoria directa -> ecuación; análisis de error -> cálculo directo).
7. Si usas soporte visual, deja los porcentajes, cantidades o relaciones también en texto visible.
8. Si la fuente evalúa afirmaciones sobre datos, tu variante DEBE incluir un conjunto de datos explícito
   (tabla o lista estructurada) y las alternativas deben seguir siendo afirmaciones sobre esos datos.

Para cada variante, genera:
- El XML QTI 3.0 completo (similar al original pero con nuevos valores)
- Una breve explicación del cambio realizado
- Un self-check breve del contrato:
  - "task_form_preserved": true/false
  - "evidence_mode_preserved": true/false
  - "cognitive_action_preserved": true/false
  - "solution_structure_preserved": true/false
  - "auxiliary_transformations_preserved": true/false
  - "distractor_logic_preserved": true/false
  - "realized_non_mechanizable_axes": ["eje1", "eje2"]
  - "main_risk_checked": "texto breve"
</tarea>

<formato_respuesta>
Responde con un JSON con esta estructura:
{{
  "variants": [
    {{
      "qti_xml": "<qti-assessment-item ...>...</qti-assessment-item>",
      "change_description": "Cambié los valores de X a Y...",
      "self_check": {{
        "task_form_preserved": true,
        "evidence_mode_preserved": true,
        "cognitive_action_preserved": true,
        "solution_structure_preserved": true,
        "auxiliary_transformations_preserved": true,
        "distractor_logic_preserved": true,
        "realized_non_mechanizable_axes": ["representacion", "distractor_dominante"],
        "main_risk_checked": "No reemplacé la representación por una tabla explícita."
      }}
    }}
  ]
}}
</formato_respuesta>

<restriccion_critica>
IMPORTANTE: El QTI XML debe:
- Usar namespace xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0"
- INCLUIR OBLIGATORIAMENTE los atributos 'title' y 'timeDependent="false"' en la etiqueta raíz (ej. <qti-assessment-item title="Variante X" timeDependent="false"...>)
- Tener un identifier único (diferente al original)
- Mantener la estructura exacta de la pregunta original
- Usar MathML para expresiones matemáticas si la original las usa
- CRÍTICO: Si la pregunta contiene sistemas de ecuaciones o tablas (etiquetas <mtable>,
  <mtr>, <mtd>), DEBES INCLUIRLAS COMPLETAS en el XML de salida, adaptando los números
  según corresponda. NO omitas las ecuaciones.
</restriccion_critica>
"""
        return prompt

    # _build_structural_profile and _extract_visual_context removed:
    # now use shared_helpers.build_source_structural_profile and extract_visual_context

    def _parse_response(self, response: str, source: SourceQuestion) -> List[Dict[str, Any]]:
        """Parse the LLM response into variant data."""
        variants = parse_generation_response(response)
        if not variants:
            print("  ⚠️ Failed to parse JSON response")
        return variants

    def _build_variant_metadata(
        self,
        source: SourceQuestion,
        variant_data: Dict[str, Any],
        blueprint: Optional[VariantBlueprint] = None,
    ) -> Dict[str, Any]:
        """Build metadata for a variant, inheriting from source."""

        # Start with inherited atoms (same concept = same atoms)
        metadata = {
            "selected_atoms": source.atoms.copy(),
            "general_analysis": source.metadata.get("general_analysis", ""),
            "difficulty": source.difficulty.copy(),
            "validation": {},  # Will be filled in validation phase
            "habilidad_principal": source.metadata.get("habilidad_principal", {}),
            "construct_contract": build_construct_contract(
                source.question_text,
                source.qti_xml,
                bool(source.image_urls),
                source.primary_atoms,
                source.metadata,
                source.choices,
                source.correct_answer,
            ),
            "source_info": {
                "source_question_id": source.question_id,
                "source_test_id": source.test_id,
                "change_description": variant_data.get("change_description", ""),
            },
            "generator_self_check": variant_data.get("self_check", {}),
        }
        if blueprint:
            metadata["planning_blueprint"] = {
                "variant_id": blueprint.variant_id,
                "scenario_description": blueprint.scenario_description,
                "non_mechanizable_axes": blueprint.non_mechanizable_axes,
                "required_reasoning": blueprint.required_reasoning,
                "difficulty_target": blueprint.difficulty_target,
                "requires_image": blueprint.requires_image,
                "image_description": blueprint.image_description,
            }

        return metadata

    def regenerate_with_feedback(
        self,
        source: SourceQuestion,
        blueprint: VariantBlueprint,
        rejection_reason: str,
    ) -> Optional[VariantQuestion]:
        """Re-generate a single variant using the rejection reason as feedback.

        Args:
            source: The source question.
            blueprint: The original blueprint for this variant.
            rejection_reason: Why the previous attempt was rejected.

        Returns:
            A new VariantQuestion if generation succeeds, None otherwise.
        """
        # Escalate reasoning level for retries
        levels = ["none", "low", "medium", "high"]
        current_level = self.config.generator_reasoning_level
        try:
            current_idx = levels.index(current_level)
            retry_level = levels[min(current_idx + 1, len(levels) - 1)]
        except ValueError:
            retry_level = current_level

        print(f"    🔄 Retrying {blueprint.variant_id} (Reasoning bump: {current_level}->{retry_level})...")

        base_prompt = self._build_generation_prompt(source, 1, [blueprint])
        feedback_section = f"""
<feedback_del_intento_anterior>
Tu variante anterior para el blueprint {blueprint.variant_id} fue RECHAZADA por la siguiente razón:

"{rejection_reason}"

DEBES corregir este problema específico en tu nuevo intento.
Genera una variante que:
1. Resuelva exactamente el problema descrito arriba
2. Siga respetando todas las reglas del contrato y del blueprint
3. Sea diferente de la variante rechazada
</feedback_del_intento_anterior>
"""
        prompt_with_feedback = base_prompt + feedback_section

        try:
            response = self.service.generate_text(
                prompt_with_feedback,
                response_mime_type="application/json",
                temperature=self.config.temperature + 0.1,  # Slight bump for diversity
                **build_reasoning_kwargs(
                    self.config.generator_provider,
                    retry_level,
                ),
            )
            variants_data = parse_generation_response(response)
            if not variants_data:
                print(f"    ⚠️ Retry failed to parse response for {blueprint.variant_id}")
                return None

            generated = self._to_variant_objects(source, variants_data[:1], [blueprint])
            if generated:
                variant = generated[0]
                variant.metadata["retry_context"] = {
                    "is_retry": True,
                    "original_rejection_reason": rejection_reason,
                }
                print(f"    ✅ Retry generated new variant for {blueprint.variant_id}")
                return variant
            return None
        except Exception as e:
            print(f"    ⚠️ Retry error for {blueprint.variant_id}: {e}")
            self.last_error = str(e)
            return None
