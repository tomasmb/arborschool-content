"""Thread-safe progress reporting for the pipeline runner.

Prints ``[PROGRESS] completed/total`` markers to stdout that are
parsed by ``api.services.pipeline_runner`` to update job progress.

Shared by generator.py (Phase 4) and validators.py (Phases 6, 9).
"""

from __future__ import annotations

import sys
import threading

# Stdout prefix parsed by pipeline_runner.py (_PROGRESS_RE)
PROGRESS_PREFIX = "[PROGRESS]"

# Lock for atomic stdout writes from concurrent workers
_progress_lock = threading.Lock()


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
