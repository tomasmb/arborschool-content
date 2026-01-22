#!/usr/bin/env python3
"""CLI script for running the variant generation pipeline.

Usage:
    python -m app.assessment.run_variant_generation \\
        --source-test "Prueba-invierno-2025" \\
        --questions "Q1,Q4,Q5" \\
        --variants-per-question 3 \\
        --output-dir "app/data/pruebas/alternativas"
"""

import argparse
import sys

from app.question_variants.models import PipelineConfig
from app.question_variants.pipeline import VariantPipeline


def main():
    parser = argparse.ArgumentParser(
        description="Generate variant questions from finalized test questions."
    )
    
    parser.add_argument(
        "--source-test",
        required=True,
        help="Test ID to generate variants from (e.g., 'Prueba-invierno-2025')"
    )
    
    parser.add_argument(
        "--questions",
        default=None,
        help="Comma-separated list of question IDs to process (e.g., 'Q1,Q4,Q5'). "
             "If not specified, processes all questions."
    )
    
    parser.add_argument(
        "--variants-per-question",
        type=int,
        default=3,
        help="Number of variants to generate per question (default: 3)"
    )
    
    parser.add_argument(
        "--output-dir",
        default="app/data/pruebas/alternativas",
        help="Output directory for generated variants"
    )
    
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip the validation phase (not recommended)"
    )
    
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.3,
        help="LLM temperature for generation (default: 0.3)"
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
        validate_variants=not args.skip_validation,
        output_dir=args.output_dir
    )
    
    # Run pipeline
    pipeline = VariantPipeline(config)
    
    try:
        reports = pipeline.run(
            test_id=args.source_test,
            question_ids=question_ids,
            num_variants=args.variants_per_question
        )
        
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
