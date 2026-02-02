"""CLI script to generate standards for a single eje.

Usage:
    python -m app.standards.run_single_eje --temario path/to/temario.json --eje numeros
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from app.gemini_client import load_default_gemini_service
from app.standards.generation import generate_standards_for_eje
from app.standards.prompts import EJE_PREFIX_MAP
from app.standards.validation import run_full_eje_validation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate standards for a single eje (for testing).",
    )
    parser.add_argument("--temario", type=Path, required=True, help="Input temario JSON")
    parser.add_argument(
        "--eje",
        type=str,
        required=True,
        choices=list(EJE_PREFIX_MAP.keys()),
        help="Eje to process (numeros, algebra_y_funciones, geometria, probabilidad_y_estadistica)",
    )
    parser.add_argument("--output", type=Path, help="Output JSON file (optional)")
    parser.add_argument("--max-retries", type=int, default=2, help="Retries per unidad")
    parser.add_argument("--skip-per-unidad-validation", action="store_true")
    parser.add_argument("--skip-per-eje-validation", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.temario.exists():
        logger.error("File not found: %s", args.temario)
        sys.exit(1)

    # Load temario
    logger.info("Loading temario: %s", args.temario)
    with args.temario.open(encoding="utf-8") as f:
        temario = json.load(f)

    # Check eje exists
    if args.eje not in temario.get("conocimientos", {}):
        logger.error("Eje '%s' not found in temario", args.eje)
        sys.exit(1)

    unidades = temario["conocimientos"][args.eje].get("unidades", [])
    if not unidades:
        logger.error("No unidades found for eje '%s'", args.eje)
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("PROCESSING EJE: %s (%d unidades)", args.eje.upper(), len(unidades))
    logger.info("=" * 60)

    # Initialize Gemini
    logger.info("Initializing Gemini service...")
    try:
        gemini = load_default_gemini_service()
    except Exception as e:
        logger.error("Failed to initialize Gemini: %s", e)
        sys.exit(1)

    # Generate standards for this eje
    logger.info("--- Stage 1: Generation ---")
    eje_result = generate_standards_for_eje(
        gemini=gemini,
        eje_key=args.eje,
        unidades=unidades,
        habilidades=temario["habilidades"],
        starting_number=1,
        max_retries=args.max_retries,
        validate_per_unidad=not args.skip_per_unidad_validation,
    )

    if eje_result.errors:
        logger.error("Generation errors:")
        for err in eje_result.errors:
            logger.error("  ✗ %s", err)
        sys.exit(1)

    if not eje_result.standards:
        logger.error("No standards generated")
        sys.exit(1)

    logger.info("✓ Generated %d standards", len(eje_result.standards))

    # Stage 2: Per-eje validation
    if not args.skip_per_eje_validation:
        logger.info("--- Stage 2: Cross-Standard Validation ---")
        validation_result = run_full_eje_validation(
            gemini=gemini,
            standards=eje_result.standards,
            eje_key=args.eje,
            original_unidades=unidades,
            habilidades=temario["habilidades"],
            temario_conocimientos=temario["conocimientos"],
        )

        if validation_result.has_errors:
            logger.warning("Validation found errors:")
            for issue in validation_result.issues:
                if issue.severity == "error":
                    logger.warning("  ✗ [%s] %s: %s", issue.standard_id or args.eje, issue.issue_type, issue.description)

        if validation_result.corrected_standards:
            logger.info("Applying %d corrections", len(validation_result.corrected_standards))
            corrected_ids = {s.id for s in validation_result.corrected_standards}
            kept = [s for s in eje_result.standards if s.id not in corrected_ids]
            eje_result.standards = kept + validation_result.corrected_standards

    # Output results
    if args.output:
        output_path = args.output
    else:
        output_path = Path(f"standards_{args.eje}_test.json")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    standards_dict = [s.model_dump() for s in eje_result.standards]
    output_path.write_text(
        json.dumps(standards_dict, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info("=" * 60)
    logger.info("RESULTS")
    logger.info("=" * 60)
    logger.info("✓ Standards generated: %d", len(eje_result.standards))
    logger.info("✓ Output saved to: %s", output_path)
    if eje_result.warnings:
        logger.info("⚠ Warnings: %d", len(eje_result.warnings))
        for w in eje_result.warnings:
            logger.info("  ⚠ %s", w)

    # Print standards IDs
    logger.info("\nGenerated standards:")
    for s in eje_result.standards:
        logger.info("  - %s: %s", s.id, s.titulo)


if __name__ == "__main__":
    main()

