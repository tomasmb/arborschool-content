"""Question processing pipeline orchestrator."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from app.question_feedback.enhancer import FeedbackEnhancer
from app.question_feedback.models import FeedbackReviewResult, PipelineResult
from app.question_feedback.reviewer import FeedbackReviewer

logger = logging.getLogger(__name__)


class QuestionPipeline:
    """Question processing pipeline with feedback generation and review.

    This class orchestrates the feedback enrichment pipeline:
    1. Stage 1: Feedback Enhancement (LLM generates QTI XML with feedback)
    2. Gate 1: XSD Validation (validates against QTI 3.0 schema)
    3. Stage 2: Feedback Review (LLM solves problem and validates feedback accuracy)

    Note: Full validation (FinalValidator) is run as a SEPARATE step after enrichment.
    The review stage catches mathematical errors and incomplete explanations early.
    """

    def __init__(
        self,
        enhancer: FeedbackEnhancer | None = None,
        reviewer: FeedbackReviewer | None = None,
    ):
        """Initialize the pipeline.

        Args:
            enhancer: FeedbackEnhancer instance. Creates default if None.
            reviewer: FeedbackReviewer instance. Creates default if None.
        """
        self.enhancer = enhancer or FeedbackEnhancer()
        self.reviewer = reviewer or FeedbackReviewer()

    def process(
        self,
        question_id: str,
        qti_xml: str,
        image_urls: list[str] | None = None,
        output_dir: Path | None = None,
    ) -> PipelineResult:
        """Process a question through the enrichment pipeline.

        Args:
            question_id: Unique identifier for the question.
            qti_xml: Original QTI XML without feedback.
            image_urls: Optional list of image URLs for the question.
            output_dir: Directory to save results. If None, results are not saved.

        Returns:
            PipelineResult with success status and details.
        """
        logger.info(f"Processing question: {question_id}")

        # Clear previous enrichment files to avoid stale data if re-enrichment fails
        if output_dir:
            self._clear_previous_enrichment(output_dir)

        # ── STAGE 1: Feedback Enhancement + XSD Validation ──
        enhancement = self.enhancer.enhance(qti_xml, image_urls)

        if not enhancement.success:
            error_msg = enhancement.error or "Enhancement failed (no details available)"
            if enhancement.xsd_errors:
                error_msg = f"XSD validation failed: {enhancement.xsd_errors}"
            result = PipelineResult(
                question_id=question_id,
                success=False,
                stage_failed="feedback_enhancement",
                error=error_msg,
                xsd_errors=enhancement.xsd_errors,
                can_sync=False,
            )
            if output_dir:
                self._save_result(output_dir, result)
            return result

        # At this point enhancement.qti_xml is guaranteed to be non-None (success=True)
        assert enhancement.qti_xml is not None
        qti_with_feedback = enhancement.qti_xml

        # ── STAGE 2: Feedback Review (solves problem and validates feedback accuracy) ──
        review = self.reviewer.review(qti_with_feedback)

        if review.review_result != "pass":
            # ── STAGE 2b: Attempt correction based on review feedback ──
            logger.info("Feedback review failed, attempting correction...")

            review_issues = self._format_review_issues(review)
            correction = self.enhancer.correct(
                qti_xml_with_errors=qti_with_feedback,
                review_issues=review_issues,
                image_urls=image_urls,
            )

            if correction.success and correction.qti_xml:
                # Re-review the corrected feedback
                corrected_review = self.reviewer.review(correction.qti_xml)

                if corrected_review.review_result == "pass":
                    logger.info("Correction successful, review passed")
                    qti_with_feedback = correction.qti_xml
                    review = corrected_review
                else:
                    # Correction didn't fix all issues
                    failed_checks = self._get_failed_checks(corrected_review)
                    error_msg = (
                        f"Feedback review failed after correction: "
                        f"{', '.join(failed_checks) or 'unknown'}"
                    )

                    result = PipelineResult(
                        question_id=question_id,
                        success=False,
                        stage_failed="feedback_review",
                        error=error_msg,
                        feedback_review_details=corrected_review.model_dump(),
                        can_sync=False,
                    )
                    if output_dir:
                        self._save_result(output_dir, result)
                    return result
            else:
                # Correction itself failed
                failed_checks = self._get_failed_checks(review)
                error_msg = (
                    f"Feedback review failed: {', '.join(failed_checks) or 'unknown'}"
                )

                result = PipelineResult(
                    question_id=question_id,
                    success=False,
                    stage_failed="feedback_review",
                    error=error_msg,
                    feedback_review_details=review.model_dump(),
                    can_sync=False,
                )
                if output_dir:
                    self._save_result(output_dir, result)
                return result

        # ── SUCCESS: Ready for full validation (separate step) ──
        result = PipelineResult(
            question_id=question_id,
            success=True,
            qti_xml_final=qti_with_feedback,
            feedback_review_details=review.model_dump(),
            can_sync=False,  # Will be set to True after full validation passes
        )

        if output_dir:
            self._save_result(output_dir, result)
            self._save_validated_xml(output_dir, qti_with_feedback)

        logger.info(f"Question {question_id} enrichment completed successfully")
        return result

    def _save_result(self, output_dir: Path, result: PipelineResult) -> None:
        """Save enrichment result to JSON file.

        Args:
            output_dir: Directory to save the result.
            result: PipelineResult to save.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        result_data = {
            "question_id": result.question_id,
            "pipeline_version": "3.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": result.success,
            "stage_failed": result.stage_failed,
            "error": result.error,
            "xsd_errors": result.xsd_errors,
            "stages": {
                "feedback_review": result.feedback_review_details,
            },
            "can_sync": result.can_sync,
            "validated_qti_path": (
                "question_validated.xml" if result.success else None
            ),
        }

        result_path = output_dir / "validation_result.json"
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved enrichment result to {result_path}")

    def _save_validated_xml(self, output_dir: Path, qti_xml: str) -> None:
        """Save validated QTI XML to file.

        Args:
            output_dir: Directory to save the XML.
            qti_xml: Validated QTI XML string.
        """
        xml_path = output_dir / "question_validated.xml"
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(qti_xml)

        logger.info(f"Saved validated QTI to {xml_path}")

    def _clear_previous_enrichment(self, output_dir: Path) -> None:
        """Clear previous enrichment files to avoid stale data.

        Called at the start of processing so that if re-enrichment fails,
        there's no misleading old enrichment data left behind.

        Args:
            output_dir: Directory containing enrichment files.
        """
        files_to_clear = ["question_validated.xml", "validation_result.json"]

        for filename in files_to_clear:
            file_path = output_dir / filename
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Cleared previous enrichment file: {file_path}")

    def _format_review_issues(self, review: FeedbackReviewResult) -> str:
        """Format review issues into a string for the correction prompt.

        Args:
            review: FeedbackReviewResult with issues.

        Returns:
            Formatted string describing all issues found.
        """
        issues_parts = []

        if review.feedback_accuracy.status.value == "fail":
            issues_parts.append("ERRORES DE PRECISIÓN MATEMÁTICA:")
            for issue in review.feedback_accuracy.issues:
                issues_parts.append(f"- {issue}")
            if review.feedback_accuracy.reasoning:
                issues_parts.append(f"Análisis: {review.feedback_accuracy.reasoning}")

        if review.feedback_clarity.status.value == "fail":
            issues_parts.append("\nERRORES DE CLARIDAD:")
            for issue in review.feedback_clarity.issues:
                issues_parts.append(f"- {issue}")

        if review.formatting_check.status.value == "fail":
            issues_parts.append("\nERRORES DE FORMATO:")
            for issue in review.formatting_check.issues:
                issues_parts.append(f"- {issue}")

        return "\n".join(issues_parts)

    def _get_failed_checks(self, review: FeedbackReviewResult) -> list[str]:
        """Get list of failed check names from a review result.

        Args:
            review: FeedbackReviewResult to check.

        Returns:
            List of failed check names.
        """
        failed_checks = []
        if review.feedback_accuracy.status.value == "fail":
            failed_checks.append("feedback_accuracy")
        if review.feedback_clarity.status.value == "fail":
            failed_checks.append("feedback_clarity")
        if review.formatting_check.status.value == "fail":
            failed_checks.append("formatting_check")
        return failed_checks


def process_question_dir(
    question_dir: Path,
    pipeline: QuestionPipeline | None = None,
) -> PipelineResult:
    """Process a question from its directory.

    Convenience function that loads QTI XML from a question directory
    and runs the pipeline.

    Args:
        question_dir: Path to the question directory containing question.xml.
        pipeline: QuestionPipeline instance. Creates default if None.

    Returns:
        PipelineResult with processing results.
    """
    if pipeline is None:
        pipeline = QuestionPipeline()

    qti_file = question_dir / "question.xml"
    if not qti_file.exists():
        return PipelineResult(
            question_id=question_dir.name,
            success=False,
            error=f"question.xml not found in {question_dir}",
            can_sync=False,
        )

    qti_xml = qti_file.read_text(encoding="utf-8")
    question_id = f"{question_dir.parent.parent.name}-{question_dir.name}"

    # Extract image URLs from QTI XML (could be enhanced later)
    from app.question_feedback.utils.image_utils import extract_image_urls

    image_urls = extract_image_urls(qti_xml)

    return pipeline.process(
        question_id=question_id,
        qti_xml=qti_xml,
        image_urls=image_urls if image_urls else None,
        output_dir=question_dir,
    )
