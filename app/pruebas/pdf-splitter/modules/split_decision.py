"""
Split-decision utilities shared by both local (main.py) and production (pdf_processor.py) flows.

This small module holds the logic that decides whether a PDF should be split
into logical parts with the LLM helper.  Centralising the decision keeps local
runs and Lambda runs in sync so behaviour is predictable.
"""

from __future__ import annotations

import os
from typing import Final

# A single place to tweak the page threshold.
# Can be overridden at runtime via the PDF_SPLIT_PAGE_THRESHOLD env-var.
_DEFAULT_THRESHOLD: Final[int] = 40

# Exported constant so callers can print it in log messages.
SPLIT_PAGE_THRESHOLD: Final[int] = int(
    os.getenv("PDF_SPLIT_PAGE_THRESHOLD", _DEFAULT_THRESHOLD)
)


def should_split_pdf(total_pages: int, threshold: int | None = None) -> bool:
    """Return True if the file is considered *large* and should be LLM-split.

    Args:
        total_pages: Number of pages in the input PDF.
        threshold: Optional explicit threshold.  When *None* we use the
                    global *SPLIT_PAGE_THRESHOLD*.
    """
    effective_threshold = threshold if threshold is not None else SPLIT_PAGE_THRESHOLD
    return total_pages > effective_threshold 