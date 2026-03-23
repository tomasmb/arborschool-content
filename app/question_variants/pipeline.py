"""Variant generation pipeline orchestrator."""
from __future__ import annotations

import logging
from typing import List, Optional

from app.question_generation.progress import report_progress
from app.question_variants.io.artifacts import save_report, save_source_snapshot, save_variant, save_variant_plan
from app.question_variants.models import (
    GenerationReport,
    PipelineConfig,
    SourceQuestion,
    VariantQuestion,
    VariantResult,
)
from app.question_variants.io.source_loader import load_source_questions
from app.question_variants.qti_validation_utils import extract_choices, extract_question_text, find_correct_answer
from app.question_variants.contracts.structural_profile import build_construct_contract
from app.question_variants.postprocess.family_repairs import repair_family_specific_qti
from app.question_variants.postprocess.repair_utils import apply_declared_correct_choice, strip_xml_comments
from app.question_variants.postprocess.presentation_transformer import normalize_variant_presentation
from app.question_variants.variant_generator import VariantGenerator
from app.question_variants.variant_planner import VariantPlanner
from app.question_variants.variant_validator import VariantValidator

logger = logging.getLogger(__name__)

class VariantPipeline:
    """Orchestrates the variant generation pipeline."""

    def __init__(self, config: Optional[PipelineConfig] = None):
        """Initialize the pipeline.

        Args:
            config: Pipeline configuration. Uses defaults if not provided.
        """
        self.config = config or PipelineConfig()
        self.planner = VariantPlanner(self.config)
        self.generator = VariantGenerator(self.config)
        self.validator = VariantValidator(self.config)
        self.feedback_pipeline = None
        if self.config.enable_feedback_pipeline:
            from app.question_feedback.pipeline import QuestionPipeline

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
        sources = load_source_questions(test_id, question_ids)

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

    def _process_question(self, source: SourceQuestion, num_variants: Optional[int] = None) -> GenerationReport:
        """Process a single source question.

        Pipeline flow for each variant:
        1. Generate raw variant QTI XML
        2. Optionally enrich with feedback via QuestionPipeline
        3. Validate semantics via VariantValidator (concept alignment, difficulty)
        4. Save only variants passing all validation stages
        """
        print(f"\n{'─' * 40}")
        print(f"Procesando: {source.question_id}")
        print(f"{'─' * 40}")

        report = GenerationReport(source_question_id=source.question_id, source_test_id=source.test_id)
        save_source_snapshot(self.config.output_dir, source)
        source_contract = build_construct_contract(
            source.question_text,
            source.qti_xml,
            bool(source.image_urls),
            source.primary_atoms,
            source.metadata,
            source.choices,
            source.correct_answer,
        )

        n = num_variants or self.config.variants_per_question

        blueprints = self.planner.plan_variants(source, n)
        if self.planner.used_fallback:
            report.stage_failures["planning_fallback"] = report.stage_failures.get("planning_fallback", 0) + 1
        if self.planner.last_error:
            report.errors.append(f"planner: {self.planner.last_error}")

        save_variant_plan(self.config.output_dir, source, blueprints)

        variants = self.generator.generate_variants(source, n, blueprints=blueprints)
        report.total_generated = len(variants)

        if not variants:
            report.stage_failures["generation"] = report.stage_failures.get("generation", 0) + 1
            if self.generator.last_error:
                report.errors.append(f"generator: {self.generator.last_error}")
            report.errors.append("No se pudieron generar variantes")
            save_report(self.config.output_dir, report)
            return report

        approved_variants: list[VariantQuestion] = []
        all_variants: list[VariantQuestion] = []  # Track all (for rejected save)
        variant_results: dict[str, VariantResult] = {}

        # Map variant_id to blueprint for retry
        blueprint_map: dict[str, VariantBlueprint] = {}
        if blueprints:
            for bp in blueprints:
                blueprint_map[bp.variant_id] = bp

        for variant in variants:
            if self.config.enable_feedback_pipeline:
                result = self._process_variant_through_pipeline(variant, source)
            else:
                result = VariantResult(
                    success=True,
                    variant_id=variant.variant_id,
                    qti_xml=variant.qti_xml,
                    validation_details={
                        "feedback_pipeline": "skipped_by_config",
                    },
                )
            variant_results[variant.variant_id] = result

            if result.success and result.qti_xml:
                # Update variant with enriched QTI XML
                variant.qti_xml = result.qti_xml
                approved, rejection_reason = self._postprocess_and_validate(
                    variant, source, source_contract, approved_variants, report,
                )

                # Retry with feedback if rejected and has a blueprint
                if (
                    not approved
                    and rejection_reason
                    and self.config.max_retries_per_variant > 0
                    and variant.variant_id in blueprint_map
                ):
                    bp = blueprint_map[variant.variant_id]
                    for attempt in range(self.config.max_retries_per_variant):
                        report.total_retried += 1
                        retry_variant = self.generator.regenerate_with_feedback(
                            source, bp, rejection_reason,
                        )
                        if retry_variant is None:
                            break
                        all_variants.append(retry_variant)
                        report.total_generated += 1
                        # Run through feedback pipeline if enabled
                        if self.config.enable_feedback_pipeline:
                            retry_result = self._process_variant_through_pipeline(retry_variant, source)
                        else:
                            retry_result = VariantResult(
                                success=True,
                                variant_id=retry_variant.variant_id,
                                qti_xml=retry_variant.qti_xml,
                            )
                        variant_results[retry_variant.variant_id + f"_retry{attempt+1}"] = retry_result
                        if retry_result.success and retry_result.qti_xml:
                            retry_variant.qti_xml = retry_result.qti_xml
                            retry_approved, retry_rejection = self._postprocess_and_validate(
                                retry_variant, source, source_contract, approved_variants, report,
                            )
                            if retry_approved:
                                report.total_approved_on_retry += 1
                                break
                            rejection_reason = retry_rejection or rejection_reason
                        else:
                            break

            else:
                report.total_rejected += 1
                stage_key = result.stage_failed or "pipeline"
                report.stage_failures[stage_key] = report.stage_failures.get(stage_key, 0) + 1
                if result.error:
                    report.errors.append(f"{stage_key}: {result.error}")
                logger.warning(
                    f"Variant {variant.variant_id} failed feedback pipeline: "
                    f"stage={result.stage_failed}, error={result.error}"
                )

            all_variants.append(variant)

        # Save approved variants
        for variant in approved_variants:
            save_variant(
                self.config.output_dir,
                variant,
                source,
                variant_results.get(variant.variant_id),
                postprocess_summary=variant.metadata.get("postprocess_summary"),
            )
            report.variants.append(variant.variant_id)

        # Save rejected variants if configured
        if self.config.save_rejected:
            rejected = [v for v in all_variants if v not in approved_variants]
            for variant in rejected:
                save_variant(
                    self.config.output_dir,
                    variant,
                    source,
                    variant_results.get(variant.variant_id),
                    is_rejected=True,
                    postprocess_summary=variant.metadata.get("postprocess_summary"),
                )

        # Save report
        save_report(self.config.output_dir, report)

        return report

    def _postprocess_and_validate(
        self,
        variant: VariantQuestion,
        source: SourceQuestion,
        source_contract: dict,
        approved_variants: list[VariantQuestion],
        report: GenerationReport,
    ) -> tuple[bool, str | None]:
        """Postprocess and validate a single variant.

        Returns:
            Tuple of (is_approved, rejection_reason or None).
        """
        from app.question_variants.qti_validation_utils import surface_similarity

        original_qti = variant.qti_xml
        variant.qti_xml = normalize_variant_presentation(
            variant.qti_xml,
            str(source_contract.get("operation_signature") or ""),
            str(source_contract.get("task_form") or ""),
            str(source_contract.get("selection_load") or "not_applicable"),
        )
        normalized_qti = variant.qti_xml
        variant.qti_xml = repair_family_specific_qti(
            variant.qti_xml,
            source_contract,
            variant.metadata,
        )
        repaired_qti = variant.qti_xml
        variant.qti_xml = apply_declared_correct_choice(
            variant.qti_xml,
            str(variant.metadata.get("generator_declared_correct_identifier") or ""),
        )
        declaration_synced_qti = variant.qti_xml
        variant.qti_xml = strip_xml_comments(variant.qti_xml)
        stripped_qti = variant.qti_xml
        variant.metadata["construct_contract"] = build_construct_contract(
            extract_question_text(variant.qti_xml),
            variant.qti_xml,
            self.validator._has_visual_support(variant.qti_xml),
            source.primary_atoms,
            source.metadata,
            extract_choices(variant.qti_xml),
            find_correct_answer(variant.qti_xml),
        )
        variant.metadata["postprocess_summary"] = {
            "presentation_normalized": normalized_qti != original_qti,
            "family_repaired": repaired_qti != normalized_qti,
            "correct_declaration_synced": declaration_synced_qti != repaired_qti,
            "comments_stripped": stripped_qti != declaration_synced_qti,
        }

        # Run semantic validation (concept alignment, difficulty)
        if self.config.validate_variants:
            semantic_result = self.validator.validate(variant, source)
            variant.validation_result = semantic_result

            if semantic_result.is_approved:
                # Inter-variant deduplication: check against already approved
                variant_text = extract_question_text(variant.qti_xml)
                for approved in approved_variants:
                    approved_text = extract_question_text(approved.qti_xml)
                    similarity = surface_similarity(variant_text, approved_text)
                    if similarity > 0.85:
                        report.total_rejected += 1
                        reason = (
                            f"Demasiado similar a {approved.variant_id} "
                            f"(similitud={similarity:.2f}). Se necesita más diversidad."
                        )
                        report.rejection_reasons.append(reason)
                        logger.warning(
                            f"Variant {variant.variant_id} too similar to "
                            f"{approved.variant_id}: {similarity:.2f}"
                        )
                        return False, reason

                approved_variants.append(variant)
                report.total_approved += 1
                return True, None
            else:
                report.total_rejected += 1
                report.stage_failures["semantic_validation"] = report.stage_failures.get("semantic_validation", 0) + 1
                if semantic_result.rejection_reason:
                    report.rejection_reasons.append(semantic_result.rejection_reason)
                logger.warning(
                    f"Variant {variant.variant_id} failed semantic validation: "
                    f"{semantic_result.rejection_reason}"
                )
                return False, semantic_result.rejection_reason
        else:
            # Skip semantic validation
            approved_variants.append(variant)
            report.total_approved += 1
            return True, None

    def _process_variant_through_pipeline(
        self, variant: VariantQuestion, source: SourceQuestion
    ) -> VariantResult:
        """Process a variant through the optional feedback enhancement pipeline.

        Args:
            variant: The variant to process.
            source: The source question (for context).

        Returns:
            VariantResult with success status and enriched QTI XML if successful.
        """
        print(f"    📝 Processing {variant.variant_id} through feedback pipeline...")

        if self.feedback_pipeline is None:
            return VariantResult(
                success=True,
                variant_id=variant.variant_id,
                qti_xml=variant.qti_xml,
                validation_details={"feedback_pipeline": "disabled"},
            )

        # Extract image URLs from variant QTI
        from app.question_feedback.utils.image_utils import extract_image_urls

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
                validation_details=(
                    pipeline_result.feedback_review_details
                    if hasattr(pipeline_result, "feedback_review_details")
                    else None
                ),
            )

        print(f"    ✅ {variant.variant_id} passed feedback pipeline")
        return VariantResult(
            success=True,
            variant_id=variant.variant_id,
            qti_xml=pipeline_result.qti_xml_final,
            validation_details=(
                pipeline_result.feedback_review_details
                if hasattr(pipeline_result, "feedback_review_details")
                else None
            ),
        )

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
