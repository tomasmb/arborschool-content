"""Crash-safe checkpoint management for the batch pipeline.

Tracks per-phase status with 5 distinct states to guarantee that
no API spend is ever lost and any interruption is fully recoverable.

All writes use atomic temp-file + rename.
"""

from __future__ import annotations

import json
import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# Phase status progression:
#   pending -> file_uploaded -> submitted -> results_downloaded -> completed
VALID_STATUSES = (
    "pending",
    "file_uploaded",
    "submitted",
    "results_downloaded",
    "completed",
)

# Canonical phase key ordering for the batch pipeline.
# Multi-round phases use suffixed keys (phase_4_r0, phase_4_r1, …).
PHASE_ORDER = [
    "phase_0",
    "phase_1",
    "phase_2",
    "phase_3",
    "phase_4",
    "phase_4b",
    "phase_5",
    "phase_6",
    "phase_78_enhance",
    "phase_78_review",
    "phase_78_correct",
    "phase_78_re_review",
    "phase_9",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------------
# State serialization
# ------------------------------------------------------------------


def new_run_state(
    job_id: str,
    atom_ids: list[str],
) -> dict[str, Any]:
    """Create a fresh batch run state dict."""
    return {
        "job_id": job_id,
        "active_atom_ids": list(atom_ids),
        "failed_atoms": {},
        "phases": {},
        "created_at": _now_iso(),
        "last_updated": _now_iso(),
    }


def new_phase_state() -> dict[str, Any]:
    """Create a fresh phase state dict."""
    return {
        "status": "pending",
        "file_id": None,
        "batch_id": None,
        "input_jsonl": None,
        "results_jsonl": None,
        "jsonl_sha256": None,
        "request_count": 0,
        "metadata": None,
    }


# ------------------------------------------------------------------
# Checkpoint I/O (atomic writes)
# ------------------------------------------------------------------


def load_run_state(checkpoint_path: Path) -> dict[str, Any] | None:
    """Load batch run state from disk.  Returns None if not found."""
    if not checkpoint_path.exists():
        return None
    try:
        text = checkpoint_path.read_text(encoding="utf-8").strip()
        if not text:
            return None
        return json.loads(text)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning(
            "Failed to load checkpoint %s: %s", checkpoint_path, exc,
        )
        return None


def save_run_state(
    checkpoint_path: Path,
    state: dict[str, Any],
) -> None:
    """Atomically save batch run state to disk."""
    state["last_updated"] = _now_iso()
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp = tempfile.mkstemp(
        dir=str(checkpoint_path.parent), suffix=".tmp",
    )
    try:
        with open(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False, default=str)
        Path(tmp).replace(checkpoint_path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


# ------------------------------------------------------------------
# Phase state helpers
# ------------------------------------------------------------------


def get_phase(
    state: dict[str, Any],
    phase_key: str,
) -> dict[str, Any]:
    """Get or create a phase state dict."""
    phases = state.setdefault("phases", {})
    if phase_key not in phases:
        phases[phase_key] = new_phase_state()
    return phases[phase_key]


def update_phase(
    state: dict[str, Any],
    phase_key: str,
    checkpoint_path: Path,
    **updates: Any,
) -> None:
    """Update fields on a phase state and persist immediately."""
    phase = get_phase(state, phase_key)
    for key, value in updates.items():
        phase[key] = value
    save_run_state(checkpoint_path, state)


def is_phase_completed(
    state: dict[str, Any],
    phase_key: str,
) -> bool:
    """Check whether a phase is already completed."""
    phases = state.get("phases", {})
    phase = phases.get(phase_key, {})
    return phase.get("status") == "completed"


def mark_atoms_failed(
    state: dict[str, Any],
    failed: dict[str, str],
    checkpoint_path: Path,
) -> None:
    """Record atom failures and remove them from the active list."""
    for atom_id, reason in failed.items():
        state["failed_atoms"][atom_id] = reason
    active = state["active_atom_ids"]
    state["active_atom_ids"] = [
        a for a in active if a not in failed
    ]
    save_run_state(checkpoint_path, state)


def get_active_atoms(state: dict[str, Any]) -> list[str]:
    """Return the list of atoms still active (not failed)."""
    return list(state.get("active_atom_ids", []))


# ------------------------------------------------------------------
# Consistency checks
# ------------------------------------------------------------------


def validate_checkpoint_consistency(
    state: dict[str, Any],
) -> list[str]:
    """Verify checkpoint is internally consistent.

    Returns a list of error messages (empty if valid).
    Checks: no completed phase may appear after a pending one
    in the canonical order.
    """
    errors: list[str] = []
    phases = state.get("phases", {})
    seen_pending = False

    for key in PHASE_ORDER:
        p = phases.get(key, {})
        status = p.get("status", "pending")

        if seen_pending and status == "completed":
            errors.append(
                f"Phase {key} is completed but a prior "
                f"phase is still pending"
            )
        if status == "pending":
            seen_pending = True

    return errors
