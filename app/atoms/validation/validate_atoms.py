"""CLI script to validate generated atoms against standards.

Usage:
    python -m app.atoms.validate_atoms \\
        --standards tests/standards/standards_numeros_test.json \\
        --atoms tests/atoms/atoms_M1_NUM_01_test_v23.json \\
        --standard-id M1-NUM-01 \\
        --output validation_result.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from app.atoms.validation import validate_atoms_from_files
from app.llm_clients import load_default_gemini_service
from app.utils.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def main() -> int:
    """Main entry point for atom validation CLI."""
    parser = argparse.ArgumentParser(description="Validate generated atoms against standards using Gemini")
    parser.add_argument("--standards", type=str, required=True, help="Path to standards JSON file")
    parser.add_argument("--atoms", type=str, required=True, help="Path to atoms JSON file")
    parser.add_argument("--standard-id", type=str, default=None, help="Standard ID to validate (required if standards file has multiple)")
    parser.add_argument("--output", type=str, default=None, help="Output path for validation result JSON (default: print to stdout)")

    args = parser.parse_args()

    # Initialize Gemini
    logger.info("Initializing Gemini service...")
    try:
        gemini = load_default_gemini_service()
    except Exception as e:
        logger.error(f"Failed to initialize Gemini: {e}")
        return 1

    # Validate atoms
    logger.info("=" * 60)
    logger.info("VALIDATING ATOMS")
    logger.info("=" * 60)
    logger.info(f"Standards: {args.standards}")
    logger.info(f"Atoms: {args.atoms}")
    if args.standard_id:
        logger.info(f"Standard ID: {args.standard_id}")
    logger.info("=" * 60)

    try:
        result = validate_atoms_from_files(
            gemini=gemini,
            standard_path=args.standards,
            atoms_path=args.atoms,
            standard_id=args.standard_id,
        )

        # Output result
        result_json = json.dumps(result, indent=2, ensure_ascii=False)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(result_json)
            logger.info(f"✓ Validation result saved to: {args.output}")
        else:
            print(result_json)

        # Print summary
        summary = result.get("evaluation_summary", {})
        logger.info("")
        logger.info("=" * 60)
        logger.info("VALIDATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total atoms: {summary.get('total_atoms', 'N/A')}")
        logger.info(f"Atoms passing all checks: {summary.get('atoms_passing_all_checks', 'N/A')}")
        logger.info(f"Atoms with issues: {summary.get('atoms_with_issues', 'N/A')}")
        logger.info(f"Overall quality: {summary.get('overall_quality', 'N/A')}")
        logger.info(f"Coverage assessment: {summary.get('coverage_assessment', 'N/A')}")
        logger.info(f"Granularity assessment: {summary.get('granularity_assessment', 'N/A')}")

        coverage = result.get("coverage_analysis", {})
        if coverage.get("missing_areas"):
            logger.warning(f"Missing areas: {coverage.get('missing_areas')}")

        return 0

    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
