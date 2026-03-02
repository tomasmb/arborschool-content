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
    return result


def fix_mathml_split(content: str) -> str:
    """Split operators out of <mn> tags into proper <mo> elements.

    ``<mn>5×4</mn>`` -> ``<mn>5</mn><mo>&#xD7;</mo><mn>4</mn>``
    ``<mn>&#x2212;13000</mn>`` ->
        ``<mo>&#x2212;</mo><mn>13000</mn>``
    """
    def _replace(m: re.Match) -> str:
        inner = m.group(1)
        replacement = _split_mn_content(inner)
        if replacement is None:
            return m.group(0)
        return replacement

    return _MN_WITH_OP_RE.sub(_replace, content)


# ------------------------------------------------------------------
# Dispatch by category
# ------------------------------------------------------------------

DETERMINISTIC_CATEGORIES = {
    "deterministic_thousands_sep": fix_thousands_sep,
    "deterministic_spacing": fix_spacing,
    "deterministic_mathml_split": fix_mathml_split,
}


def apply_deterministic_fixes(
    content: str, categories: set[str],
) -> str:
    """Apply all relevant deterministic fixes to content."""
    for cat, fn in DETERMINISTIC_CATEGORIES.items():
        if cat in categories:
            content = fn(content)
    return content
