"""Script para validar todos los estándares usando el módulo de validación existente.

Este script itera sobre todos los estándares y usa validate_atoms_from_files
para validar cada uno.

Usage:
    python -m app.atoms.scripts.validate_all_atoms \\
        --standards app/data/standards/paes_m1_2026.json \\
        --atoms app/data/atoms/paes_m1_2026_atoms.json \\
        --output-dir validation_results
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from app.atoms.models import Atom, CanonicalAtomsFile
from app.gemini_client import load_default_gemini_service
from app.atoms.validation import validate_atoms_from_files

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Validate all atoms from canonical atoms file using existing validation module.",
    )
    parser.add_argument(
        "--standards",
        type=Path,
        required=True,
        help="Input standards JSON file",
    )
    parser.add_argument(
        "--atoms",
        type=Path,
        required=True,
        help="Canonical atoms JSON file",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("validation_results"),
        help="Output directory for validation results (default: validation_results)",
    )
    parser.add_argument(
        "--standard-ids",
        nargs="+",
        type=str,
        help="Specific standard IDs to validate (default: all)",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip standards that already have validation results",
    )
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load standards
    if not args.standards.exists():
        logger.error("Standards file not found: %s", args.standards)
        sys.exit(1)

    logger.info("Loading standards: %s", args.standards)
    with args.standards.open(encoding="utf-8") as f:
        standards_data = json.load(f)

    if isinstance(standards_data, list):
        standards_list = standards_data
    else:
        standards_list = standards_data.get("standards", [])

    # Load atoms to get list of standards
    if not args.atoms.exists():
        logger.error("Atoms file not found: %s", args.atoms)
        sys.exit(1)

    logger.info("Loading atoms: %s", args.atoms)
    with args.atoms.open(encoding="utf-8") as f:
        atoms_data = json.load(f)

    canonical_file = CanonicalAtomsFile.model_validate(atoms_data)
    atoms = canonical_file.atoms

    # Get unique standard IDs from atoms
    standard_ids_in_atoms = set()
    for atom in atoms:
        standard_ids_in_atoms.update(atom.standard_ids)

    # Filter standards
    if args.standard_ids:
        standards_list = [s for s in standards_list if s.get("id") in args.standard_ids]
        if len(standards_list) != len(args.standard_ids):
            found_ids = {s.get("id") for s in standards_list}
            missing = set(args.standard_ids) - found_ids
            logger.error("Standards not found: %s", ", ".join(missing))
            sys.exit(1)
    else:
        # Only validate standards that have atoms
        standards_list = [
            s for s in standards_list if s.get("id") in standard_ids_in_atoms
        ]

    # Initialize Gemini
    logger.info("Initializing Gemini service...")
    try:
        gemini = load_default_gemini_service()
    except Exception as e:
        logger.error("Failed to initialize Gemini: %s", e)
        sys.exit(1)

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 70)
    logger.info("VALIDATING ALL ATOMS")
    logger.info("=" * 70)
    logger.info("Standards file: %s", args.standards)
    logger.info("Atoms file: %s", args.atoms)
    logger.info("Total standards to validate: %d", len(standards_list))
    logger.info("Total atoms: %d", len(atoms))
    logger.info("Output directory: %s", args.output_dir)
    logger.info("=" * 70)
    logger.info("")

    results: dict[str, Any] = {}
    failed_standards: list[str] = []

    for standard_dict in standards_list:
        standard_id = standard_dict.get("id", "unknown")
        standard_title = standard_dict.get("titulo", "unknown")

        # Check if already exists
        output_path = args.output_dir / f"validation_{standard_id}.json"
        if args.skip_existing and output_path.exists():
            logger.info("⏭  Skipping %s (already exists)", standard_id)
            try:
                with output_path.open(encoding="utf-8") as f:
                    results[standard_id] = json.load(f)
            except Exception as e:
                logger.warning("Failed to load existing result: %s", e)
            continue

        logger.info("-" * 70)
        logger.info("Validating: %s", standard_id)
        logger.info("Title: %s", standard_title)
        logger.info("-" * 70)

        try:
            # Extract atoms for this standard and create temporary list file
            standard_atoms = [
                atom for atom in atoms if standard_id in atom.standard_ids
            ]
            
            if not standard_atoms:
                logger.warning("⚠ No atoms found for %s", standard_id)
                continue
            
            # Convert to dict list for validation
            atoms_dict = [atom.model_dump(mode="json") for atom in standard_atoms]
            
            # Use validate_atoms_with_gemini directly since we have the data in memory
            from app.atoms.validation import validate_atoms_with_gemini
            result = validate_atoms_with_gemini(
                gemini=gemini,
                standard=standard_dict,
                atoms=atoms_dict,
            )

            results[standard_id] = result

            # Save individual result
            with output_path.open("w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            # Print summary
            summary = result.get("evaluation_summary", {})
            logger.info("✓ Validation completed")
            logger.info(
                "  Atoms passing: %d / %d",
                summary.get("atoms_passing_all_checks", 0),
                summary.get("total_atoms", 0),
            )
            logger.info("  Overall quality: %s", summary.get("overall_quality", "N/A"))

            # Show high priority issues
            issues = result.get("detailed_issues", [])
            high_priority = [i for i in issues if i.get("priority") == "high"]
            if high_priority:
                logger.warning("  ⚠ High priority issues: %d", len(high_priority))
                for issue in high_priority[:3]:  # Show first 3
                    logger.warning("    - %s", issue.get("description", "")[:80])

        except Exception as e:
            logger.error("❌ Validation failed for %s: %s", standard_id, e, exc_info=args.verbose)
            failed_standards.append(standard_id)

        logger.info("")

    # Save combined results
    combined_output = args.output_dir / "validation_all_standards.json"
    with combined_output.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info("=" * 70)
    logger.info("VALIDATION COMPLETE")
    logger.info("=" * 70)
    logger.info("✓ Validated: %d standards", len(results))
    if failed_standards:
        logger.error("❌ Failed: %d standards", len(failed_standards))
        for std_id in failed_standards:
            logger.error("  - %s", std_id)
    logger.info("✓ Results saved to: %s", args.output_dir)
    logger.info("✓ Combined results: %s", combined_output)
    logger.info("=" * 70)

    if failed_standards:
        sys.exit(1)


if __name__ == "__main__":
    main()

