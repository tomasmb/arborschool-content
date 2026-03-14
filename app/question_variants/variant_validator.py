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
from app.question_variants.structural_profile import build_construct_contract, build_structural_profile
from app.utils.mathml_parser import process_mathml
from app.utils.qti_extractor import extract_choices_from_qti, get_correct_answer_text


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
        lowered = self._extract_question_text(xml_content).lower()
        mentions_visual = any(
            token in lowered
            for token in ("figura", "gráfico", "grafico", "diagrama", "infografía", "infografia", "tabla")
        )
        has_visual_tag = any(token in xml_content.lower() for token in ("<img", "<object", "<qti-object", "<table", "<qti-table"))

        if mentions_visual and not has_visual_tag:
            return False, (
                "La variante está incompleta: menciona una figura, gráfico, diagrama, infografía o tabla "
                "pero no incluye esa representación en el XML."
            )

        if not source.image_urls and mentions_visual:
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
        )
        variant_contract = build_construct_contract(
            self._extract_question_text(xml_content),
            xml_content,
            self._has_visual_support(xml_content),
            source.primary_atoms,
            source.metadata,
        )
        source_profile = self._build_structural_profile(
            source.question_text,
            source.qti_xml,
            bool(source.image_urls),
            source.primary_atoms,
            source.metadata.get("habilidad_principal", {}).get("habilidad_principal", ""),
        )
        variant_text = self._extract_question_text(xml_content)
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

        if self._must_preserve_cognitive_action(contract) and contract["cognitive_action"] != variant_contract["cognitive_action"]:
            return False, (
                "La variante fue rechazada por drift de constructo: cambió la acción cognitiva dominante de "
                f"{contract['cognitive_action']} a {variant_contract['cognitive_action']}."
            )

        if self._must_preserve_solution_structure(contract) and contract["solution_structure"] != variant_contract["solution_structure"]:
            return False, (
                "La variante fue rechazada por drift de dificultad/constructo: cambió la estructura de solución de "
                f"{contract['solution_structure']} a {variant_contract['solution_structure']}."
            )

        if source_profile["requires_direct_computation"] and variant_profile["appears_multi_step"]:
            return False, (
                "La variante fue rechazada por drift de dificultad: la fuente exige un cálculo directo "
                "y la variante parece convertirlo en una tarea de varios pasos."
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

    def _must_preserve_cognitive_action(self, contract: dict[str, object]) -> bool:
        return str(contract.get("cognitive_action")) in {
            "identify_error",
            "interpret_representation",
            "evaluate_claims",
            "substitute_and_compute",
        }

    def _must_preserve_solution_structure(self, contract: dict[str, object]) -> bool:
        return str(contract.get("solution_structure")) in {
            "direct_single_step",
            "representation_reading",
            "data_to_claim_check",
            "error_localization",
            "equation_resolution",
        }

    def _validate_with_llm(self, variant: VariantQuestion, source: SourceQuestion) -> ValidationResult:
        """Use LLM to validate concept alignment, difficulty, and correctness."""

        # Extract variant text for easier reading
        variant_text = self._extract_question_text(variant.qti_xml)
        variant_choices = self._extract_choices(variant.qti_xml)
        variant_correct = self._find_correct_answer(variant.qti_xml)

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

2. **DIFICULTAD IGUAL**: ¿Tiene el mismo nivel de dificultad?
   - Misma cantidad de pasos
   - Mismo nivel de complejidad numérica

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
  "dificultad_igual": true/false,
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

            verdict = ValidationVerdict.APPROVED if data.get("veredicto") == "APROBADA" else ValidationVerdict.REJECTED

            return ValidationResult(
                verdict=verdict,
                concept_aligned=data.get("concepto_alineado", False),
                difficulty_equal=data.get("dificultad_igual", False),
                answer_correct=data.get("respuesta_correcta", False),
                calculation_steps=data.get("tu_calculo", ""),
                distractors_plausible=data.get("distractores_plausibles", False),
                non_mechanizable=data.get("no_mecanizable", False),
                rejection_reason=data.get("razon_rechazo", ""),
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

    def _extract_question_text(self, xml_content: str) -> str:
        """Extract question text from QTI XML, properly handling MathML.

        Delegates to shared utility with local helper for element-to-text conversion.
        """
        try:
            root = ET.fromstring(xml_content)
            # Find item body (use explicit 'is not None' to avoid Element truthiness bug)
            item_body = root.find(".//{*}qti-item-body")
            if item_body is None:
                item_body = root.find(".//{*}itemBody")
            if item_body is not None:
                return self._element_to_text(item_body)
            return ""
        except Exception:
            return ""

    def _element_to_text(self, element: ET.Element) -> str:
        """Recursively extract text from an element, properly handling MathML."""
        parts = []
        tag_name = element.tag.split("}")[-1].lower()

        if tag_name == "img":
            alt = element.attrib.get("alt", "").strip()
            if alt:
                parts.append(alt)
            return " ".join(filter(None, parts))
        if tag_name == "object":
            label = (
                element.attrib.get("aria-label", "").strip()
                or element.attrib.get("label", "").strip()
                or element.attrib.get("title", "").strip()
            )
            if label:
                parts.append(label)
            return " ".join(filter(None, parts))

        if element.text:
            parts.append(element.text.strip())

        for child in element:
            tag = child.tag.split("}")[-1].lower()

            if tag in ("qti-feedback-inline", "feedbackinline", "qti-feedback-block", "feedbackblock"):
                # Exclude solution/feedback blocks from semantic comparison of question text.
                continue

            if tag == "math":
                # Process MathML to readable text using shared utility
                parts.append(process_mathml(child))
            elif tag in ("qti-simple-choice", "simplechoice"):
                # Skip individual choices (we extract them separately)
                pass
            else:
                # Include qti-prompt, qti-choice-interaction, and all other elements
                parts.append(self._element_to_text(child))

            if child.tail:
                parts.append(child.tail.strip())

        return " ".join(filter(None, parts))

    def _extract_choices(self, xml_content: str) -> list[str]:
        """Extract choice texts from QTI XML, excluding embedded feedback nodes."""
        try:
            root = ET.fromstring(xml_content)
            raw_choices = root.findall(".//{*}qti-simple-choice")
            if not raw_choices:
                raw_choices = root.findall(".//{*}simpleChoice")

            choices: list[str] = []
            for choice in raw_choices:
                choices.append(self._choice_text_without_feedback(choice))
            return choices
        except Exception:
            # Fallback to shared utility if custom extraction fails.
            choices, _ = extract_choices_from_qti(xml_content)
            return choices

    def _choice_text_without_feedback(self, element: ET.Element) -> str:
        """Extract visible choice text while ignoring feedback inline blocks."""
        parts: list[str] = []
        if element.text:
            parts.append(element.text.strip())

        for child in element:
            tag = child.tag.split("}")[-1].lower()
            if tag in ("qti-feedback-inline", "feedbackinline"):
                continue
            if tag == "math":
                parts.append(process_mathml(child))
            else:
                parts.append(self._element_to_text(child))
            if child.tail:
                parts.append(child.tail.strip())

        return " ".join(filter(None, parts))

    def _find_correct_answer(self, xml_content: str) -> str:
        """Find the correct answer from QTI XML, properly handling MathML."""
        return get_correct_answer_text(xml_content)
