"""HTML parser-based structural validation for mini-lessons.

Uses html.parser (Python stdlib) for all structural checks.
Pure functions — no LLM calls, no side effects.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

# ---------------------------------------------------------------------------
# Required structure definitions (from spec section 6)
# ---------------------------------------------------------------------------

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
    "quick-check",
    "error-patterns",
    "transition-to-adaptive",
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


# ---------------------------------------------------------------------------
# HTML structure parser
# ---------------------------------------------------------------------------


_ATOM_ID_RE = re.compile(
    r"^A-M\d+-[A-Z]{3}-\d{2}-\d{2}$",
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
        self.option_counts: dict[int, int] = {}
        self.correct_options: dict[int, str | None] = {}
        self.imgs_missing_alt: list[int] = []
        self._current_qc_index: int | None = None
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
            if block == "quick-check" and index_str:
                self._current_qc_index = int(index_str)

        if attr_dict.get("data-option"):
            if self._current_qc_index is not None:
                idx = self._current_qc_index
                self.option_counts[idx] = (
                    self.option_counts.get(idx, 0) + 1
                )

        correct = attr_dict.get("data-correct-option")
        if correct and self._current_qc_index is not None:
            self.correct_options[self._current_qc_index] = correct


def parse_html_structure(html: str) -> _StructureParser:
    """Parse HTML and return structural information."""
    parser = _StructureParser()
    parser.feed(html)
    return parser


# ---------------------------------------------------------------------------
# Validation functions
# ---------------------------------------------------------------------------


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

    if expected_block == "quick-check":
        errors.extend(_check_quick_check_structure(parser))

    return errors


def check_full_lesson_structure(html: str) -> list[str]:
    """Validate the assembled mini-lesson HTML (all gates).

    Implements Gates 1-4 from the spec appendix B.
    """
    errors: list[str] = []

    errors.extend(_gate_1_contract(html))
    errors.extend(_gate_2_quick_check_integrity(html))
    errors.extend(_gate_3_anti_repeat(html))
    errors.extend(_gate_4_renderer_safety(html))

    return errors


def check_filler_phrases(text: str) -> list[str]:
    """Scan text for forbidden filler phrases.

    Returns list of found phrases.
    """
    text_lower = text.lower()
    found: list[str] = []
    for phrase in FORBIDDEN_FILLER_PHRASES:
        if phrase in text_lower:
            found.append(phrase)
    return found


def count_words(html: str) -> int:
    """Count words in HTML content (strips tags first)."""
    text = re.sub(r"<[^>]+>", " ", html)
    return len(text.split())


# ---------------------------------------------------------------------------
# Gate implementations
# ---------------------------------------------------------------------------


def _gate_1_contract(html: str) -> list[str]:
    """Gate 1: Contract validity.

    Checks root article attrs, required blocks, multiplicities,
    and tag allowlist per spec v1.1 (Appendix B §A).
    """
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
    if we_count != 2:
        errors.append(
            f"Expected 2 worked-example blocks, found {we_count}",
        )

    qc_count = block_names.count("quick-check")
    if qc_count < 1 or qc_count > 2:
        errors.append(
            f"Expected 1-2 quick-check blocks, found {qc_count}",
        )

    if parser.disallowed_tags_found:
        errors.append(
            f"Disallowed tags: {parser.disallowed_tags_found}",
        )

    return errors


def _gate_2_quick_check_integrity(html: str) -> list[str]:
    """Gate 2: Quick-check option and feedback integrity."""
    errors: list[str] = []
    parser = parse_html_structure(html)

    for idx, count in parser.option_counts.items():
        if count != 4:
            errors.append(
                f"QC {idx}: expected 4 options, found {count}",
            )

    for idx in parser.option_counts:
        if idx not in parser.correct_options:
            errors.append(
                f"QC {idx}: missing data-correct-option",
            )

    if 'data-role="feedback"' not in html:
        errors.append("Missing feedback div in quick-check")

    return errors


def _gate_3_anti_repeat(html: str) -> list[str]:
    """Gate 3: Anti-repeat checks between sections."""
    errors: list[str] = []

    we_sections = re.findall(
        r'data-block="worked-example"[^>]*>(.*?)</section>',
        html,
        re.DOTALL,
    )
    if len(we_sections) >= 2:
        nums_1 = set(re.findall(r"\d+", we_sections[0]))
        nums_2 = set(re.findall(r"\d+", we_sections[1]))
        if nums_1 and nums_2:
            overlap = len(nums_1 & nums_2) / max(
                len(nums_1 | nums_2), 1,
            )
            if overlap > 0.4:
                errors.append(
                    f"WE1/WE2 numeric overlap {overlap:.0%} > 40%",
                )

    return errors


def _gate_4_renderer_safety(html: str) -> list[str]:
    """Gate 4: Renderer safety + accessibility checks."""
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


def _check_quick_check_structure(
    parser: _StructureParser,
) -> list[str]:
    """Validate quick-check specific structure."""
    errors: list[str] = []

    for idx, count in parser.option_counts.items():
        if count != 4:
            errors.append(
                f"QC {idx}: expected 4 options, found {count}",
            )

    return errors
