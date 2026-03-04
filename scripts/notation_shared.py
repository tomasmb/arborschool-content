"""Shared helpers for sync-scoped QA scan/confirm scripts."""

from __future__ import annotations

from typing import Any

from app.prompts.notation_check import ISSUE_CATEGORIES


def is_lesson_source(source: str) -> bool:
    return source in {"lesson", "mini-class"}


def normalize_confirmed_issues(
    confirmed: Any,
    *,
    default_check_name: str = "content_quality_check",
) -> list[dict]:
    if not isinstance(confirmed, list):
        return []
    out: list[dict] = []
    for ci in confirmed:
        if not isinstance(ci, dict):
            continue
        if ci.get("category") not in ISSUE_CATEGORIES:
            ci["category"] = "manual_fix"
        ci.setdefault("check_name", default_check_name)
        ci.setdefault("severity", "non_blocking")
        ci.setdefault("evidence", "")
        ci.setdefault("decision", "confirm")
        out.append(ci)
    return out


def normalize_rejected_issues(rejected: Any) -> list[dict]:
    if not isinstance(rejected, list):
        return []
    out: list[dict] = []
    for ri in rejected:
        if not isinstance(ri, dict):
            continue
        ri.setdefault("decision", "reject")
        out.append(ri)
    return out
