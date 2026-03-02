"""Deterministic fix functions for notation issues.

Each function takes a content string and returns the fixed version.
They are designed to be safe and minimal — only fix the specific
pattern they target.
"""

from __future__ import annotations

import re

# ------------------------------------------------------------------
# thousands_sep: dot as thousands separator in <mn>
# ------------------------------------------------------------------

# Matches <mn>X.XXX</mn> or <mn>X.XXX.XXX</mn> etc.
# Also handles combined like <mn>10.000,5</mn>
_MN_DOT_THOUSANDS_RE = re.compile(
    r"<mn>"
    r"(\d{1,3})"
    r"((?:\.\d{3})+)"
    r"(,\d+)?"
    r"</mn>",
)

# Plain-text: dot between digits where RHS is exactly 3 digits.
# Chilean notation: 10.000 = ten thousand (comma is decimal).
# Negative lookahead rejects comma+digit (decimal part like ,5)
# but allows comma+non-digit (punctuation like ", ya que").
_PLAIN_DOT_THOUSANDS_RE = re.compile(
    r"(\d{1,3})"
    r"((?:\.\d{3})+)"
    r"(?!\d|,\d)",
)

_MATH_BLOCK_FOR_TSEP_RE = re.compile(
    r"<math[^>]*>.*?</math>", re.DOTALL,
)


def _replace_mn_dot(m: re.Match) -> str:
    """Replace dots with &#160; inside a <mn> thousands pattern."""
    prefix = m.group(1)
    groups_of_3 = m.group(2)
    decimal = m.group(3) or ""
    parts = groups_of_3.split(".")
    joined = "&#160;".join([prefix] + [p for p in parts if p])
    return f"<mn>{joined}{decimal}</mn>"


def _replace_plain_dot(m: re.Match) -> str:
    """Replace dots with &#160; in a plain-text thousands pattern."""
    prefix = m.group(1)
    groups = m.group(2).split(".")
    return "&#160;".join([prefix] + [p for p in groups if p])


def fix_thousands_sep(content: str) -> str:
    """Replace dots used as thousands separators.

    Inside <mn> tags:
      ``<mn>10.000</mn>`` -> ``<mn>10&#160;000</mn>``
    In plain text (outside <math>):
      ``$3.200`` -> ``$3&#160;200``
    """
    result = _MN_DOT_THOUSANDS_RE.sub(_replace_mn_dot, content)
    math_spans: list[tuple[int, int]] = [
        (m.start(), m.end())
        for m in _MATH_BLOCK_FOR_TSEP_RE.finditer(result)
    ]

    def _in_math(pos: int) -> bool:
        return any(s <= pos < e for s, e in math_spans)

    parts: list[str] = []
    last = 0
    for m in _PLAIN_DOT_THOUSANDS_RE.finditer(result):
        if _in_math(m.start()):
            continue
        parts.append(result[last:m.start()])
        parts.append(_replace_plain_dot(m))
        last = m.end()
    parts.append(result[last:])
    return "".join(parts)


# ------------------------------------------------------------------
# spacing: regular space -> &#160; in plain-text thousands
# ------------------------------------------------------------------

# Match digits with regular space as separator OUTSIDE <math> blocks.
# Pattern: 1-3 digits, space, exactly 3 digits (possibly chained).
# Lookbehind for $ or start context; lookahead for non-digit.
_PLAIN_THOUSANDS_RE = re.compile(
    r"(?<=\d) (?=\d{3}(?:\D|$))",
)

# Regions to protect (MathML blocks and HTML tags).
_MATH_BLOCK_RE = re.compile(
    r"<math[^>]*>.*?</math>", re.DOTALL,
)


def fix_spacing(content: str) -> str:
    r"""Replace regular space thousands separators with &#160;.

    Only operates outside ``<math>`` blocks.
    ``$10 000`` -> ``$10&#160;000``
    ``150 000 litros`` -> ``150&#160;000 litros``
    """
    math_spans: list[tuple[int, int]] = [
        (m.start(), m.end())
        for m in _MATH_BLOCK_RE.finditer(content)
    ]

    def _in_math(pos: int) -> bool:
        return any(s <= pos < e for s, e in math_spans)

    result = []
    last = 0
    for m in _PLAIN_THOUSANDS_RE.finditer(content):
        if _in_math(m.start()):
            continue
        before = content[max(0, m.start() - 4):m.start()]
        if not re.search(r"\d{1,3}$", before):
            continue
        result.append(content[last:m.start()])
        result.append("&#160;")
        last = m.end()
    result.append(content[last:])
    return "".join(result)


# ------------------------------------------------------------------
# mathml_split: operators stuck inside <mn> tags
# ------------------------------------------------------------------

# Operators that should be <mo>, not inside <mn>.
_OPERATOR_CHARS = {
    "+", "-", "×", "÷", "=",
    "\u2212",  # minus sign
    "\u00d7",  # multiplication sign
    "\u00f7",  # division sign
}

# HTML entities for operators.
_OPERATOR_ENTITIES = {
    "&#x2212;": "\u2212",
    "&#x00D7;": "\u00d7",
    "&#x00d7;": "\u00d7",
    "&#xD7;": "\u00d7",
    "&#xd7;": "\u00d7",
    "&#x00F7;": "\u00f7",
    "&#x00f7;": "\u00f7",
    "&#215;": "\u00d7",
    "&#8722;": "\u2212",
}

# Match <mn> containing operator characters or entities.
_MN_WITH_OP_RE = re.compile(
    r"<mn>([^<]+)</mn>",
)

