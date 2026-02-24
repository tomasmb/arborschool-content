"""Shared XML processing utilities for QTI generation pipelines.

Canonical implementations of XML extraction, control-character
stripping, HTML-entity normalization, and generation-response parsing.
Both the single-atom and batch pipelines import from here.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.question_generation.models import GeneratedItem, PlanSlot

# ---------------------------------------------------------------------------
# HTML entity normalization
# ---------------------------------------------------------------------------

# HTML entities the LLM writes in feedback that are not valid in XML.
# XML only allows 5 built-ins: &amp; &lt; &gt; &quot; &apos;
_HTML_ENTITY_MAP: dict[str, str] = {
    "nbsp": "\u00a0", "oacute": "ó", "aacute": "á", "eacute": "é",
    "iacute": "í", "uacute": "ú", "ntilde": "ñ", "ordm": "º",
    "ordf": "ª",
    "Aacute": "Á", "Eacute": "É", "Iacute": "Í", "Oacute": "Ó",
    "Uacute": "Ú", "Ntilde": "Ñ", "Agrave": "À", "Egrave": "È",
    "rarr": "→", "larr": "←", "uarr": "↑", "darr": "↓", "harr": "↔",
    "minus": "−", "times": "×", "divide": "÷", "plusmn": "±",
    "le": "≤", "ge": "≥", "ne": "≠", "approx": "≈", "infin": "∞",
    "alpha": "α", "beta": "β", "pi": "π", "theta": "θ", "sigma": "σ",
    "lambda": "λ", "delta": "δ", "epsilon": "ε", "phi": "φ",
    "omega": "ω",
    "iexcl": "¡", "iquest": "¿", "ldquo": "\u201c", "rdquo": "\u201d",
    "lsquo": "\u2018", "rsquo": "\u2019", "hellip": "…",
    "mdash": "—", "ndash": "–", "bull": "•",
    "deg": "°", "sup2": "²", "sup3": "³", "frac12": "½", "frac14": "¼",
    "laquo": "«", "raquo": "»", "thinsp": "\u2009",
    "div": "÷", "leq": "≤", "ctdot": "⋯",
}

_ENTITY_RE = re.compile(r"&([a-zA-Z][a-zA-Z0-9]*);")


def normalize_html_entities(xml: str) -> str:
    """Replace HTML entities with UTF-8 equivalents before XSD validation.

    LLMs frequently write HTML entities (&oacute;, &nbsp;, &rarr;, etc.)
    that are invalid in XML.  Replace known entities with their UTF-8
    characters so the XSD validator sees clean XML.  Unknown entities
    are left unchanged so the validator can still report them.
    """
    return _ENTITY_RE.sub(
        lambda m: _HTML_ENTITY_MAP.get(m.group(1), m.group(0)), xml,
    )


# ---------------------------------------------------------------------------
# Control character stripping
# ---------------------------------------------------------------------------

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def strip_control_chars(text: str) -> str:
    """Strip invalid XML control characters from text.

    LLMs occasionally emit raw control bytes where accented characters
    should be, making the XML unparseable.  Valid XML whitespace
    (tab, newline, carriage return) is preserved.
    """
    return _CONTROL_CHAR_RE.sub("", text)


# ---------------------------------------------------------------------------
# QTI XML extraction
# ---------------------------------------------------------------------------


def extract_qti_xml(text: str) -> str:
    """Extract QTI XML from potentially wrapped text.

    Handles markdown code blocks and extraneous content before/after
    the ``<qti-assessment-item>`` element.  Control characters are
    stripped after extraction.
    """
    cleaned = text.strip()

    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)

    if "<qti-assessment-item" in cleaned:
        start = cleaned.index("<qti-assessment-item")
        end_tag = "</qti-assessment-item>"
        end = cleaned.rindex(end_tag) + len(end_tag)
        cleaned = cleaned[start:end]

    return strip_control_chars(cleaned.strip())


# ---------------------------------------------------------------------------
# Generation response parsing
# ---------------------------------------------------------------------------


def parse_generation_response(
    response: str,
    atom_id: str,
    slot: PlanSlot,
) -> GeneratedItem:
    """Parse a single-item LLM JSON response into a GeneratedItem.

    Expected format::

        {"slot_index": N, "qti_xml": "..."}

    Image slots also include ``"image_description": "..."``.

    Supports both flat format and wrapped ``{"items": [...]}``.

    Raises:
        json.JSONDecodeError: If *response* is not valid JSON.
        ValueError: If ``qti_xml`` is empty.
    """
    data: dict[str, Any] = json.loads(response)

    if "items" in data and isinstance(data["items"], list):
        if not data["items"]:
            msg = "LLM returned empty items array"
            raise ValueError(msg)
        data = data["items"][0]

    qti_xml = data.get("qti_xml", "")
    if not qti_xml:
        msg = f"Slot {slot.slot_index}: LLM returned empty qti_xml"
        raise ValueError(msg)

    qti_xml = extract_qti_xml(qti_xml)
    slot_idx = data.get("slot_index", slot.slot_index)
    image_desc = data.get("image_description", "")

    return GeneratedItem(
        item_id=f"{atom_id}_Q{slot_idx}",
        qti_xml=qti_xml,
        slot_index=slot_idx,
        image_description=image_desc,
    )
