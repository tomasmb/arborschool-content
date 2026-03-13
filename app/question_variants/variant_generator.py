"""Variant question generator.

This module generates pedagogically-sound variant questions from source
exemplars, guided by planning blueprints that enforce same-construct
alignment with non-mechanizable structural variation.
"""

import json
import re
from typing import Any, Dict, List, Optional

from app.llm_clients import load_default_gemini_service
from app.question_variants.models import (
    PipelineConfig,
    SourceQuestion,
    VariantBlueprint,
    VariantQuestion,
)


class VariantGenerator:
    """Generates variant questions from source exemplars."""

    def __init__(self, config: Optional[PipelineConfig] = None):
        """Initialize the generator.

        Args:
            config: Pipeline configuration. Uses defaults if not provided.
        """
        self.config = config or PipelineConfig()
        self.service = load_default_gemini_service()

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

        # Build the restrictive prompt
        prompt = self._build_generation_prompt(source, n, blueprints)

        print(f"  Generating {n} variants for {source.question_id}...")

        try:
            response = self.service.generate_text(prompt, response_mime_type="application/json", temperature=self.config.temperature)

            # Parse the response
            variants_data = self._parse_response(response, source)

            # Convert to VariantQuestion objects
            variants = []
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

            print(f"  ✅ Generated {len(variants)} variants")
            return variants

        except Exception as e:
            print(f"  ❌ Error generating variants: {e}")
            import traceback

            traceback.print_exc()
            return []

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

        # Check for image info and add instruction if decorative
        image_info = source.metadata.get("image_info", {})
        image_instruction = ""
        if image_info.get("image_type") == "decorative":
            image_instruction = (
                "7. ESTA PREGUNTA CONTIENE UNA IMAGEN DECORATIVA (Support visual). "
                "DEBES INCLUIR LA ETIQUETA <img ...> EXACTAMENTE IGUAL QUE EN LA "
                "ORIGINAL dentro del texto."
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

<tarea>
Genera exactamente {n} variantes. Cada variante DEBE:
1. Tener una respuesta correcta DIFERENTE a la original (distintos números)
2. Mantener exactamente 4 opciones (A, B, C, D) con distractores plausibles
3. Usar el MISMO formato QTI 3.0 que la original
4. Incluir feedback educativo para cada opción siguiendo el estilo de la original
5. Incorporar cambios estructurales no mecanizables (no solo cambio superficial)

Para cada variante, genera:
- El XML QTI 3.0 completo (similar al original pero con nuevos valores)
- Feedback por opción explicando por qué es correcta/incorrecta
- Una breve explicación del cambio realizado
</tarea>

<formato_respuesta>
Responde con un JSON con esta estructura:
{{
  "variants": [
    {{
      "qti_xml": "<qti-assessment-item ...>...</qti-assessment-item>",
      "feedback": {{
        "general_guidance": "Explicación general...",
        "per_option_feedback": {{
          "opcion_A_texto": "Feedback para A...",
          "opcion_B_texto": "Feedback para B...",
          "opcion_C_texto": "Feedback para C...",
          "opcion_D_texto": "Feedback para D..."
        }}
      }},
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
            "feedback": variant_data.get("feedback", {}),
            "validation": {},  # Will be filled in validation phase
            "habilidad_principal": source.metadata.get("habilidad_principal", {}),
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
