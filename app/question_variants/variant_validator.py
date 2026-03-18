"""Variant question validator.

This module validates generated variants to ensure they:
1. Are valid QTI 3.0 XML
2. Test the EXACT SAME concept as the original
3. Have the same difficulty level
4. Have a mathematically correct answer
5. Have plausible distractors
6. Are non-mechanizable (not solvable by rote pattern only)
"""

import json
import re
import xml.etree.ElementTree as ET
from typing import Optional

from app.question_variants.llm_service import build_text_service
from app.question_variants.models import (
    PipelineConfig,
    SourceQuestion,
    ValidationResult,
    ValidationVerdict,
    VariantQuestion,
)
from app.question_variants.qti_validation_utils import extract_choices, extract_question_text, find_correct_answer
from app.question_variants.contracts.semantic_guardrails import (
    adds_auxiliary_transformations,
    adds_reference_load,
    breaks_expected_distractor_logic,
    failed_generator_self_check,
    has_equivalent_correct_choice,
    has_semantic_contract_drift,
    has_numeric_option_scale_outlier,
    inflates_data_burden,
    is_insufficiently_different,
    repeats_claim_archetype,
)
from app.question_variants.contracts.preservation_policy import (
    must_preserve_cognitive_action,
    must_preserve_main_skill,
    must_preserve_solution_structure,
)
from app.question_variants.contracts.structural_profile import build_construct_contract, build_structural_profile


