#!/usr/bin/env python3
"""CLI for running the variant generation pipeline.

Usage (batch mode -- default):
    python -m app.question_variants.run_variant_generation \\
        --source-test "prueba-invierno-2025" \\
        --variants-per-question 10

Usage (sync debug mode):
    python -m app.question_variants.run_variant_generation \\
        --source-test "prueba-invierno-2025" \\
        --questions "Q1,Q11,Q12" \\
        --variants-per-question 3 \\
        --no-batch

Resume a previous batch run:
    python -m app.question_variants.run_variant_generation \\
        --source-test "prueba-invierno-2025" \\
        --job-id "abc123"
"""

from __future__ import annotations

import argparse
import sys

from app.question_variants.models import PipelineConfig

DEFAULT_RUN_OUTPUT_DIR = "app/data/pruebas/hard_variants"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate variant questions from finalized tests.",
    )
    parser.add_argument(
        "--source-test", required=True,
        help="Test ID (e.g., 'prueba-invierno-2025')",
    )
    parser.add_argument(
        "--questions", default=None,
        help="Comma-separated question IDs (e.g., 'Q1,Q4,Q5'). "
        "Omit to process all questions.",
    )
    parser.add_argument(
        "--variants-per-question", type=int, default=10,
        help="Variants to generate per question (default: 10)",
    )
    parser.add_argument(
        "--output-dir", default=DEFAULT_RUN_OUTPUT_DIR,
        help="Output directory for generated variants",
    )
    parser.add_argument(
        "--model", default="gpt-5.1",
        help="OpenAI model for all LLM phases (default: gpt-5.1)",
    )
    parser.add_argument(
        "--no-batch", action="store_true",
        help="Run in sync mode (no Batch API). For debugging / pilot.",
    )
    parser.add_argument(
        "--job-id", default=None,
        help="Resume a previous batch run from this job ID.",
    )
    parser.add_argument(
        "--batch-poll-interval", type=int, default=30,
        help="Seconds between batch status polls (default: 30)",
    )
    parser.add_argument(
        "--skip-validation", action="store_true",
        help="Skip the validation phase (not recommended)",
    )
    parser.add_argument(
        "--temperature", type=float, default=0.3,
        help="LLM temperature for generation (default: 0.3)",
    )
    parser.add_argument(
        "--max-retries", type=int, default=1,
        help="Max retry attempts per rejected variant (default: 1)",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()

    question_ids = None
    if args.questions:
        question_ids = [q.strip() for q in args.questions.split(",")]

    config = PipelineConfig(
        variants_per_question=args.variants_per_question,
        temperature=args.temperature,
        model=args.model,
        use_batch_api=not args.no_batch,
        batch_poll_interval=args.batch_poll_interval,
        job_id=args.job_id,
        validate_variants=not args.skip_validation,
        max_retries_per_variant=args.max_retries,
        output_dir=args.output_dir,
    )

    if config.use_batch_api:
        from app.question_variants.pipeline import BatchVariantPipeline
        pipeline = BatchVariantPipeline(config)
    else:
        from app.question_variants.pipeline import SyncVariantPipeline
        pipeline = SyncVariantPipeline(config)

    try:
        reports = pipeline.run(
            test_id=args.source_test,
            question_ids=question_ids,
            num_variants=args.variants_per_question,
        )
        total_approved = sum(r.total_approved for r in reports)
        if total_approved == 0:
            print(
                "\n⚠️ No se aprobó ninguna variante. "
                "Revisa los logs para más detalles.",
            )
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrumpido por el usuario.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
