"""Phase 6 -- parallel feedback enrichment for approved variants.

Reuses ``QuestionPipeline`` from ``app.question_feedback.pipeline``
(the same enrichment/review/correction loop used by the atom question
generation pipeline).  Pattern follows ``app.question_generation.phase8_runner``.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.question_feedback.models import PipelineResult as FeedbackResult
from app.question_feedback.pipeline import QuestionPipeline
from app.question_variants.models import SourceQuestion, VariantQuestion

logger = logging.getLogger(__name__)

_DEFAULT_MAX_WORKERS = 10


def run_enrichment(
    variants: list[VariantQuestion],
    sources_map: dict[str, SourceQuestion],
    *,
    max_workers: int = _DEFAULT_MAX_WORKERS,
    enrichment_model: str | None = None,
    max_correction_retries: int = 2,
) -> tuple[list[VariantQuestion], list[VariantQuestion]]:
    """Enrich approved variants with feedback in parallel.

    Each variant is processed through the full feedback pipeline
    (enhance + XSD + review + correction loop).

    Returns (enriched, failed).
    """
    total = len(variants)
    if total == 0:
        return [], []

    pipeline = QuestionPipeline(
        max_correction_retries=max_correction_retries,
    )
    if enrichment_model:
        from app.question_feedback.enhancer import FeedbackEnhancer
        from app.question_feedback.reviewer import FeedbackReviewer
        pipeline = QuestionPipeline(
            enhancer=FeedbackEnhancer(model=enrichment_model),
            reviewer=FeedbackReviewer(model=enrichment_model),
            max_correction_retries=max_correction_retries,
        )

    logger.info(
        "Phase 6: Enriching %d variants (workers=%d)",
        total, max_workers,
    )

    enriched: list[VariantQuestion] = []
    failed: list[VariantQuestion] = []
    completed = 0
    lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(
                _enrich_single, pipeline, v, sources_map,
            ): v
            for v in variants
        }
        for future in as_completed(futures):
            variant = futures[future]
            fb_result = future.result()
            with lock:
                completed += 1
                if fb_result.success and fb_result.qti_xml_final:
                    variant.qti_xml = fb_result.qti_xml_final
                    variant.metadata["enrichment"] = "pass"
                    enriched.append(variant)
                    logger.info(
                        "  ✅ %s enriched (%d/%d)",
                        variant.variant_id, completed, total,
                    )
                else:
                    variant.metadata["enrichment"] = "fail"
                    variant.metadata["enrichment_error"] = (
                        f"{fb_result.stage_failed}: {fb_result.error}"
                    )
                    failed.append(variant)
                    logger.warning(
                        "  ❌ %s enrichment failed: %s (%d/%d)",
                        variant.variant_id,
                        fb_result.error or "unknown",
                        completed, total,
                    )

    logger.info(
        "Phase 6 done: %d enriched, %d failed",
        len(enriched), len(failed),
    )
    return enriched, failed


def _enrich_single(
    pipeline: QuestionPipeline,
    variant: VariantQuestion,
    sources_map: dict[str, SourceQuestion],
) -> FeedbackResult:
    """Run feedback enrichment on a single variant."""
    source_key = f"{variant.source_test_id}__{variant.source_question_id}"
    source = sources_map.get(source_key)
    image_urls = source.image_urls if source else None

    return pipeline.process(
        question_id=variant.variant_id,
        qti_xml=variant.qti_xml,
        image_urls=image_urls if image_urls else None,
        output_dir=None,
    )
