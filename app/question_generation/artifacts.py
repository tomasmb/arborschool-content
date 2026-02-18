"""Stale artifact detection and cleanup for the question pipeline.

When re-running an earlier phase, downstream checkpoints, generated
items, and the pipeline report become stale. This module detects
and removes those outdated artifacts.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Downstream checkpoint mapping
# ---------------------------------------------------------------------------

# Phase group -> checkpoint phases that become stale when re-running.
# Running a phase invalidates everything downstream.
_DOWNSTREAM_CHECKPOINTS: dict[str, list[tuple[int, str]]] = {
    "all": [
        (1, "enrichment"), (3, "plan"), (4, "generation"),
        (6, "base_validation"), (8, "feedback"),
        (9, "final_validation"),
    ],
    "enrich": [
        (3, "plan"), (4, "generation"),
        (6, "base_validation"), (8, "feedback"),
        (9, "final_validation"),
    ],
    "plan": [
        (4, "generation"), (6, "base_validation"),
        (8, "feedback"), (9, "final_validation"),
    ],
    "generate": [
        (6, "base_validation"), (8, "feedback"),
        (9, "final_validation"),
    ],
    "validate": [(8, "feedback"), (9, "final_validation")],
    "feedback": [(9, "final_validation")],
    "final_validate": [],
}

# Phase groups that always clear items/ and pipeline_report.json.
# Only "final_validate" leaves them untouched.
_CLEARS_ITEMS = frozenset(
    {"all", "enrich", "plan", "generate", "validate", "feedback"},
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_stale_artifacts(
    atom_id: str,
    phase_group: str,
) -> dict:
    """Detect downstream artifacts that would be deleted.

    Scans the atom's output directory and returns what exists
    downstream of the given phase group.

    Args:
        atom_id: Atom identifier.
        phase_group: Phase group about to run.

    Returns:
        Dict with keys: checkpoint_files, item_count,
        has_report, has_stale_data.
    """
    from app.utils.paths import QUESTION_GENERATION_DIR

    output_dir = QUESTION_GENERATION_DIR / atom_id
    return _scan_stale(output_dir, phase_group)


def clean_stale_artifacts(
    atom_id: str,
    phase_group: str,
) -> None:
    """Delete downstream artifacts before re-running a phase.

    Removes stale checkpoints, items, and the pipeline report
    so a fresh run starts clean.

    Args:
        atom_id: Atom identifier.
        phase_group: Phase group about to run.
    """
    from app.utils.paths import QUESTION_GENERATION_DIR

    output_dir = QUESTION_GENERATION_DIR / atom_id
    _delete_stale(output_dir, phase_group)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _scan_stale(
    output_dir: Path,
    phase_group: str,
) -> dict:
    """Scan for downstream artifacts that exist on disk."""
    ckpt_dir = output_dir / "checkpoints"
    items_dir = output_dir / "items"
    report_path = output_dir / "pipeline_report.json"

    # Downstream checkpoint files that exist on disk
    checkpoint_files: list[str] = []
    for phase_num, phase_name in _DOWNSTREAM_CHECKPOINTS.get(
        phase_group, [],
    ):
        fname = f"phase_{phase_num}_{phase_name}.json"
        if (ckpt_dir / fname).exists():
            checkpoint_files.append(fname)

    # Count XML items
    item_count = 0
    if phase_group in _CLEARS_ITEMS and items_dir.exists():
        item_count = len(list(items_dir.glob("*.xml")))

    # Pipeline report
    has_report = (
        phase_group in _CLEARS_ITEMS and report_path.exists()
    )

    # The report is always overwritten at the end of a run, so
    # it alone doesn't warrant a warning — only flag when there
    # are also stale checkpoints or items to delete.
    has_stale = bool(checkpoint_files or item_count > 0)

    return {
        "checkpoint_files": checkpoint_files,
        "item_count": item_count,
        "has_report": has_report,
        "has_stale_data": has_stale,
    }


def _delete_stale(
    output_dir: Path,
    phase_group: str,
) -> None:
    """Remove downstream checkpoints, items, and report."""
    ckpt_dir = output_dir / "checkpoints"
    items_dir = output_dir / "items"
    report_path = output_dir / "pipeline_report.json"

    # Delete downstream checkpoint files
    for phase_num, phase_name in _DOWNSTREAM_CHECKPOINTS.get(
        phase_group, [],
    ):
        path = ckpt_dir / f"phase_{phase_num}_{phase_name}.json"
        if path.exists():
            path.unlink()
            logger.info(
                "Deleted stale checkpoint: %s", path.name,
            )

    # Clear items directory
    if phase_group in _CLEARS_ITEMS and items_dir.exists():
        for xml_file in items_dir.glob("*.xml"):
            xml_file.unlink()
        logger.info("Cleared items/ directory")

    # Remove pipeline report
    if phase_group in _CLEARS_ITEMS and report_path.exists():
        report_path.unlink()
        logger.info("Deleted stale pipeline_report.json")
