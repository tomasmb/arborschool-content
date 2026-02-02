"""image_detection.py
---------------------
AI-powered visual content detection helpers. This module provides fallback
image detection when the main AI content analyzer is not available or when
additional image area detection is needed.

Following converter guidelines: prefer AI analysis over heuristics.

This module re-exports from specialized submodules for backward compatibility.
The implementation is now split across:
- image_detection_ai.py: AI-powered detection functions
- image_detection_helpers.py: Helper utilities
- image_bbox_construction.py: Bbox construction from gaps
- image_bbox_expansion.py: Intelligent bbox expansion
- image_adequacy.py: Adequacy assessment
"""

from __future__ import annotations

# Re-export all public functions for backward compatibility
from .image_adequacy import assess_pymupdf_image_adequacy
from .image_bbox_construction import construct_image_bbox_from_gaps, detect_potential_image_areas
from .image_bbox_expansion import expand_pymupdf_bbox_intelligently
from .image_detection_ai import detect_images_with_ai, should_use_ai_image_detection

__all__ = [
    "should_use_ai_image_detection",
    "detect_images_with_ai",
    "detect_potential_image_areas",
    "construct_image_bbox_from_gaps",
    "assess_pymupdf_image_adequacy",
    "expand_pymupdf_bbox_intelligently",
]
