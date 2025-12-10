"""Script para generar átomos para todos los estándares y guardarlos en un archivo canónico.

Usage:
    python -m app.atoms.generate_all_atoms --standards app/data/standards/paes_m1_2026.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path
from typing import Any

from app.atoms.generation import generate_atoms_for_standard
from app.atoms.models import Atom, AtomsMetadata, CanonicalAtomsFile
from app.gemini_client import load_default_gemini_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate atoms for all standards and save to canonical file.",
    )
    parser.add_argument(
        "--standards",
        type=Path,
        required=True,
        help="Input standards JSON file (e.g., app/data/standards/paes_m1_2026.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output atoms JSON file (default: app/data/atoms/{standards_id}_atoms.json)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="Retries on failure per standard (default: 2)",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip standards that already have atoms in output file",
    )
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

    if isinstance(standards_data, list):
        standards_list = standards_data
        metadata_dict: dict[str, Any] = {}
    else:
        standards_list = standards_data.get("standards", [])
        metadata_dict = standards_data.get("metadata", {})

    if not standards_list:
        logger.error("No standards found in file")
        sys.exit(1)

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        # Extract ID from standards metadata or filename
        standards_id = metadata_dict.get("id", args.standards.stem)
        atoms_id = f"{standards_id}_atoms"
        output_dir = args.standards.parent.parent / "atoms"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{atoms_id}.json"

    # Load existing atoms if skip-existing is enabled
    existing_atoms: dict[str, list[Atom]] = {}
    if args.skip_existing and output_path.exists():
        logger.info("Loading existing atoms from: %s", output_path)
        try:
            with output_path.open(encoding="utf-8") as f:
                existing_data = json.load(f)
            if isinstance(existing_data, dict) and "atoms" in existing_data:
                existing_atoms_list = [
                    Atom.model_validate(a) for a in existing_data["atoms"]
                ]
                # Group by standard_id
                for atom in existing_atoms_list:
                    for std_id in atom.standard_ids:
                        if std_id not in existing_atoms:
                            existing_atoms[std_id] = []
                        existing_atoms[std_id].append(atom)
                logger.info(
                    "Found existing atoms for %d standards",
                    len(existing_atoms),
                )
        except Exception as e:
            logger.warning("Failed to load existing atoms: %s", e)

    # Determine temario path
    temario_path_str = metadata_dict.get("source_temario_json", "")
    if not temario_path_str:
        logger.error(
            "No source_temario_json found in standards metadata. "
            "Cannot determine temario path.",
        )
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

    logger.info("=" * 70)
    logger.info("GENERATING ATOMS FOR ALL STANDARDS")
    logger.info("=" * 70)
    logger.info("Standards file: %s", args.standards)
    logger.info("Output file: %s", output_path)
    logger.info("Total standards: %d", len(standards_list))
    logger.info("=" * 70)
    logger.info("")

    all_atoms: list[Atom] = []
    failed_standards: list[str] = []
    skipped_standards: list[str] = []

    for standard_dict in standards_list:
        standard_id = standard_dict.get("id", "unknown")
        standard_title = standard_dict.get("titulo", "unknown")

        # Skip if already exists
        if args.skip_existing and standard_id in existing_atoms:
            logger.info("⏭  Skipping %s (already exists)", standard_id)
            all_atoms.extend(existing_atoms[standard_id])
            skipped_standards.append(standard_id)
            continue

        logger.info("-" * 70)
        logger.info("Processing: %s", standard_id)
        logger.info("Title: %s", standard_title)
        logger.info("-" * 70)

        result = generate_atoms_for_standard(
            gemini=gemini,
            standard=standard_dict,
            habilidades=habilidades,
            max_retries=args.max_retries,
        )

        if not result.success:
            logger.error("❌ Generation failed for %s: %s", standard_id, result.error)
            if result.raw_response:
                logger.debug("Raw response: %s", result.raw_response[:500])
            failed_standards.append(standard_id)
        elif not result.atoms:
            logger.error("❌ No atoms generated for %s", standard_id)
            failed_standards.append(standard_id)
        else:
            logger.info(
                "✓ Generated %d atoms for %s",
                len(result.atoms),
                standard_id,
            )
            all_atoms.extend(result.atoms)

        if result.warnings:
            for w in result.warnings:
                logger.warning("  ⚠ %s", w)
        logger.info("")

    # Build metadata
    # Use relative path for source_standards_json if possible
    try:
        source_standards_path = str(args.standards.relative_to(Path.cwd()))
    except ValueError:
        # If not relative, use absolute path
        source_standards_path = str(args.standards)

    atoms_metadata = AtomsMetadata(
        id=metadata_dict.get("id", args.standards.stem) + "_atoms",
        proceso_admision=metadata_dict.get("proceso_admision", 2026),
        tipo_aplicacion=metadata_dict.get("tipo_aplicacion", "unknown"),
        nombre_prueba=metadata_dict.get("nombre_prueba", "unknown"),
        source_standards_json=source_standards_path,
        generated_with="gemini-3-pro",
        version=date.today().isoformat(),
    )

    # Build canonical file
    canonical_file = CanonicalAtomsFile(
        metadata=atoms_metadata,
        atoms=all_atoms,
    )

    # Save to file
    logger.info("=" * 70)
    logger.info("SAVING CANONICAL ATOMS FILE")
    logger.info("=" * 70)
    logger.info("Output: %s", output_path)
    logger.info("Total atoms: %d", len(all_atoms))
    logger.info("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(
            canonical_file.model_dump(mode="json"),
            f,
            ensure_ascii=False,
            indent=2,
        )

    logger.info("✅ File saved successfully!")

    # Final summary
    logger.info("")
    logger.info("=" * 70)
    logger.info("FINAL SUMMARY")
    logger.info("=" * 70)
    logger.info("✓ Successfully generated: %d standards", len(standards_list) - len(failed_standards) - len(skipped_standards))
    if skipped_standards:
        logger.info("⏭  Skipped (existing): %d standards", len(skipped_standards))
    if failed_standards:
        logger.error("❌ Failed: %d standards", len(failed_standards))
        for std_id in failed_standards:
            logger.error("  - %s", std_id)
    logger.info("✓ Total atoms: %d", len(all_atoms))
    logger.info("✓ Output file: %s", output_path)
    logger.info("=" * 70)

    if failed_standards:
        logger.error("")
        logger.error("❌ Some generations failed. Please check logs for details.")
        sys.exit(1)
    else:
        logger.info("")
        logger.info("✅ All generations completed successfully!")


if __name__ == "__main__":
    main()