class VariantValidator:
    """Validates generated variant questions."""

    def __init__(self, config: Optional[PipelineConfig] = None):
        """Initialize the validator.

        Args:
            config: Pipeline configuration. Uses defaults if not provided.
        """
        self.config = config or PipelineConfig()
        self.service = build_text_service(
            self.config.validator_provider,
            self.config.validator_model,
            timeout_seconds=self.config.llm_request_timeout_seconds,
            max_attempts=self.config.llm_max_attempts,
        )

    def validate(self, variant: VariantQuestion, source: SourceQuestion) -> ValidationResult:
        """Validate a variant question against its source.

        Args:
            variant: The variant to validate
            source: The original source question

        Returns:
            ValidationResult with verdict and details
        """
        print(f"    Validating {variant.variant_id}...")

        # Step 1: Basic XML validation
        xml_valid, xml_error = self._validate_xml(variant.qti_xml)
        if not xml_valid:
            return ValidationResult(
                verdict=ValidationVerdict.REJECTED,
                concept_aligned=False,
                difficulty_equal=False,
                answer_correct=False,
                non_mechanizable=False,
                rejection_reason=f"XML inválido: {xml_error}",
            )

        visual_ref_ok, visual_ref_error = self._validate_visual_completeness(variant.qti_xml, source)
        if not visual_ref_ok:
            return ValidationResult(
                verdict=ValidationVerdict.REJECTED,
                concept_aligned=False,
                difficulty_equal=False,
                answer_correct=False,
                non_mechanizable=False,
                rejection_reason=visual_ref_error,
            )
        structural_ok, structural_error = self._validate_structural_alignment(variant.qti_xml, source)
        if not structural_ok:
            return ValidationResult(
                verdict=ValidationVerdict.REJECTED,
                concept_aligned=False,
                difficulty_equal=False,
                answer_correct=False,
                non_mechanizable=False,
                rejection_reason=structural_error,
            )

        self_check_error = failed_generator_self_check(variant.metadata)
        if self_check_error:
            return ValidationResult(
                verdict=ValidationVerdict.REJECTED,
                concept_aligned=False,
                difficulty_equal=False,
                answer_correct=False,
                non_mechanizable=False,
                rejection_reason=self_check_error,
            )

        # Step 2: LLM-based validation
        return self._validate_with_llm(variant, source)

    def _validate_xml(self, xml_content: str) -> tuple[bool, str]:
        """Validate that the XML is parseable.

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Basic parse check
            ET.fromstring(xml_content)
            return True, ""
        except ET.ParseError as e:
            return False, str(e)

    def _validate_visual_completeness(self, xml_content: str, source: SourceQuestion) -> tuple[bool, str]:
        lowered = extract_question_text(xml_content).lower()
        mentions_image_like = any(
            token in lowered for token in ("figura", "gráfico", "grafico", "diagrama", "infografía", "infografia")
        )
        mentions_table = "tabla" in lowered
        has_image_tag = any(token in xml_content.lower() for token in ("<img", "<object", "<qti-object"))
        has_table_tag = any(token in xml_content.lower() for token in ("<table", "<qti-table"))

        has_textual_dataset_fallback = has_table_tag or self._has_explicit_textual_dataset(lowered)

        if (mentions_image_like and not has_image_tag and not has_textual_dataset_fallback) or (mentions_table and not has_table_tag):
            return False, (
                "La variante está incompleta: menciona una figura, gráfico, diagrama, infografía o tabla "
                "pero no incluye esa representación en el XML."
            )

        if not source.image_urls and (mentions_image_like or has_image_tag):
            return False, (
                "La variante fue rechazada porque introduce soporte visual que no existe en la pregunta fuente, "
                "alterando la forma de representación y arriesgando un ítem incompleto."
            )

        return True, ""

    def _validate_structural_alignment(self, xml_content: str, source: SourceQuestion) -> tuple[bool, str]:
        contract = build_construct_contract(
            source.question_text,
            source.qti_xml,
            bool(source.image_urls),
            source.primary_atoms,
            source.metadata,
            source.choices,
            source.correct_answer,
        )
        variant_contract = build_construct_contract(
            extract_question_text(xml_content),
            xml_content,
            self._has_visual_support(xml_content),
            source.primary_atoms,
            source.metadata,
            extract_choices(xml_content),
            find_correct_answer(xml_content),
        )
        source_profile = self._build_structural_profile(
            source.question_text,
            source.qti_xml,
            bool(source.image_urls),
            source.primary_atoms,
            source.metadata.get("habilidad_principal", {}).get("habilidad_principal", ""),
        )
        variant_text = extract_question_text(xml_content)
        variant_profile = self._build_structural_profile(
            variant_text,
            xml_content,
            self._has_visual_support(xml_content),
            source.primary_atoms,
            source.metadata.get("habilidad_principal", {}).get("habilidad_principal", ""),
        )

        if source_profile["task_form"] != variant_profile["task_form"]:
            return False, (
                "La variante fue rechazada por drift de constructo: la forma de tarea cambió de "
                f"{source_profile['task_form']} a {variant_profile['task_form']}."
            )

        if source_profile["must_not_introduce_algebraic_unknowns"] and variant_profile["introduces_unknowns"]:
            return False, (
                "La variante fue rechazada por drift de constructo/dificultad: introduce incógnitas "
                "algebraicas que no existen en la pregunta fuente."
            )

        if source_profile["operation_signature"] == "direct_percentage_calculation" and variant_profile["extra_base_quantity"]:
            return False, (
                "La variante fue rechazada por drift de dificultad: un cálculo directo de porcentaje "
                "no puede introducir magnitudes adicionales que obliguen a un cálculo intermedio."
            )

        if source_profile["operation_signature"] == "trinomial_factorization" and self._introduces_rational_expression(xml_content):
            return False, (
                "La variante fue rechazada por drift de constructo: una factorización de trinomio "
                "no puede transformarse en simplificación de expresiones racionales o fracciones algebraicas."
            )

        if "must_preserve_standard_trinomial_form" in contract["hard_constraints"] and self._introduces_shifted_trinomial_form(xml_content):
            return False, (
                "La variante fue rechazada por drift de dificultad: una factorización rutinaria de trinomio "
                "no debe reescribirse en formas desplazadas o equivalentes que agreguen expansión o cambio de variable."
            )

        if source_profile["claim_evaluation"] and not variant_profile["claim_evaluation"]:
            return False, (
                "La variante fue rechazada por drift de constructo: la fuente evalúa afirmaciones "
                "basadas en datos y la variante dejó de hacerlo."
            )

        if source_profile["representation_interpretation"] and not variant_profile["representation_interpretation"]:
            return False, (
                "La variante fue rechazada por drift de constructo: la fuente exige interpretar una "
                "representación o relación entre magnitudes y la variante dejó de hacerlo."
            )

        if contract["representation_must_remain_primary"] and self._short_circuits_representation(xml_content):
            return False, (
                "La variante fue rechazada por drift de constructo: reemplaza la representación como evidencia "
                "primaria por una tabla o listado explícito que permite responder sin interpretar la representación."
            )

        if must_preserve_cognitive_action(contract) and contract["cognitive_action"] != variant_contract["cognitive_action"]:
            return False, (
                "La variante fue rechazada por drift de constructo: cambió la acción cognitiva dominante de "
                f"{contract['cognitive_action']} a {variant_contract['cognitive_action']}."
            )

        if must_preserve_solution_structure(contract) and contract["solution_structure"] != variant_contract["solution_structure"]:
            return False, (
                "La variante fue rechazada por drift de dificultad/constructo: cambió la estructura de solución de "
                f"{contract['solution_structure']} a {variant_contract['solution_structure']}."
            )

        if must_preserve_main_skill(contract) and contract["main_skill"] != variant_contract["main_skill"]:
            return False, (
                "La variante fue rechazada por drift de constructo: cambió la habilidad principal de "
                f"{contract['main_skill']} a {variant_contract['main_skill']}."
            )

        if source_profile["requires_direct_computation"] and variant_profile["appears_multi_step"]:
            return False, (
                "La variante fue rechazada por drift de dificultad: la fuente exige un cálculo directo "
                "y la variante parece convertirlo en una tarea de varios pasos."
            )

        if adds_auxiliary_transformations(contract, variant_contract):
            return False, (
                "La variante fue rechazada por drift de dificultad: agregó transformaciones auxiliares "
                "o pasos intermedios que no están en la pregunta fuente."
            )

        if breaks_expected_distractor_logic(contract, variant_contract):
            return False, (
                "La variante fue rechazada por drift de calidad: perdió los arquetipos de distractor "
                "necesarios para conservar la misma trampa conceptual de la fuente."
            )

        if adds_reference_load(contract, variant_contract):
            return False, (
                "La variante fue rechazada por drift de dificultad: agregó relaciones de referencia o "
                "conversiones adicionales que no están en la pregunta fuente."
            )

        if inflates_data_burden(contract, variant_contract):
            return False, (
                "La variante fue rechazada por drift de dificultad: aumentó artificialmente la carga de datos "
                "o frecuencias a procesar respecto de la fuente."
            )

        semantic_contract_drift = has_semantic_contract_drift(contract, variant_contract)
        if semantic_contract_drift:
            return False, f"La variante fue rechazada por drift de constructo/dificultad: {semantic_contract_drift}"

        if repeats_claim_archetype(contract, variant_contract):
            return False, (
                "La variante fue rechazada por calidad insuficiente: repite el mismo arquetipo semántico decisivo "
                "de la fuente en vez de variar la validación conceptual dentro del mismo constructo."
            )

        if has_numeric_option_scale_outlier(extract_choices(xml_content), find_correct_answer(xml_content), contract):
            return False, (
                "La variante fue rechazada por calidad de distractores: incluye opciones numéricas fuera de escala "
                "respecto de la respuesta correcta."
            )

        if has_equivalent_correct_choice(extract_choices(xml_content), find_correct_answer(xml_content), contract):
            return False, (
                "La variante fue rechazada porque tiene más de una opción equivalente correcta, "
                "expresada con diferentes unidades o escalas."
            )

        if is_insufficiently_different(source.question_text, source.choices, variant_text, extract_choices(xml_content), contract):
            return False, (
                "La variante fue rechazada por calidad insuficiente: quedó demasiado cercana a la fuente "
                "y no materializa suficiente variación estructural no mecanizable."
            )

        if source_profile["expects_explicit_dataset"] and not variant_profile["has_explicit_dataset"]:
            return False, (
                "La variante fue rechazada porque no deja un conjunto de datos explícito y autocontenido, "
                "a pesar de que la fuente sí depende de información visual o tabular."
            )

        return True, ""

    def _build_structural_profile(
        self,
        question_text: str,
        qti_xml: str,
        has_visual_support: bool,
        primary_atoms: list[dict],
        main_skill: str,
    ) -> dict[str, bool | str]:
        return build_structural_profile(question_text, qti_xml, has_visual_support, primary_atoms, main_skill)

    def _has_visual_support(self, xml_content: str) -> bool:
        lowered = xml_content.lower()
        return any(token in lowered for token in ("<img", "<object", "<qti-object", "<table", "<qti-table"))

    def _short_circuits_representation(self, xml_content: str) -> bool:
        lowered = xml_content.lower()
        has_table = "<table" in lowered or "<qti-table" in lowered
        numeric_density = len(re.findall(r"\d+(?:[.,]\d+)?", lowered))
        return has_table and numeric_density >= 6

    def _has_explicit_textual_dataset(self, lowered_text: str) -> bool:
        has_coordinate_pairs = len(re.findall(r"\(\s*\d+(?:[.,]\d+)?\s*,\s*\d+(?:[.,]\d+)?\s*\)", lowered_text)) >= 2
        has_labeled_value_list = len(re.findall(r"[a-záéíóúñ][^:\n]{0,30}:\s*\d+(?:[.,]\d+)?", lowered_text)) >= 3
        return has_coordinate_pairs or has_labeled_value_list

    def _introduces_rational_expression(self, xml_content: str) -> bool:
        lowered = xml_content.lower()
        return "<mfrac" in lowered or "≠" in lowered or "&#x2260;" in lowered or "dominio" in lowered

    def _introduces_shifted_trinomial_form(self, xml_content: str) -> bool:
        lowered = xml_content.lower()
        return "<msup><mrow><mo>(</mo><mi>x</mi>" in lowered or "(x-" in lowered or "(x+" in lowered

    def _validate_with_llm(self, variant: VariantQuestion, source: SourceQuestion) -> ValidationResult:
        """Use LLM to validate concept alignment, difficulty, and correctness."""

        # Extract variant text for easier reading
        variant_text = extract_question_text(variant.qti_xml)
        variant_choices = extract_choices(variant.qti_xml)
        variant_correct = find_correct_answer(variant.qti_xml)

        prompt = f"""
