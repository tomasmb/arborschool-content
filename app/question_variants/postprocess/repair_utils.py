"""Shared helpers for deterministic family repairs."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

NS = {"qti": "http://www.imsglobal.org/xsd/imsqtiasi_v3p0"}
QTI_NS = "http://www.imsglobal.org/xsd/imsqtiasi_v3p0"
MATHML_NS = "http://www.w3.org/1998/Math/MathML"

ET.register_namespace("", QTI_NS)
ET.register_namespace("m", MATHML_NS)


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
    return ET.fromstring(serialize_xml(element))


def serialize_xml(element: ET.Element) -> str:
    return ET.tostring(element, encoding="unicode")
