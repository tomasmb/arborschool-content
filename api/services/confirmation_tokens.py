"""Confirmation tokens for AI pipeline cost approval.

Tokens prove the user has seen a cost estimate before running
an expensive pipeline. Generated after estimate, verified before run.
"""

from __future__ import annotations

import hashlib
import secrets
from typing import Any


def generate_confirmation_token(
    pipeline_id: str, params: dict[str, Any],
) -> str:
    """Generate a confirmation token tied to pipeline + params."""
    salt = secrets.token_hex(8)
    content = f"{pipeline_id}:{sorted(params.items())}:{salt}"
    token_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    return f"{salt}:{token_hash}"


def verify_confirmation_token(
    token: str,
    pipeline_id: str,
    params: dict[str, Any],
) -> bool:
    """Verify a confirmation token (simplified format check)."""
    if not token or ":" not in token:
        return False
    parts = token.split(":")
    return (
        len(parts) == 2
        and len(parts[0]) == 16
        and len(parts[1]) == 16
    )
