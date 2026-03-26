"""Assessment variant generation pipeline.

This module provides tools for generating pedagogically-sound variant
questions from source exemplars. Each variant tests the same concept
as the original while using different scenarios, contexts, and numbers.
"""

from app.question_variants.contracts import (
    build_construct_contract,
    build_structural_profile,
)
from app.question_variants.models import (
    PipelineConfig,
    SourceQuestion,
    ValidationResult,
    VariantBlueprint,
    VariantQuestion,
)
from app.question_variants.pipeline import (
    BatchVariantPipeline,
    SyncVariantPipeline,
)
from app.question_variants.variant_generator import VariantGenerator
from app.question_variants.variant_planner import VariantPlanner
from app.question_variants.variant_validator import VariantValidator

__all__ = [
    "SourceQuestion",
    "VariantQuestion",
    "VariantBlueprint",
    "ValidationResult",
    "PipelineConfig",
    "VariantPlanner",
    "VariantGenerator",
    "VariantValidator",
    "BatchVariantPipeline",
    "SyncVariantPipeline",
    "build_construct_contract",
    "build_structural_profile",
]
