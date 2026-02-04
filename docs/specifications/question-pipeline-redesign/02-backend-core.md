# Task 02: Backend Core Module

> **Type**: Implementation Task
> **Prerequisites**: [01-cleanup-tasks.md](./01-cleanup-tasks.md) completed
> **Estimated Sessions**: 2-3

## Context

Create the `app/question_feedback/` module that handles:
1. Feedback enhancement (Stage 1) - LLM generates complete QTI XML with feedback
2. XSD validation (Gate 1) - Validate against QTI 3.0 schema
3. Final validation (Stage 2) - LLM validates content quality
4. Pipeline orchestration - Coordinate all stages

## Acceptance Criteria

- [x] `app/question_feedback/` module created with all files
- [x] `FeedbackEnhancer` class generates complete QTI XML with feedback
- [x] XSD validation integrated with retry logic
- [x] `FinalValidator` class performs comprehensive quality checks
- [x] `QuestionPipeline` orchestrates all stages
- [x] `validation_result.json` saved after processing
- [x] `question_validated.xml` saved for successful questions
- [ ] Unit tests for all components

---

## Files to Create

```
app/question_feedback/
├── __init__.py
├── enhancer.py           # FeedbackEnhancer class (Stage 1)
├── validator.py          # FinalValidator class (Stage 2)
├── pipeline.py           # QuestionPipeline orchestrator
├── prompts.py            # PAES-specific prompts (Spanish)
├── schemas.py            # JSON schemas for structured output
├── models.py             # Pydantic models for results
└── utils/
    ├── __init__.py
    ├── qti_parser.py     # Extract info from QTI XML
    └── image_utils.py    # Image URL handling
```

---

## Task 2.1: Create Models (`models.py`)

### Implementation

```python
"""Pydantic models for question feedback pipeline results."""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel


class CheckStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"


class CheckResult(BaseModel):
    """Result of a single validation check."""
    status: CheckStatus
    issues: list[str] = []
    reasoning: str = ""


class CorrectAnswerCheck(BaseModel):
    """Result of correct answer validation."""
    status: CheckStatus
    expected_answer: str
    marked_answer: str
    verification_steps: str
    issues: list[str] = []


class ValidationResult(BaseModel):
    """Complete validation result from FinalValidator."""
    validation_result: str  # "pass" or "fail"
    correct_answer_check: CorrectAnswerCheck
    feedback_check: CheckResult
    content_quality_check: CheckResult
    image_check: CheckResult
    math_validity_check: CheckResult
    overall_reasoning: str


class EnhancementResult(BaseModel):
    """Result from FeedbackEnhancer."""
    success: bool
    qti_xml: str | None = None
    error: str | None = None
    xsd_errors: str | None = None
    attempts: int = 1


class PipelineResult(BaseModel):
    """Complete pipeline result."""
    question_id: str
    success: bool
    stage_failed: str | None = None
    error: str | None = None
    xsd_errors: str | None = None
    qti_xml_final: str | None = None
    validation_details: dict[str, Any] | None = None
    can_sync: bool = False
```

---

## Task 2.2: Create Prompts (`prompts.py`)

### Implementation

```python
"""PAES-specific prompts for feedback generation and validation (Spanish)."""
from __future__ import annotations

FEEDBACK_ENHANCEMENT_PROMPT = """
Eres un experto en educación matemática para la prueba PAES de Chile y en el formato QTI 3.0.

TAREA: Agregar retroalimentación educativa a esta pregunta de matemáticas.
Debes devolver el QTI XML COMPLETO con la retroalimentación incluida.

AUDIENCIA:
- Estudiantes de 3° y 4° medio (16-18 años)
- Preparación para PAES Matemática M1
- Nivel de lectura: claro y preciso, sin jerga innecesaria

QTI XML ORIGINAL:
```xml
{original_qti_xml}
```

{images_section}

REQUISITOS DE RETROALIMENTACIÓN:

1. DECLARACIONES DE OUTCOME (agregar después de qti-response-declaration):
```xml
<qti-outcome-declaration identifier="FEEDBACK" cardinality="single" base-type="identifier"/>
<qti-outcome-declaration identifier="SOLUTION" cardinality="single" base-type="identifier"/>
```

2. RETROALIMENTACIÓN POR OPCIÓN (dentro de cada qti-simple-choice):
```xml
<qti-feedback-inline outcome-identifier="FEEDBACK" identifier="ChoiceX" show-hide="show">
  [Prefijo automático: "¡Correcto! " o "Incorrecto. "]
  [Tu explicación de 1-3 oraciones]
