"""Variant question generator.

This module generates pedagogically-sound variant questions from source
exemplars, guided by planning blueprints that enforce same-construct
alignment with non-mechanizable structural variation.
"""

import json
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

from app.question_variants.llm_service import build_text_service
from app.question_variants.models import (
    PipelineConfig,
    SourceQuestion,
    VariantBlueprint,
    VariantQuestion,
)
from app.question_variants.structural_profile import build_construct_contract, build_structural_profile


class VariantGenerator:
    """Generates variant questions from source exemplars."""

    def __init__(self, config: Optional[PipelineConfig] = None):
        """Initialize the generator.

        Args:
            config: Pipeline configuration. Uses defaults if not provided.
        """
        self.config = config or PipelineConfig()
        self.service = build_text_service(
            self.config.generator_provider,
            self.config.generator_model,
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
        n = num_variants or self.config.variants_per_question

        print(f"  Generating {n} variants for {source.question_id}...")

        try:
            if blueprints:
                variants = self._generate_from_blueprints(source, blueprints[:n])
            else:
                prompt = self._build_generation_prompt(source, n, None)
                response = self.service.generate_text(
                    prompt,
                    response_mime_type="application/json",
                    temperature=self.config.temperature,
                )
                variants_data = self._parse_response(response, source)
                variants = self._to_variant_objects(source, variants_data, None)

            print(f"  ✅ Generated {len(variants)} variants")
            return variants

        except Exception as e:
            print(f"  ❌ Error generating variants: {e}")
            import traceback

            traceback.print_exc()
            return []

    def _generate_from_blueprints(self, source: SourceQuestion, blueprints: List[VariantBlueprint]) -> List[VariantQuestion]:
        variants: List[VariantQuestion] = []
        for blueprint in blueprints:
            try:
                prompt = self._build_generation_prompt(source, 1, [blueprint])
                response = self.service.generate_text(
                    prompt,
                    response_mime_type="application/json",
                    temperature=self.config.temperature,
                )
                variants_data = self._parse_response(response, source)
                generated = self._to_variant_objects(source, variants_data[:1], [blueprint])
                if generated:
                    variants.extend(generated)
                else:
                    print(f"  ⚠️ No se pudo parsear la variante {blueprint.variant_id}")
            except Exception as e:
                print(f"  ⚠️ Error generating {blueprint.variant_id}: {e}")
        return variants

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
        structural_profile = self._build_structural_profile(source)
        construct_contract = build_construct_contract(
            source.question_text,
            source.qti_xml,
            bool(source.image_urls),
            source.primary_atoms,
            source.metadata,
        )
        visual_context = self._extract_visual_context(source.qti_xml)
        evaluation_style = self._build_evaluation_style(source)

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
                "7. ESTA PREGUNTA DEPENDE DE SOPORTE VISUAL. La variante DEBE ser autocontenida: "
                "debes incorporar los datos cuantitativos de la representación en texto visible o en una tabla "
                "dentro del item-body, y preferir tabla/lista textual como representación primaria. "
                "Puedes incluir <img>/<object>, pero NO dependas solo del alt ni de un placeholder. "
                "NO puedes mencionar figura, diagrama, gráfico o infografía si no dejas también los datos explícitos "
                "que permitan resolver la pregunta sin ambigüedad."
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

        prompt = f"""
<role>
Eres un profesor de matemáticas creando variantes de ejercicios para exámenes PAES.
Tu ÚNICA tarea es cambiar los NÚMEROS o el CONTEXTO de la pregunta,
NUNCA el concepto matemático evaluado.
</role>

<reglas_estrictas>
1. La variante DEBE evaluar EXACTAMENTE el mismo concepto que la original
2. La variante DEBE tener la MISMA dificultad ({diff_text})
3. SOLO puedes cambiar:
   - Valores numéricos (ej: 5 → 8, -2 → -3)
   - Nombres de personas/objetos (ej: Juan → María)
   - Contexto superficial manteniendo la estructura (ej: "20% de descuento" → "15% de aumento")
4. NO puedes cambiar:
   - El tipo de operación matemática requerida
   - La cantidad de pasos para resolver
   - El nivel de abstracción o complejidad
5. La respuesta correcta DEBE poder calcularse con el MISMO procedimiento
6. Los distractores DEBEN representar errores plausibles (NO valores aleatorios)
7. DEBES respetar estas invariantes estructurales:
   {json.dumps(structural_profile, ensure_ascii=False)}
8. Si la fuente es "error_analysis", la variante DEBE seguir preguntando por el primer error/paso incorrecto.
9. Si la fuente no usa incógnitas algebraicas, NO puedes introducir x, y, z ni ecuaciones a resolver.
10. Si la firma operacional es "direct_percentage_calculation", la variante DEBE seguir siendo
    un cálculo directo de porcentaje de una cantidad, no un problema de varios pasos ni de interpretación abierta.
11. Para "direct_percentage_calculation", usa exactamente un porcentaje y una cantidad base.
    NO introduzcas área, largo/ancho, volumen ni cálculos intermedios.
12. Debes respetar el contrato de constructo completo, especialmente el modo de evidencia.
    Si el contrato dice "representation_primary", NO reemplaces la interpretación de representación
    por una tabla o lista de datos que permita responder sin interpretar la representación.
13. Debes respetar la accion cognitiva y la estructura de solucion del contrato.
    No conviertas una tarea de interpretacion en una de calculo directo, ni una de un paso
    en una de varios pasos, ni una de sustitucion algebraica en una modelacion distinta.
{image_instruction}
{blueprint_instruction}
</reglas_estrictas>

<pregunta_original>
{source.qti_xml}
</pregunta_original>

<texto_pregunta>
{source.question_text}
</texto_pregunta>

<opciones_originales>
{json.dumps(source.choices, ensure_ascii=False)}
</opciones_originales>

<respuesta_correcta_original>
{source.correct_answer}
</respuesta_correcta_original>

<concepto_evaluado>
{atoms_text}
</concepto_evaluado>

<dificultad>
{diff_text}
Análisis: {diff.get("analysis", "N/A")}
</dificultad>

<invariantes_estructurales>
{json.dumps(structural_profile, ensure_ascii=False, indent=2)}
</invariantes_estructurales>

<contrato_constructo>
{json.dumps(construct_contract, ensure_ascii=False, indent=2)}
</contrato_constructo>

<soporte_visual_fuente>
{visual_context or "N/A"}
</soporte_visual_fuente>

<estilo_evaluacion>
{json.dumps(evaluation_style, ensure_ascii=False, indent=2)}
</estilo_evaluacion>

<tarea>
Genera exactamente {n} variantes. Cada variante DEBE:
1. Tener una respuesta correcta DIFERENTE a la original (distintos números)
2. Mantener exactamente 4 opciones (A, B, C, D) con distractores plausibles
3. Usar el MISMO formato QTI 3.0 que la original
4. Incorporar cambios estructurales no mecanizables (no solo cambio superficial)
5. NO agregues bloques de feedback, solución, ni retroalimentación inline
6. Antes de responder, verifica internamente que NO cambiaste la forma de tarea
   (por ejemplo, operatoria directa -> ecuación; análisis de error -> cálculo directo).
7. Si usas soporte visual, deja los porcentajes, cantidades o relaciones también en texto visible.
8. Si la fuente evalúa afirmaciones sobre datos, tu variante DEBE incluir un conjunto de datos explícito
   (tabla o lista estructurada) y las alternativas deben seguir siendo afirmaciones sobre esos datos.

Para cada variante, genera:
- El XML QTI 3.0 completo (similar al original pero con nuevos valores)
- Una breve explicación del cambio realizado
</tarea>

<formato_respuesta>
Responde con un JSON con esta estructura:
{{
  "variants": [
    {{
      "qti_xml": "<qti-assessment-item ...>...</qti-assessment-item>",
      "change_description": "Cambié los valores de X a Y..."
    }}
  ]
}}
</formato_respuesta>

<restriccion_critica>
IMPORTANTE: El QTI XML debe:
- Usar namespace xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0"
- Tener un identifier único (diferente al original)
- Mantener la estructura exacta de la pregunta original
- Usar MathML para expresiones matemáticas si la original las usa
- CRÍTICO: Si la pregunta contiene sistemas de ecuaciones o tablas (etiquetas <mtable>,
  <mtr>, <mtd>), DEBES INCLUIRLAS COMPLETAS en el XML de salida, adaptando los números
  según corresponda. NO omitas las ecuaciones.
</restriccion_critica>
"""
        return prompt

    def _build_structural_profile(self, source: SourceQuestion) -> Dict[str, Any]:
        profile = build_structural_profile(
            source.question_text,
            source.qti_xml,
            bool(source.image_urls),
            source.primary_atoms,
            source.metadata.get("habilidad_principal", {}).get("habilidad_principal", ""),
        )
        profile["source_has_visual_support"] = bool(source.image_urls)
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

    def _build_evaluation_style(self, source: SourceQuestion) -> Dict[str, Any]:
        atom_titles = [str(a.get("atom_title", "")).lower() for a in source.primary_atoms]
        is_claim_evaluation = any("afirmaciones basadas en datos" in title for title in atom_titles)
        return {
            "claim_evaluation": is_claim_evaluation,
            "expects_explicit_dataset": bool(source.image_urls) or is_claim_evaluation,
        }

    def _parse_response(self, response: str, source: SourceQuestion) -> List[Dict[str, Any]]:
        """Parse the LLM response into variant data."""
        try:
            data = json.loads(response)
            return data.get("variants", [])
        except json.JSONDecodeError as e:
            # Try to fix common JSON issues
            cleaned = re.sub(r'\\(?![/"\\\bfnrtu])', r"\\\\", response)
            try:
                data = json.loads(cleaned)
                return data.get("variants", [])
            except json.JSONDecodeError:
                print(f"  ⚠️ Failed to parse JSON response: {e}")
                return []

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
            ),
            "source_info": {
                "source_question_id": source.question_id,
                "source_test_id": source.test_id,
                "change_description": variant_data.get("change_description", ""),
            },
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
