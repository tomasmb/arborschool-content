"""Thread-safe progress and cost reporting for the pipeline runner.

Prints ``[PROGRESS] completed/total`` and ``[COST] $X.XXXX``
markers to stdout.  These are parsed by
``api.services.pipeline_runner`` to update job progress and cost.

Shared by generator.py (Phase 4), validators.py (Phases 6, 9),
pipeline.py (Phase 7-8), variant pipeline, and tagging.
"""

from __future__ import annotations

import sys
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.llm_clients import LLMUsage

# Stdout prefixes parsed by pipeline_runner.py
PROGRESS_PREFIX = "[PROGRESS]"
COST_PREFIX = "[COST]"

# Lock for atomic stdout writes from concurrent workers
_progress_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Per-1M-token pricing (input / output) — update when models change
# ---------------------------------------------------------------------------
_MODEL_PRICING: dict[str, tuple[float, float]] = {
    "gpt-5.1": (2.00, 8.00),
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
}

# Default price per 1M tokens when model is unknown
_DEFAULT_PRICING = (2.00, 8.00)


def report_progress(completed: int, total: int) -> None:
    """Print a progress marker for the pipeline runner.

    Thread-safe: uses a lock so concurrent workers don't
    interleave progress lines.

    Args:
        completed: Number of items finished so far.
        total: Total number of items to process.
    """
    with _progress_lock:
        print(
            f"{PROGRESS_PREFIX} {completed}/{total}",
            flush=True,
            file=sys.stdout,
        )


def report_cost(cost_usd: float) -> None:
    """Print a cost marker for the pipeline runner.

    Called once at the end of a pipeline run.

    Args:
        cost_usd: Total estimated cost in USD.
    """
    with _progress_lock:
        print(
            f"{COST_PREFIX} ${cost_usd:.4f}",
            flush=True,
            file=sys.stdout,
        )


def print_pipeline_header(atom_id: str) -> None:
    """Print pipeline header to console."""
    print(f"\n{'=' * 60}")
    print("PIPELINE: Generación de Preguntas por Átomo")
    print(f"Átomo: {atom_id}")
    print(f"{'=' * 60}\n")


def print_pipeline_summary(result: object) -> None:
    """Print pipeline summary to console.

    Args:
        result: PipelineResult (untyped to avoid circular import).
    """
    print(f"\n{'=' * 60}")
    print("RESUMEN")
    print(f"{'=' * 60}")
    print(f"Átomo: {result.atom_id}")  # type: ignore[attr-defined]
    print(f"Planificados:       {result.total_planned}")  # type: ignore[attr-defined]
    print(f"Generados:          {result.total_generated}")  # type: ignore[attr-defined]
    print(f"Pasaron dedupe:     {result.total_passed_dedupe}")  # type: ignore[attr-defined]
    print(f"Pasaron validación: {result.total_passed_base_validation}")  # type: ignore[attr-defined]
    print(f"Pasaron feedback:   {result.total_passed_feedback}")  # type: ignore[attr-defined]
    print(f"Finales:            {result.total_final}")  # type: ignore[attr-defined]

    for phase in result.phase_results:  # type: ignore[attr-defined]
        if phase.errors:
            print(f"\n  Errores [{phase.phase_name}]:")
            for err in phase.errors:
                print(f"    - {err}")
        if phase.warnings:
            print(f"\n  Advertencias [{phase.phase_name}]:")
            for w in phase.warnings:
                print(f"    - {w}")

    print(f"{'=' * 60}\n")


class CostAccumulator:
    """Thread-safe accumulator for LLM token usage across a run.

    Usage::

        acc = CostAccumulator()
        # ... in workers:
        acc.add(llm_response.usage)
        # ... at end:
        acc.report()  # prints [COST] $X.XXXX
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._input_tokens = 0
        self._output_tokens = 0
        self._model: str = ""

    def add(self, usage: LLMUsage) -> None:
        """Accumulate tokens from a single LLM call."""
        with self._lock:
            self._input_tokens += usage.input_tokens
            self._output_tokens += usage.output_tokens
            if usage.model and not self._model:
                self._model = usage.model

    @property
    def total_cost_usd(self) -> float:
        """Compute estimated cost from accumulated tokens."""
        pricing = _MODEL_PRICING.get(self._model, _DEFAULT_PRICING)
        input_cost = (self._input_tokens / 1_000_000) * pricing[0]
        output_cost = (self._output_tokens / 1_000_000) * pricing[1]
        return input_cost + output_cost

    def report(self) -> None:
        """Print ``[COST] $X.XXXX`` to stdout for the runner."""
        report_cost(self.total_cost_usd)