</qti-feedback-inline>
```

Requisitos para cada opción:
- Opción correcta: Explica POR QUÉ es correcta matemáticamente
- Opciones incorrectas: Identifica el ERROR CONCEPTUAL específico
- NO uses "Correcto" o "Incorrecto" al inicio (ya incluido en el prefijo)
- Sé específico a ESTA pregunta, no genérico

3. SOLUCIÓN PASO A PASO (al final de qti-item-body):
```xml
<qti-feedback-block identifier="show" outcome-identifier="SOLUTION" show-hide="show">
  <qti-content-body>
    <p><strong>[Título descriptivo del método]</strong></p>
    <ol>
      <li>Paso 1: [Descripción clara]</li>
      <li>Paso 2: [Descripción clara]</li>
      <!-- 2-5 pasos total -->
    </ol>
  </qti-content-body>
</qti-feedback-block>
```

4. RESPONSE PROCESSING (reemplazar el existente):
```xml
<qti-response-processing>
  <qti-response-condition>
    <qti-response-if>
      <qti-match>
        <qti-variable identifier="RESPONSE"/>
        <qti-correct identifier="RESPONSE"/>
      </qti-match>
      <qti-set-outcome-value identifier="SCORE">
        <qti-base-value base-type="float">1</qti-base-value>
      </qti-set-outcome-value>
    </qti-response-if>
    <qti-response-else>
      <qti-set-outcome-value identifier="SCORE">
        <qti-base-value base-type="float">0</qti-base-value>
      </qti-set-outcome-value>
    </qti-response-else>
  </qti-response-condition>
  <qti-set-outcome-value identifier="FEEDBACK">
    <qti-variable identifier="RESPONSE"/>
  </qti-set-outcome-value>
  <qti-set-outcome-value identifier="SOLUTION">
    <qti-base-value base-type="identifier">show</qti-base-value>
  </qti-set-outcome-value>
</qti-response-processing>
```

REGLAS CRÍTICAS:
- Mantén TODOS los elementos originales (stem, choices, images, etc.)
- NO modifiques el contenido de la pregunta, solo agrega retroalimentación
- Usa el namespace QTI 3.0 correcto
- Asegura que el XML sea válido y bien formado
- Usa comillas dobles para atributos
- No uses caracteres especiales que rompan XML (usa entidades si es necesario)

FORMATO DE SALIDA:
Devuelve SOLO el QTI XML completo, sin markdown, sin explicaciones.
El XML debe empezar con <qti-assessment-item y terminar con </qti-assessment-item>
"""


FINAL_VALIDATION_PROMPT = """
Eres un validador experto de preguntas para la prueba PAES de Matemática M1 de Chile.
Tu trabajo es encontrar CUALQUIER error o problema en esta pregunta.

QTI XML CON RETROALIMENTACIÓN:
```xml
{qti_xml_with_feedback}
```

{images_section}

VALIDACIONES REQUERIDAS:

1. VALIDACIÓN DE RESPUESTA CORRECTA
   - ¿La respuesta marcada en <qti-correct-response> es matemáticamente correcta?
   - Resuelve el problema paso a paso para verificar
   - ¿El valor numérico/expresión es exactamente correcto?

2. VALIDACIÓN DE RETROALIMENTACIÓN
   - ¿La retroalimentación de la opción correcta explica correctamente POR QUÉ es correcta?
   - ¿La retroalimentación de cada opción incorrecta identifica el ERROR CONCEPTUAL real?
   - ¿La solución paso a paso lleva a la respuesta correcta?
   - ¿Los pasos matemáticos son correctos y completos?

3. VALIDACIÓN DE CONTENIDO
   - ¿Hay errores tipográficos?
   - ¿Hay caracteres extraños o mal codificados?
   - ¿Las expresiones matemáticas están correctas? (signos, exponentes, fracciones)
   - ¿El lenguaje es claro y apropiado para estudiantes de 3°-4° medio?

4. VALIDACIÓN DE IMÁGENES (si hay imágenes)
   - ¿Las referencias a imágenes en el enunciado tienen imagen correspondiente?
   - ¿La imagen es relevante y correcta para la pregunta?
   - ¿El alt-text describe adecuadamente la imagen?
   - ¿No hay imágenes huérfanas (presentes pero no referenciadas)?

5. VALIDACIÓN MATEMÁTICA PAES
   - ¿El contenido está dentro del temario PAES M1?
   - ¿Los valores numéricos son razonables? (no hay errores de orden de magnitud)
   - ¿Las unidades son correctas si aplica?

INSTRUCCIONES:
- Sé ESTRICTO: cualquier error debe resultar en "fail"
- Proporciona reasoning específico citando el contenido exacto
- Los issues deben ser ESPECÍFICOS y ACCIONABLES
- Si no hay imágenes, marca image_check como "not_applicable"
"""
```

