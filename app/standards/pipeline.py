"""Standards generation pipeline orchestrator.

Transforms temario JSON to canonical standards JSON using two-stage validation:
- Stage 1 (per-unidad): Generate → Validate immediately → Retry if needed
- Stage 2 (per-eje): Cross-standard validation for coverage and consistency

Usage:
    python -m app.standards.pipeline --temario path/to/temario.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from app.gemini_client import GeminiService, load_default_gemini_service
from app.standards.generation import EjeGenerationResult, generate_standards_for_eje
from app.standards.models import (
    CanonicalStandardsFile,
    Standard,
    StandardsMetadata,
)
from app.standards.prompts import EJE_PREFIX_MAP
from app.standards.validation import run_full_eje_validation
from app.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "standards"


# -----------------------------------------------------------------------------
# Data classes
# -----------------------------------------------------------------------------

@dataclass
class PipelineConfig:
    """Configuration for the standards generation pipeline."""

    temario_path: Path
    output_path: Path | None = None
    max_retries: int = 2
    skip_per_unidad_validation: bool = False
    skip_per_eje_validation: bool = False
    verbose: bool = False


@dataclass
class PipelineResult:
    """Result of running the full pipeline."""

    success: bool
    output_path: Path | None = None
    standards_count: int = 0
    generation_errors: list[str] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# -----------------------------------------------------------------------------
# Main pipeline
# -----------------------------------------------------------------------------

def run_standards_pipeline(config: PipelineConfig) -> PipelineResult:
    """
    Run the full standards generation pipeline.

    Returns PipelineResult with success status and any errors/warnings.
    """
    result = PipelineResult(success=False)

    # Load temario
    logger.info("=" * 60)
    logger.info("LOADING TEMARIO: %s", config.temario_path)
    logger.info("=" * 60)

    temario = _load_temario_safe(config.temario_path, result)
    if temario is None:
        return result

    # Initialize Gemini
    logger.info("Initializing Gemini service...")
    gemini = _init_gemini_safe(result)
    if gemini is None:
        return result

    # Process each eje
    all_standards = _process_all_ejes(config, temario, gemini, result)

    # Export if no errors
    if all_standards and not result.generation_errors and not result.validation_errors:
        _export_standards(config, temario, all_standards, result)

    result.standards_count = len(all_standards)
    return result


# -----------------------------------------------------------------------------
# Pipeline steps
# -----------------------------------------------------------------------------

def _load_temario_safe(
    path: Path,
    result: PipelineResult,
) -> dict[str, Any] | None:
    """Load temario, adding errors to result on failure."""
    try:
        temario = _load_temario(path)
        logger.info("✓ Temario loaded")
        return temario
    except Exception as e:
        result.generation_errors.append(f"Failed to load temario: {e}")
        return None


def _init_gemini_safe(result: PipelineResult) -> GeminiService | None:
    """Initialize Gemini service, adding errors to result on failure."""
    try:
        gemini = load_default_gemini_service()
        logger.info("✓ Gemini initialized")
        return gemini
    except Exception as e:
        result.generation_errors.append(f"Failed to initialize Gemini: {e}")
        return None


def _process_all_ejes(
    config: PipelineConfig,
    temario: dict[str, Any],
    gemini: GeminiService,
    result: PipelineResult,
) -> list[Standard]:
    """Process all ejes and return collected standards."""
    all_standards: list[Standard] = []
    habilidades = temario["habilidades"]
    conocimientos = temario["conocimientos"]

    for eje_key in EJE_PREFIX_MAP:
        if eje_key not in conocimientos:
            continue

        unidades = conocimientos[eje_key].get("unidades", [])
        if not unidades:
            continue

        logger.info("\n" + "=" * 60)
        logger.info("EJE: %s (%d unidades)", eje_key.upper(), len(unidades))
        logger.info("=" * 60)

        eje_standards = _process_single_eje(
            config, gemini, eje_key, unidades, habilidades, conocimientos, result
        )
        all_standards.extend(eje_standards)

    return all_standards


def _process_single_eje(
    config: PipelineConfig,
    gemini: GeminiService,
    eje_key: str,
    unidades: list[dict[str, Any]],
    habilidades: dict[str, Any],
    conocimientos: dict[str, Any],
    result: PipelineResult,
) -> list[Standard]:
    """Process a single eje: generate + validate. Returns standards for this eje."""
    # Stage 1: Generation with per-unidad validation
    logger.info("--- Stage 1: Generation ---")
    eje_result: EjeGenerationResult = generate_standards_for_eje(
        gemini=gemini,
        eje_key=eje_key,
        unidades=unidades,
        habilidades=habilidades,
        starting_number=1,
        max_retries=config.max_retries,
        validate_per_unidad=not config.skip_per_unidad_validation,
    )

    result.generation_errors.extend(eje_result.errors)
    result.warnings.extend(eje_result.warnings)

    if eje_result.errors or not eje_result.standards:
        logger.error("Stage 1 failed for eje '%s'", eje_key)
        return []

    logger.info("✓ Stage 1: %d standards generated", len(eje_result.standards))

    # Stage 2: Per-eje validation
    if config.skip_per_eje_validation:
        logger.info("Stage 2 skipped")
        return eje_result.standards

    logger.info("--- Stage 2: Cross-Standard Validation ---")
    validation_result = run_full_eje_validation(
        gemini=gemini,
        standards=eje_result.standards,
        eje_key=eje_key,
        original_unidades=unidades,
        habilidades=habilidades,
        temario_conocimientos=conocimientos,
    )

    # Collect issues
    for issue in validation_result.issues:
        msg = f"[{issue.standard_id or eje_key}] {issue.issue_type}: {issue.description}"
        if issue.severity == "error":
            result.validation_errors.append(msg)
        else:
            result.warnings.append(msg)

    # Apply corrections if provided
    if validation_result.corrected_standards:
        logger.info("Applying %d corrections", len(validation_result.corrected_standards))
        return _apply_corrections(eje_result.standards, validation_result.corrected_standards)

    return eje_result.standards


def _apply_corrections(
    originals: list[Standard],
    corrections: list[Standard],
) -> list[Standard]:
    """Replace originals with corrections where IDs match."""
    corrected_ids = {s.id for s in corrections}
    kept = [s for s in originals if s.id not in corrected_ids]
    return kept + corrections


def _export_standards(
    config: PipelineConfig,
    temario: dict[str, Any],
    standards: list[Standard],
    result: PipelineResult,
) -> None:
    """Export standards to JSON file."""
    logger.info("\n--- Exporting %d Standards ---", len(standards))

    output_path = config.output_path or _default_output_path(temario)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        canonical = _build_canonical_file(temario, standards, config.temario_path)
        CanonicalStandardsFile.model_validate(canonical.model_dump())  # Final check

        output_path.write_text(
            json.dumps(canonical.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        logger.info("✓ Wrote: %s", output_path)
        result.success = True
        result.output_path = output_path

    except Exception as e:
        result.generation_errors.append(f"Export failed: {e}")
        logger.exception("Export failed")


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _load_temario(path: Path) -> dict[str, Any]:
    """Load and validate basic temario structure."""
    with path.open(encoding="utf-8") as f:
        temario = json.load(f)

    required = {"id", "habilidades", "conocimientos"}
    missing = required - set(temario.keys())
    if missing:
        raise ValueError(f"Missing keys: {missing}")

    return temario


def _default_output_path(temario: dict[str, Any]) -> Path:
    """Generate default output path based on temario ID."""
    return DEFAULT_OUTPUT_DIR / f"{temario.get('id', 'unknown')}.json"


def _build_canonical_file(
    temario: dict[str, Any],
    standards: list[Standard],
    source_path: Path,
) -> CanonicalStandardsFile:
    """Build canonical standards file from generated standards."""
    # Handle tipo_aplicacion: can be string or list
    tipo_aplicacion = temario.get("tipo_aplicacion", "unknown")
    if isinstance(tipo_aplicacion, list):
        tipo_aplicacion = ", ".join(tipo_aplicacion)  # Convert list to comma-separated string

    metadata = StandardsMetadata(
        id=temario.get("id", "unknown"),
        proceso_admision=temario.get("proceso_admision", 2026),
        tipo_aplicacion=tipo_aplicacion,
        nombre_prueba=temario.get("nombre_prueba", "Unknown"),
        source_temario_json=str(source_path),
        generated_with="gemini-3-pro-preview",
        version=datetime.now().strftime("%Y-%m-%d"),
    )

    return CanonicalStandardsFile(
        metadata=metadata,
        standards=sorted(standards, key=lambda s: s.id),
    )


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate canonical standards JSON from DEMRE temario.",
    )
    parser.add_argument("--temario", type=Path, required=True, help="Input temario JSON")
    parser.add_argument("--output", type=Path, help="Output standards JSON")
    parser.add_argument("--max-retries", type=int, default=2, help="Retries per unidad")
    parser.add_argument("--skip-per-unidad-validation", action="store_true")
    parser.add_argument("--skip-per-eje-validation", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    setup_logging(verbose=args.verbose)

    if not args.temario.exists():
        logger.error("File not found: %s", args.temario)
        sys.exit(1)

    config = PipelineConfig(
        temario_path=args.temario,
        output_path=args.output,
        max_retries=args.max_retries,
        skip_per_unidad_validation=args.skip_per_unidad_validation,
        skip_per_eje_validation=args.skip_per_eje_validation,
        verbose=args.verbose,
    )

    result = run_standards_pipeline(config)
    _print_results(result)
    sys.exit(0 if result.success else 1)


def _print_results(result: PipelineResult) -> None:
    """Print final results to stdout."""
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    if result.success:
        print(f"✓ SUCCESS: {result.standards_count} standards → {result.output_path}")
    else:
        print(f"✗ FAILED: {result.standards_count} standards (with errors)")

    if result.generation_errors:
        print(f"\nGeneration Errors ({len(result.generation_errors)}):")
        for err in result.generation_errors:
            print(f"  ✗ {err}")

    if result.validation_errors:
        print(f"\nValidation Errors ({len(result.validation_errors)}):")
        for err in result.validation_errors:
            print(f"  ✗ {err}")

    if result.warnings:
        print(f"\nWarnings ({len(result.warnings)}):")
        for w in result.warnings:
            print(f"  ⚠ {w}")


if __name__ == "__main__":
    main()
