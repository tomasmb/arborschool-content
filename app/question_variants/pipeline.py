"""Variant generation pipeline orchestrator.

This module orchestrates the full variant generation workflow:
1. Load source questions from finalized tests
2. Generate variants using VariantGenerator
3. Enhance variants with feedback using QuestionPipeline
4. Validate variants using VariantValidator (semantic checks)
5. Save approved variants to output directory
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict
from datetime import datetime, timezone
from typing import List, Optional

from app.question_feedback.pipeline import QuestionPipeline
from app.question_generation.progress import report_progress
from app.question_feedback.utils.image_utils import extract_image_urls
from app.question_variants.models import (
    GenerationReport,
    PipelineConfig,
    SourceQuestion,
    VariantQuestion,
    VariantResult,
)
from app.question_variants.variant_generator import VariantGenerator
from app.question_variants.variant_validator import VariantValidator
from app.utils.qti_extractor import parse_qti_xml

logger = logging.getLogger(__name__)


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
        self.feedback_pipeline = QuestionPipeline()

    def run(self, test_id: str, question_ids: Optional[List[str]] = None, num_variants: Optional[int] = None) -> List[GenerationReport]:
        """Run the variant generation pipeline.

        Args:
            test_id: Test identifier (e.g., "prueba-invierno-2025")
            question_ids: Specific question IDs to process. If None, processes all.
            num_variants: Override for number of variants per question.

        Returns:
            List of GenerationReport, one per source question.
        """
        print(f"\n{'=' * 60}")
        print("PIPELINE: Generación de Variantes")
        print(f"Test: {test_id}")
        print(f"{'=' * 60}\n")

        # Load source questions
        sources = self._load_source_questions(test_id, question_ids)

        if not sources:
            print("❌ No se encontraron preguntas para procesar.")
            return []

        print(f"📋 Cargadas {len(sources)} preguntas fuente\n")

        reports = []
        total = len(sources)
        report_progress(0, total)

        for i, source in enumerate(sources):
            report = self._process_question(source, num_variants)
            reports.append(report)
            report_progress(i + 1, total)

        # Print summary
        self._print_summary(reports)

        return reports

    def _load_source_questions(self, test_id: str, question_ids: Optional[List[str]] = None) -> List[SourceQuestion]:
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

            # Extract text and choices from XML using shared utility
            parsed = parse_qti_xml(qti_xml)

            source = SourceQuestion(
                question_id=q_dir,
                test_id=test_id,
                qti_xml=qti_xml,
                metadata=metadata,
                question_text=parsed.text,
                choices=parsed.choices,
                correct_answer=parsed.correct_answer_text or "",
                image_urls=parsed.image_urls,
            )

            sources.append(source)

        return sources

    def _process_question(self, source: SourceQuestion, num_variants: Optional[int] = None) -> GenerationReport:
        """Process a single source question.

        Pipeline flow for each variant:
        1. Generate raw variant QTI XML
        2. Enhance with feedback via QuestionPipeline (includes XSD validation)
        3. Validate semantics via VariantValidator (concept alignment, difficulty)
        4. Save only variants passing all validation stages
        """
        print(f"\n{'─' * 40}")
        print(f"Procesando: {source.question_id}")
        print(f"{'─' * 40}")

        report = GenerationReport(source_question_id=source.question_id, source_test_id=source.test_id)

        # Generate variants (raw QTI without feedback)
        variants = self.generator.generate_variants(source, num_variants)
        report.total_generated = len(variants)

        if not variants:
            report.errors.append("No se pudieron generar variantes")
            return report

        # Process each variant through feedback pipeline + semantic validation
        approved_variants: list[VariantQuestion] = []
        variant_results: dict[str, VariantResult] = {}

        for variant in variants:
            result = self._process_variant_through_pipeline(variant, source)
            variant_results[variant.variant_id] = result

            if result.success and result.qti_xml:
                # Update variant with enriched QTI XML
                variant.qti_xml = result.qti_xml

                # Run semantic validation (concept alignment, difficulty)
                if self.config.validate_variants:
                    semantic_result = self.validator.validate(variant, source)
                    variant.validation_result = semantic_result

                    if semantic_result.is_approved:
                        approved_variants.append(variant)
                        report.total_approved += 1
                    else:
                        report.total_rejected += 1
                        logger.warning(
                            f"Variant {variant.variant_id} failed semantic validation: "
                            f"{semantic_result.rejection_reason}"
                        )
                else:
                    # Skip semantic validation
                    approved_variants.append(variant)
                    report.total_approved += 1
            else:
                report.total_rejected += 1
                logger.warning(
                    f"Variant {variant.variant_id} failed feedback pipeline: "
                    f"stage={result.stage_failed}, error={result.error}"
                )

        # Save approved variants
        for variant in approved_variants:
            self._save_variant(variant, source, variant_results.get(variant.variant_id))
            report.variants.append(variant.variant_id)

        # Save rejected variants if configured
        if self.config.save_rejected:
            rejected = [v for v in variants if v not in approved_variants]
            for variant in rejected:
                self._save_variant(
                    variant, source, variant_results.get(variant.variant_id), is_rejected=True
                )

        # Save report
        self._save_report(report)

        return report

    def _process_variant_through_pipeline(
        self, variant: VariantQuestion, source: SourceQuestion
    ) -> VariantResult:
        """Process a variant through the feedback enhancement pipeline.

        Args:
            variant: The variant to process.
            source: The source question (for context).

        Returns:
            VariantResult with success status and enriched QTI XML if successful.
        """
        print(f"    📝 Processing {variant.variant_id} through feedback pipeline...")

        # Extract image URLs from variant QTI
        image_urls = extract_image_urls(variant.qti_xml)

        # Run through feedback pipeline (enhancement + XSD + content validation)
        pipeline_result = self.feedback_pipeline.process(
            question_id=variant.variant_id,
            qti_xml=variant.qti_xml,
            image_urls=image_urls if image_urls else None,
            output_dir=None,  # Don't save intermediate results
        )

        if not pipeline_result.success:
            print(f"    ❌ {variant.variant_id} failed: {pipeline_result.stage_failed}")
            return VariantResult(
                success=False,
                variant_id=variant.variant_id,
                error=pipeline_result.error,
                stage_failed=pipeline_result.stage_failed,
                validation_details=pipeline_result.validation_details,
            )

        print(f"    ✅ {variant.variant_id} passed feedback pipeline")
        return VariantResult(
            success=True,
            variant_id=variant.variant_id,
            qti_xml=pipeline_result.qti_xml_final,
            validation_details=pipeline_result.validation_details,
        )

    def _save_variant(
        self,
        variant: VariantQuestion,
        source: SourceQuestion,
        pipeline_result: VariantResult | None = None,
        is_rejected: bool = False,
    ) -> None:
        """Save a variant to disk.

        Args:
            variant: The variant to save.
            source: The source question.
            pipeline_result: Result from feedback pipeline (for validation_result.json).
            is_rejected: Whether this variant was rejected.
        """
        # Build output path
        status = "rejected" if is_rejected else "approved"
        variant_path = os.path.join(
            self.config.output_dir, source.test_id, source.question_id, status, variant.variant_id
        )

        os.makedirs(variant_path, exist_ok=True)

        # Add semantic validation result to metadata (if available)
        if variant.validation_result:
            variant.metadata["semantic_validation"] = {
                "verdict": variant.validation_result.verdict.value,
                "concept_aligned": variant.validation_result.concept_aligned,
                "difficulty_equal": variant.validation_result.difficulty_equal,
                "answer_correct": variant.validation_result.answer_correct,
                "calculation_steps": variant.validation_result.calculation_steps,
                "rejection_reason": variant.validation_result.rejection_reason,
            }

        variant_info = {
            "variant_id": variant.variant_id,
            "source_question_id": variant.source_question_id,
            "source_test_id": variant.source_test_id,
            "is_rejected": is_rejected,
        }

        os.makedirs(variant_path, exist_ok=True)

        # Save QTI XML (with feedback if pipeline passed)
        with open(os.path.join(variant_path, "question.xml"), "w", encoding="utf-8") as f:
            f.write(variant.qti_xml)

        # Save metadata
        with open(os.path.join(variant_path, "metadata_tags.json"), "w", encoding="utf-8") as f:
            json.dump(variant.metadata, f, ensure_ascii=False, indent=2)

        # Save variant info
        with open(os.path.join(variant_path, "variant_info.json"), "w", encoding="utf-8") as f:
            json.dump(variant_info, f, ensure_ascii=False, indent=2)

        # Save validation_result.json (pipeline validation details)
        validation_data = {
            "variant_id": variant.variant_id,
            "pipeline_version": "2.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pipeline_success": pipeline_result.success if pipeline_result else None,
            "pipeline_stage_failed": pipeline_result.stage_failed if pipeline_result else None,
            "pipeline_error": pipeline_result.error if pipeline_result else None,
            "pipeline_validation_details": pipeline_result.validation_details if pipeline_result else None,
            "semantic_validation": variant.metadata.get("semantic_validation"),
            "is_approved": not is_rejected,
        }
        with open(os.path.join(variant_path, "validation_result.json"), "w", encoding="utf-8") as f:
            json.dump(validation_data, f, ensure_ascii=False, indent=2)

    def _save_report(self, report: GenerationReport):
        """Save generation report."""

        report_path = os.path.join(self.config.output_dir, report.source_test_id, report.source_question_id, "generation_report.json")

        os.makedirs(os.path.dirname(report_path), exist_ok=True)

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, ensure_ascii=False, indent=2)

    def _print_summary(self, reports: List[GenerationReport]):
        """Print summary of pipeline run."""

        total_gen = sum(r.total_generated for r in reports)
        total_app = sum(r.total_approved for r in reports)
        total_rej = sum(r.total_rejected for r in reports)

        print(f"\n{'=' * 60}")
        print("RESUMEN")
        print(f"{'=' * 60}")
        print(f"Preguntas procesadas: {len(reports)}")
        print(f"Variantes generadas:  {total_gen}")
        print(f"Variantes aprobadas:  {total_app} ({100 * total_app / total_gen:.1f}%)" if total_gen > 0 else "N/A")
        print(f"Variantes rechazadas: {total_rej}")
        print(f"\nOutput: {self.config.output_dir}")
        print(f"{'=' * 60}\n")
