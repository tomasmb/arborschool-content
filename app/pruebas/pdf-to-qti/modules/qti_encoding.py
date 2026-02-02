"""
QTI Encoding Utilities

This module handles detection and validation of encoding errors in QTI content.
These errors typically occur when PDF text extraction produces garbled Spanish characters
due to non-standard font mappings.

IMPORTANT: Auto-fixing encoding errors via string replacement is error-prone because
it can match IDs, codes, URLs, etc. The pipeline should reject content with encoding
errors rather than attempt to fix them.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

_logger = logging.getLogger(__name__)


# Mapeo de errores de codificación comunes a caracteres correctos
# Used for DETECTION only - NOT for auto-correction
ENCODING_FIXES: dict[str, str] = {
    # Tildes comunes
    'e1cido': 'ácido',
    'e1tomos': 'átomos',
    'e1tomo': 'átomo',
    'c1cido': 'ácido',
    'c1tomo': 'átomo',
    'oxedgeno': 'oxígeno',
    'hidrf3geno': 'hidrógeno',
    'sulffarico': 'sulfúrico',
    'quedmico': 'químico',
    'informacif3n': 'información',
    'continuacif3n': 'continuación',
    'reflexif3n': 'reflexión',
    'traslacif3n': 'traslación',
    'isome9tricas': 'isométricas',
    've9rtice': 'vértice',
    've9rtices': 'vértices',
    'producif3n': 'producción',
    'tecnolf3gica': 'tecnológica',
    'cumplif3': 'cumplió',
    'Funcif3n': 'Función',
    'razf3n': 'razón',
    'me1s': 'más',
    'd1a': 'día',
    'd1as': 'días',
    'Mi1rcoles': 'Miércoles',
    'Gr1fico': 'Gráfico',

    # Ñ
    'af1o': 'año',
    'af1os': 'años',

    # Signos de interrogación
    'bfCue1l': '¿Cuál',
    'bfcue1l': '¿cuál',
    'bfcue1ntos': '¿cuántos',
    'bfcue1les': '¿cuáles',
    'bfCue': '¿Cu',
    'bfcue': '¿cu',

    # Otros
    'sere1': 'será',
    'produciredan': 'producirían',
    'comenzare1': 'comenzará',
    'restaurare1': 'restaurará',
    'vaceda': 'vacía',

    # Comillas mal codificadas
    'ab bajabb': '"baja"',
    'ab no bajabb': '"no baja"',
    'bfCon cue1l': '¿Con cuál',
    'bfCon': '¿Con',
    'cue1l': 'cuál',

    # Más tildes
    'orge1nicos': 'orgánicos',
    'gre1ficos': 'gráficos',
    'construccif3n': 'construcción',
    'comparacif3n': 'comparación',
    'afirmacif3n': 'afirmación',
    'continfachn': 'continuación',
    'este1n': 'están',
    'este1': 'está',
    'este1 graduados': 'están graduados',
    'este1 escritos': 'están escritos',
    'este1 juntas': 'están juntas',
    'Ilustracif3n': 'Ilustración',
    'ilustracif3n': 'ilustración',
}


def detect_encoding_errors(content: str) -> list[str]:
    """
    Detect encoding error patterns in content.

    These patterns indicate PDF text extraction produced garbled Spanish
    characters. The content should be REJECTED rather than auto-fixed,
    because auto-fixing with string replacements is error-prone and could
    introduce false positives (matching IDs, codes, URLs, etc.).

    Args:
        content: Text content to check (XML or plain text)

    Returns:
        List of found encoding error patterns (empty if clean)
    """
    if not content:
        return []

    found = []
    for pattern in ENCODING_FIXES.keys():
        if pattern in content:
            found.append(pattern)
        elif pattern.capitalize() in content:
            found.append(pattern.capitalize())
        elif pattern.upper() in content:
            found.append(pattern.upper())

    return found


def validate_no_encoding_errors_or_raise(content: str, context: str = "content") -> None:
    """
    Validate that content has no encoding errors. Raises ValueError if errors found.

    This should be called on content to ensure no encoding errors are present.
    If errors are found, the pipeline should reject the content rather than
    attempt auto-correction (which is error-prone).

    Args:
        content: Content to validate
        context: Description of what's being validated (for error message)

    Raises:
        ValueError: If encoding errors are detected
    """
    errors = detect_encoding_errors(content)
    if errors:
        samples = errors[:5]
        raise ValueError(
            f"Encoding errors detected in {context}. "
            f"Found patterns: {samples}. "
            "This indicates PDF text extraction produced garbled Spanish characters. "
            "The source PDF has non-standard font mappings and should be replaced."
        )


def verify_and_fix_encoding(qti_xml: str) -> tuple[str, bool]:
    """
    DEPRECATED: Detects encoding errors but does NOT fix them.

    Auto-fixing encoding errors via string replacement is error-prone
    because it can match IDs, codes, URLs, etc. Instead, this function
    now only DETECTS errors and logs a warning.

    The pipeline should reject content with encoding errors rather than
    attempt to fix them.

    Args:
        qti_xml: The QTI XML to check

    Returns:
        Tuple of (xml_unchanged, encoding_issues_found)
    """
    if not qti_xml:
        return qti_xml, False

    errors = detect_encoding_errors(qti_xml)
    if not errors:
        return qti_xml, False

    # Log warning but do NOT fix - fixing is error-prone
    _logger.warning(
        "Encoding errors detected in QTI XML. "
        "Content should be rejected, not auto-fixed. "
        f"Found {len(errors)} pattern(s): {errors[:5]}"
    )

    # Return unchanged XML with flag indicating errors were found
    # The caller should reject this content
    return qti_xml, True
