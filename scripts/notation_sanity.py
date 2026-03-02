"""Deterministic sanity checks for notation fix proposals.

Run *before* LLM validation to catch obvious problems instantly
and cheaply (e.g. stripped currency symbols, deleted content).
Includes hard invariant checks (answer key, choice set, MathML
equivalence) and XSD validation for QTI XML.
"""

from __future__ import annotations

import importlib.util
import logging
import re
import xml.etree.ElementTree as ET
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)

# Symbols that must never decrease between original and corrected.
_PROTECTED_SYMBOLS: tuple[str, ...] = (
    "$", "%", "°", "×", "÷", "√", "π",
    "≤", "≥", "≠", "±", "∞", "∈", "∉",
    "∪", "∩", "⊂", "⊃",
)

# Tags whose count may decrease (merging) or increase (splitting).
_SHRINKABLE_TAGS: frozenset[str] = frozenset({"mn", "mspace"})
_GROWABLE_TAGS: frozenset[str] = frozenset({"mn", "mo", "mrow"})

_OPEN_TAG_RE = re.compile(r"<([a-zA-Z][\w.-]*)")
_STRIP_TAGS_RE = re.compile(r"<[^>]+>")
_MAX_SHRINK_PCT = 0.02  # text content may be at most 2 % shorter

_MATH_BLOCK_RE = re.compile(
    r"<math[^>]*>.*?</math>", re.DOTALL,
)
_MSPACE_RE = re.compile(r"<mspace[^/]*/?>(?:</mspace>)?")
# Only merge truly adjacent <mn> tags (no whitespace between).
# Previous version used \s* which incorrectly merged <mfrac>
# children separated by newlines/indentation.
_ADJACENT_MN_RE = re.compile(r"</mn><mn>")
_MN_CONTENT_RE = re.compile(r"<mn>(.*?)</mn>", re.DOTALL)
_CHOICE_ID_RE = re.compile(
    r"<(?:qti-simple-choice|simpleChoice)[^>]*"
    r'\bidentifier=["\']([^"\']+)["\']',
)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


def run_sanity_checks(
    original: str,
    corrected: str,
    content_type: str = "QTI XML",
    *,
    lenient: bool = False,
) -> tuple[bool, list[str]]:
    """Return (passed, reasons).

    ``passed`` is True when all deterministic checks pass.
    ``reasons`` lists every failing check (empty when passed).

    ``content_type`` is ``"QTI XML"`` or ``"HTML"``.
    QTI-specific checks (answer key, choice set) run only for
    QTI XML content.

    When ``lenient`` is True (for LLM fixes that intentionally
    change content like garbled text), MathML equivalence and
    tag-balance checks are skipped.  Critical invariants (answer
    key, choice set, content shrinkage) still run.
    """
    reasons: list[str] = []
    _check_symbols(original, corrected, reasons)
    _check_length(original, corrected, reasons, lenient=lenient)
    if not lenient:
        _check_tag_balance(original, corrected, reasons)
        _check_mathml_equivalence(original, corrected, reasons)
    if content_type == "QTI XML":
        _check_answer_key(original, corrected, reasons)
        _check_choice_set(original, corrected, reasons)
    return (len(reasons) == 0, reasons)


# ------------------------------------------------------------------
# Individual checks
# ------------------------------------------------------------------


_ENTITY_TO_CHAR: dict[str, str] = {
    "&#xD7;": "×", "&#xd7;": "×", "&#215;": "×",
    "&#x00D7;": "×", "&#x00d7;": "×",
    "&#xF7;": "÷", "&#xf7;": "÷", "&#247;": "÷",
    "&#x00F7;": "÷", "&#x00f7;": "÷",
    "&#x2212;": "−", "&#8722;": "−",
    "&#xB7;": "·", "&#183;": "·",
}


def _decode_symbol_entities(text: str) -> str:
    """Decode common operator entities to characters."""
    for entity, char in _ENTITY_TO_CHAR.items():
        text = text.replace(entity, char)
    return text


def _check_symbols(
    original: str, corrected: str, reasons: list[str],
) -> None:
    """Fail if any protected symbol lost occurrences."""
    orig_d = _decode_symbol_entities(original)
    corr_d = _decode_symbol_entities(corrected)
    for sym in _PROTECTED_SYMBOLS:
        orig_n = orig_d.count(sym)
        corr_n = corr_d.count(sym)
        if corr_n < orig_n:
            reasons.append(
                f"Symbol '{sym}' decreased from {orig_n} to {corr_n}",
            )


