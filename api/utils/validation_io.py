"""Shared helpers for reading and interpreting validation_result.json.

Every consumer that needs to check validation status should use these
helpers instead of re-implementing the file-read + JSON-parse + can_sync
check inline.  This guarantees a single source of truth for:

- What "validated" means  (can_sync is True)
- What "failed" means     (final_validation ran AND can_sync is False)
- What "pending" means    (enriched but final_validation hasn't run yet)
"""

from __future__ import annotations

import json
from pathlib import Path

VALIDATION_RESULT_FILENAME = "validation_result.json"


def read_validation_data(folder: Path) -> dict | None:
    """Read and parse validation_result.json from *folder*.

    Returns the parsed dict, or None if the file is missing or
    unreadable (corrupt JSON, permission error, etc.).
    """
    path = folder / VALIDATION_RESULT_FILENAME
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def is_can_sync(vdata: dict | None) -> bool:
    """True when validation passed and the item is ready to sync.

    Returns True if either:
    - Automated validation passed (can_sync=True), or
    - A human marked it as manually validated (manually_validated=True)
    """
    if vdata is None:
        return False
    if vdata.get("manually_validated", False):
        return True
    return bool(vdata.get("can_sync", False))


def has_final_validation(vdata: dict | None) -> bool:
    """True when the final_validation stage has actually been executed.

    Distinguishes 'validation ran and failed' from 'enrichment wrote
    the file but validation hasn't run yet'.
    """
    if vdata is None:
        return False
    stages = vdata.get("stages", {})
    return "final_validation" in stages


def validation_failed(vdata: dict | None) -> bool:
    """True when final validation ran and the item did NOT pass.

    Returns False if validation hasn't run yet (pending) or if
    there is no validation data at all.
    """
    if vdata is None:
        return False
    return not is_can_sync(vdata) and has_final_validation(vdata)