<role>
Eres un revisor de calidad de exámenes matemáticos PAES.
Tu tarea es verificar que una variante generada automáticamente es válida.
</role>

<pregunta_original>
Texto: {source.question_text}

Opciones: {json.dumps(source.choices, ensure_ascii=False)}

Respuesta correcta: {source.correct_answer}

Concepto evaluado: {json.dumps([a.get("atom_title") for a in source.primary_atoms], ensure_ascii=False)}

Dificultad: {source.difficulty.get("level", "Medium")}
</pregunta_original>

<variante_a_validar>
Texto: {variant_text}

Opciones: {json.dumps(variant_choices, ensure_ascii=False)}

Respuesta marcada como correcta: {variant_correct}
</variante_a_validar>

<tarea>
Verifica cuidadosamente:

1. **CONCEPTO ALINEADO**: ¿La variante evalúa EXACTAMENTE el mismo concepto matemático?
   - Debe requerir las mismas operaciones/habilidades
   - No puede ser más abstracta ni más concreta

2. **DIFICULTAD ACEPTABLE**: ¿Mantiene la banda de dificultad objetivo?
   - Debe ser igual o, si el diseño lo permite, levemente más difícil
   - No puede subir de forma que cambie el tipo de razonamiento, la cantidad de pasos
     o la complejidad estructural del ítem

