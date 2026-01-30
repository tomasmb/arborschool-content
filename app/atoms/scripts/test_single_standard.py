"""Script para probar generación de átomos para un solo estándar.

Usage:
    python -m app.atoms.test_single_standard --standards path/to/standards.json --standard-id M1-NUM-01
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
        description="Generate atoms for a single standard (for testing).",
    )
    parser.add_argument(
        "--standards",
        type=Path,
        required=True,
        help="Input standards JSON file",
    )
    parser.add_argument(
        "--standard-id",
        type=str,
        required=True,
        help="Standard ID to process (e.g. M1-NUM-01)",
    )
    parser.add_argument("--temario", type=Path, help="Temario JSON file (if not in standards metadata)")
    parser.add_argument("--output", type=Path, help="Output JSON file (optional)")
    parser.add_argument("--max-retries", type=int, default=2, help="Retries on failure")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.standards.exists():
        logger.error("File not found: %s", args.standards)
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

    # Find the requested standard
    standard_dict: dict[str, Any] | None = None
    for std in standards_list:
        if std.get("id") == args.standard_id:
            standard_dict = std
            break

    if not standard_dict:
        logger.error("Standard '%s' not found in standards file", args.standard_id)
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

    logger.info("=" * 60)
    logger.info("PROCESSING STANDARD: %s", args.standard_id)
    logger.info("Title: %s", standard_dict.get("titulo"))
    logger.info("=" * 60)

    # Initialize Gemini
    logger.info("Initializing Gemini service...")
    try:
        gemini = load_default_gemini_service()
    except Exception as e:
        logger.error("Failed to initialize Gemini: %s", e)
        sys.exit(1)

    # Generate atoms for this standard
    logger.info("--- Generating Atoms ---")
    result = generate_atoms_for_standard(
        gemini=gemini,
        standard=standard_dict,
        habilidades=habilidades,
        max_retries=args.max_retries,
    )

    if not result.success:
        logger.error("Generation failed: %s", result.error)
        if result.raw_response:
            logger.debug("Raw response: %s", result.raw_response[:500])
        sys.exit(1)

    if not result.atoms:
        logger.error("No atoms generated")
        sys.exit(1)

    logger.info("✓ Generated %d atoms", len(result.atoms))

    # Output results
    if args.output:
        output_path = args.output
    else:
        standard_id_clean = args.standard_id.replace("-", "_")
        output_path = Path(f"tests/atoms/atoms_{standard_id_clean}_test.json")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    atoms_dict = [a.model_dump() for a in result.atoms]
    output_path.write_text(
        json.dumps(atoms_dict, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info("=" * 60)
    logger.info("RESULTS")
    logger.info("=" * 60)
    logger.info("✓ Atoms generated: %d", len(result.atoms))
    logger.info("✓ Output saved to: %s", output_path)
    if result.warnings:
        logger.info("⚠ Warnings: %d", len(result.warnings))
        for w in result.warnings:
            logger.info("  ⚠ %s", w)

    # Print atoms IDs
    logger.info("\nGenerated atoms:")
    for a in result.atoms:
        logger.info("  - %s: %s", a.id, a.titulo)
        logger.info("    Habilidad: %s", a.habilidad_principal)
        logger.info("    Tipo: %s", a.tipo_atomico)


if __name__ == "__main__":
    main()

