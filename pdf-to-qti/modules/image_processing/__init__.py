# Image Processing Modules
# Specialized modules for different types of visual content extraction

from .choice_diagrams import detect_and_extract_choice_diagrams
from .prompt_choice_main import separate_prompt_and_choice_images
from .image_detection import (
    should_use_ai_image_detection,
    detect_images_with_ai, 
    assess_pymupdf_image_adequacy,
    expand_pymupdf_bbox_intelligently
)
from .bbox_utils import (
    expand_image_bbox_to_boundaries,
    check_bbox_overlap_with_text,
    shrink_image_bbox_away_from_text
)

__all__ = [
    'detect_and_extract_choice_diagrams',
    'separate_prompt_and_choice_images',
    'should_use_ai_image_detection',
    'detect_images_with_ai',
    'assess_pymupdf_image_adequacy', 
    'expand_pymupdf_bbox_intelligently',
    'expand_image_bbox_to_boundaries',
    'check_bbox_overlap_with_text',
    'shrink_image_bbox_away_from_text'
] 