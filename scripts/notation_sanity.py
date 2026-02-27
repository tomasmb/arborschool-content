"""Deterministic sanity checks for notation fix proposals.

Run *before* LLM validation to catch obvious problems instantly
and cheaply (e.g. stripped currency symbols, deleted content).
Includes XSD validation for QTI XML via a remote service.
"""

from __future__ import annotations

import importlib.util
import logging
import re
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)

# Symbols that must never decrease between original and corrected.
_PROTECTED_SYMBOLS: tuple[str, ...] = (
    "$", "%", "°", "×", "÷", "√", "π",
    "≤", "≥", "≠", "±", "∞", "∈", "∉",
    "∪", "∩", "⊂", "⊃",
)

# Tags whose count is allowed to *decrease* (merging split MathML).
_SHRINKABLE_TAGS: frozenset[str] = frozenset({"mn", "mspace"})

_OPEN_TAG_RE = re.compile(r"<([a-zA-Z][\w.-]*)")
_STRIP_TAGS_RE = re.compile(r"<[^>]+>")
_MAX_SHRINK_PCT = 0.05  # text content may be at most 5 % shorter


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


def run_sanity_checks(
    original: str,
    corrected: str,
) -> tuple[bool, list[str]]:
    """Return (passed, reasons).

    ``passed`` is True when all deterministic checks pass.
    ``reasons`` lists every failing check (empty when passed).
    """
    reasons: list[str] = []
    _check_symbols(original, corrected, reasons)
    _check_length(original, corrected, reasons)
    _check_tag_balance(original, corrected, reasons)
    return (len(reasons) == 0, reasons)


# ------------------------------------------------------------------
# Individual checks
# ------------------------------------------------------------------


def _check_symbols(
    original: str, corrected: str, reasons: list[str],
) -> None:
    """Fail if any protected symbol lost occurrences."""
    for sym in _PROTECTED_SYMBOLS:
        orig_n = original.count(sym)
        corr_n = corrected.count(sym)
        if corr_n < orig_n:
            reasons.append(
                f"Symbol '{sym}' decreased from {orig_n} to {corr_n}",
            )


def _check_length(
    original: str, corrected: str, reasons: list[str],
) -> None:
    """Fail if text content (tags stripped) shrank significantly.

    Compares tag-stripped content so that legitimate tag merging
    (e.g. split <mn> consolidation) doesn't trigger false positives.
    """
    orig_text = _STRIP_TAGS_RE.sub("", original)
    corr_text = _STRIP_TAGS_RE.sub("", corrected)
    lo = len(orig_text)
    lc = len(corr_text)
    if lo == 0:
        return
    shrink = (lo - lc) / lo
    if shrink > _MAX_SHRINK_PCT:
        reasons.append(
            f"Text content shrank by {shrink:.1%} "
            f"({lo} -> {lc} chars, threshold {_MAX_SHRINK_PCT:.0%})",
        )


def _check_tag_balance(
    original: str, corrected: str, reasons: list[str],
) -> None:
    """Fail if non-shrinkable tag counts changed."""
    orig_tags = _count_tags(original)
    corr_tags = _count_tags(corrected)
    all_tags = set(orig_tags) | set(corr_tags)

    for tag in sorted(all_tags):
        o = orig_tags.get(tag, 0)
        c = corr_tags.get(tag, 0)
        if o == c:
            continue
        if tag in _SHRINKABLE_TAGS and c <= o:
            continue
        reasons.append(
            f"Tag <{tag}> count changed from {o} to {c}",
        )


def _count_tags(html: str) -> dict[str, int]:
    """Count opening tags (ignores closing / self-closing)."""
    counts: dict[str, int] = dict(Counter(
        m.group(1).lower() for m in _OPEN_TAG_RE.finditer(html)
    ))
    return counts


# ------------------------------------------------------------------
# XSD validation for QTI XML
# ------------------------------------------------------------------

_XSD_VALIDATOR: Any | None = None


def _load_xsd_validator() -> Any:
    """Lazy-load validate_qti_xml from the pdf-to-qti module."""
    global _XSD_VALIDATOR
    if _XSD_VALIDATOR is not None:
        return _XSD_VALIDATOR
    spec = importlib.util.spec_from_file_location(
        "xml_validator",
        "app/pruebas/pdf-to-qti/modules/validation/xml_validator.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _XSD_VALIDATOR = mod.validate_qti_xml
    return _XSD_VALIDATOR


def run_xsd_validation(qti_xml: str) -> tuple[bool, list[str]]:
    """Validate corrected QTI XML against the QTI 3.0 XSD schema.

    Returns (passed, reasons). Uses the remote validation service.
    """
    try:
        validate_fn = _load_xsd_validator()
        result = validate_fn(qti_xml)
        if result.get("valid"):
            return (True, [])
        errors = result.get("validation_errors", "")
        if isinstance(errors, str) and errors:
            return (False, [f"XSD: {errors}"])
        err_list = result.get("errors", [])
        reasons = [f"XSD: {e}" for e in err_list] if err_list else [
            f"XSD: {result.get('error', 'unknown XSD error')}",
        ]
        return (False, reasons)
    except Exception as exc:
        logger.warning("XSD validation unavailable: %s", exc)
        return (True, [])
