#!/usr/bin/env python3
"""CLI script for running the variant generation pipeline.

Usage:
    python -m app.assessment.run_variant_generation \\
        --source-test "prueba-invierno-2025" \\
        --questions "Q1,Q4,Q5" \\
        --variants-per-question 10 \\
        --output-dir "app/data/pruebas/hard_variants"
"""

import argparse
import sys

from app.question_variants.models import PipelineConfig
from app.question_variants.io.network_preflight import check_required_providers
from app.question_variants.pipeline import VariantPipeline

DEFAULT_RUN_OUTPUT_DIR = "app/data/pruebas/hard_variants"


def main():
    parser = argparse.ArgumentParser(description="Generate variant questions from finalized test questions.")

    parser.add_argument("--source-test", required=True, help="Test ID to generate variants from (e.g., 'prueba-invierno-2025')")

    parser.add_argument(
        "--questions",
        default=None,
        help="Comma-separated list of question IDs to process (e.g., 'Q1,Q4,Q5'). If not specified, processes all questions.",
    )

    parser.add_argument(
        "--variants-per-question",
        type=int,
        default=10,
        help="Number of variants to generate per question (initial default: 10)",
    )

    parser.add_argument(
        "--output-dir",
        default=DEFAULT_RUN_OUTPUT_DIR,
        help="Output directory for generated variants (default: app/data/pruebas/hard_variants)",
    )

    parser.add_argument("--skip-validation", action="store_true", help="Skip the validation phase (not recommended)")
    parser.add_argument(
        "--enable-feedback-pipeline",
        action="store_true",
        help="Enable feedback enrichment as a later optional pass (disabled by default for hard variants)",
    )

    parser.add_argument("--temperature", type=float, default=0.3, help="LLM temperature for generation (default: 0.3)")
    parser.add_argument(
        "--llm-timeout-seconds",
        type=int,
        default=180,
        help="Per-call timeout for variant LLM stages (default: 180)",
    )
    parser.add_argument(
        "--llm-max-attempts",
        type=int,
        default=2,
        help="Retry attempts per variant LLM stage (default: 2)",
    )
    parser.add_argument("--planner-provider", default="gemini", choices=["gemini", "openai"], help="LLM provider for blueprint planning")
    parser.add_argument("--planner-model", default=None, help="Optional explicit model for blueprint planning")
    parser.add_argument(
        "--planner-reasoning-level",
        default="high",
        choices=["none", "low", "medium", "high"],
        help="Reasoning level for blueprint planning (default: high)",
    )
    parser.add_argument("--generator-provider", default="gemini", choices=["gemini", "openai"], help="LLM provider for variant generation")
    parser.add_argument("--generator-model", default=None, help="Optional explicit model for variant generation")
    parser.add_argument(
        "--generator-reasoning-level",
        default="medium",
        choices=["none", "low", "medium", "high"],
        help="Reasoning level for variant generation (default: medium)",
    )
    parser.add_argument("--validator-provider", default="openai", choices=["gemini", "openai"], help="LLM provider for semantic validation")
    parser.add_argument("--validator-model", default=None, help="Optional explicit model for semantic validation")
    parser.add_argument(
        "--validator-reasoning-level",
        default="medium",
        choices=["none", "low", "medium", "high"],
        help="Reasoning level for semantic validation (default: medium)",
    )
    parser.add_argument(
        "--skip-network-preflight",
        action="store_true",
        help="Skip Python DNS preflight for configured providers (not recommended)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=1,
        help="Max retry attempts per rejected variant with feedback (default: 1, 0 to disable)",
    )

    args = parser.parse_args()

    # Parse question IDs
    question_ids = None
    if args.questions:
        question_ids = [q.strip() for q in args.questions.split(",")]

    # Create config
    config = PipelineConfig(
        variants_per_question=args.variants_per_question,
        temperature=args.temperature,
        llm_request_timeout_seconds=args.llm_timeout_seconds,
        llm_max_attempts=args.llm_max_attempts,
        planner_provider=args.planner_provider,
        planner_model=args.planner_model,
        planner_reasoning_level=args.planner_reasoning_level,
        generator_provider=args.generator_provider,
        generator_model=args.generator_model,
        generator_reasoning_level=args.generator_reasoning_level,
        validator_provider=args.validator_provider,
        validator_model=args.validator_model,
        validator_reasoning_level=args.validator_reasoning_level,
        validate_variants=not args.skip_validation,
        enable_feedback_pipeline=args.enable_feedback_pipeline,
        max_retries_per_variant=args.max_retries,
        output_dir=args.output_dir,
    )

    if not args.skip_network_preflight:
        checks = check_required_providers(
            [args.planner_provider, args.generator_provider, args.validator_provider]
        )
        failed = [check for check in checks if not check.ok]
        if failed:
            print("\n❌ Network preflight failed for configured providers:")
            for check in failed:
                print(f"  - {check.provider}: {check.error}")
            print(
                "\nEsto indica un problema de red/DNS en Python antes de llegar al modelo. "
                "La corrida se aborta para evitar falsos diagnósticos del pipeline."
            )
            sys.exit(1)

    # Run pipeline
    pipeline = VariantPipeline(config)

    try:
        reports = pipeline.run(test_id=args.source_test, question_ids=question_ids, num_variants=args.variants_per_question)

        # Exit with error if no variants were approved
        total_approved = sum(r.total_approved for r in reports)
        if total_approved == 0:
            print("\n⚠️ No se aprobó ninguna variante. Revisa los logs para más detalles.")
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
