"""HTML parser-based structural validation for mini-lessons.

Uses html.parser (Python stdlib) for all structural checks.
Pure functions — no LLM calls, no side effects.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

ALLOWED_TAGS = frozenset({
    "article", "section", "header", "h1", "h2", "h3", "h4",
    "p", "ul", "ol", "li", "table", "thead", "tbody", "tr",
    "th", "td", "strong", "em", "code", "math", "mrow", "mi",
    "mn", "mo", "msup", "msub", "mfrac", "msqrt", "mtext",
    "details", "summary", "blockquote", "hr", "div", "img",
})

DISALLOWED_TAGS = frozenset({
    "style", "script", "link", "iframe", "embed", "object",
    "form", "input", "button",
})

REQUIRED_BLOCKS = [
    "objective",
    "concept",
    "worked-example",
]

FORBIDDEN_FILLER_PHRASES = [
    "es importante recordar que",
    "cabe destacar que",
    "a continuación veremos",
    "como ya sabemos",
    "en este contexto",
    "vale la pena mencionar",
    "se procederá a analizar",
    "considerando lo anterior",
    "esto es muy fácil",
    "no te preocupes",
]


_ATOM_ID_RE = re.compile(
    r"^A-M\d+-[A-Z]{3,4}-\d{2}-\d{2}$",
)
_VALID_TEMPLATES = frozenset({"P", "C", "M"})


class _StructureParser(HTMLParser):
    """Extracts structural information from mini-lesson HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.tags_found: list[str] = []
        self.blocks: list[dict[str, str | None]] = []
        self.has_inline_style: bool = False
        self.disallowed_tags_found: list[str] = []
        self.imgs_missing_alt: list[int] = []
        self._img_count: int = 0
        self.article_atom_id: str | None = None
        self.article_template: str | None = None

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self.tags_found.append(tag)
        attr_dict = dict(attrs)

        if tag in DISALLOWED_TAGS:
            self.disallowed_tags_found.append(tag)

        if attr_dict.get("style"):
            self.has_inline_style = True

        if tag == "img":
            self._img_count += 1
            if not attr_dict.get("alt"):
                self.imgs_missing_alt.append(self._img_count)

        if tag == "article":
            self.article_atom_id = attr_dict.get("data-atom-id")
            self.article_template = attr_dict.get("data-template")

        block = attr_dict.get("data-block")
        if block:
            index_str = attr_dict.get("data-index")
            self.blocks.append({
                "block": block,
                "index": index_str,
                "tag": tag,
            })


def parse_html_structure(html: str) -> _StructureParser:
    """Parse HTML and return structural information."""
    parser = _StructureParser()
    parser.feed(html)
    return parser


def check_section_html(
    html: str,
    expected_block: str,
    expected_index: int | None = None,
) -> list[str]:
    """Validate a single section's HTML structure.

    Returns list of error messages (empty = passed).
    """
    errors: list[str] = []
    parser = parse_html_structure(html)

    if parser.disallowed_tags_found:
        errors.append(
            f"Disallowed tags: {parser.disallowed_tags_found}",
        )

    if parser.has_inline_style:
        errors.append("Inline styles are not allowed")

    block_found = any(
        b["block"] == expected_block for b in parser.blocks
    )
    if not block_found:
        errors.append(
            f"Missing data-block=\"{expected_block}\"",
        )

    if expected_index is not None:
        index_found = any(
            b["block"] == expected_block
            and b.get("index") == str(expected_index)
            for b in parser.blocks
        )
        if not index_found:
            errors.append(
                f"Missing data-index=\"{expected_index}\" "
                f"for {expected_block}",
            )

    return errors


def check_full_lesson_structure(html: str) -> list[str]:
    """Validate the assembled mini-lesson HTML (all gates).

    Checks contract validity, renderer safety, and
    notation consistency.
    """
    errors: list[str] = []

    errors.extend(_gate_1_contract(html))
    errors.extend(_gate_2_renderer_safety(html))
    errors.extend(check_decimal_notation(html))

    return errors


