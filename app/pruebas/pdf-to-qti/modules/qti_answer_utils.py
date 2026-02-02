"""
QTI Answer Utilities

This module provides utilities for extracting and updating correct answers
in QTI 3.0 XML content.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Optional


def extract_correct_answer_from_qti(qti_xml: str) -> Optional[str]:
    """
    Extract the correct answer from QTI XML.

    Args:
        qti_xml: QTI XML string

    Returns:
        Correct answer identifier (e.g., "ChoiceA") or None if not found
    """
    try:
        root = ET.fromstring(qti_xml)
        QTI_NS = "{http://www.imsglobal.org/xsd/imsqtiasi_v3p0}"

        response_decl = root.find(f".//{QTI_NS}qti-response-declaration")
        if response_decl is None:
            return None

        correct_response = response_decl.find(f"{QTI_NS}qti-correct-response")
        if correct_response is None:
            return None

        qti_value = correct_response.find(f"{QTI_NS}qti-value")
        if qti_value is None or not qti_value.text:
            return None

        return qti_value.text.strip()
    except ET.ParseError:
        # If XML parsing fails, try regex as fallback
        match = re.search(r"<qti-value>([^<]+)</qti-value>", qti_xml)
        if match:
            return match.group(1).strip()
        return None
    except Exception:
        return None


def update_correct_answer_in_qti_xml(qti_xml: str, correct_answer: str) -> str:
    """
    Update or add the correct answer in QTI XML.

    Args:
        qti_xml: QTI XML string
        correct_answer: Correct answer identifier (e.g., "ChoiceA")

    Returns:
        Updated QTI XML string
    """
    try:
        root = ET.fromstring(qti_xml)
        QTI_NS = "{http://www.imsglobal.org/xsd/imsqtiasi_v3p0}"

        response_decl = root.find(f".//{QTI_NS}qti-response-declaration")
        if response_decl is None:
            # If no response declaration, return original (shouldn't happen)
            return qti_xml

        correct_response = response_decl.find(f"{QTI_NS}qti-correct-response")
        if correct_response is None:
            # Create correct-response element if missing
            correct_response = ET.SubElement(response_decl, f"{QTI_NS}qti-correct-response")

        qti_value = correct_response.find(f"{QTI_NS}qti-value")
        if qti_value is None:
            # Create value element if missing
            qti_value = ET.SubElement(correct_response, f"{QTI_NS}qti-value")

        qti_value.text = correct_answer

        # Convert back to string
        return ET.tostring(root, encoding="unicode")
    except ET.ParseError:
        # Fallback to regex replacement if XML parsing fails
        # Try to replace existing value
        pattern = (
            r"(<qti-correct-response[^>]*>\s*<qti-value>)"
            r"[^<]+"
            r"(</qti-value>\s*</qti-correct-response>)"
        )
        if re.search(pattern, qti_xml):
            return re.sub(pattern, r"\1" + correct_answer + r"\2", qti_xml)

        # If no correct-response found, try to add it after response-declaration
        pattern = r"(<qti-response-declaration[^>]*>)"
        replacement = r"\1\n    <qti-correct-response>\n      <qti-value>" + correct_answer + "</qti-value>\n    </qti-correct-response>"
        if re.search(pattern, qti_xml):
            return re.sub(pattern, replacement, qti_xml, count=1)

        return qti_xml
    except Exception:
        return qti_xml
