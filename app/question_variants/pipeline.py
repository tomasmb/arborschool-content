"""Variant generation pipeline orchestrator.

This module orchestrates the full variant generation workflow:
1. Load source questions from finalized tests
2. Generate variants using VariantGenerator
3. Validate variants using VariantValidator
4. Save approved variants to output directory
"""

import json
import os
import re
from typing import List, Optional, Dict, Any
from dataclasses import asdict
import xml.etree.ElementTree as ET

from app.question_variants.models import (
    SourceQuestion,
    VariantQuestion,
    ValidationResult,
    PipelineConfig,
    GenerationReport,
)
from app.question_variants.variant_generator import VariantGenerator
from app.question_variants.variant_validator import VariantValidator


class VariantPipeline:
    """Orchestrates the variant generation pipeline."""
    
    # Base path for finalized tests
    FINALIZED_PATH = "app/data/pruebas/finalizadas"
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        """Initialize the pipeline.
        
        Args:
            config: Pipeline configuration. Uses defaults if not provided.
        """
        self.config = config or PipelineConfig()
        self.generator = VariantGenerator(self.config)
        self.validator = VariantValidator(self.config)
    
    def run(
        self,
        test_id: str,
        question_ids: Optional[List[str]] = None,
        num_variants: Optional[int] = None
    ) -> List[GenerationReport]:
        """Run the variant generation pipeline.
        
        Args:
            test_id: Test identifier (e.g., "Prueba-invierno-2025")
            question_ids: Specific question IDs to process. If None, processes all.
            num_variants: Override for number of variants per question.
            
        Returns:
            List of GenerationReport, one per source question.
        """
        print(f"\n{'='*60}")
        print(f"PIPELINE: Generación de Variantes")
        print(f"Test: {test_id}")
        print(f"{'='*60}\n")
        
        # Load source questions
        sources = self._load_source_questions(test_id, question_ids)
        
        if not sources:
            print("❌ No se encontraron preguntas para procesar.")
            return []
        
        print(f"📋 Cargadas {len(sources)} preguntas fuente\n")
        
        reports = []
        
        for source in sources:
            report = self._process_question(source, num_variants)
            reports.append(report)
        
        # Print summary
        self._print_summary(reports)
        
        return reports
    
    def _load_source_questions(
        self, 
        test_id: str, 
        question_ids: Optional[List[str]] = None
    ) -> List[SourceQuestion]:
        """Load source questions from disk."""
        
        test_path = os.path.join(self.FINALIZED_PATH, test_id, "qti")
        
        if not os.path.exists(test_path):
            print(f"❌ Test path not found: {test_path}")
            return []
        
        sources = []
        
        # Get question directories
        q_dirs = sorted(os.listdir(test_path))
        
        for q_dir in q_dirs:
            # Filter by question_ids if specified
            if question_ids and q_dir not in question_ids:
                continue
            
            q_path = os.path.join(test_path, q_dir)
            
            if not os.path.isdir(q_path):
                continue
            
            xml_path = os.path.join(q_path, "question.xml")
            meta_path = os.path.join(q_path, "metadata_tags.json")
            
            if not os.path.exists(xml_path) or not os.path.exists(meta_path):
                print(f"  ⚠️ Skipping {q_dir}: missing files")
                continue
            
            # Load QTI XML
            with open(xml_path, "r", encoding="utf-8") as f:
                qti_xml = f.read()
            
            # Load metadata
            with open(meta_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            
            # Extract text and choices from XML
            parsed = self._parse_qti(qti_xml)
            
            source = SourceQuestion(
                question_id=q_dir,
                test_id=test_id,
                qti_xml=qti_xml,
                metadata=metadata,
                question_text=parsed["text"],
                choices=parsed["choices"],
                correct_answer=parsed["correct_answer"],
                image_urls=parsed["image_urls"]
            )
            
            sources.append(source)
        
        return sources
    
    def _parse_qti(self, xml_content: str) -> Dict[str, Any]:
        """Parse QTI XML to extract text, choices, and images."""
        result = {
            "text": "",
            "choices": [],
            "correct_answer": "",
            "image_urls": []
        }
        
        try:
            root = ET.fromstring(xml_content)
            
            # Find correct answer ID
            correct_id = None
            correct_resp = root.find(".//{*}qti-correct-response") or root.find(".//{*}correctResponse")
            if correct_resp is not None:
                value = correct_resp.find(".//{*}qti-value") or correct_resp.find(".//{*}value")
                if value is not None and value.text:
                    correct_id = value.text.strip()
            
            # Extract question text
            item_body = root.find(".//{*}qti-item-body") or root.find(".//{*}itemBody")
            if item_body is not None:
                text_parts = []
                self._extract_text_recursive(item_body, text_parts)
                result["text"] = " ".join(filter(None, text_parts))
            
            # Extract choices
            choice_map = {}
            for choice in root.findall(".//{*}qti-simple-choice") + root.findall(".//{*}simpleChoice"):
                cid = choice.get("identifier")
                text_parts = []
                self._extract_text_recursive(choice, text_parts)
                choice_text = " ".join(filter(None, text_parts))
                result["choices"].append(choice_text)
                if cid:
                    choice_map[cid] = choice_text
            
            # Set correct answer text
            if correct_id and correct_id in choice_map:
                result["correct_answer"] = choice_map[correct_id]
            
            # Extract image URLs
            for img in root.findall(".//{*}img") + root.findall(".//{*}qti-img"):
                src = img.get("src")
                if src:
                    result["image_urls"].append(src)
            
        except ET.ParseError:
            pass
        
        return result
    
    def _extract_text_recursive(self, element: ET.Element, parts: List[str]):
        """Recursively extract text from XML element."""
        if element.text:
            parts.append(element.text.strip())
        for child in element:
            # Handle MathML specially - just get the content
            tag = child.tag.split('}')[-1].lower()
            if tag == 'math':
                self._extract_math_text(child, parts)
            else:
                self._extract_text_recursive(child, parts)
            if child.tail:
                parts.append(child.tail.strip())
    
    def _extract_math_text(self, element: ET.Element, parts: List[str]):
        """Extract text from MathML element."""
        for child in element.iter():
            tag = child.tag.split('}')[-1].lower()
            if tag in ('mn', 'mi', 'mo', 'mtext') and child.text:
                parts.append(child.text.strip())
    
    def _process_question(
        self, 
        source: SourceQuestion, 
        num_variants: Optional[int] = None
    ) -> GenerationReport:
        """Process a single source question."""
        
        print(f"\n{'─'*40}")
        print(f"Procesando: {source.question_id}")
        print(f"{'─'*40}")
        
        report = GenerationReport(
            source_question_id=source.question_id,
            source_test_id=source.test_id
        )
        
        # Generate variants
        variants = self.generator.generate_variants(source, num_variants)
        report.total_generated = len(variants)
        
        if not variants:
            report.errors.append("No se pudieron generar variantes")
            return report
        
        # Validate each variant
        approved_variants = []
        
        if self.config.validate_variants:
            for variant in variants:
                result = self.validator.validate(variant, source)
                variant.validation_result = result
                
                if result.is_approved:
                    approved_variants.append(variant)
                    report.total_approved += 1
                else:
                    report.total_rejected += 1
        else:
            # Skip validation
            approved_variants = variants
            report.total_approved = len(variants)
        
        # Save approved variants
        for variant in approved_variants:
            self._save_variant(variant, source)
            report.variants.append(variant.variant_id)
        
        # Save rejected variants if configured
        if self.config.save_rejected:
            rejected = [v for v in variants if v not in approved_variants]
            for variant in rejected:
                self._save_variant(variant, source, is_rejected=True)
        
        # Save report
        self._save_report(report)
        
        return report
    
    def _save_variant(
        self, 
        variant: VariantQuestion, 
        source: SourceQuestion,
        is_rejected: bool = False
    ):
        """Save a variant to disk."""
        
        # Build output path
        status = "rejected" if is_rejected else "approved"
        variant_path = os.path.join(
            self.config.output_dir,
            source.test_id,
            source.question_id,
            status,
            variant.variant_id
        )
        
        os.makedirs(variant_path, exist_ok=True)
        
        # Save QTI XML
        xml_path = os.path.join(variant_path, "question.xml")
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(variant.qti_xml)
        
        # Save metadata
        meta_path = os.path.join(variant_path, "metadata_tags.json")
        
        # Add validation result to metadata
        if variant.validation_result:
            variant.metadata["validation"] = {
                "verdict": variant.validation_result.verdict.value,
                "concept_aligned": variant.validation_result.concept_aligned,
                "difficulty_equal": variant.validation_result.difficulty_equal,
                "answer_correct": variant.validation_result.answer_correct,
                "calculation_steps": variant.validation_result.calculation_steps,
                "rejection_reason": variant.validation_result.rejection_reason
            }
        
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(variant.metadata, f, ensure_ascii=False, indent=2)
        
        # Save variant info
        info_path = os.path.join(variant_path, "variant_info.json")
        info = {
            "variant_id": variant.variant_id,
            "source_question_id": variant.source_question_id,
            "source_test_id": variant.source_test_id,
            "is_rejected": is_rejected
        }
        with open(info_path, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
    
    def _save_report(self, report: GenerationReport):
        """Save generation report."""
        
        report_path = os.path.join(
            self.config.output_dir,
            report.source_test_id,
            report.source_question_id,
            "generation_report.json"
        )
        
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, ensure_ascii=False, indent=2)
    
    def _print_summary(self, reports: List[GenerationReport]):
        """Print summary of pipeline run."""
        
        total_gen = sum(r.total_generated for r in reports)
        total_app = sum(r.total_approved for r in reports)
        total_rej = sum(r.total_rejected for r in reports)
        
        print(f"\n{'='*60}")
        print("RESUMEN")
        print(f"{'='*60}")
        print(f"Preguntas procesadas: {len(reports)}")
        print(f"Variantes generadas:  {total_gen}")
        print(f"Variantes aprobadas:  {total_app} ({100*total_app/total_gen:.1f}%)" if total_gen > 0 else "N/A")
        print(f"Variantes rechazadas: {total_rej}")
        print(f"\nOutput: {self.config.output_dir}")
        print(f"{'='*60}\n")
