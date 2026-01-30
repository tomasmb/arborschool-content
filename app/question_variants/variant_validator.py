"""Variant question validator.

This module validates generated variants to ensure they:
1. Are valid QTI 3.0 XML
2. Test the EXACT SAME concept as the original
3. Have the same difficulty level
4. Have a mathematically correct answer
5. Have plausible distractors
"""

import json
import xml.etree.ElementTree as ET
from typing import Optional

from app.gemini_client import load_default_gemini_service
from app.question_variants.models import (
    PipelineConfig,
    SourceQuestion,
    ValidationResult,
    ValidationVerdict,
    VariantQuestion,
)


class VariantValidator:
    """Validates generated variant questions."""

    def __init__(self, config: Optional[PipelineConfig] = None):
        """Initialize the validator.
        
        Args:
            config: Pipeline configuration. Uses defaults if not provided.
        """
        self.config = config or PipelineConfig()
        self.service = load_default_gemini_service()

    def validate(
        self,
        variant: VariantQuestion,
        source: SourceQuestion
    ) -> ValidationResult:
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
                rejection_reason=f"XML inválido: {xml_error}"
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

    def _validate_with_llm(
        self,
        variant: VariantQuestion,
        source: SourceQuestion
    ) -> ValidationResult:
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

Concepto evaluado: {json.dumps([a.get('atom_title') for a in source.primary_atoms], ensure_ascii=False)}

Dificultad: {source.difficulty.get('level', 'Medium')}
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
                temperature=0.0  # Deterministic for validation
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
                rejection_reason=f"Error de validación: {str(e)}"
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
                rejection_reason=data.get("razon_rechazo", "")
            )
        except json.JSONDecodeError:
            return ValidationResult(
                verdict=ValidationVerdict.REJECTED,
                concept_aligned=False,
                difficulty_equal=False,
                answer_correct=False,
                rejection_reason="No se pudo parsear respuesta de validación"
            )

    def _extract_question_text(self, xml_content: str) -> str:
        """Extract question text from QTI XML, properly handling MathML."""
        try:
            root = ET.fromstring(xml_content)
            # Find item body (use explicit 'is not None' to avoid Element truthiness bug)
            item_body = root.find(".//{*}qti-item-body")
            if item_body is None:
                item_body = root.find(".//{*}itemBody")
            if item_body is not None:
                return self._element_to_text(item_body)
            return ""
        except:
            return ""

    def _element_to_text(self, element: ET.Element) -> str:
        """Recursively extract text from an element, properly handling MathML."""
        parts = []

        if element.text:
            parts.append(element.text.strip())

        for child in element:
            tag = child.tag.split('}')[-1].lower()

            if tag == 'math':
                # Process MathML to readable text
                parts.append(self._mathml_to_text(child))
            elif tag in ('qti-simple-choice', 'simplechoice'):
                # Skip individual choices (we extract them separately)
                pass
            else:
                # Include qti-prompt, qti-choice-interaction, and all other elements
                parts.append(self._element_to_text(child))

            if child.tail:
                parts.append(child.tail.strip())

        return " ".join(filter(None, parts))

    def _mathml_to_text(self, math_elem: ET.Element) -> str:
        """Convert MathML element to readable text representation."""
        return self._process_mathml_element(math_elem)

    def _process_mathml_element(self, elem: ET.Element) -> str:
        """Recursively process a MathML element to text."""
        tag = elem.tag.split('}')[-1].lower()

        if tag == 'mfrac':
            # Handle fractions: numerator/denominator
            children = list(elem)
            if len(children) >= 2:
                num = self._process_mathml_element(children[0])
                den = self._process_mathml_element(children[1])
                return f"({num}/{den})"
        elif tag == 'msup':
            # Handle superscripts: base^exp
            children = list(elem)
            if len(children) >= 2:
                base = self._process_mathml_element(children[0])
                exp = self._process_mathml_element(children[1])
                return f"{base}^{exp}"
        elif tag == 'msqrt':
            # Handle square roots
            inner = "".join(self._process_mathml_element(c) for c in elem)
            return f"sqrt({inner})"
        elif tag == 'mtable':
            # Handle tables/matrices (equation systems)
            rows = []
            for child in elem:
                rows.append(self._process_mathml_element(child))
            return "\n".join(rows)
        elif tag == 'mtr':
            # Handle table rows
            cells = []
            for child in elem:
                cells.append(self._process_mathml_element(child))
            return " ".join(cells)
        elif tag == 'mtd':
            # Handle table cells
            parts = []
            for child in elem:
                parts.append(self._process_mathml_element(child))
            return "".join(parts)
        elif tag in ('mn', 'mi', 'mo', 'mtext'):
            return (elem.text or "").strip()
        elif tag in ('mrow', 'math', 'mstyle'):
            # Container elements - process children
            parts = []
            for child in elem:
                parts.append(self._process_mathml_element(child))
            return "".join(parts)
        else:
            # Default: try to get text or process children
            if elem.text:
                return elem.text.strip()
            parts = []
            for child in elem:
                parts.append(self._process_mathml_element(child))
            return "".join(parts)

    def _extract_choices(self, xml_content: str) -> list[str]:
        """Extract choice texts from QTI XML, properly handling MathML."""
        try:
            root = ET.fromstring(xml_content)
            choices = []
            for choice in root.findall(".//{*}qti-simple-choice") + root.findall(".//{*}simpleChoice"):
                choice_text = self._element_to_text(choice)
                choices.append(choice_text)
            return choices
        except:
            return []

    def _find_correct_answer(self, xml_content: str) -> str:
        """Find the correct answer from QTI XML, properly handling MathML."""
        try:
            root = ET.fromstring(xml_content)
            # Find correct response value
            # Note: Use explicit 'is not None' checks because XML Elements with no
            # children evaluate as False in boolean context (Python/ElementTree quirk)
            correct_resp = root.find(".//{*}qti-correct-response")
            if correct_resp is None:
                correct_resp = root.find(".//{*}correctResponse")
            if correct_resp is not None:
                value = correct_resp.find(".//{*}qti-value")
                if value is None:
                    value = correct_resp.find(".//{*}value")
                if value is not None and value.text:
                    correct_id = value.text.strip()
                    # Find the choice with this ID
                    for choice in root.findall(".//{*}qti-simple-choice") + root.findall(".//{*}simpleChoice"):
                        if choice.get("identifier") == correct_id:
                            return self._element_to_text(choice)
            return ""
        except:
            return ""