3. **RESPUESTA CORRECTA**: ¿La respuesta marcada como correcta ES realmente correcta?
   - Resuelve el problema paso a paso
   - Muestra tu cálculo completo
   - Verifica que tu resultado coincide con la opción marcada

4. **DISTRACTORES PLAUSIBLES**: ¿Los distractores representan errores comunes?
   - No deben ser valores absurdos o aleatorios
   - Deben ser errores que un estudiante podría cometer

5. **VARIANTE DIFERENTE**: ¿Es suficientemente diferente de la original?
   - Debe tener al menos un cambio significativo (números diferentes, contexto diferente)
   - La respuesta correcta debe ser DIFERENTE a la original

6. **NO MECANIZABLE**: ¿Evita resolución por receta memorizada?
   - Debe cambiar al menos 2 ejes estructurales (forma, representación, distractor o secuencia)
   - Debe exigir comprender el por qué del método
</tarea>

<formato_respuesta>
Responde en JSON:
{{
  "concepto_alineado": true/false,
  "razon_concepto": "Explicación breve...",
  "dificultad_aceptable": true/false,
  "razon_dificultad": "Explicación breve...",
  "respuesta_correcta": true/false,
  "tu_calculo": "Paso 1: ... Paso 2: ... Resultado: ...",
  "distractores_plausibles": true/false,
  "razon_distractores": "Explicación breve...",
  "es_diferente": true/false,
  "no_mecanizable": true/false,
  "razon_no_mecanizable": "Explicación breve...",
  "veredicto": "APROBADA" o "RECHAZADA",
  "razon_rechazo": "Si es rechazada, explicar por qué..."
}}
</formato_respuesta>

