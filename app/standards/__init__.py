"""Standards generation pipeline.

Transforms structured temario JSON into canonical standards JSON,
as specified in `docs/standards-from-temarios.md`.

Two-stage validation ensures high-quality output:
1. Per-unidad: Immediate validation after each standard
2. Per-eje: Cross-standard validation for coverage and consistency

Usage:
    from app.standards import run_standards_pipeline, PipelineConfig
    from pathlib import Path

    config = PipelineConfig(temario_path=Path("path/to/temario.json"))
    result = run_standards_pipeline(config)

CLI:
    python -m app.standards.pipeline --temario path/to/temario.json
"""

from __future__ import annotations

from app.standards.models import (
    CanonicalStandardsFile,
    Standard,
    StandardsMetadata,
)
from app.standards.pipeline import (
    PipelineConfig,
    PipelineResult,
    run_standards_pipeline,
)

__all__ = [
    "CanonicalStandardsFile",
    "PipelineConfig",
    "PipelineResult",
    "Standard",
    "StandardsMetadata",
    "run_standards_pipeline",
]

