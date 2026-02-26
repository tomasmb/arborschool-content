"""Pedagogical structure checks for mini-lesson HTML.

Soft warnings for concept chunking and progressive disclosure
in worked examples.
"""

from __future__ import annotations

import re


def check_concept_h3_count(html: str) -> list[str]:
    """Warn if concept section has fewer than 2 <h3> sub-blocks."""
    warnings: list[str] = []
    concept_match = re.search(
        r'data-block="concept"[^>]*>(.*?)</section>',
        html,
        re.DOTALL,
    )
    if concept_match:
        h3_count = len(re.findall(r"<h3[^>]*>", concept_match[1]))
        if h3_count < 2:
            warnings.append(
                f"Concept section has {h3_count} <h3> sub-blocks "
                f"(expected >= 2 for micro-block chunking)",
            )
    return warnings


def check_we_details_wrappers(html: str) -> list[str]:
    """Warn if worked-example steps lack <details> wrappers."""
    warnings: list[str] = []
    we_sections = re.findall(
        r'data-block="worked-example"\s+data-index="(\d+)"'
        r"[^>]*>(.*?)</section>",
        html,
        re.DOTALL,
    )
    for idx_str, content in we_sections:
        if "<details>" not in content and "<details " not in content:
            warnings.append(
                f"WE {idx_str}: steps not wrapped in "
                f"<details>/<summary> (progressive disclosure)",
            )
    return warnings


def collect_pedagogical_warnings(
    html: str,
    template_type: str = "",
) -> list[str]:
    """Run all pedagogical structure checks, return warnings."""
    warnings: list[str] = []
    warnings.extend(check_concept_h3_count(html))
    warnings.extend(check_we_details_wrappers(html))
    return warnings