<regla_critica>
Si la respuesta marcada como correcta NO es matemáticamente correcta,
el veredicto DEBE ser "RECHAZADA" sin importar lo demás.
</regla_critica>
"""

        try:
            response = self.service.generate_text(
                prompt,
                response_mime_type="application/json",
                temperature=0.0,  # Deterministic for validation
            )

            result = self._parse_validation_response(response)

            if result.is_approved:
                print(f"    ✅ {variant.variant_id} APROBADA")
            else:
                print(f"    ❌ {variant.variant_id} RECHAZADA: {result.rejection_reason}")

            return result

        except Exception as e:
            print(f"    ⚠️ Error validating: {e}")
            return ValidationResult(
                verdict=ValidationVerdict.REJECTED,
                concept_aligned=False,
                difficulty_equal=False,
                answer_correct=False,
                non_mechanizable=False,
                rejection_reason=f"Error de validación: {str(e)}",
            )

    def _parse_validation_response(self, response: str) -> ValidationResult:
        """Parse LLM validation response into ValidationResult."""
        try:
            data = json.loads(response)

            concept_aligned = data.get("concepto_alineado", False)
            difficulty_acceptable = data.get("dificultad_aceptable", data.get("dificultad_igual", False))
            answer_correct = data.get("respuesta_correcta", False)
            rejection_reason = data.get("razon_rechazo", "")
            verdict = ValidationVerdict.APPROVED if data.get("veredicto") == "APROBADA" else ValidationVerdict.REJECTED

            if not answer_correct:
                verdict = ValidationVerdict.REJECTED
                rejection_reason = rejection_reason or (
                    "La respuesta marcada como correcta no coincide con la resolución matemática del ítem."
                )
            if not concept_aligned:
                verdict = ValidationVerdict.REJECTED
                rejection_reason = rejection_reason or (
                    "La variante no evalúa exactamente el mismo concepto matemático que la fuente."
                )

            return ValidationResult(
                verdict=verdict,
                concept_aligned=concept_aligned,
                difficulty_equal=difficulty_acceptable,
                answer_correct=answer_correct,
                calculation_steps=data.get("tu_calculo", ""),
                distractors_plausible=data.get("distractores_plausibles", False),
                non_mechanizable=data.get("no_mecanizable", False),
                rejection_reason=rejection_reason,
            )
        except json.JSONDecodeError:
            return ValidationResult(
                verdict=ValidationVerdict.REJECTED,
                concept_aligned=False,
                difficulty_equal=False,
                answer_correct=False,
                non_mechanizable=False,
                rejection_reason="No se pudo parsear respuesta de validación",
            )
