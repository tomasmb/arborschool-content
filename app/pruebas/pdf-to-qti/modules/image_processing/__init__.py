# Image Processing Modules
# Specialized modules for different types of visual content extraction

from .bbox_utils import check_bbox_overlap_with_text, expand_image_bbox_to_boundaries, shrink_image_bbox_away_from_text
from .choice_diagrams import detect_and_extract_choice_diagrams
from .image_detection import (
    assess_pymupdf_image_adequacy,
    detect_images_with_ai,
    expand_pymupdf_bbox_intelligently,
    should_use_ai_image_detection,
)
from .prompt_choice_main import separate_prompt_and_choice_images

__all__ = [
    "detect_and_extract_choice_diagrams",
    "separate_prompt_and_choice_images",
    "should_use_ai_image_detection",
    "detect_images_with_ai",
    "assess_pymupdf_image_adequacy",
    "expand_pymupdf_bbox_intelligently",
    "expand_image_bbox_to_boundaries",
    "check_bbox_overlap_with_text",
    "shrink_image_bbox_away_from_text",
]