---

## Task 2.3: Create Schemas (`schemas.py`)

### Implementation

```python
"""JSON schemas for structured LLM output."""
from __future__ import annotations

FINAL_VALIDATION_SCHEMA = {
    "type": "object",
    "properties": {
        "validation_result": {
            "type": "string",
            "enum": ["pass", "fail"]
        },
        "correct_answer_check": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["pass", "fail"]},
                "expected_answer": {"type": "string"},
                "marked_answer": {"type": "string"},
                "verification_steps": {"type": "string"},
                "issues": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["status", "expected_answer", "marked_answer", 
                        "verification_steps", "issues"]
        },
        "feedback_check": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["pass", "fail"]},
                "issues": {"type": "array", "items": {"type": "string"}},
                "reasoning": {"type": "string"}
            },
            "required": ["status", "issues", "reasoning"]
        },
        "content_quality_check": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["pass", "fail"]},
                "typos_found": {"type": "array", "items": {"type": "string"}},
                "character_issues": {"type": "array", "items": {"type": "string"}},
                "clarity_issues": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["status", "typos_found", "character_issues", "clarity_issues"]
        },
        "image_check": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["pass", "fail", "not_applicable"]},
                "issues": {"type": "array", "items": {"type": "string"}},
                "reasoning": {"type": "string"}
            },
            "required": ["status", "issues", "reasoning"]
        },
        "math_validity_check": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["pass", "fail"]},
                "issues": {"type": "array", "items": {"type": "string"}},
                "reasoning": {"type": "string"}
            },
            "required": ["status", "issues", "reasoning"]
        },
        "overall_reasoning": {"type": "string"}
    },
    "required": [
        "validation_result",
        "correct_answer_check",
        "feedback_check",
        "content_quality_check",
        "image_check",
        "math_validity_check",
        "overall_reasoning"
    ]
}
```

---

## Task 2.4: Create Enhancer (`enhancer.py`)

### Implementation

```python
"""Feedback enhancement using GPT 5.1."""
from __future__ import annotations

import logging

from openai import OpenAI

from app.question_feedback.models import EnhancementResult
from app.question_feedback.prompts import FEEDBACK_ENHANCEMENT_PROMPT

# Import existing XSD validator
from app.pruebas.pdf_to_qti.modules.validation.xml_validator import validate_qti_xml

logger = logging.getLogger(__name__)


class FeedbackEnhancer:
    """Enhance QTI XML with feedback using GPT 5.1."""
    
    def __init__(
        self, 
        model: str = "gpt-5.1",
        reasoning_effort: str = "medium",
        max_retries: int = 2
    ):
        self.client = OpenAI()
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.max_retries = max_retries
        self._last_xsd_errors: str | None = None
    
    def enhance(
        self,
        qti_xml: str,
        image_urls: list[str] | None = None
    ) -> EnhancementResult:
        """Generate complete QTI XML with feedback embedded."""
        
        for attempt in range(self.max_retries + 1):
            logger.info(f"Enhancement attempt {attempt + 1}/{self.max_retries + 1}")
            
            # Build prompt
            images_section = ""
            if image_urls:
                images_section = f"IMÁGENES: {len(image_urls)} imagen(es) adjuntas."
            
            prompt = FEEDBACK_ENHANCEMENT_PROMPT.format(
                original_qti_xml=qti_xml,
                images_section=images_section
            )
            
            # Add XSD errors if this is a retry
            if attempt > 0 and self._last_xsd_errors:
                prompt += f"\n\nERRORES XSD DEL INTENTO ANTERIOR:\n{self._last_xsd_errors}\n"
                prompt += "Por favor corrige estos errores en tu respuesta."
            
            # Call GPT 5.1
            content = self._build_content(prompt, image_urls)
            
            response = self.client.chat.completions.create(
                model=self.model,
                reasoning_effort=self.reasoning_effort,
                messages=[{"role": "user", "content": content}]
            )
            
            enhanced_xml = self._extract_xml(response.choices[0].message.content or "")
            
            # XSD Validation immediately
            xsd_result = validate_qti_xml(enhanced_xml)
            
            if xsd_result.get("valid"):
                logger.info("XSD validation passed")
                return EnhancementResult(
                    success=True,
                    qti_xml=enhanced_xml,
                    attempts=attempt + 1
                )
            
            # Store errors for retry
            self._last_xsd_errors = str(xsd_result.get("validation_errors", "Unknown error"))
            logger.warning(f"XSD validation failed: {self._last_xsd_errors}")
            
            if attempt == self.max_retries:
                return EnhancementResult(
                    success=False,
                    error=f"XSD validation failed after {attempt + 1} attempts",
                    xsd_errors=self._last_xsd_errors,
                    attempts=attempt + 1
                )
        
        return EnhancementResult(success=False, error="Max retries exceeded")
    
    def _build_content(
        self, 
        prompt: str, 
        image_urls: list[str] | None
    ) -> list[dict]:
        """Build message content with optional images."""
        content: list[dict] = [{"type": "text", "text": prompt}]
        if image_urls:
            for url in image_urls:
                content.append({"type": "image_url", "image_url": {"url": url}})
        return content
    
    def _extract_xml(self, response_text: str) -> str:
        """Extract QTI XML from response, handling any wrapping."""
        text = response_text.strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]  # Remove first line (```xml or ```)
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]  # Remove last line (```)
            text = "\n".join(lines)
        
        # Ensure it starts with the QTI element
        if "<qti-assessment-item" in text:
            start = text.index("<qti-assessment-item")
            end = text.rindex("</qti-assessment-item>") + len("</qti-assessment-item>")
            text = text[start:end]
        
        return text.strip()
