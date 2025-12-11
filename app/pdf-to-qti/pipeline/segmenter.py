"""Segmenter - Splits parsed PDF into individual questions.

This is the second step in the pipeline: Parsed JSON → Segmented Questions.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Import from parent package
try:
    from models import ParsedPdf, SegmenterOutput, ModelProvider
    from services import create_ai_client, SpatialSegmentationService, SplitValidator
except ImportError:
    from ..models import ParsedPdf, SegmenterOutput, ModelProvider
    from ..services import create_ai_client, SpatialSegmentationService, SplitValidator

logger = logging.getLogger(__name__)


class Segmenter:
    """
    Segments parsed PDF content into individual questions.
    
    Uses AI to:
    1. Identify question boundaries using line numbers
    2. Extract shared contexts (passages, figures for multiple questions)
    3. Validate that each question is self-contained
    """
    
    def __init__(self, model_provider: ModelProvider = "gemini"):
        """
        Initialize segmenter.
        
        Args:
            model_provider: AI provider to use ("gemini", "gpt", or "opus")
        """
        self.model_provider = model_provider
        self.ai_client = create_ai_client(model_provider)
        self.segmentation_service = SpatialSegmentationService(self.ai_client)
        self.split_validator = SplitValidator(self.ai_client)
    
    def segment(
        self,
        parsed_data: Dict[str, Any],
        output_dir: Optional[str] = None,
        save_individual_questions: bool = True
    ) -> SegmenterOutput:
        """
        Segment parsed PDF into individual questions.
        
        Args:
            parsed_data: Parsed PDF data (from PDFParser or loaded JSON)
            output_dir: Optional directory to save segmentation results
            save_individual_questions: If True, save each question as Q1.md, Q2.md, etc.
            
        Returns:
            SegmenterOutput with validated questions and any errors
        """
        logger.info(f"Starting segmentation using {self.model_provider}...")
        
        # Validate input structure
        parsed_pdf = ParsedPdf(**parsed_data)
        
        logger.info(f"Input: {len(parsed_pdf.chunks)} chunks")
        
        try:
            # Step 1 & 2: Extract and segment
            segmentation_result = self.segmentation_service.segment(
                parsed_pdf,
                raw_parsed_pdf_data=parsed_data
            )
            
            logger.info(
                f"Segmented into {len(segmentation_result.questions)} questions, "
                f"{len(segmentation_result.shared_contexts)} shared contexts"
            )
            
            # Step 3: Validate splits
            logger.info("Validating splits...")
            validation_result = self.split_validator.validate(
                segmentation_result.questions,
                segmentation_result.shared_contexts
            )
            
            # Separate validated and unvalidated questions
            validated_questions = []
            unvalidated_questions = []
            errors = []
            
            question_map = {q.id: q for q in segmentation_result.questions}
            
            for result in validation_result.validation_results:
                question = question_map.get(result.question_id)
                if not question:
                    continue
                    
                if result.is_self_contained:
                    validated_questions.append(question)
                else:
                    unvalidated_questions.append(question)
                    errors.extend([
                        f"Question {result.question_id}: {error}"
                        for error in result.errors
                    ])
            
            success = len(validated_questions) > 0
            
            output = SegmenterOutput(
                success=success,
                shared_contexts=segmentation_result.shared_contexts,
                validated_questions=validated_questions,
                unvalidated_questions=unvalidated_questions,
                errors=errors
            )
            
            logger.info(
                f"Segmentation complete: {len(validated_questions)} valid, "
                f"{len(unvalidated_questions)} invalid"
            )
            
            # Save results
            if output_dir:
                self._save_results(output, output_dir, save_individual_questions)
            
            return output
            
        except Exception as e:
            logger.error(f"Segmentation failed: {e}")
            return SegmenterOutput(
                success=False,
                shared_contexts=[],
                validated_questions=[],
                unvalidated_questions=[],
                errors=[str(e)]
            )
    
    def segment_from_json(
        self,
        json_path: str,
        output_dir: Optional[str] = None,
        save_individual_questions: bool = True
    ) -> SegmenterOutput:
        """
        Segment from a parsed.json file.
        
        Args:
            json_path: Path to parsed.json file
            output_dir: Optional output directory
            save_individual_questions: Whether to save individual question files
            
        Returns:
            SegmenterOutput
        """
        json_path = Path(json_path)
        if not json_path.exists():
            raise FileNotFoundError(f"JSON file not found: {json_path}")
        
        with open(json_path, 'r') as f:
            parsed_data = json.load(f)
        
        return self.segment(parsed_data, output_dir, save_individual_questions)
    
    def _save_results(
        self,
        output: SegmenterOutput,
        output_dir: str,
        save_individual_questions: bool
    ) -> None:
        """Save segmentation results to files."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save full segmentation output
        segmented_path = output_path / "segmented.json"
        with open(segmented_path, 'w') as f:
            json.dump(output.model_dump(), f, indent=2)
        logger.info(f"Saved segmentation results to: {segmented_path}")
        
        # Save individual question files
        if save_individual_questions:
            questions_dir = output_path / "questions"
            questions_dir.mkdir(exist_ok=True)
            
            for question in output.validated_questions:
                question_path = questions_dir / f"{question.id}.md"
                content = question.content
                
                # Add shared context if present
                if question.shared_context_id:
                    for ctx in output.shared_contexts:
                        if ctx.id == question.shared_context_id:
                            content = f"## Shared Context\n\n{ctx.content}\n\n---\n\n## Question\n\n{content}"
                            break
                
                with open(question_path, 'w') as f:
                    f.write(content)
            
            logger.info(f"Saved {len(output.validated_questions)} question files to: {questions_dir}")