_ENTITY_RE = re.compile(r"&#x?[0-9a-fA-F]+;")


def _decode_entities(text: str) -> str:
    """Decode known operator entities to characters."""
    for entity, char in _OPERATOR_ENTITIES.items():
        text = text.replace(entity, char)
    return text


def _encode_operator(char: str) -> str:
    """Encode an operator character back to an entity for MathML."""
    mapping = {
        "\u2212": "&#x2212;",
        "\u00d7": "&#xD7;",
        "\u00f7": "&#xF7;",
        "+": "+",
        "-": "&#x2212;",
        "=": "=",
        "×": "&#xD7;",
        "÷": "&#xF7;",
    }
    return mapping.get(char, char)


def _split_mn_content(inner: str) -> str | None:
    """Split <mn> content with operators into proper MathML.

    Returns None if no splitting needed.
    ``5×4`` -> ``<mn>5</mn><mo>&#xD7;</mo><mn>4</mn>``
    ``-13000`` -> ``<mo>&#x2212;</mo><mn>13000</mn>``
    """
    decoded = _decode_entities(inner)
    has_op = any(c in _OPERATOR_CHARS for c in decoded)
    if not has_op:
        return None

    parts: list[str] = []
    current_digits: list[str] = []

    for char in decoded:
        if char in _OPERATOR_CHARS:
            if current_digits:
                parts.append(f"<mn>{''.join(current_digits)}</mn>")
                current_digits = []
            parts.append(f"<mo>{_encode_operator(char)}</mo>")
        else:
            current_digits.append(char)

    if current_digits:
        parts.append(f"<mn>{''.join(current_digits)}</mn>")

    result = "".join(parts)
    if result == f"<mn>{inner}</mn>":
        return None
    if len(parts) > 1:
        result = f"<mrow>{result}</mrow>"
    return result


def fix_mathml_split(content: str) -> str:
    r"""Split operators out of <mn> tags into proper <mo> elements.

    Wraps multi-element results in <mrow> to keep valid structure
    (critical when the <mn> is a child of <mfrac>).

    ``<mn>5×4</mn>`` ->
        ``<mrow><mn>5</mn><mo>&#xD7;</mo><mn>4</mn></mrow>``
    ``<mn>&#x2212;13000</mn>`` ->
        ``<mrow><mo>&#x2212;</mo><mn>13000</mn></mrow>``
    """
    def _replace(m: re.Match) -> str:
        inner = m.group(1)
        replacement = _split_mn_content(inner)
        if replacement is None:
            return m.group(0)
        return replacement

    return _MN_WITH_OP_RE.sub(_replace, content)


# ------------------------------------------------------------------
# mn_space: regular space -> &#160; inside <mn> tags
# ------------------------------------------------------------------

_MN_SPACE_RE = re.compile(r"<mn>([^<]+)</mn>")


def _fix_mn_space_inner(m: re.Match) -> str:
    """Replace regular spaces with &#160; inside <mn>."""
    inner = m.group(1)
    if " " not in inner:
        return m.group(0)
    fixed = inner.replace(" ", "&#160;")
    return f"<mn>{fixed}</mn>"


def fix_mn_space(content: str) -> str:
    r"""Replace regular spaces inside <mn> with &#160;.

    ``<mn>12 000</mn>`` -> ``<mn>12&#160;000</mn>``

    Regular spaces inside <mn> can cause numbers to break
    across lines when rendered.
    """
    return _MN_SPACE_RE.sub(_fix_mn_space_inner, content)


# ------------------------------------------------------------------
# bare_thousands_mn: add &#160; separators to 5+ digit <mn>
# ------------------------------------------------------------------

_MN_BARE_RE = re.compile(r"<mn>(\d{5,})</mn>")


def _add_thousands_sep(m: re.Match) -> str:
    """Add &#160; thousands separators to a bare number in <mn>."""
    digits = m.group(1)
    parts: list[str] = []
    while len(digits) > 3:
        parts.append(digits[-3:])
        digits = digits[:-3]
    parts.append(digits)
    parts.reverse()
    return f"<mn>{'&#160;'.join(parts)}</mn>"


def fix_bare_thousands_mn(content: str) -> str:
    r"""Add &#160; thousands separators to bare 5+ digit <mn>.

    ``<mn>25000</mn>`` -> ``<mn>25&#160;000</mn>``
    ``<mn>1250000</mn>`` -> ``<mn>1&#160;250&#160;000</mn>``

    Only targets <mn> containing solely digits (no existing
    separators, operators, or decimal parts).
    """
    return _MN_BARE_RE.sub(_add_thousands_sep, content)


# ------------------------------------------------------------------
# Dispatch by category
# ------------------------------------------------------------------

DETERMINISTIC_CATEGORIES = {
    "deterministic_thousands_sep": fix_thousands_sep,
    "deterministic_spacing": fix_spacing,
}

# Spacing also applies mn_space and bare_thousands_mn for
# items flagged as spacing or thousands_sep respectively.
_SUPPLEMENTARY_FIXES: list[tuple[set[str], callable]] = [
    ({"deterministic_spacing"}, fix_mn_space),
    ({"deterministic_thousands_sep"}, fix_bare_thousands_mn),
]


def apply_deterministic_fixes(
    content: str, categories: set[str],
) -> str:
    """Apply all relevant deterministic fixes to content."""
    for cat, fn in DETERMINISTIC_CATEGORIES.items():
        if cat in categories:
            content = fn(content)
    for trigger_cats, fn in _SUPPLEMENTARY_FIXES:
        if trigger_cats & categories:
            content = fn(content)
    return content