```

---

## Task 2.5: Create Validator (`validator.py`)

### Implementation

```python
"""Final LLM validation for PAES questions."""
from __future__ import annotations

import json
import logging

from openai import OpenAI

from app.question_feedback.models import ValidationResult
from app.question_feedback.prompts import FINAL_VALIDATION_PROMPT
from app.question_feedback.schemas import FINAL_VALIDATION_SCHEMA

logger = logging.getLogger(__name__)


class FinalValidator:
    """Final LLM validation for PAES questions using GPT 5.1."""
    
    def __init__(
        self,
        model: str = "gpt-5.1",
        reasoning_effort: str = "high"
    ):
        self.client = OpenAI()
        self.model = model
        self.reasoning_effort = reasoning_effort
    
    def validate(
        self,
        qti_xml_with_feedback: str,
        image_urls: list[str] | None = None
    ) -> ValidationResult:
        """Perform comprehensive validation."""
        
        images_section = ""
        if image_urls:
            images_section = f"IMÁGENES: {len(image_urls)} imagen(es) adjuntas para validación."
        
        prompt = FINAL_VALIDATION_PROMPT.format(
            qti_xml_with_feedback=qti_xml_with_feedback,
            images_section=images_section
        )
        
        content = self._build_content(prompt, image_urls)
        
        logger.info("Running final validation with GPT 5.1 (high reasoning)")
        
        response = self.client.chat.completions.create(
            model=self.model,
            reasoning_effort=self.reasoning_effort,
            messages=[{"role": "user", "content": content}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "final_validation",
                    "schema": FINAL_VALIDATION_SCHEMA,
                    "strict": True
                }
            }
        )
        
        result = json.loads(response.choices[0].message.content or "{}")
        logger.info(f"Validation result: {result.get('validation_result')}")
        
        return ValidationResult(**result)
    
    def _build_content(
        self, 
        prompt: str, 
        image_urls: list[str] | None
    ) -> list[dict]:
        """Build message content with optional images."""
        content: list[dict] = [{"type": "text", "text": prompt}]
        if image_urls:
            for url in image_urls:
                content.append({"type": "image_url", "image_url": {"url": url}})
        return content
