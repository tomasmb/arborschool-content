"""Validator - Validates generated QTI XML for extraction quality.

This is the fourth step in the pipeline: QTI XML → Validated QTI.

Validates extraction quality (was content correctly parsed from PDF),
NOT assessment completeness (answer keys, feedback, etc.).
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

# Import from parent package
try:
    from models import (
        GeneratorOutput, QTIItem, ModelProvider, ValidatorOutput,
        QTIValidationOutput,
    )
    from services import create_ai_client, QTIValidatorService
except ImportError:
    from ..models import (
        GeneratorOutput, QTIItem, ModelProvider, ValidatorOutput,
        QTIValidationOutput,
    )
    from ..services import create_ai_client, QTIValidatorService

logger = logging.getLogger(__name__)


class Validator:
    """
    Validates QTI 3.0 XML extraction quality.
    
    For each QTI item:
    1. Validates content completeness (stem, choices, etc.)
    2. Validates structure (itemBody, interaction elements)
    3. Validates parse quality (no artifacts, encoding issues)
    4. Optionally validates media (images match context)
    
    Focus is on extraction quality, NOT assessment completeness.
    """
    
    def __init__(
        self, 
        model_provider: ModelProvider = "gemini",
    ):
        """
        Initialize validator.
        
        Args:
            model_provider: AI provider to use ("gemini", "gpt", or "opus")
        """
        self.model_provider = model_provider
        self.ai_client = create_ai_client(model_provider)
        self.validator_service = QTIValidatorService(
            ai_client=self.ai_client,
            model_provider=model_provider,
        )
    
    def validate(
        self,
        generator_output: GeneratorOutput,
        output_dir: Optional[str] = None,
        images: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> ValidatorOutput:
        """
        Validate all QTI items in the generator output.
        
        Args:
            generator_output: Output from Generator with QTI items
            output_dir: Optional directory to save validation results
            images: Optional dict mapping question_id to list of images
            
        Returns:
            ValidatorOutput with validation results for each item
        """
        if not generator_output.success:
            return ValidatorOutput(
                success=False,
                validation_results=[],
                errors=["Generator output indicates failure"] + generator_output.errors
            )
        
        logger.info(
            f"Validating {len(generator_output.qti_items)} QTI items "
            f"using {self.model_provider}..."
        )
        
        images = images or {}
        validation_results = []
        valid_count = 0
        invalid_count = 0
        errors = []
        
        for qti_item in generator_output.qti_items:
            try:
                # Get images for this question if provided
                item_images = images.get(qti_item.question_id, [])
                
                result = self.validator_service.validate(
                    qti_xml=qti_item.qti_xml,
                    images=item_images,
                    question_id=qti_item.question_id,
                )
                
                validation_results.append(result)
                
                if result.is_valid:
                    valid_count += 1
                    logger.info(f"✓ {qti_item.question_id}: valid (score: {result.overall_score})")
                else:
                    invalid_count += 1
                    issues = []
                    if not result.content_completeness.passed:
                        issues.extend(result.content_completeness.issues)
                    if not result.structure_validity.passed:
                        issues.extend(result.structure_validity.issues)
                    if not result.parse_quality.passed:
                        issues.extend(result.parse_quality.issues)
                    logger.warning(
                        f"✗ {qti_item.question_id}: invalid (score: {result.overall_score}) "
                        f"- {', '.join(issues[:3])}"
                    )
                
            except Exception as e:
                error_msg = f"Question {qti_item.question_id} validation failed: {e}"
                logger.error(f"✗ {error_msg}")
                errors.append(error_msg)
                invalid_count += 1
        
        success = valid_count > 0
        
        output = ValidatorOutput(
            success=success,
            validation_results=validation_results,
            valid_count=valid_count,
            invalid_count=invalid_count,
            errors=errors
        )
        
        logger.info(
            f"Validation complete: {valid_count} valid, {invalid_count} invalid"
        )
        
        # Save results
        if output_dir:
            self._save_results(output, output_dir)
        
        return output
    
    def validate_from_files(
        self,
        qti_dir: str,
        output_dir: Optional[str] = None,
        images: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> ValidatorOutput:
        """
        Validate QTI files from a directory.
        
        Args:
            qti_dir: Directory containing QTI XML files
            output_dir: Optional output directory
            images: Optional dict mapping question_id to list of images
            
        Returns:
            ValidatorOutput
        """
        qti_path = Path(qti_dir)
        if not qti_path.exists():
            raise FileNotFoundError(f"QTI directory not found: {qti_path}")
        
        # Load QTI files into GeneratorOutput format
        qti_items = []
        for xml_file in qti_path.glob("*.xml"):
            with open(xml_file, 'r') as f:
                qti_xml = f.read()
            
            qti_items.append(QTIItem(
                question_id=xml_file.stem,
                qti_xml=qti_xml,
            ))
        
        if not qti_items:
            return ValidatorOutput(
                success=False,
                validation_results=[],
                errors=[f"No QTI files found in {qti_dir}"]
            )
        
        generator_output = GeneratorOutput(
            success=True,
            qti_items=qti_items,
        )
        
        return self.validate(generator_output, output_dir, images)
    
    def validate_from_json(
        self,
        json_path: str,
        output_dir: Optional[str] = None,
        images: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> ValidatorOutput:
        """
        Validate from a generator_output.json file.
        
        Args:
            json_path: Path to generator_output.json file
            output_dir: Optional output directory
            images: Optional dict mapping question_id to list of images
            
        Returns:
            ValidatorOutput
        """
        json_path = Path(json_path)
        if not json_path.exists():
            raise FileNotFoundError(f"JSON file not found: {json_path}")
        
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        generator_output = GeneratorOutput(**data)
        return self.validate(generator_output, output_dir, images)
    
    def _save_results(self, output: ValidatorOutput, output_dir: str) -> None:
        """Save validation results to files."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save full validation output
        validation_path = output_path / "validation_output.json"
        with open(validation_path, 'w') as f:
            json.dump(output.model_dump(), f, indent=2)
        logger.info(f"Saved validation results to: {validation_path}")
        
        # Save summary report
        summary = {
            "total": len(output.validation_results),
            "valid": output.valid_count,
            "invalid": output.invalid_count,
            "success_rate": (
                f"{(output.valid_count / len(output.validation_results) * 100):.1f}%"
                if output.validation_results else "N/A"
            ),
            "questions": []
        }
        
        for result in output.validation_results:
            summary["questions"].append({
                "id": result.question_id,
                "valid": result.is_valid,
                "score": result.overall_score,
                "type": result.detected_question_type,
                "issues": (
                    result.content_completeness.issues +
                    result.structure_validity.issues +
                    result.parse_quality.issues
                )[:5]  # Limit issues for readability
            })
        
        summary_path = output_path / "validation_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Saved validation summary to: {summary_path}")

