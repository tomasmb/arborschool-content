"""Variant question validator -- simplified 3-gate validation.

Deterministic pre-checks (no LLM cost):
  1. Valid XML
  2. Choice interaction integrity (QTI wiring)
  3. Visual completeness (mentions figure/table -> must exist in XML)

LLM semantic gates (3 essential):
  1. respuesta_correcta -- is the marked answer mathematically correct?
  2. concepto_alineado -- does it test the same atoms/concept?
  3. es_diferente -- is it genuinely different from the original?
"""

from __future__ import annotations

import json
import logging
import re
import xml.etree.ElementTree as ET
from typing import Optional

from app.question_variants.models import (
    PipelineConfig,
    SourceQuestion,
    ValidationResult,
    ValidationVerdict,
    VariantQuestion,
)
from app.question_variants.qti_validation_utils import (
    extract_choices,
    extract_question_text,
    find_correct_answer,
    validate_choice_interaction_integrity,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pure functions -- shared by sync and batch paths (DRY)
# ---------------------------------------------------------------------------


def build_validation_prompt(variant: VariantQuestion, source: SourceQuestion) -> str:
    """Build the LLM validation prompt for a variant.

    Pure function with no side effects -- used by both the sync validator
    and the batch request builders.
    """
    variant_text = extract_question_text(variant.qti_xml)
    variant_choices = extract_choices(variant.qti_xml)
    variant_correct = find_correct_answer(variant.qti_xml)

    atoms_json = json.dumps(
        [a.get("atom_title") for a in source.primary_atoms],
        ensure_ascii=False,
    )

    return f"""<role>
Eres un revisor de calidad de exámenes matemáticos PAES.
Tu tarea es verificar que una variante generada automáticamente es válida.
</role>

<pregunta_original>
Texto: {source.question_text}

Opciones: {json.dumps(source.choices, ensure_ascii=False)}

Respuesta correcta: {source.correct_answer}

Concepto evaluado: {atoms_json}

Dificultad: {source.difficulty.get("level", "Medium")}
</pregunta_original>

<variante_a_validar>
Texto: {variant_text}

Opciones: {json.dumps(variant_choices, ensure_ascii=False)}

Respuesta marcada como correcta: {variant_correct}
</variante_a_validar>

<tarea>
Verifica cuidadosamente estos 3 criterios:

1. **RESPUESTA CORRECTA**: ¿La respuesta marcada como correcta ES realmente correcta?
   - Resuelve el problema paso a paso.
   - Muestra tu cálculo completo.
   - Verifica que tu resultado coincide con la opción marcada.

2. **CONCEPTO ALINEADO**: ¿La variante evalúa el mismo concepto matemático?
   - Un estudiante necesita los mismos conocimientos matemáticos para resolver ambas.
   - La variante puede presentar el concepto de forma diferente (distinto contexto,
     distinta representación, distinto orden de pasos) siempre que el conocimiento
     requerido sea el mismo.

3. **ES DIFERENTE**: ¿Es una pregunta genuinamente diferente de la original?
   - No basta con cambiar números: debe cambiar contexto, representación o forma.
   - La respuesta correcta debe ser diferente a la de la original.
</tarea>

<formato_respuesta>
Responde en JSON:
{{
  "respuesta_correcta": true/false,
  "tu_calculo": "Paso 1: ... Paso 2: ... Resultado: ...",
  "concepto_alineado": true/false,
  "razon_concepto": "Explicación breve...",
  "es_diferente": true/false,
  "razon_diferencia": "Explicación breve...",
  "veredicto": "APROBADA" o "RECHAZADA",
  "razon_rechazo": "Si es rechazada, explicar por qué..."
}}
</formato_respuesta>

<regla_critica>
Si la respuesta marcada como correcta NO es matemáticamente correcta,
el veredicto DEBE ser "RECHAZADA" sin importar lo demás.
</regla_critica>"""


def parse_validation_json(raw: str) -> ValidationResult:
    """Parse LLM validation JSON into a ValidationResult.

    Pure function -- shared by sync and batch paths.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return ValidationResult(
            verdict=ValidationVerdict.REJECTED,
            concept_aligned=False,
            difficulty_equal=True,
            answer_correct=False,
            rejection_reason="No se pudo parsear respuesta de validación",
        )

    answer_correct = data.get("respuesta_correcta", False)
    concept_aligned = data.get("concepto_alineado", False)
    is_different = data.get("es_diferente", False)
    calculation_steps = data.get("tu_calculo", "")
    rejection_reason = data.get("razon_rechazo", "")

    verdict_str = data.get("veredicto", "")
    verdict = (
        ValidationVerdict.APPROVED
        if verdict_str == "APROBADA"
        else ValidationVerdict.REJECTED
    )

    if not answer_correct:
        verdict = ValidationVerdict.REJECTED
        rejection_reason = rejection_reason or (
            "La respuesta marcada como correcta no coincide "
            "con la resolución matemática del ítem."
        )
    if not concept_aligned:
        verdict = ValidationVerdict.REJECTED
        rejection_reason = rejection_reason or (
            "La variante no evalúa el mismo concepto "
            "matemático que la fuente."
        )
    if not is_different:
        verdict = ValidationVerdict.REJECTED
        rejection_reason = rejection_reason or (
            "La variante no es suficientemente diferente "
            "de la fuente."
        )

    return ValidationResult(
        verdict=verdict,
        concept_aligned=concept_aligned,
        difficulty_equal=True,
        answer_correct=answer_correct,
        calculation_steps=calculation_steps,
        rejection_reason=rejection_reason,
    )


# ---------------------------------------------------------------------------
# Deterministic checks -- no LLM cost
# ---------------------------------------------------------------------------


def validate_xml(xml_content: str) -> tuple[bool, str]:
    """Check that the XML is parseable."""
    try:
        ET.fromstring(xml_content)
        return True, ""
    except ET.ParseError as e:
        return False, str(e)


def validate_visual_completeness(
    xml_content: str, source: SourceQuestion,
) -> tuple[bool, str]:
    """Reject variants that mention visuals but don't include them."""
    lowered = extract_question_text(xml_content).lower()
    image_tokens = (
        "figura", "gráfico", "grafico",
        "diagrama", "infografía", "infografia",
    )
    mentions_image = any(t in lowered for t in image_tokens)
    mentions_table = "tabla" in lowered

    has_img = _contains_xml_visual_object(xml_content)
    has_table = _contains_xml_table(xml_content)
    has_dataset = has_table or _has_explicit_textual_dataset(lowered)

    if (mentions_image and not has_img and not has_dataset) or (
        mentions_table and not has_table and not has_dataset
    ):
        return False, (
            "La variante está incompleta: menciona una figura, "
            "gráfico, diagrama, infografía o tabla pero no incluye "
            "esa representación en el XML."
        )

    if not source.image_urls and (mentions_image or has_img):
        return False, (
            "La variante introduce soporte visual que no existe "
            "en la pregunta fuente."
        )

    return True, ""


# ---------------------------------------------------------------------------
# XML helpers
# ---------------------------------------------------------------------------


def _contains_xml_visual_object(xml_content: str) -> bool:
    lo = xml_content.lower()
    return bool(
        re.search(r"<(?:[\w.-]+:)?img\b", lo)
        or re.search(r"<(?:[\w.-]+:)?object\b", lo)
        or re.search(r"<(?:[\w.-]+:)?qti-object\b", lo)
    )


def _contains_xml_table(xml_content: str) -> bool:
    lo = xml_content.lower()
    return bool(
        re.search(r"<(?:[\w.-]+:)?table\b", lo)
        or re.search(r"<(?:[\w.-]+:)?qti-table\b", lo)
    )


def _has_explicit_textual_dataset(lowered_text: str) -> bool:
    pairs = re.findall(
        r"\(\s*\d+(?:[.,]\d+)?\s*,\s*\d+(?:[.,]\d+)?\s*\)",
        lowered_text,
    )
    labels = re.findall(
        r"[a-záéíóúñ][^:\n]{0,30}:\s*\d+(?:[.,]\d+)?",
        lowered_text,
    )
    return len(pairs) >= 2 or len(labels) >= 3


# ---------------------------------------------------------------------------
# VariantValidator class -- sync path (used by --no-batch mode)
# ---------------------------------------------------------------------------


class VariantValidator:
    """Validates generated variant questions (sync mode)."""

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        from app.question_variants.llm_service import build_text_service

        self.service = build_text_service(
            "openai",
            self.config.model,
            timeout_seconds=self.config.llm_request_timeout_seconds,
            max_attempts=self.config.llm_max_attempts,
        )

    def validate(
        self,
        variant: VariantQuestion,
        source: SourceQuestion,
    ) -> ValidationResult:
        """Run deterministic checks then LLM validation."""
        print(f"    Validating {variant.variant_id}...")

        xml_ok, xml_err = validate_xml(variant.qti_xml)
        if not xml_ok:
            return _rejected(f"XML inválido: {xml_err}")

        wire_ok, wire_err = validate_choice_interaction_integrity(
            variant.qti_xml,
        )
        if not wire_ok:
            return _rejected(wire_err)

        vis_ok, vis_err = validate_visual_completeness(
            variant.qti_xml, source,
        )
        if not vis_ok:
            return _rejected(vis_err)

        return self._validate_with_llm(variant, source)

    def _validate_with_llm(
        self,
        variant: VariantQuestion,
        source: SourceQuestion,
    ) -> ValidationResult:
        """Call the LLM for semantic validation."""
        prompt = build_validation_prompt(variant, source)
        try:
            response = self.service.generate_text(
                prompt,
                response_mime_type="application/json",
                temperature=0.0,
                reasoning_effort="medium",
            )
            result = parse_validation_json(response)
            if result.is_approved:
                print(f"    ✅ {variant.variant_id} APROBADA")
            else:
                reason = result.rejection_reason
                print(f"    ❌ {variant.variant_id} RECHAZADA: {reason}")
            return result
        except Exception as e:
            print(f"    ⚠️ Error validating: {e}")
            return _rejected(f"Error de validación: {e}")


def _rejected(reason: str) -> ValidationResult:
    """Shorthand for a rejected ValidationResult."""
    return ValidationResult(
        verdict=ValidationVerdict.REJECTED,
        concept_aligned=False,
        difficulty_equal=True,
        answer_correct=False,
        rejection_reason=reason,
    )
