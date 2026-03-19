"""Shared helpers for deterministic family repairs."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

NS = {"qti": "http://www.imsglobal.org/xsd/imsqtiasi_v3p0"}


def parse_number(text: str) -> float | None:
    cleaned = re.sub(r"[^0-9,.-]", "", text.replace("\xa0", ""))
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def format_number(value: float) -> str:
    rounded = int(value) if float(value).is_integer() else round(value, 2)
    if isinstance(rounded, int):
        return str(rounded)
    return str(rounded).replace(".", ",")


def clone_element(element: ET.Element) -> ET.Element:
    return ET.fromstring(ET.tostring(element, encoding="unicode"))