def check_filler_phrases(text: str) -> list[str]:
    """Scan text for forbidden filler phrases."""
    text_lower = text.lower()
    return [p for p in FORBIDDEN_FILLER_PHRASES if p in text_lower]


_MATH_BLOCK_RE = re.compile(r"<math[^>]*>.*?</math>", re.DOTALL)
_MATH_WORD_EQUIVALENT = 3


def count_words(html: str) -> int:
    """Count words in HTML, collapsing each MathML formula to ~3 words.

    Students process a formula as one visual unit, not as individual
    XML tokens. Without collapsing, a simple fraction in MathML can
    inflate the count by 10+ phantom "words."
    """
    collapsed = _MATH_BLOCK_RE.sub(
        " MATHBLOCK " * _MATH_WORD_EQUIVALENT, html,
    )
    text = re.sub(r"<[^>]+>", " ", collapsed)
    return len(text.split())


_DECIMAL_PERIOD_RE = re.compile(r"\d+\.\d+")
_FALSE_POSITIVE_RE = re.compile(
    r"(?:version|v|pipeline)[_ ]?\d+\.\d+", re.IGNORECASE,
)


def check_decimal_notation(html: str) -> list[str]:
    """Check that all decimals use comma (Chilean convention)."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = _FALSE_POSITIVE_RE.sub("", text)
    matches = _DECIMAL_PERIOD_RE.findall(text)
    if not matches:
        return []
    samples = ", ".join(matches[:5])
    extra = f" (+{len(matches) - 5} more)" if len(matches) > 5 else ""
    return [
        f"Decimal period notation found (must use comma): "
        f"{samples}{extra}",
    ]


def _gate_1_contract(html: str) -> list[str]:
    """Gate 1: Contract validity (root attrs, required blocks)."""
    errors: list[str] = []
    parser = parse_html_structure(html)

    article_count = parser.tags_found.count("article")
    if article_count != 1:
        errors.append(
            f"Expected 1 <article>, found {article_count}",
        )

    aid = parser.article_atom_id
    if not aid:
        errors.append("Missing data-atom-id on <article>")
    elif not _ATOM_ID_RE.match(aid):
        errors.append(
            f"data-atom-id '{aid}' does not match "
            f"expected pattern A-M<d>+-<ABC>-<dd>-<dd>",
        )

    tmpl = parser.article_template
    if not tmpl:
        errors.append("Missing data-template on <article>")
    elif tmpl not in _VALID_TEMPLATES:
        errors.append(
            f"data-template '{tmpl}' not in {{P, C, M}}",
        )

    block_names = [b["block"] for b in parser.blocks]

    for required in REQUIRED_BLOCKS:
        if required not in block_names:
            errors.append(f"Missing required block: {required}")

    we_count = block_names.count("worked-example")
    if we_count != 1:
        errors.append(
            f"Expected 1 worked-example block, found {we_count}",
        )

    for b in parser.blocks:
        if b["block"] == "objective" and b["tag"] != "header":
            errors.append(
                f"objective block should use <header>, "
                f"found <{b['tag']}>",
            )

    if parser.disallowed_tags_found:
        errors.append(
            f"Disallowed tags: {parser.disallowed_tags_found}",
        )

    return errors


def _gate_2_renderer_safety(html: str) -> list[str]:
    """Gate 2: Renderer safety + accessibility checks."""
    errors: list[str] = []
    parser = parse_html_structure(html)

    if parser.has_inline_style:
        errors.append("Inline styles found")

    if parser.imgs_missing_alt:
        errors.append(
            f"<img> tags missing alt attribute: "
            f"{parser.imgs_missing_alt}",
        )

    dangerous_patterns = [
        "onerror=", "onclick=", "onload=",
        "javascript:", "<script",
    ]
    html_lower = html.lower()
    for pattern in dangerous_patterns:
        if pattern in html_lower:
            errors.append(f"Dangerous pattern found: {pattern}")

    return errors
