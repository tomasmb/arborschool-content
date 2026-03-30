"""Shared helper functions for the variant pipeline.

These were previously duplicated across variant_planner.py,
variant_generator.py, and variant_validator.py.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from app.question_variants.contracts.structural_profile import build_structural_profile
from app.question_variants.models import SourceQuestion


def build_source_structural_profile(source: SourceQuestion) -> dict[str, Any]:
    """Build a structural profile from a source question.

    Centralises the logic that was duplicated across planner, generator,
    and validator, ensuring they all compute the same profile fields.
    """
    profile = build_structural_profile(
        source.question_text,
        source.qti_xml,
        bool(source.image_urls),
        source.primary_atoms,
        source.metadata.get("habilidad_principal", {}).get("habilidad_principal", ""),
    )
    profile["source_has_visual_support"] = bool(source.image_urls)
    profile["requires_image"] = bool(source.image_urls)
    profile["allows_new_visual_representation"] = bool(source.image_urls)
    profile["must_preserve_error_analysis"] = profile["task_form"] == "error_analysis"
    profile["allows_unknowns"] = profile["introduces_unknowns"]
    return profile


def extract_visual_context(qti_xml: str) -> str:
    """Extract visual context descriptions from QTI XML.

    Collects alt text from <img> elements and aria-label/label from
    <object> elements, returning a pipe-separated string.
    """
    try:
        root = ET.fromstring(qti_xml)
    except ET.ParseError:
        return ""

    descriptions: list[str] = []
    for element in root.findall(".//{*}img"):
        alt = (element.attrib.get("alt") or "").strip()
        if alt:
            descriptions.append(alt)
    for element in root.findall(".//{*}object"):
        label = (element.attrib.get("aria-label") or element.attrib.get("label") or "").strip()
        if label:
            descriptions.append(label)
    return " | ".join(descriptions)