```

---

## Task 2.6: Create Pipeline Orchestrator (`pipeline.py`)

### Implementation

```python
"""Question processing pipeline orchestrator."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from app.question_feedback.enhancer import FeedbackEnhancer
from app.question_feedback.models import PipelineResult
from app.question_feedback.validator import FinalValidator

logger = logging.getLogger(__name__)


class QuestionPipeline:
    """Complete question processing pipeline with validation gates."""
    
    def __init__(self):
        self.enhancer = FeedbackEnhancer()  # GPT 5.1, medium reasoning
        self.validator = FinalValidator()    # GPT 5.1, high reasoning
    
    def process(
        self,
        question_id: str,
        qti_xml: str,
        image_urls: list[str] | None = None,
        output_dir: Path | None = None
    ) -> PipelineResult:
        """Process a question through the complete pipeline."""
        
        logger.info(f"Processing question: {question_id}")
        
        # ─────────────────────────────────────────────────────────────
        # STAGE 1: Feedback Enhancement + XSD Validation
        # ─────────────────────────────────────────────────────────────
        enhancement = self.enhancer.enhance(qti_xml, image_urls)
        
        if not enhancement.success:
            result = PipelineResult(
                question_id=question_id,
                success=False,
                stage_failed="feedback_enhancement",
                error=enhancement.error,
                xsd_errors=enhancement.xsd_errors,
                can_sync=False
            )
            if output_dir:
                self._save_result(output_dir, result)
            return result
        
        qti_with_feedback = enhancement.qti_xml
        
        # ─────────────────────────────────────────────────────────────
        # STAGE 2: Final LLM Validation
        # ─────────────────────────────────────────────────────────────
        validation = self.validator.validate(qti_with_feedback, image_urls)
        
        if validation.validation_result != "pass":
            result = PipelineResult(
                question_id=question_id,
                success=False,
                stage_failed="final_validation",
                validation_details=validation.model_dump(),
                can_sync=False
            )
            if output_dir:
                self._save_result(output_dir, result)
            return result
        
        # ─────────────────────────────────────────────────────────────
        # SUCCESS: Ready for sync
        # ─────────────────────────────────────────────────────────────
        result = PipelineResult(
            question_id=question_id,
            success=True,
            qti_xml_final=qti_with_feedback,
            validation_details=validation.model_dump(),
            can_sync=True
        )
        
        if output_dir:
            self._save_result(output_dir, result)
            self._save_validated_xml(output_dir, qti_with_feedback)
        
        logger.info(f"Question {question_id} processed successfully")
        return result
    
    def _save_result(self, output_dir: Path, result: PipelineResult) -> None:
        """Save validation result to JSON file."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        result_data = {
            "question_id": result.question_id,
            "pipeline_version": "2.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": result.success,
            "stage_failed": result.stage_failed,
            "error": result.error,
            "xsd_errors": result.xsd_errors,
            "validation_details": result.validation_details,
            "can_sync": result.can_sync,
            "validated_qti_path": "question_validated.xml" if result.success else None
        }
        
        result_path = output_dir / "validation_result.json"
        with open(result_path, "w") as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved validation result to {result_path}")
    
    def _save_validated_xml(self, output_dir: Path, qti_xml: str) -> None:
        """Save validated QTI XML to file."""
        xml_path = output_dir / "question_validated.xml"
        with open(xml_path, "w") as f:
            f.write(qti_xml)
        
        logger.info(f"Saved validated QTI to {xml_path}")
```

---

## Task 2.7: Create Utility Modules

### utils/qti_parser.py

```python
"""Utilities for parsing QTI XML."""
from __future__ import annotations

from xml.etree import ElementTree as ET


def extract_correct_answer(qti_xml: str) -> str | None:
    """Extract correct answer identifier from QTI XML."""
    try:
        root = ET.fromstring(qti_xml)
        ns = {"qti": "http://www.imsglobal.org/xsd/imsqtiasi_v3p0"}
        correct = root.find(".//qti:qti-correct-response/qti:qti-value", ns)
        return correct.text if correct is not None else None
    except ET.ParseError:
        return None


def extract_title(qti_xml: str) -> str | None:
    """Extract title from QTI XML."""
    try:
        root = ET.fromstring(qti_xml)
        return root.get("title")
    except ET.ParseError:
        return None


def has_feedback(qti_xml: str) -> bool:
    """Check if QTI XML contains feedback elements."""
    return "<qti-feedback-inline" in qti_xml or "<qti-feedback-block" in qti_xml
```

### utils/image_utils.py

```python
"""Utilities for handling question images."""
from __future__ import annotations

import re


def extract_image_urls(qti_xml: str) -> list[str]:
    """Extract all image URLs from QTI XML."""
    pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
    return re.findall(pattern, qti_xml)


def is_s3_url(url: str) -> bool:
    """Check if URL is an S3 URL."""
    return "s3.amazonaws.com" in url or url.startswith("s3://")
```

---

## Summary Checklist

```
[x] 2.1 Create app/question_feedback/__init__.py
[x] 2.1 Create app/question_feedback/models.py
[x] 2.2 Create app/question_feedback/prompts.py
[x] 2.3 Create app/question_feedback/schemas.py
[x] 2.4 Create app/question_feedback/enhancer.py
[x] 2.5 Create app/question_feedback/validator.py
[x] 2.6 Create app/question_feedback/pipeline.py
[x] 2.7 Create app/question_feedback/utils/__init__.py
[x] 2.7 Create app/question_feedback/utils/qti_parser.py
[x] 2.7 Create app/question_feedback/utils/image_utils.py
[ ] Write unit tests for FeedbackEnhancer
[ ] Write unit tests for FinalValidator
[ ] Write integration test for QuestionPipeline
[ ] Test with a real question (dry run)
```