def _check_length(
    original: str, corrected: str, reasons: list[str],
    *, lenient: bool = False,
) -> None:
    """Fail if text content (tags stripped) shrank significantly.

    Compares tag-stripped content so that legitimate tag merging
    (e.g. split <mn> consolidation) doesn't trigger false positives.
    In lenient mode (LLM fixes) the threshold is 5 % instead of 2 %.
    """
    orig_text = _STRIP_TAGS_RE.sub("", original)
    corr_text = _STRIP_TAGS_RE.sub("", corrected)
    lo = len(orig_text)
    lc = len(corr_text)
    if lo == 0:
        return
    threshold = 0.05 if lenient else _MAX_SHRINK_PCT
    shrink = (lo - lc) / lo
    if shrink > threshold:
        reasons.append(
            f"Text content shrank by {shrink:.1%} "
            f"({lo} -> {lc} chars, threshold {threshold:.0%})",
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
        if tag in _GROWABLE_TAGS and c >= o:
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
# Hard invariant checks
# ------------------------------------------------------------------


def _normalize_mn_content(m: re.Match[str]) -> str:
    """Normalize a <mn> tag's inner text for comparison.

    Strips ALL separators (dots, spaces, nbsp) between digits
    and normalizes decimal commas to dots, so that format-only
    changes (e.g. 10.000 -> 10&#160;000) become invisible.
    Both sides get the same treatment, so the comparison works
    even if the stripping is aggressive.
    """
    c = m.group(1)
    c = c.replace("&#160;", "").replace("&nbsp;", "")
    c = c.replace("\u00a0", "").replace(" ", "")
    c = re.sub(r"(?<=\d)\.(?=\d)", "", c)
    c = re.sub(r"(\d),(\d)", r"\1.\2", c)
    return f"<mn>{c}</mn>"


def _normalize_mathml(block: str) -> str:
    """Normalize a single <math> block for equivalence comparison.

    Strips all tags to produce pure text content, then normalizes
    notation (dots, spaces, entities) so structural changes like
    <mn>5×4</mn> -> <mn>5</mn><mo>×</mo><mn>4</mn> compare equal.
    """
    result = _MSPACE_RE.sub("", block)
    result = _decode_symbol_entities(result)
    result = _STRIP_TAGS_RE.sub("", result)
    result = result.replace("&#160;", "").replace("\u00a0", "")
    result = result.replace(" ", "")
    result = result.replace("-", "\u2212")
    result = re.sub(r"(?<=\d)\.(?=\d)", "", result)
    result = re.sub(r"(\d),(\d)", r"\1.\2", result)
    return result


def _check_mathml_equivalence(
    original: str, corrected: str, reasons: list[str],
) -> None:
    """Fail if any MathML block changed its semantic content."""
    orig_blocks = _MATH_BLOCK_RE.findall(original)
    corr_blocks = _MATH_BLOCK_RE.findall(corrected)

    if len(orig_blocks) != len(corr_blocks):
        reasons.append(
            f"MathML block count changed: "
            f"{len(orig_blocks)} -> {len(corr_blocks)}",
        )
        return

    for i, (ob, cb) in enumerate(
        zip(orig_blocks, corr_blocks),
    ):
        norm_o = _normalize_mathml(ob)
        norm_c = _normalize_mathml(cb)
        if norm_o != norm_c:
            reasons.append(
                f"MathML block {i + 1} changed after "
                f"notation normalization",
            )


def _extract_correct_answer_id(xml: str) -> str | None:
    """Extract the correct answer identifier from QTI XML."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return None
    resp = (
        root.find(".//{*}responseDeclaration")
        or root.find(".//{*}qti-response-declaration")
    )
    if resp is None:
        return None
    corr = (
        resp.find(".//{*}correctResponse")
        or resp.find(".//{*}qti-correct-response")
    )
    if corr is None:
        return None
    val = (
        corr.find(".//{*}value")
        or corr.find(".//{*}qti-value")
    )
    if val is not None and val.text:
        return val.text.strip()
    return None


def _check_answer_key(
    original: str, corrected: str, reasons: list[str],
) -> None:
    """Fail if the correct answer identifier changed."""
    orig_id = _extract_correct_answer_id(original)
    corr_id = _extract_correct_answer_id(corrected)
    if orig_id is None and corr_id is None:
        return
    if orig_id != corr_id:
        reasons.append(
            f"Correct answer changed: "
            f"'{orig_id}' -> '{corr_id}'",
        )


def _check_choice_set(
    original: str, corrected: str, reasons: list[str],
) -> None:
    """Fail if answer choice identifiers changed or reordered."""
    orig_ids = _CHOICE_ID_RE.findall(original)
    corr_ids = _CHOICE_ID_RE.findall(corrected)
    if not orig_ids and not corr_ids:
        return
    if orig_ids != corr_ids:
        reasons.append(
            f"Choice identifiers changed: "
            f"{orig_ids} -> {corr_ids}",
        )


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
