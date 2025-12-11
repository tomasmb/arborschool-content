"""Generator - Converts segmented questions to QTI XML.

This is the third step in the pipeline: Segmented Questions → QTI XML.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Import from parent package
try:
    from models import (
        SegmenterOutput, GeneratorOutput, QTIItem, 
        QuestionChunk, SharedContext, ModelProvider, SourceFormat
    )
    from services import (
        create_ai_client, QTIService, XSDValidator,
        SemanticValidator, QuestionTypeDetector
    )
except ImportError:
    from ..models import (
        SegmenterOutput, GeneratorOutput, QTIItem, 
        QuestionChunk, SharedContext, ModelProvider, SourceFormat
    )
    from ..services import (
        create_ai_client, QTIService, XSDValidator,
        SemanticValidator, QuestionTypeDetector
    )

logger = logging.getLogger(__name__)


class Generator:
    """
    Generates QTI 3.0 XML from segmented questions.
    
    For each question:
    1. Detect question type (if not already detected)
    2. Generate QTI XML
    3. Validate XSD compliance
    4. Validate semantic fidelity
    """
    
    def __init__(
        self, 
        model_provider: ModelProvider = "gemini",
        skip_validation: bool = False
    ):
        """
        Initialize generator.
        
        Args:
            model_provider: AI provider to use ("gemini", "gpt", or "opus")
            skip_validation: If True, skip XSD and semantic validation
        """
        self.model_provider = model_provider
        self.skip_validation = skip_validation
        
        self.ai_client = create_ai_client(model_provider)
        self.question_type_detector = QuestionTypeDetector(self.ai_client)
        self.qti_service = QTIService(self.ai_client)
        self.xsd_validator = XSDValidator()
        self.semantic_validator = SemanticValidator(self.ai_client)
    
    def generate(
        self,
        segmenter_output: SegmenterOutput,
        output_dir: Optional[str] = None,
        source_format: SourceFormat = "markdown"
    ) -> GeneratorOutput:
        """
        Generate QTI XML for all validated questions.
        
        Args:
            segmenter_output: Output from Segmenter
            output_dir: Optional directory to save QTI files
            source_format: Input format ("markdown" or "html")
            
        Returns:
            GeneratorOutput with QTI items and any errors
        """
        if not segmenter_output.success:
            return GeneratorOutput(
                success=False,
                qti_items=[],
                errors=["Segmenter output indicates failure"] + segmenter_output.errors
            )
        
        logger.info(
            f"Generating QTI for {len(segmenter_output.validated_questions)} questions "
            f"using {self.model_provider}..."
        )
        
        # Build shared context map
        shared_contexts_map = {
            ctx.id: ctx for ctx in segmenter_output.shared_contexts
        }
        
        qti_items = []
        errors = []
        
        for question in segmenter_output.validated_questions:
            try:
                qti_item = self._process_question(
                    question, 
                    shared_contexts_map, 
                    source_format
                )
                qti_items.append(qti_item)
                logger.info(f"✓ Generated QTI for {question.id}")
                
            except Exception as e:
                error_msg = f"Question {question.id} failed: {e}"
                logger.error(f"✗ {error_msg}")
                errors.append(error_msg)
        
        success = len(qti_items) > 0
        
        output = GeneratorOutput(
            success=success,
            qti_items=qti_items,
            errors=errors
        )
        
        logger.info(
            f"Generation complete: {len(qti_items)} successful, {len(errors)} failed"
        )
        
        # Save results
        if output_dir:
            self._save_results(output, output_dir)
        
        return output
    
    def generate_from_json(
        self,
        json_path: str,
        output_dir: Optional[str] = None,
        source_format: SourceFormat = "markdown"
    ) -> GeneratorOutput:
        """
        Generate QTI from a segmented.json file.
        
        Args:
            json_path: Path to segmented.json file
            output_dir: Optional output directory
            source_format: Input format
            
        Returns:
            GeneratorOutput
        """
        json_path = Path(json_path)
        if not json_path.exists():
            raise FileNotFoundError(f"JSON file not found: {json_path}")
        
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        segmenter_output = SegmenterOutput(**data)
        return self.generate(segmenter_output, output_dir, source_format)
    
    def _process_question(
        self,
        question: QuestionChunk,
        shared_contexts: Dict[str, SharedContext],
        source_format: SourceFormat
    ) -> QTIItem:
        """Process a single question through the generation pipeline."""
        
        # Step 1: Detect question type (if not already detected)
        question_type = question.question_type
        if not question_type:
            logger.info(f"  Detecting question type for {question.id}...")
            detection_result = self.question_type_detector.detect(question, source_format)
            
            if not detection_result.get("success"):
                raise ValueError(
                    f"Question type detection failed: "
                    f"{detection_result.get('error', 'Unknown error')}"
                )
            
            if not detection_result.get("can_represent"):
                raise ValueError(
                    f"Cannot represent in QTI 3.0: "
                    f"{detection_result.get('reason', 'Unknown reason')}"
                )
            
            question_type = detection_result.get("question_type", "choice")
            logger.info(f"  Detected type: {question_type}")
        
        # Step 2: Generate QTI XML
        logger.info(f"  Generating QTI XML for {question.id}...")
        qti_item = self.qti_service.generate(
            question, shared_contexts, question_type, source_format
        )
        
        if self.skip_validation:
            return qti_item
        
        # Step 3: Validate XSD
        logger.info(f"  Validating XSD for {question.id}...")
        is_valid_xsd, xsd_error = self.xsd_validator.validate(qti_item.qti_xml)
        
        if not is_valid_xsd:
            raise ValueError(f"XSD validation failed: {xsd_error}")
        
        # Step 4: Semantic Validation
        logger.info(f"  Validating semantics for {question.id}...")
        semantic_result = self.semantic_validator.validate(
            source_content=question.content,
            xml=qti_item.qti_xml,
            source_format=source_format
        )
        
        if not semantic_result.is_valid:
            error_msg = (
                f"Semantic validation failed (fidelity: {semantic_result.fidelity_score}/100): "
                + "; ".join(semantic_result.errors)
            )
            raise ValueError(error_msg)
        
        logger.info(
            f"  ✓ Validated (fidelity: {semantic_result.fidelity_score}/100)"
        )
        
        return qti_item
    
    def _save_results(self, output: GeneratorOutput, output_dir: str) -> None:
        """Save QTI generation results to files."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save full generator output
        generator_path = output_path / "generator_output.json"
        with open(generator_path, 'w') as f:
            json.dump(output.model_dump(), f, indent=2)
        logger.info(f"Saved generator output to: {generator_path}")
        
        # Save individual QTI files
        qti_dir = output_path / "qti"
        qti_dir.mkdir(exist_ok=True)
        
        for item in output.qti_items:
            qti_path = qti_dir / f"{item.question_id}.xml"
            with open(qti_path, 'w') as f:
                f.write(item.qti_xml)
        
        logger.info(f"Saved {len(output.qti_items)} QTI files to: {qti_dir}")

