"""
Part Validator Module

This module provides functions to validate the results of a PDF segmentation part.
"""

import os
import json
from typing import Dict, Any

def validate_segmentation_results(results: Dict[str, Any], output_dir: str) -> bool:
    """
    Validates the segmentation results for a single part.
    A part is considered invalid if any of its segments (questions, references)
    could not be successfully located in the PDF.
    
    Args:
        results: The segmentation results for the part.
        output_dir: The output directory for the part.
        
    Returns:
        True if the part is valid, False otherwise.
    """
    print("🔎 Validating segmentation results...")

    all_segments_valid = True
    segment_types = ["questions", "multi_question_references", "unrelated_content_segments"]

    for seg_type in segment_types:
        for i, segment in enumerate(results.get(seg_type, [])):
            # The `compute_bboxes_for_segments` function is now responsible for NOT
            # adding a 'bboxes' key if it can't find the segment.
            if "bboxes" not in segment or not segment["bboxes"]:
                segment_id = segment.get('id', f'index_{i}')
                print(f"❌ VALIDATION FAILED: Segment '{segment_id}' (type: {seg_type}) could not be located in the PDF. It is missing bounding box information.")
                all_segments_valid = False

    if all_segments_valid:
        print("✅ Validation successful: All segments were located.")
    else:
        print("❌ Validation failed for one or more segments.")
        # Save the failed results for debugging
        failed_dir = os.path.join(output_dir, "failed")
        os.makedirs(failed_dir, exist_ok=True)
        failed_path = os.path.join(failed_dir, "failed_segmentation_results.json")
        with open(failed_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"💾 Failed segmentation results saved to: {failed_path}")

    return all_segments_valid 