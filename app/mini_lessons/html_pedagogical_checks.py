"""Pedagogical structure checks for mini-lesson HTML (v1.1).

Includes both soft warnings (h3 chunking, progressive disclosure,
template-specific QC counts) and hard checks (scope gate
violations, canonical step consistency).
"""

from __future__ import annotations

import re

# ------------------------------------------------------------------
# Scope gate: off-scope trigger phrases (hard check)
# ------------------------------------------------------------------

SCOPE_TRIGGER_PHRASES: list[str] = [
    "denominador común",
    "invierte la fracción",
    "invertir la fracción",
    "simplifica la fracción",
    "simplificar la fracción",
    "mínimo común múltiplo",
    "mínimo común denominador",
    "convierte a decimal",
    "convertir a decimal",
    "alinea la coma",
    "alinear la coma",
    "igualar denominadores",
    "igualamos denominadores",
]

_MAX_SCOPE_PHRASE_OCCURRENCES = 1


def check_scope_violations(html: str) -> list[str]:
    """Check for off-scope teaching phrases that exceed threshold.

    Returns errors (not warnings) when off-scope prerequisite
    phrases appear more than _MAX_SCOPE_PHRASE_OCCURRENCES times
    in the full lesson text.
    """
    text = re.sub(r"<[^>]+>", " ", html).lower()
    errors: list[str] = []
    for phrase in SCOPE_TRIGGER_PHRASES:
        count = text.count(phrase)
        if count > _MAX_SCOPE_PHRASE_OCCURRENCES:
            errors.append(
                f"Scope gate violation: '{phrase}' appears "
                f"{count} times (max {_MAX_SCOPE_PHRASE_OCCURRENCES})"
            )
    return errors


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


_STEP_NAME_RE = re.compile(
    r"<summary>\s*<strong>Paso\s+\d+:\s*</strong>\s*(.+?)\s*</summary>",
    re.IGNORECASE,
)


def _extract_step_names(we_html: str) -> list[str]:
    """Extract canonical step names from a worked-example section."""
    return [
        m.strip().rstrip(".")
        for m in _STEP_NAME_RE.findall(we_html)
    ]


def check_canonical_step_consistency(
    html: str,
    template_type: str = "",
) -> list[str]:
    """Warn if WE1 and WE2 use different canonical step names.

    Only checked for P-template (procedural atoms) where a fixed
    recipe is required.
    """
    if template_type and template_type != "P":
        return []

    warnings: list[str] = []
    we_sections = re.findall(
        r'data-block="worked-example"\s+data-index="(\d+)"'
        r"[^>]*>(.*?)</section>",
        html,
        re.DOTALL,
    )
    names_by_index: dict[str, list[str]] = {}
    for idx_str, content in we_sections:
        names_by_index[idx_str] = _extract_step_names(content)

    we1_names = names_by_index.get("1", [])
    we2_names = names_by_index.get("2", [])

    if not we1_names or not we2_names:
        return warnings

    # WE2 may have fewer steps (omits verification) so compare
    # only up to the shorter list length.
    compare_len = min(len(we1_names), len(we2_names))
    for i in range(compare_len):
        n1 = we1_names[i].lower()
        n2 = we2_names[i].lower()
        if n1 != n2:
            warnings.append(
                f"Canonical step mismatch at Paso {i + 1}: "
                f"WE1='{we1_names[i]}' vs WE2='{we2_names[i]}'"
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
    warnings.extend(
        check_canonical_step_consistency(html, template_type),
    )
    if template_type:
        warnings.extend(
            check_template_qc_count(html, template_type),
        )
    return warnings
