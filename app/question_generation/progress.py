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
