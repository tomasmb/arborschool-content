"""Persist and reload fix-pipeline results.

Saves ``FixResult`` objects to timestamped JSON files so that:
  - Dry-run results can be reviewed later.
  - Successful results can be applied without re-running LLM calls.
  - Failed actions can be retried selectively.

Storage location: ``app/data/atoms/fix_results/``.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.atoms.fixing.models import FixResult
from app.utils.paths import ATOM_FIX_RESULTS_DIR

logger = logging.getLogger(__name__)

# File naming convention: fix_run_YYYYMMDD_HHMMSS.json
_FILE_PREFIX = "fix_run_"
_FILE_SUFFIX = ".json"
_TIMESTAMP_FMT = "%Y%m%d_%H%M%S"


# -----------------------------------------------------------------------------
# Save
# -----------------------------------------------------------------------------


def save_results(
    results: list[FixResult],
    *,
    run_dir: Path | None = None,
) -> Path:
    """Save all fix results to a timestamped JSON file.

    Args:
        results: All FixResults from a pipeline run.
        run_dir: Override storage directory (defaults to ATOM_FIX_RESULTS_DIR).

    Returns:
        Path to the saved JSON file.
    """
    out_dir = run_dir or ATOM_FIX_RESULTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(tz=timezone.utc).strftime(_TIMESTAMP_FMT)
    filename = f"{_FILE_PREFIX}{ts}{_FILE_SUFFIX}"
    path = out_dir / filename

    succeeded = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)

    payload: dict[str, Any] = {
        "timestamp": ts,
        "total": len(results),
        "succeeded": succeeded,
        "failed": failed,
        "results": [r.to_dict() for r in results],
    }

    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    # Trailing newline.
    with path.open("a", encoding="utf-8") as f:
        f.write("\n")

    logger.info("Saved %d results to %s", len(results), path)
    return path


# -----------------------------------------------------------------------------
# Load
# -----------------------------------------------------------------------------


def load_latest_results(
    *,
    run_dir: Path | None = None,
) -> tuple[list[FixResult], Path] | None:
    """Load the most recent saved results.

    Args:
        run_dir: Override storage directory (defaults to ATOM_FIX_RESULTS_DIR).

    Returns:
        Tuple of (results, file_path), or None if no saved runs exist.
    """
    out_dir = run_dir or ATOM_FIX_RESULTS_DIR
    files = sorted(
        out_dir.glob(f"{_FILE_PREFIX}*{_FILE_SUFFIX}"),
        reverse=True,
    )
    if not files:
        return None
    return load_results(files[0]), files[0]


def load_results(path: Path) -> list[FixResult]:
    """Load fix results from a specific JSON file.

    Args:
        path: Path to a ``fix_run_*.json`` file.

    Returns:
        List of FixResult objects.
    """
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    return [FixResult.from_dict(r) for r in data["results"]]


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def get_failed_actions_from_latest(
    *,
    run_dir: Path | None = None,
) -> tuple[list[FixResult], Path] | None:
    """Load only the failed results from the most recent run.

    Returns:
        Tuple of (failed_results, file_path), or None if no saved runs.
    """
    loaded = load_latest_results(run_dir=run_dir)
    if loaded is None:
        return None
    results, path = loaded
    failed = [r for r in results if not r.success]
    return failed, path
