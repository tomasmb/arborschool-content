"""CLI script to generate atoms for multiple standards simultaneously.

Usage:
    python -m app.atoms.scripts.run_multiple_standards --standards path/to/standards.json --standard-ids M1-GEO-01 M1-PROB-01
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from app.atoms.generation import generate_atoms_for_standard
from app.gemini_client import load_default_gemini_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate atoms for multiple standards simultaneously (for testing).",
    )
    parser.add_argument(
        "--standards",
        type=Path,
        required=True,
        help="Input standards JSON file",
    )
    parser.add_argument(
        "--standard-ids",
        type=str,
        nargs="+",
        required=True,
        help="Standard IDs to process (e.g. M1-GEO-01 M1-PROB-01)",
    )
    parser.add_argument("--temario", type=Path, help="Temario JSON file (if not in standards metadata)")
    parser.add_argument("--output-dir", type=Path, help="Output directory (default: tests/atoms/generacion_automatica)")
    parser.add_argument("--max-retries", type=int, default=2, help="Retries on failure")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.standards.exists():
        logger.error("File not found: %s", args.standards)
        sys.exit(1)

    if len(args.standard_ids) < 2:
        logger.error("Please provide at least 2 standard IDs")
        sys.exit(1)

    # Load standards JSON
    logger.info("Loading standards: %s", args.standards)
    with args.standards.open(encoding="utf-8") as f:
        standards_data = json.load(f)

    # Handle both formats: array directly or object with "standards" key
    if isinstance(standards_data, list):
        standards_list = standards_data
        metadata = {}
    else:
        standards_list = standards_data.get("standards", [])
        metadata = standards_data.get("metadata", {})

    # Find the requested standards
    standard_dicts: dict[str, dict[str, Any]] = {}
    for std in standards_list:
        std_id = std.get("id")
        if std_id in args.standard_ids:
            standard_dicts[std_id] = std

    missing = set(args.standard_ids) - set(standard_dicts.keys())
    if missing:
        logger.error("Standards not found: %s", ", ".join(missing))
        logger.info("Available standards:")
        for std in standards_list:
            logger.info("  - %s: %s", std.get("id"), std.get("titulo"))
        sys.exit(1)

    # Determine temario path
    if args.temario:
        temario_path = args.temario
    else:
        temario_path_str = metadata.get("source_temario_json", "")
        if not temario_path_str:
            logger.error("No source_temario_json found in standards metadata and --temario not provided")
            sys.exit(1)
        # Resolve temario path (could be relative or absolute)
        temario_path = Path(temario_path_str)
        if not temario_path.is_absolute():
            # Try relative to standards file
            temario_path = args.standards.parent.parent / temario_path
            # Or try relative to project root
            if not temario_path.exists():
                temario_path = Path(temario_path_str)

    if not temario_path.exists():
        logger.error("Temario file not found: %s", temario_path)
        sys.exit(1)

    logger.info("Loading habilidades from temario: %s", temario_path)
    with temario_path.open(encoding="utf-8") as f:
        temario_data = json.load(f)

    habilidades = temario_data.get("habilidades", {})
    if not habilidades:
        logger.error("No habilidades found in temario file")
        sys.exit(1)

    # Initialize Gemini
    logger.info("Initializing Gemini service...")
    try:
        gemini = load_default_gemini_service()
    except Exception as e:
        logger.error("Failed to initialize Gemini: %s", e)
        sys.exit(1)

    # Determine output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        output_dir = Path("tests/atoms/generacion_automatica")
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 70)
    logger.info("GENERATING ATOMS FOR %d STANDARDS SIMULTANEOUSLY", len(args.standard_ids))
    logger.info("=" * 70)
    logger.info("Standards: %s", ", ".join(args.standard_ids))
    logger.info("Output directory: %s", output_dir)
    logger.info("=" * 70)

    # Generate atoms for each standard
    results: dict[str, Any] = {}
    all_success = True

    for std_id in args.standard_ids:
        standard_dict = standard_dicts[std_id]
        logger.info("")
        logger.info("-" * 70)
        logger.info("PROCESSING STANDARD: %s", std_id)
        logger.info("Title: %s", standard_dict.get("titulo"))
        logger.info("-" * 70)

        result = generate_atoms_for_standard(
            gemini=gemini,
            standard=standard_dict,
            habilidades=habilidades,
            max_retries=args.max_retries,
        )

        if not result.success:
            logger.error("❌ Generation failed for %s: %s", std_id, result.error)
            all_success = False
            results[std_id] = {"success": False, "error": result.error}
            continue

        if not result.atoms:
            logger.error("❌ No atoms generated for %s", std_id)
            all_success = False
            results[std_id] = {"success": False, "error": "No atoms generated"}
            continue

        logger.info("✓ Generated %d atoms for %s", len(result.atoms), std_id)

        # Save results
        standard_id_clean = std_id.replace("-", "_")
        output_path = output_dir / f"atoms_{standard_id_clean}_test.json"
        atoms_dict = [a.model_dump() for a in result.atoms]
        output_path.write_text(
            json.dumps(atoms_dict, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        logger.info("✓ Output saved to: %s", output_path)
        if result.warnings:
            logger.info("⚠ Warnings: %d", len(result.warnings))
            for w in result.warnings:
                logger.info("  ⚠ %s", w)

        results[std_id] = {
            "success": True,
            "atoms_count": len(result.atoms),
            "output_path": str(output_path),
            "warnings": result.warnings,
        }

        # Print atoms IDs
        logger.info("\nGenerated atoms for %s:", std_id)
        for a in result.atoms:
            logger.info("  - %s: %s", a.id, a.titulo)

    # Final summary
    logger.info("")
    logger.info("=" * 70)
    logger.info("FINAL SUMMARY")
    logger.info("=" * 70)
    for std_id, result in results.items():
        if result.get("success"):
            logger.info("✓ %s: %d atoms generated", std_id, result.get("atoms_count", 0))
        else:
            logger.info("❌ %s: FAILED - %s", std_id, result.get("error", "Unknown error"))

    if not all_success:
        logger.error("")
        logger.error("Some generations failed. Check the logs above.")
        sys.exit(1)

    logger.info("")
    logger.info("✅ All generations completed successfully!")


if __name__ == "__main__":
    main()

