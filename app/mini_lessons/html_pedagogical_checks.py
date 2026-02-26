"""Pedagogical structure warnings for mini-lesson HTML (v1.1).

Soft checks that complement the hard-fail structural validation
in html_validator.py. These produce warnings (not errors) about
pedagogical patterns like h3 chunking, progressive disclosure
via <details>, and template-specific QC counts.
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


def check_qc_feedback_details(html: str) -> list[str]:
    """Warn if QC feedback is not inside a <details> wrapper."""
    warnings: list[str] = []
    qc_sections = re.findall(
        r'data-block="quick-check"\s+data-index="(\d+)"'
        r"[^>]*>(.*?)</section>",
        html,
        re.DOTALL,
    )
    for idx_str, content in qc_sections:
        has_feedback = 'data-role="feedback"' in content
        has_details = (
            "<details>" in content or "<details " in content
        )
        if has_feedback and not has_details:
            warnings.append(
                f"QC {idx_str}: feedback not wrapped in "
                f"<details> (should be progressive disclosure)",
            )
    return warnings


def check_template_qc_count(
    html: str,
    template_type: str,
) -> list[str]:
    """Warn if P/M-template has only 1 QC when 2 are expected."""
    warnings: list[str] = []
    if template_type in ("P", "M"):
        qc_count = len(re.findall(
            r'data-block="quick-check"', html,
        ))
        if qc_count < 2:
            warnings.append(
                f"{template_type}-template has {qc_count} "
                f"quick-check(s), expected 2",
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
    warnings.extend(check_qc_feedback_details(html))
    if template_type:
        warnings.extend(
            check_template_qc_count(html, template_type),
        )
    return warnings
